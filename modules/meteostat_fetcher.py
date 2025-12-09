import os
from datetime import datetime

import numpy as np
import pandas as pd
from geopy.distance import geodesic
from meteostat import Stations, Hourly


def get_nearest_stations_info(lat, lon, limit=2):
    """
    Return the closest Meteostat stations for a given site.

    Output structure:
        {
            "station1": {
                "id": ...,
                "name": ...,
                "distance_km": ...,
                "latitude": ...,
                "longitude": ...,
                "elevation": ...,
                "timezone": ...
            },
            "station2": { ... },
            ...
        }
    """
    stations = Stations().nearby(lat, lon)
    results = stations.fetch(limit)

    info = {}
    for i, (index, row) in enumerate(results.iterrows(), 1):
        dist = geodesic((lat, lon), (row["latitude"], row["longitude"])).km
        info[f"station{i}"] = {
            "id": index,
            "name": row.get("name", ""),
            "distance_km": round(dist, 2),
            "latitude": float(row["latitude"]),
            "longitude": float(row["longitude"]),
            "elevation": float(row["elevation"]) if not pd.isna(row.get("elevation")) else np.nan,
            "timezone": row.get("timezone", "UTC"),
        }
    return info


def _fetch_meteostat_daily_for_station(
    station_id,
    lat,
    lon,
    start_date,
    end_date,
    mean_correction_factor=None,
    gust_correction_factor=None,
    station_meta=None,
):
    """
    Download Meteostat hourly data for ONE station, aggregate by day,
    and format to the standard schema for the stats engine.

    Using Meteostat Hourly (timezone=UTC) we expect:
        - wspd : hourly wind speed (km/h, mean over the hour)
        - wpgt : hourly gust max (km/h)
        - wdir : hourly wind direction (deg)

    Conventions:
        - Always convert km/h to m/s (/3.6).
        - Daily aggregates:
            * windspeed_mean      : daily MAX of hourly speeds (m/s)
            * windspeed_daily_avg : daily average of hourly speeds (m/s)
            * windspeed_gust      : daily MAX of hourly gusts (m/s)
            * wind_direction      : daily vector-mean direction (deg)
            * n_hours             : number of hourly samples

    Optional factors:
        - mean_correction_factor:
            * multiply windspeed_mean AND windspeed_daily_avg by this factor (e.g., 1h->10min correction).
        - gust_correction_factor:
            * Meteostat already provides gusts via wpgt.
            * If gust_correction_factor is None:
                - use existing gusts (max of wpgt_ms).
            * If gust_correction_factor is provided:
                - do NOT change existing gusts (non-NaN),
                - when windspeed_gust is NaN, fill fallback = gust_correction_factor * windspeed_mean.
    """
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    # Hourly data (timezone=UTC for alignment)
    data = Hourly(station_id, start, end, timezone="UTC")
    df = data.fetch().reset_index()  # index 'time' to column 'time'

    if df.empty:
        print(f"No hourly data for Meteostat station {station_id}")
        return pd.DataFrame()

    # Expected columns
    required_cols = {"time", "wspd", "wpgt", "wdir"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(
            f"Missing columns in Meteostat Hourly for station {station_id}: {missing}"
        )

    df["time"] = pd.to_datetime(df["time"], utc=True)

    # Convert km/h to m/s
    df["wspd_ms"] = df["wspd"].astype(float) / 3.6
    df["wpgt_ms"] = df["wpgt"].astype(float) / 3.6

    # Direction for vector mean
    dir_rad = np.deg2rad(df["wdir"].astype(float))
    df["dir_u"] = np.cos(dir_rad)
    df["dir_v"] = np.sin(dir_rad)

    # Daily grouping
    df["date"] = df["time"].dt.date
    grouped = df.groupby("date")

    daily_speed_max = grouped["wspd_ms"].max()
    daily_speed_avg = grouped["wspd_ms"].mean()
    daily_gust_max = grouped["wpgt_ms"].max()

    u_mean = grouped["dir_u"].mean()
    v_mean = grouped["dir_v"].mean()
    daily_direction = np.rad2deg(np.arctan2(v_mean, u_mean))
    daily_direction = (daily_direction + 360.0) % 360.0

    n_hours = grouped.size()

    daily_df = pd.DataFrame(
        {
            "time": pd.to_datetime(daily_speed_max.index),
            "windspeed_mean": daily_speed_max.values,          # daily max of hourly means
            "windspeed_daily_avg": daily_speed_avg.values,     # daily average of hourly means
            "wind_direction": daily_direction.values,
            "windspeed_gust": daily_gust_max.values,           # daily max of hourly gusts
            "n_hours": n_hours.values,
        }
    )

    # Optional correction on mean speeds
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

    # Optional gust fallback factor (only for NaN gusts)
    if gust_correction_factor is not None:
        factor = float(gust_correction_factor)
        mask_nan = daily_df["windspeed_gust"].isna()
        if mask_nan.any():
            print(
                f"[Meteostat] Applying gust_correction_factor={factor} on days "
                "without gusts (NaN) using windspeed_mean as fallback."
            )
            daily_df.loc[mask_nan, "windspeed_gust"] = (
                daily_df.loc[mask_nan, "windspeed_mean"] * factor
            )
        daily_df["gust_correction_factor"] = factor
    else:
        daily_df["gust_correction_factor"] = 1.0

    # Metadata
    meta = station_meta or {}
    daily_df["source"] = "meteostat"
    daily_df["station_id"] = station_id
    daily_df["station_name"] = meta.get("name", "")
    daily_df["station_latitude"] = meta.get("latitude", np.nan)
    daily_df["station_longitude"] = meta.get("longitude", np.nan)
    daily_df["station_distance_km"] = meta.get("distance_km", np.nan)
    daily_df["station_elevation"] = meta.get("elevation", np.nan)
    daily_df["timezone"] = meta.get("timezone", "UTC")

    return daily_df


def fetch_meteostat_data(
    site_name,
    site_folder,
    lat,
    lon,
    start_date,
    end_date,
    station_ids=None,
    mean_correction_factor=None,
    gust_correction_factor=None,
):
    """
    High-level wrapper to fetch Meteostat for one or two stations.

    Returns a dict with keys meteostat1 / meteostat2 when available.
    """
    if station_ids is None:
        station_ids = []

    data = {}
    station_meta = get_nearest_stations_info(lat, lon, limit=max(2, len(station_ids)))

    for i, station_id in enumerate(station_ids[:2], 1):
        meta = station_meta.get(f"station{i}", {})
        daily_df = _fetch_meteostat_daily_for_station(
            station_id=station_id,
            lat=lat,
            lon=lon,
            start_date=start_date,
            end_date=end_date,
            mean_correction_factor=mean_correction_factor,
            gust_correction_factor=gust_correction_factor,
            station_meta=meta,
        )
        # Save CSV
        filename = f"meteostat{i}_{site_name}.csv"
        filepath = os.path.join(site_folder, filename)
        daily_df.to_csv(filepath, index=False)
        print(f"Saved Meteostat station{i} daily CSV: {filepath}")
        data[f"meteostat{i}"] = daily_df

    return data
