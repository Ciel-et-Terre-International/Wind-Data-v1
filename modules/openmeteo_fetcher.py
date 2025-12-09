import os
from datetime import datetime

import numpy as np
import pandas as pd
import requests


def fetch_openmeteo_data(
    lat,
    lon,
    start_date,
    end_date,
    model=None,
    gust_correction_factor=None,
    mean_correction_factor=None,
):
    """
    Download Open-Meteo hourly data (archive API) and build standardized
    daily aggregates for the statistics engine.

    Key assumptions (Open-Meteo docs):
    - Hourly variables (all at 10 m):
        * wind_speed_10m     : instantaneous model wind speed at the given hour
        * wind_direction_10m : instantaneous direction (deg)
        * wind_gusts_10m     : max gust over the previous hour
    - Units: m/s via wind_speed_unit=ms.
    - Timezone: UTC for consistency with other sources.

    Daily aggregates produced:
        * windspeed_mean      : daily MAX of wind_speed_10m (m/s)
        * windspeed_daily_avg : daily average of wind_speed_10m (m/s)
        * wind_direction      : daily vector-mean direction (deg)
        * windspeed_gust      : daily MAX of wind_gusts_10m (m/s)
        * n_hours             : number of hourly samples per day

    Optional factors:
    - mean_correction_factor: multiply windspeed_mean and windspeed_daily_avg by this factor.
    - gust_correction_factor: if provided, only used as fallback when daily gust is NaN
      (windspeed_gust = factor * windspeed_mean). Existing gusts are not modified.
    """
    base_url = "https://archive-api.open-meteo.com/v1/archive"
    model_param = f"&models={model}" if model else ""

    url_hourly = (
        f"{base_url}?latitude={lat}&longitude={lon}"
        f"&start_date={start_date}&end_date={end_date}"
        f"&hourly=wind_speed_10m,wind_direction_10m,wind_gusts_10m"
        f"&wind_speed_unit=ms"
        f"&timezone=UTC{model_param}"
    )

    print(f"Open-Meteo API call (hourly): {url_hourly}")
    response_hourly = requests.get(url_hourly)
    if response_hourly.status_code != 200:
        raise Exception(
            f"Open-Meteo API error (hourly): {response_hourly.status_code} - {response_hourly.text}"
        )

    data_hourly_json = response_hourly.json()
    data_hourly = data_hourly_json.get("hourly", {})
    if not data_hourly:
        raise ValueError("Open-Meteo hourly response missing 'hourly' block.")

    df_hourly = pd.DataFrame(data_hourly)
    if df_hourly.empty:
        raise ValueError("Open-Meteo hourly response empty after DataFrame conversion.")

    expected_cols = {"time", "wind_speed_10m", "wind_direction_10m"}
    missing_cols = expected_cols - set(df_hourly.columns)
    if missing_cols:
        raise ValueError(f"Missing columns in Open-Meteo hourly response: {missing_cols}")

    if "wind_gusts_10m" not in df_hourly.columns:
        df_hourly["wind_gusts_10m"] = np.nan

    df_hourly["time"] = pd.to_datetime(df_hourly["time"], utc=True)

    # Daily aggregates
    df_hourly["date"] = df_hourly["time"].dt.date

    dir_rad = np.deg2rad(df_hourly["wind_direction_10m"].astype(float))
    df_hourly["dir_u"] = np.cos(dir_rad)
    df_hourly["dir_v"] = np.sin(dir_rad)

    grouped = df_hourly.groupby("date")

    daily_speed_max = grouped["wind_speed_10m"].max()
    daily_speed_avg = grouped["wind_speed_10m"].mean()

    u_mean = grouped["dir_u"].mean()
    v_mean = grouped["dir_v"].mean()
    daily_direction_mean = np.rad2deg(np.arctan2(v_mean, u_mean))
    daily_direction_mean = (daily_direction_mean + 360.0) % 360.0

    daily_gust_max = grouped["wind_gusts_10m"].max()
    n_hours = grouped.size()

    df_daily_agg = pd.DataFrame(
        {
            "time": daily_speed_max.index,
            "windspeed_mean": daily_speed_max.values,
            "windspeed_daily_avg": daily_speed_avg.values,
            "wind_direction": daily_direction_mean.values,
            "windspeed_gust": daily_gust_max.values,
            "n_hours": n_hours.values,
        }
    )

    df_daily_agg["time"] = pd.to_datetime(df_daily_agg["time"])

    if mean_correction_factor is not None:
        factor_mean = float(mean_correction_factor)
        print(f"Applying mean correction factor: x{factor_mean}")
        df_daily_agg["windspeed_mean"] *= factor_mean
        df_daily_agg["windspeed_daily_avg"] *= factor_mean
        df_daily_agg["mean_correction_factor"] = factor_mean
    else:
        df_daily_agg["mean_correction_factor"] = 1.0

    if gust_correction_factor is not None:
        factor = float(gust_correction_factor)
        mask_nan = df_daily_agg["windspeed_gust"].isna()
        if mask_nan.any():
            print(
                f"Applying gust_correction_factor={factor} on days without gusts "
                "(windspeed_gust NaN) using windspeed_mean."
            )
            df_daily_agg.loc[mask_nan, "windspeed_gust"] = (
                df_daily_agg.loc[mask_nan, "windspeed_mean"] * factor
            )
        df_daily_agg["gust_correction_factor"] = factor
    else:
        df_daily_agg["gust_correction_factor"] = 1.0

    timezone = data_hourly_json.get("timezone", "UTC")
    utc_offset_seconds = data_hourly_json.get("utc_offset_seconds", 0)
    elevation = data_hourly_json.get("elevation", np.nan)
    meta_lat = data_hourly_json.get("latitude", lat)
    meta_lon = data_hourly_json.get("longitude", lon)

    df_daily_agg["source"] = "open-meteo"
    df_daily_agg["latitude"] = float(meta_lat)
    df_daily_agg["longitude"] = float(meta_lon)
    df_daily_agg["elevation"] = float(elevation) if pd.notnull(elevation) else np.nan
    df_daily_agg["timezone"] = timezone
    df_daily_agg["utc_offset_seconds"] = int(utc_offset_seconds)
    df_daily_agg["model"] = model if model is not None else ""

    print("Open-Meteo data downloaded and aggregated successfully (v1-audit).")
    return df_daily_agg


def save_openmeteo_data(
    site_name,
    site_folder,
    lat,
    lon,
    start_date,
    end_date,
    model=None,
    gust_correction_factor=None,
    mean_correction_factor=None,
):
    """
    Convenience wrapper:
    - calls fetch_openmeteo_data(...)
    - saves CSV in the site folder
    - returns a summary dict (filename, path, coordinates)
    """
    os.makedirs(site_folder, exist_ok=True)

    df = fetch_openmeteo_data(
        lat=lat,
        lon=lon,
        start_date=start_date,
        end_date=end_date,
        model=model,
        gust_correction_factor=gust_correction_factor,
        mean_correction_factor=mean_correction_factor,
    )

    filename = f"openmeteo_{site_name}.csv"
    filepath = os.path.join(site_folder, filename)
    df.to_csv(filepath, index=False)

    print(f"Open-Meteo CSV saved: {filepath}")
    return {
        "filename": filename,
        "filepath": filepath,
        "latitude": lat,
        "longitude": lon,
    }
