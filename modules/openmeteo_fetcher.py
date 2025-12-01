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
    Télécharge les données horaires brutes d'Open-Meteo (archive API) et calcule des agrégats journaliers
    standardisés pour l'analyse statistique.

    Hypothèses / conventions importantes (doc Open-Meteo) :
    - Variables horaires utilisées (toutes à 10 m au-dessus du sol) :
        * wind_speed_10m       : vitesse de vent INSTANTANÉE (modèle) à l'heure donnée
        * wind_direction_10m   : direction de vent INSTANTANÉE (°)
        * wind_gusts_10m       : rafale max sur l'heure précédente
    - Unités : vitesses en m/s via `wind_speed_unit=ms`.
    - Fuseau horaire : `timezone=UTC` pour être cohérent avec les autres sources (ERA5, etc.).

    Agrégats journaliers produits :
        * windspeed_mean      : MAXIMUM journalier de wind_speed_10m (m/s)
        * windspeed_daily_avg : moyenne journalière de wind_speed_10m (m/s)
        * wind_direction      : moyenne journalière de la direction (°), moyenne vectorielle (sin/cos)
        * windspeed_gust      : MAXIMUM journalier de wind_gusts_10m (m/s)

    Standardisation des noms de colonnes pour l'analyse :
        * time                : date (UTC) du jour considéré
        * windspeed_mean      : max journalier (m/s)
        * windspeed_daily_avg : moyenne journalière (m/s)
        * wind_direction      : direction moyenne journalière (°)
        * windspeed_gust      : rafale maximale journalière (m/s)
        * n_hours             : nb de pas horaires par jour

    Facteurs optionnels :
    - mean_correction_factor :
        * Si spécifié (float), multiplie windspeed_mean ET windspeed_daily_avg par ce facteur.
        * Permet d'appliquer une correction empirique (ex. passage “moyenne 1h → moyenne 10 min”).
        * Si None (par défaut), aucune correction (facteur effectif = 1.0).

    - gust_correction_factor :
        * Open-Meteo fournit déjà des rafales horaires via wind_gusts_10m.
        * Si gust_correction_factor est None : les rafales journalières (max des wind_gusts_10m)
          sont utilisées telles quelles.
        * Si gust_correction_factor est spécifié :
            - on NE modifie PAS les rafales existantes (valeurs non NaN),
            - pour les jours où la rafale est NaN, on crée un fallback :
              windspeed_gust = gust_correction_factor * windspeed_mean.
    """
    base_url = "https://archive-api.open-meteo.com/v1/archive"
    model_param = f"&models={model}" if model else ""

    # -------------------------------------------------------------------------
    # 1) Appel API : données horaires (vent à 10 m, en m/s, en UTC)
    # -------------------------------------------------------------------------
    url_hourly = (
        f"{base_url}?latitude={lat}&longitude={lon}"
        f"&start_date={start_date}&end_date={end_date}"
        f"&hourly=wind_speed_10m,wind_direction_10m,wind_gusts_10m"
        f"&wind_speed_unit=ms"
        f"&timezone=UTC{model_param}"
    )

    print(f"Appel API Open-Meteo (hourly) : {url_hourly}")
    response_hourly = requests.get(url_hourly)
    if response_hourly.status_code != 200:
        raise Exception(
            f"Erreur API Open-Meteo (hourly) : {response_hourly.status_code} - {response_hourly.text}"
        )

    data_hourly_json = response_hourly.json()
    data_hourly = data_hourly_json.get("hourly", {})
    if not data_hourly:
        raise ValueError("Réponse Open-Meteo (hourly) sans bloc 'hourly' exploitable.")

    df_hourly = pd.DataFrame(data_hourly)
    if df_hourly.empty:
        raise ValueError("Réponse Open-Meteo (hourly) vide après conversion en DataFrame.")

    # Colonnes attendues
    expected_cols = {"time", "wind_speed_10m", "wind_direction_10m"}
    missing_cols = expected_cols - set(df_hourly.columns)
    if missing_cols:
        raise ValueError(
            f"Colonnes manquantes dans la réponse Open-Meteo hourly : {missing_cols}"
        )

    # wind_gusts_10m : si absent, on remplit en NaN
    if "wind_gusts_10m" not in df_hourly.columns:
        df_hourly["wind_gusts_10m"] = np.nan

    # time en datetime (UTC)
    df_hourly["time"] = pd.to_datetime(df_hourly["time"], utc=True)

    # -------------------------------------------------------------------------
    # 2) Agrégats journaliers (vitesse, direction vectorielle, rafales)
    # -------------------------------------------------------------------------
    df_hourly["date"] = df_hourly["time"].dt.date

    # Direction en radians pour moyenne vectorielle
    dir_rad = np.deg2rad(df_hourly["wind_direction_10m"].astype(float))
    df_hourly["dir_u"] = np.cos(dir_rad)
    df_hourly["dir_v"] = np.sin(dir_rad)

    grouped = df_hourly.groupby("date")

    # MAX et moyenne journalière de la vitesse
    daily_speed_max = grouped["wind_speed_10m"].max()
    daily_speed_avg = grouped["wind_speed_10m"].mean()

    # Moyenne vectorielle de la direction
    u_mean = grouped["dir_u"].mean()
    v_mean = grouped["dir_v"].mean()
    daily_direction_mean = np.rad2deg(np.arctan2(v_mean, u_mean))
    daily_direction_mean = (daily_direction_mean + 360.0) % 360.0  # dans [0, 360)

    # Rafale journalière max (max des rafales horaires)
    daily_gust_max = grouped["wind_gusts_10m"].max()

    # Nombre de pas horaires par jour (traçabilité)
    n_hours = grouped.size()

    df_daily_agg = pd.DataFrame(
        {
            "time": daily_speed_max.index,  # date (UTC)
            "windspeed_mean": daily_speed_max.values,          # max journalier
            "windspeed_daily_avg": daily_speed_avg.values,     # moyenne journalière
            "wind_direction": daily_direction_mean.values,
            "windspeed_gust": daily_gust_max.values,           # max rafale
            "n_hours": n_hours.values,
        }
    )

    # time en datetime (date uniquement)
    df_daily_agg["time"] = pd.to_datetime(df_daily_agg["time"])

    # -------------------------------------------------------------------------
    # 3) Facteurs de correction optionnels
    # -------------------------------------------------------------------------
    # Correction sur la vitesse moyenne (ex-1.10, maintenant optionnel)
    if mean_correction_factor is not None:
        print(f"Application facteur correctif sur la moyenne du vent : x{mean_correction_factor}")
        df_daily_agg["windspeed_mean"] = df_daily_agg["windspeed_mean"] * float(
            mean_correction_factor
        )
        df_daily_agg["windspeed_daily_avg"] = df_daily_agg["windspeed_daily_avg"] * float(
            mean_correction_factor
        )
        df_daily_agg["mean_correction_factor"] = float(mean_correction_factor)
    else:
        df_daily_agg["mean_correction_factor"] = 1.0

    # Correction / fallback sur les rafales (gust factor)
    if gust_correction_factor is not None:
        factor = float(gust_correction_factor)
        # On n'applique PAS le facteur sur les rafales existantes.
        # On ne l'utilise que comme fallback là où windspeed_gust est NaN.
        mask_nan = df_daily_agg["windspeed_gust"].isna()
        if mask_nan.any():
            print(
                f"Application gust_correction_factor={factor} sur les jours sans rafales "
                "(windspeed_gust NaN) à partir de windspeed_mean."
            )
            df_daily_agg.loc[mask_nan, "windspeed_gust"] = (
                df_daily_agg.loc[mask_nan, "windspeed_mean"] * factor
            )
        df_daily_agg["gust_correction_factor"] = factor
    else:
        df_daily_agg["gust_correction_factor"] = 1.0

    # -------------------------------------------------------------------------
    # 4) Métadonnées (source, coordonnées, timezone, etc.)
    # -------------------------------------------------------------------------
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

    print("Données Open-Meteo téléchargées et agrégées proprement (v1-audit).")
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
    Wrapper pratique :
    - appelle fetch_openmeteo_data(...)
    - sauvegarde le CSV dans le dossier du site
    - renvoie un dict de résumé (nom de fichier, chemin, coord.)
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

    print(f"Fichier Open-Meteo sauvegardé : {filepath}")
    return {
        "filename": filename,
        "filepath": filepath,
        "latitude": lat,
        "longitude": lon,
    }
