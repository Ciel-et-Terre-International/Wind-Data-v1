import cdsapi
import os
import zipfile
import pandas as pd
import numpy as np
from datetime import datetime


def read_era5_csv(filepath):
    """
    Read an ERA5 timeseries CSV (reanalysis-era5-single-levels-timeseries)
    with at least:
        - valid_time (or time)
        - u10, v10

    ERA5 conventions:
        - u10, v10 in m/s at 10 m height.
        - Time in UTC (valid_time).

    Computed columns:
        - time (UTC datetime)
        - windspeed_10m = sqrt(u10^2 + v10^2)  [m/s]
        - wind_direction: meteorological direction (deg) from which the wind blows,
          computed from u10, v10 via atan2(-u, -v).

    Returns DataFrame with:
        - time (datetime64[ns, UTC])
        - u10, v10 (m/s)
        - windspeed_10m (m/s)
        - wind_direction (deg)
    """
    df = pd.read_csv(filepath)

    # Time column: valid_time or time
    if "valid_time" in df.columns:
        time_col = "valid_time"
    elif "time" in df.columns:
        time_col = "time"
    else:
        raise ValueError(
            "No 'valid_time' or 'time' column found in ERA5 CSV."
        )

    df = df.rename(columns={time_col: "time"})

    # Convert to datetime UTC
    df["time"] = pd.to_datetime(df["time"], errors="coerce", utc=True)

    # u10 / v10 columns (standard ERA5 output for 10m components)
    for comp in ["u10", "v10"]:
        if comp not in df.columns:
            raise ValueError(f"Missing '{comp}' column in ERA5 CSV.")
        df[comp] = df[comp].astype(float)

    # 10 m wind speed
    df["windspeed_10m"] = np.sqrt(df["u10"] ** 2 + df["v10"] ** 2)

    # Meteorological direction (0° = north, 90° = east, etc.), wind coming from that angle
    # ECMWF convention: u = -|V| sin(phi), v = -|V| cos(phi)  =>  phi = atan2(-u, -v)
    phi_deg = np.rad2deg(np.arctan2(-df["u10"], -df["v10"]))
    df["wind_direction"] = (phi_deg + 360.0) % 360.0

    # Drop rows without valid time
    df = df.dropna(subset=["time"])

    return df[["time", "u10", "v10", "windspeed_10m", "wind_direction"]]


def _aggregate_era5_daily(
    hourly_df,
    lat=None,
    lon=None,
    mean_correction_factor=None,
    gust_correction_factor=None,
):
    """
    Aggregate ERA5 hourly data (u10, v10, windspeed_10m, wind_direction)
    into standardized daily data for the stats pipeline.
    """
    df = hourly_df.copy()
    df["date"] = df["time"].dt.date

    grouped = df.groupby("date")

    daily_speed_avg = grouped["windspeed_10m"].mean()
    daily_speed_max = grouped["windspeed_10m"].max()

    u_mean = grouped["u10"].mean()
    v_mean = grouped["v10"].mean()
    phi_daily = np.rad2deg(np.arctan2(-u_mean, -v_mean))
    daily_direction = (phi_daily + 360.0) % 360.0

    n_hours = grouped.size()

    daily_df = pd.DataFrame(
        {
            "time": pd.to_datetime(daily_speed_max.index),
            "windspeed_mean": daily_speed_max.values,         # daily max
            "windspeed_daily_avg": daily_speed_avg.values,    # daily average
            "wind_direction": daily_direction.values,
            "windspeed_gust": np.nan,                         # no dedicated gusts here
            "n_hours": n_hours.values,
        }
    )

    if mean_correction_factor is not None:
        daily_df["windspeed_mean"] = (
            daily_df["windspeed_mean"] * float(mean_correction_factor)
        )
        daily_df["windspeed_daily_avg"] = (
            daily_df["windspeed_daily_avg"] * float(mean_correction_factor)
        )
        daily_df["mean_correction_factor"] = float(mean_correction_factor)
    else:
        daily_df["mean_correction_factor"] = 1.0

    if gust_correction_factor is not None:
        factor = float(gust_correction_factor)
        mask_nan = daily_df["windspeed_gust"].isna()
        if mask_nan.any():
            print(
                f"[ERA5] Applying gust_correction_factor={factor} to create "
                "pseudo-gusts from windspeed_mean."
            )
            daily_df.loc[mask_nan, "windspeed_gust"] = (
                daily_df.loc[mask_nan, "windspeed_mean"] * factor
            )
        daily_df["gust_correction_factor"] = factor
    else:
        daily_df["gust_correction_factor"] = 1.0

    daily_df["source"] = "era5"
    daily_df["latitude"] = float(lat) if lat is not None else np.nan
    daily_df["longitude"] = float(lon) if lon is not None else np.nan
    daily_df["elevation"] = np.nan
    daily_df["timezone"] = "UTC"
    daily_df["utc_offset_seconds"] = 0
    daily_df["model"] = "ERA5"

    return daily_df


