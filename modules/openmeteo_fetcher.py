import os
import requests
import pandas as pd
from datetime import datetime

def fetch_openmeteo_data(lat, lon, start_date, end_date, model=None, gust_correction_factor=None):
    """
    Télécharge les données horaires brutes d'OpenMeteo pour calculer soi-même :
    - la moyenne journalière du vent moyen
    - la moyenne journalière de la direction
    - le max journalier des rafales horaires (gusts)
    """

    base_url = "https://archive-api.open-meteo.com/v1/archive"
    model_param = f"&models={model}" if model else ""

    # Données horaires brutes : windspeed + direction + gusts
    url_hourly = (
        f"{base_url}?latitude={lat}&longitude={lon}"
        f"&start_date={start_date}&end_date={end_date}"
        f"&hourly=windspeed_10m,winddirection_10m,windgusts_10m"
        f"&windspeed_unit=ms&windgusts_unit=ms"  # HYPER IMPORTANT : unité m/s pour éviter les erreurs de conversion (on récupère des données brutes en km/h sans cette option)
        f"&timezone=auto{model_param}"
    )

    print(f"Appel API OpenMeteo (hourly) : {url_hourly}")
    response_hourly = requests.get(url_hourly)
    if response_hourly.status_code != 200:
        raise Exception(f"Erreur API OpenMeteo (hourly) : {response_hourly.status_code} - {response_hourly.text}")

    data_hourly = response_hourly.json().get("hourly", {})
    df_hourly = pd.DataFrame(data_hourly)
    df_hourly["time"] = pd.to_datetime(df_hourly["time"])
    df_hourly["date"] = df_hourly["time"].dt.date

    # Calcul des agrégats journaliers
    df_daily_agg = df_hourly.groupby("date").agg({
        "windspeed_10m": "mean",
        "winddirection_10m": "mean",
        "windgusts_10m": "max"
    }).reset_index()

    df_daily_agg = df_daily_agg.rename(columns={
        "date": "time",
        "windspeed_10m": "windspeed_mean",
        "winddirection_10m": "wind_direction",
        "windgusts_10m": "windspeed_gust"
    })

    df_daily_agg["time"] = pd.to_datetime(df_daily_agg["time"])

    df_daily_agg["windspeed_mean"] = df_daily_agg["windspeed_mean"] * 1.10  # Conversion 1h → 10min

    # Application optionnelle d'un facteur correctif sur les rafales
    # if gust_correction_factor is not None:
    #     print(f"Application facteur correctif rafales : x{gust_correction_factor}")
    #     df_daily_agg["windspeed_gust"] = df_daily_agg["windspeed_gust"] * gust_correction_factor

    print(f"Données OpenMeteo téléchargées et agrégées proprement.")
    return df_daily_agg


def save_openmeteo_data(site_name, site_folder, lat, lon, start_date, end_date, model=None, gust_correction_factor=None):
    df = fetch_openmeteo_data(lat, lon, start_date, end_date, model=model, gust_correction_factor=gust_correction_factor)

    filename = f"openmeteo_{site_name}.csv"
    filepath = os.path.join(site_folder, filename)
    df.to_csv(filepath, index=False)

    print(f"Fichier OpenMeteo sauvegardé : {filepath}")
    return {
        'filename': filename,
        'filepath': filepath,
        'latitude': lat,
        'longitude': lon
    }
