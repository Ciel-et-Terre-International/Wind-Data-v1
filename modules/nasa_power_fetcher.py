import os
from datetime import datetime, timedelta
from typing import Union, Optional, Dict, Any

import requests
import pandas as pd
import numpy as np

# NASA POWER daily data (UTC/LST) available starting 1981-01-01.
NASA_POWER_START_DATE = datetime(1981, 1, 1)


def _to_datetime(dt: Union[str, datetime]) -> datetime:
    """Convert input to datetime (expects '%Y-%m-%d' for strings)."""
    if isinstance(dt, datetime):
        return dt
    return datetime.strptime(dt, "%Y-%m-%d")


def _create_empty_period(start_dt: datetime, end_dt: datetime) -> pd.DataFrame:
    """
    Build an empty DataFrame between two dates (inclusive) with the target schema.
    Used to prefix series before NASA coverage starts.
    """
    if end_dt < start_dt:
        return pd.DataFrame(
            columns=[
                "time",
                "windspeed_mean",
                "windspeed_daily_avg",
                "windspeed_gust",
                "wind_direction",
                "u_component_10m",
                "v_component_10m",
                "n_hours",
            ]
        )

    dates = pd.date_range(start=start_dt, end=end_dt, freq="D")

    return pd.DataFrame(
        {
            "time": dates,
            "windspeed_mean": np.nan,
            "windspeed_daily_avg": np.nan,
            "windspeed_gust": np.nan,
            "wind_direction": np.nan,
            "u_component_10m": np.nan,
            "v_component_10m": np.nan,
            # No hourly info before NASA period
            "n_hours": np.nan,
        }
    )


def fetch_nasa_power_data(
    site_name: str,
    site_folder: str,
    lat: float,
    lon: float,
    start_date: Union[str, datetime],
    end_date: Union[str, datetime],
    mean_correction_factor: Optional[float] = None,
    gust_correction_factor: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Fetch NASA POWER (Daily API, RE community) 10 m wind data and return
    a standardized daily CSV.

    Variables (Daily API, point):
      - WS10M      : daily average wind speed at 10 m (m/s)
      - WS10M_MAX  : daily maximum wind speed at 10 m (m/s)
      - WD10M      : daily average wind direction at 10 m (deg)
      - U10M       : eastward wind at 10 m (daily avg, m/s)
      - V10M       : northward wind at 10 m (daily avg, m/s)

    Standardization:
      - Measurement height: 10 m.
      - time-standard=UTC for consistency with other fetchers.
      - windspeed_mean       = WS10M_MAX (daily max mean wind at 10 m).
      - windspeed_daily_avg  = WS10M (daily average wind at 10 m).
      - windspeed_gust       = windspeed_mean * gust_correction_factor when provided, else NaN.
      - wind_direction       = WD10M (degrees 0-360).
      - n_hours              = 24 for days covered by NASA POWER.

    If start_date < 1981-01-01, prefix with empty rows up to 1980-12-31.
    """
    os.makedirs(site_folder, exist_ok=True)

    start_dt = _to_datetime(start_date)
    end_dt = _to_datetime(end_date)

    if end_dt < start_dt:
        raise ValueError("end_date must be >= start_date")

    # Optional prefix before NASA POWER coverage
    df_prefix = None
    start_real_dt = start_dt
    if start_dt < NASA_POWER_START_DATE:
        cutoff_dt = NASA_POWER_START_DATE - timedelta(days=1)
        print("Start date before 1981, adding empty values.")
        df_prefix = _create_empty_period(start_dt, cutoff_dt)
        start_real_dt = NASA_POWER_START_DATE

    start_str = start_real_dt.strftime("%Y%m%d")
    end_str = end_dt.strftime("%Y%m%d")

    parameters = "WS10M,WS10M_MAX,WD10M,U10M,V10M"

    url = (
        "https://power.larc.nasa.gov/api/temporal/daily/point?"
        f"parameters={parameters}"
        f"&community=RE"
        f"&longitude={lon}"
        f"&latitude={lat}"
        f"&start={start_str}"
        f"&end={end_str}"
        f"&format=JSON"
        f"&time-standard=UTC"
    )

    print(f"Calling NASA POWER API (Daily, 10 m) for {site_name}...")
    response = requests.get(url, timeout=60)

    if response.status_code != 200:
        raise RuntimeError(
            f"NASA POWER API error: {response.status_code} - {response.text}"
        )

    data = response.json()
    param = data["properties"]["parameter"]

    if "WS10M" not in param:
        raise KeyError("WS10M missing in NASA POWER response.")

    dates_str = list(param["WS10M"].keys())
    dates_dt = pd.to_datetime(dates_str)

    ws10m = list(param["WS10M"].values())

    if "WS10M_MAX" in param:
        ws10m_max = list(param["WS10M_MAX"].values())
    else:
        print("WS10M_MAX missing in NASA POWER response, falling back to WS10M.")
        ws10m_max = ws10m

    if "WD10M" in param:
        wd10m = list(param["WD10M"].values())
    else:
        print("WD10M missing in NASA POWER response, wind_direction set to NaN.")
        wd10m = [np.nan] * len(dates_dt)

    if "U10M" in param:
        u10m = list(param["U10M"].values())
    else:
        u10m = [np.nan] * len(dates_dt)

    if "V10M" in param:
        v10m = list(param["V10M"].values())
    else:
        v10m = [np.nan] * len(dates_dt)

    df_nasa = pd.DataFrame(
        {
            "time": dates_dt,
            "windspeed_mean": ws10m_max,      # daily max wind at 10 m
            "windspeed_daily_avg": ws10m,     # daily average wind at 10 m
            "windspeed_gust": np.nan,         # built via gust factor if any
            "wind_direction": wd10m,
            "u_component_10m": u10m,
            "v_component_10m": v10m,
        }
    )

    # Apply mean correction if provided
    if mean_correction_factor is not None:
        factor_mean = float(mean_correction_factor)
        df_nasa["windspeed_mean"] = df_nasa["windspeed_mean"] * factor_mean
        df_nasa["windspeed_daily_avg"] = df_nasa["windspeed_daily_avg"] * factor_mean
        df_nasa["mean_correction_factor"] = factor_mean
    else:
        df_nasa["mean_correction_factor"] = 1.0

    # Apply gust factor only as fallback
    if gust_correction_factor is not None:
        factor_gust = float(gust_correction_factor)
        df_nasa["windspeed_gust"] = df_nasa["windspeed_mean"] * factor_gust
        df_nasa["gust_correction_factor"] = factor_gust
    else:
        df_nasa["gust_correction_factor"] = np.nan

    # Metadata
    df_nasa["source"] = "NASA_POWER"
    df_nasa["latitude"] = lat
    df_nasa["longitude"] = lon
    df_nasa["timezone"] = "UTC"
    df_nasa["n_hours"] = 24

    # Concatenate prefix if needed
    if df_prefix is not None:
        df_nasa = pd.concat([df_prefix, df_nasa], ignore_index=True)

    output_path = os.path.join(site_folder, f"nasa_power_{site_name}.csv")
    df_nasa.to_csv(output_path, index=False)

    print(f"NASA POWER daily CSV saved: {output_path}")

    return {"filename": os.path.basename(output_path), "filepath": output_path}