def save_era5_daily(site_name, site_folder, hourly_df):
    """
    Legacy helper kept for compatibility:

    - Aggregate ERA5 hourly DataFrame (from read_era5_csv)
      into daily data with standardized columns.
    - Save to `era5_daily_{site_name}.csv` in site_folder.
    - Lat/lon are left as NaN (not provided here).
    """
    os.makedirs(site_folder, exist_ok=True)

    daily_df = _aggregate_era5_daily(hourly_df)

    filename = f"era5_daily_{site_name}.csv"
    filepath = os.path.join(site_folder, filename)
    daily_df.to_csv(filepath, index=False)

    return filepath


def save_era5_data(
    site_name,
    site_folder,
    lat,
    lon,
    start_date,
    end_date,
    mean_correction_factor=None,
    gust_correction_factor=None,
):
    """
    Download ERA5 timeseries (reanalysis-era5-single-levels-timeseries)
    for a site and format them for the analysis pipeline.

    Dataset:
        "reanalysis-era5-single-levels-timeseries"
    Variables:
        - 10m_u_component_of_wind  -> u10 (m/s)
        - 10m_v_component_of_wind  -> v10 (m/s)
    Time:
        - Hourly series in UTC (valid_time).

    Saves:
        * era5_{site_name}.csv        (hourly)
        * era5_daily_{site_name}.csv  (daily)
    """
    print(f"[ERA5] Downloading timeseries for {site_name}...")

    os.makedirs(site_folder, exist_ok=True)
    dataset = "reanalysis-era5-single-levels-timeseries"
    request = {
        "variable": [
            "10m_u_component_of_wind",
            "10m_v_component_of_wind",
        ],
        "location": {
            "longitude": float(lon),
            "latitude": float(lat),
        },
        "date": f"{start_date}/{end_date}",
        "data_format": "csv",
    }

    temp_zip = os.path.join(site_folder, f"era5_temp_{site_name}.zip")

    try:
        c = cdsapi.Client()
    except Exception as e:
        print(f"[ERA5] Error creating CDSAPI client: {e}")
        return None

    try:
        result = c.retrieve(dataset, request)
        result.download(temp_zip)
    except Exception as e:
        print(f"[ERA5] ERA5 API error: {e}")
        return None

    try:
        with zipfile.ZipFile(temp_zip, "r") as zip_ref:
            zip_ref.extractall(site_folder)
            extracted_files = zip_ref.namelist()

        csv_files = [f for f in extracted_files if f.endswith(".csv")]
        if not csv_files:
            raise Exception("No CSV file found in downloaded ERA5 ZIP.")

        temp_csv = os.path.join(site_folder, csv_files[0])

        # Hourly raw data
        df_hourly_raw = read_era5_csv(temp_csv)
        if df_hourly_raw.empty:
            print("[ERA5] ERA5 file empty after processing.")
            return None

        # Add windspeed_mean (hourly) for the raw file
        df_hourly = df_hourly_raw.copy()
        df_hourly["windspeed_mean"] = df_hourly["windspeed_10m"]

        if mean_correction_factor is not None:
            df_hourly["windspeed_mean"] = (
                df_hourly["windspeed_mean"] * float(mean_correction_factor)
            )
            df_hourly["mean_correction_factor"] = float(mean_correction_factor)
        else:
            df_hourly["mean_correction_factor"] = 1.0

        # Simple metadata on hourly file
        df_hourly["source"] = "era5"
        df_hourly["latitude"] = float(lat)
        df_hourly["longitude"] = float(lon)
        df_hourly["timezone"] = "UTC"
        df_hourly["utc_offset_seconds"] = 0
        df_hourly["model"] = "ERA5"

        final_csv = os.path.join(site_folder, f"era5_{site_name}.csv")
        df_hourly.to_csv(final_csv, index=False)

        # Daily aggregation
        df_daily = _aggregate_era5_daily(
            df_hourly_raw,
            lat=lat,
            lon=lon,
            mean_correction_factor=mean_correction_factor,
            gust_correction_factor=gust_correction_factor,
        )

        daily_csv = os.path.join(site_folder, f"era5_daily_{site_name}.csv")
        df_daily.to_csv(daily_csv, index=False)
        print(f"[ERA5] Daily file generated: {daily_csv}")
        print(f"[ERA5] Hourly file generated: {final_csv}")

        os.remove(temp_csv)
        os.remove(temp_zip)

        return {
            "filename": os.path.basename(final_csv),
            "filepath": final_csv,
            "filepath_daily": daily_csv,
            "latitude": lat,
            "longitude": lon,
        }

    except Exception as e:
        print(f"[ERA5] ERA5 processing error: {e}")
        return None
