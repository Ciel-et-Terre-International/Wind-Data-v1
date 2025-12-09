# noaa_isd_fetcher.py

import os
import pandas as pd
import numpy as np
from tqdm import tqdm


def fetch_isd_series(
    usaf,
    wban,
    years,
    output_dir,
    site_name="site",
    verbose=False,
    return_raw=False,
    station_rank=None,
    gust_correction_factor=None,
    mean_correction_factor=None,
    station_metadata=None,
):
    """
    Download NOAA ISD (Global Hourly CSV) hourly data and aggregate to daily
    with the standardized columns used by the analysis.

    Technical references:
    - DATE/time: observation time in UTC.
    - WND (WIND-OBSERVATION speed rate): speed in m/s with scale factor 10,
      so speed_m/s = value / 10.

    Assumptions and conventions:
    - CSV files read from:
      https://www.ncei.noaa.gov/data/global-hourly/access/{year}/{usaf}{wban}.csv
    - Columns used:
        * DATE : timestamp (UTC)
        * WND  : raw direction + wind speed (tenths of m/s)
        * GUST : gust (tenths of m/s) when present
        * DRCT : wind direction (deg) when present
    - Always convert speeds to m/s.

    Daily aggregates produced:
        * time                : date (UTC, naive)
        * windspeed_mean      : daily MAX of hourly speed (m/s)
        * windspeed_daily_avg : daily average of hourly speed (m/s)
        * wind_direction      : daily vector-mean direction (deg)
        * windspeed_gust      : daily MAX of hourly gusts (m/s)
        * n_hours             : number of hourly samples used

    Optional factors:
    - mean_correction_factor:
        * If provided (float), multiply windspeed_mean AND windspeed_daily_avg
          by this factor (e.g., empirical correction).
    - gust_correction_factor:
        * NOAA provides gusts via GUST.
        * If gust_correction_factor is None:
            - use daily gusts as-is (max of GUST).
        * If gust_correction_factor is provided:
            - do NOT modify existing gusts (non-NaN),
            - when windspeed_gust is NaN, fill fallback:
              windspeed_gust = gust_correction_factor * windspeed_mean.

    Optional metadata:
    - station_metadata: optional dict from noaa_station_finder, may contain:
        {
            "name": str,
            "country": str,
            "latitude": float,
            "longitude": float,
            "elevation_m": float,
            "distance_km": float,
            ...
        }
    """
    base_url = "https://www.ncei.noaa.gov/data/global-hourly/access"
    all_data = []

    if station_rank:
        print(
            f"Downloading NOAA ISD data for station {station_rank} ({usaf}-{wban})"
        )

    years = list(years)
    print(f"Downloading NOAA files {usaf}-{wban} across {len(years)} year(s)...")

    for i, year in enumerate(tqdm(years, desc=f"{usaf}-{wban}", ncols=80), 1):
        file_url = f"{base_url}/{year}/{usaf}{wban}.csv"
        if verbose:
            print(f"  -> {i}/{len(years)} : {file_url}")

        try:
            df = pd.read_csv(file_url)
        except Exception as e:
            if verbose:
                print(f"Error for {usaf}-{wban} {year}: {e}")
            continue

        if "DATE" not in df.columns or "WND" not in df.columns:
            if verbose:
                print(
                    f"Missing 'DATE' or 'WND' columns for {usaf}-{wban} in {year}"
                )
            continue

        # DATE to datetime (UTC) per ISD docs
        df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce", utc=True)
        df = df.dropna(subset=["DATE"])
        df["date"] = df["DATE"].dt.date

        # Parse WND column: "dir,dir_qc,speed,speed_qc,type"
        parsed = df["WND"].astype(str).str.split(",", expand=True)
        df["wind_dir_raw"] = pd.to_numeric(parsed[0], errors="coerce")

        # Speed in tenths of m/s -> m/s
        df["wind_speed"] = pd.to_numeric(parsed[3], errors="coerce") / 10.0
        # Filter outliers
        df["wind_speed"] = df["wind_speed"].mask(
            (df["wind_speed"] > 100) | (df["wind_speed"] < 0)
        )

        # Gusts: GUST column in tenths of m/s
        if "GUST" in df.columns:
            df["windspeed_gust"] = pd.to_numeric(df["GUST"], errors="coerce") / 10.0
            df["windspeed_gust"] = df["windspeed_gust"].mask(
                (df["windspeed_gust"] > 150) | (df["windspeed_gust"] < 0)
            )
        else:
            df["windspeed_gust"] = np.nan

        # Direction: DRCT takes precedence, otherwise raw WND direction
        if "DRCT" in df.columns:
            df["wind_direction"] = pd.to_numeric(df["DRCT"], errors="coerce")
        else:
            df["wind_direction"] = df["wind_dir_raw"]

        # Filter invalid directions (999, <0, >360)
        df["wind_direction"] = df["wind_direction"].mask(
            (df["wind_direction"] > 360)
            | (df["wind_direction"] < 0)
            | (df["wind_direction"] == 999)
        )

        # Keep only columns needed for aggregation
        subset = df[["DATE", "date", "wind_speed", "windspeed_gust", "wind_direction"]].copy()
        subset = subset.rename(columns={"DATE": "time"})
        all_data.append(subset)

    if not all_data:
        print(f"No data retrieved for station {usaf}-{wban}.")
        return None

    # Merge years
    full_df = pd.concat(all_data, ignore_index=True)

    if return_raw:
        full_df = full_df.sort_values("time").reset_index(drop=True)
        return full_df

    # Daily aggregation
    full_df["date"] = pd.to_datetime(full_df["date"])
    full_df_speed = full_df.dropna(subset=["wind_speed"]).copy()
    grouped = full_df_speed.groupby("date", sort=True)

    daily_speed_max = grouped["wind_speed"].max()
    daily_speed_avg = grouped["wind_speed"].mean()
    daily_gust_max = grouped["windspeed_gust"].max()
    n_hours = grouped.size()

    # Vector-mean direction (only valid directions)
    df_dir = full_df_speed.dropna(subset=["wind_direction"]).copy()
    if not df_dir.empty:
        rad = np.deg2rad(df_dir["wind_direction"].astype(float))
        df_dir["u"] = np.cos(rad)
        df_dir["v"] = np.sin(rad)
        grouped_dir = df_dir.groupby("date", sort=True)
        u_mean = grouped_dir["u"].mean()
        v_mean = grouped_dir["v"].mean()
        dir_deg = np.rad2deg(np.arctan2(v_mean, u_mean))
        dir_deg = (dir_deg + 360.0) % 360.0
        daily_direction = dir_deg.reindex(daily_speed_max.index)
    else:
        daily_direction = pd.Series(
            index=daily_speed_max.index, data=np.nan, dtype=float
        )

    daily_df = pd.DataFrame(
        {
            "time": pd.to_datetime(daily_speed_max.index),
            "windspeed_mean": daily_speed_max.values,
            "windspeed_daily_avg": daily_speed_avg.values,
            "wind_direction": daily_direction.values,
            "windspeed_gust": daily_gust_max.values,
            "n_hours": n_hours.values,
        }
    )

    # Mean correction factor (optional)
    if mean_correction_factor is not None:
        factor_mean = float(mean_correction_factor)
        if verbose:
            print(
                f"Applying mean_correction_factor={factor_mean} "
                "to windspeed_mean and windspeed_daily_avg."
            )
        daily_df["windspeed_mean"] = daily_df["windspeed_mean"] * factor_mean
        daily_df["windspeed_daily_avg"] = (
            daily_df["windspeed_daily_avg"] * factor_mean
        )
        daily_df["mean_correction_factor"] = factor_mean
    else:
        daily_df["mean_correction_factor"] = 1.0

    # Gust correction factor (fallback only)
    if gust_correction_factor is not None:
        factor_gust = float(gust_correction_factor)
        mask_nan = daily_df["windspeed_gust"].isna()
        if mask_nan.any() and verbose:
            print(
                f"Applying gust_correction_factor={factor_gust} "
                "on days without gusts (NaN) using windspeed_mean."
            )
        daily_df.loc[mask_nan, "windspeed_gust"] = (
            daily_df.loc[mask_nan, "windspeed_mean"] * factor_gust
        )
        daily_df["gust_correction_factor"] = factor_gust
    else:
        daily_df["gust_correction_factor"] = 1.0

    # Metadata
    meta = station_metadata or {}

    daily_df["source"] = "noaa-isd"
    daily_df["usaf"] = usaf
    daily_df["wban"] = wban
    daily_df["station_id"] = f"{usaf}-{wban}"

    daily_df["station_name"] = meta.get("name", "")
    daily_df["country"] = meta.get("country", "")

    daily_df["station_latitude"] = float(meta["latitude"]) if "latitude" in meta else np.nan
    daily_df["station_longitude"] = float(meta["longitude"]) if "longitude" in meta else np.nan
    daily_df["station_elevation"] = float(meta["elevation_m"]) if "elevation_m" in meta else np.nan
    daily_df["station_distance_km"] = (
        float(meta["distance_km"]) if "distance_km" in meta else np.nan
    )

    daily_df["timezone"] = "UTC"
    daily_df["utc_offset_seconds"] = 0

    # Save daily CSV
    os.makedirs(output_dir, exist_ok=True)
    rank = station_rank if station_rank is not None else "X"
    final_csv = os.path.join(output_dir, f"noaa_station{rank}_{site_name}.csv")
    daily_df.to_csv(final_csv, index=False)

    if verbose:
        print(f"\nNOAA ISD daily CSV saved to {final_csv}")
        print(
            "   Main columns: time, windspeed_mean, windspeed_daily_avg, "
            "wind_direction, windspeed_gust, n_hours"
        )

    return daily_df
