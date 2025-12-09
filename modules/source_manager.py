# source_manager.py
import os
import pandas as pd

from modules.meteostat_fetcher import fetch_meteostat_data
from modules.era5_fetcher import save_era5_data
from modules.nasa_power_fetcher import fetch_nasa_power_data
from modules.openmeteo_fetcher import save_openmeteo_data


def fetch_observed_sources(
    site_info,
    site_name,
    site_folder,
    lat,
    lon,
    start_date,
    end_date,
    meteostat_id1=None,
    meteostat_id2=None,
):
    observed = {}

    # Meteostat Station 1
    try:
        if meteostat_id1:
            df_meteo = fetch_meteostat_data(
                site_name,
                site_folder,
                lat,
                lon,
                start_date,
                end_date,
                station_ids=[meteostat_id1],
            )
            df1 = df_meteo.get("meteostat1")
            if df1 is not None and not df1.empty:
                observed["meteostat1"] = {"data": df1, "station_id": meteostat_id1}
            else:
                print(f"Meteostat station1 data ({meteostat_id1}) missing.")
    except Exception as e:
        print(f"Meteostat 1 error: {e}")

    # Meteostat Station 2
    try:
        if meteostat_id2:
            df_meteo = fetch_meteostat_data(
                site_name,
                site_folder,
                lat,
                lon,
                start_date,
                end_date,
                station_ids=[meteostat_id2],
            )
            df2 = df_meteo.get("meteostat1")
            if df2 is not None and not df2.empty:
                observed["meteostat2"] = {"data": df2, "station_id": meteostat_id2}
            else:
                print(f"Meteostat station2 data ({meteostat_id2}) missing.")
    except Exception as e:
        print(f"Meteostat 2 error: {e}")

    return observed


def fetch_model_source(
    site_info,
    site_name,
    site_folder,
    lat,
    lon,
    start_date,
    end_date,
    openmeteo_model=None,
    gust_correction_factor=None,
):
    model = {}

    # Open-Meteo with optional model and gust factor
    try:
        df_openmeteo = save_openmeteo_data(
            site_name,
            site_folder,
            lat,
            lon,
            start_date,
            end_date,
            model=openmeteo_model,
            gust_correction_factor=gust_correction_factor,
        )
        if df_openmeteo and os.path.exists(df_openmeteo["filepath"]):
            df = pd.read_csv(df_openmeteo["filepath"])
            model["openmeteo"] = {"data": df}
        else:
            print("No OpenMeteo data retrieved.")
    except Exception as e:
        print(f"OpenMeteo error: {e}")

    # NASA POWER
    try:
        df_nasa_result = fetch_nasa_power_data(site_name, site_folder, lat, lon, start_date, end_date)
        if df_nasa_result and os.path.exists(df_nasa_result["filepath"]):
            df = pd.read_csv(df_nasa_result["filepath"])
            model["nasa_power"] = {"data": df}
        else:
            print("Empty dataset for NASA POWER")
    except Exception as e:
        print(f"NASA POWER error: {e}")

    # ERA5 with cached files
    try:
        filepath = os.path.join(site_folder, f"era5_{site_name}.csv")
        dailypath = os.path.join(site_folder, f"era5_daily_{site_name}.csv")
        if os.path.exists(filepath) and os.path.exists(dailypath):
            print(f"ERA5 files already present - reading directly: {filepath}")
            df_era5 = pd.read_csv(filepath)
            df_era5_daily = pd.read_csv(dailypath)
        else:
            era5_result = save_era5_data(site_name, site_folder, lat, lon, start_date, end_date)
            if era5_result and os.path.exists(era5_result["filepath"]):
                df_era5 = pd.read_csv(era5_result["filepath"])
                df_era5_daily = pd.read_csv(era5_result["filepath_daily"])
            else:
                print("Empty data or missing file for ERA5")
                df_era5, df_era5_daily = None, None

        if df_era5 is not None and not df_era5.empty:
            model["era5"] = {"data": df_era5, "daily": df_era5_daily}
    except Exception as e:
        print(f"ERA5 error: {e}")

    return model
