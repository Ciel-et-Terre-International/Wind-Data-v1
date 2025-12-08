import os
from datetime import datetime

import numpy as np
import pandas as pd
from geopy.distance import geodesic
from meteostat import Stations, Hourly


def get_nearest_stations_info(lat, lon, limit=2):
    """
    Retourne les stations Meteostat les plus proches d'un site donné.

    Sortie :
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
    Récupère les données horaires Meteostat pour UNE station, agrège par jour
    et met au format standard pour l'analyse statistique.

    On utilise Meteostat Hourly (timezone=UTC) pour obtenir :
        - wspd : vitesse de vent horaire (km/h, moyenne sur l'heure)
        - wpgt : rafale horaire max (km/h)
        - wdir : direction horaire (°)

    Conventions utilisées :
        - On convertit systématiquement km/h → m/s (/3.6).
        - Agrégats journaliers :
            * windspeed_mean      : MAXIMUM journalier de la vitesse horaire (m/s)
            * windspeed_daily_avg : moyenne journalière des vitesses horaires (m/s)
            * windspeed_gust      : MAXIMUM journalier des rafales horaires (m/s)
            * wind_direction      : moyenne vectorielle journalière de la direction (°)
            * n_hours             : nombre de pas horaires utilisés

    Facteurs optionnels :
        - mean_correction_factor :
            * multiplie windspeed_mean ET windspeed_daily_avg par ce facteur
              (ex. correction 1h→10min).
        - gust_correction_factor :
            * Meteostat fournit déjà des rafales via wpgt.
            * Si gust_correction_factor est None :
                - on utilise les rafales journalières telles quelles (max des wpgt_ms).
            * Si gust_correction_factor est spécifié :
                - on NE modifie PAS les rafales existantes (valeurs non NaN),
                - pour les jours où windspeed_gust est NaN (pas de rafale dispo),
                  on crée un fallback : windspeed_gust = gust_correction_factor * windspeed_mean.
    """
    # Parse dates (YYYY-MM-DD)
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    # Données horaires (timezone=UTC pour alignement avec les autres sources)
    data = Hourly(station_id, start, end, timezone="UTC")
    df = data.fetch().reset_index()  # index 'time' → colonne 'time'

    if df.empty:
        print(f"Pas de données horaires pour Meteostat station {station_id}")
        return pd.DataFrame()

    # Colonnes attendues :
    required_cols = {"time", "wspd", "wpgt", "wdir"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(
            f"Colonnes manquantes dans les données Meteostat Hourly pour la station "
            f"{station_id} : {missing}"
        )

    df["time"] = pd.to_datetime(df["time"], utc=True)

    # Conversion km/h → m/s
    df["wspd_ms"] = df["wspd"].astype(float) / 3.6
    df["wpgt_ms"] = df["wpgt"].astype(float) / 3.6

    # Direction pour moyenne vectorielle
    dir_rad = np.deg2rad(df["wdir"].astype(float))
    df["dir_u"] = np.cos(dir_rad)
    df["dir_v"] = np.sin(dir_rad)

    # Date (UTC)
    df["date"] = df["time"].dt.date
    grouped = df.groupby("date")

    # Agrégats
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
            "windspeed_mean": daily_speed_max.values,          # max journalier des vitesses
            "windspeed_daily_avg": daily_speed_avg.values,     # moyenne journalière
            "wind_direction": daily_direction.values,
            "windspeed_gust": daily_gust_max.values,           # max journalier des rafales
            "n_hours": n_hours.values,
        }
    )

    # Facteur correctif optionnel sur la moyenne
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

    # Facteur correctif optionnel sur les rafales (fallback uniquement)
    if gust_correction_factor is not None:
        factor = float(gust_correction_factor)
        # On ne touche pas aux rafales existantes (non NaN).
        # On ne l'utilise que pour remplir les NaN.
        mask_nan = daily_df["windspeed_gust"].isna()
        if mask_nan.any():
            print(
                f"[Meteostat] Application gust_correction_factor={factor} sur les jours "
                "sans rafales (windspeed_gust NaN) à partir de windspeed_mean."
            )
            daily_df.loc[mask_nan, "windspeed_gust"] = (
                daily_df.loc[mask_nan, "windspeed_mean"] * factor
            )
        daily_df["gust_correction_factor"] = factor
    else:
        daily_df["gust_correction_factor"] = 1.0

    # Métadonnées
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
    Wrapper haut niveau compatible v1, avec standardisation des colonnes et métadonnées.

    Comportement :
    - Si station_ids est None :
        * Recherche les 2 stations Meteostat les plus proches.
    - Pour chaque station :
        * Télécharge les données horaires (Hourly)
        * Agrège en journalier :
            - windspeed_mean      [m/s] : max journalier
            - windspeed_daily_avg [m/s] : moyenne journalière
            - windspeed_gust      [m/s] : max journalier des rafales (ou fallback)
            - wind_direction      [°]   : moyenne vectorielle journalière
            - n_hours
        * Applique les facteurs de correction éventuels
        * Ajoute les métadonnées station
        * Sauvegarde un CSV : meteostat{i}_{site_name}.csv dans site_folder
    """
    os.makedirs(site_folder, exist_ok=True)

    # Stations à utiliser
    meta_info = {}
    if station_ids is None:
        meta_info = get_nearest_stations_info(lat, lon, limit=2)
        station_ids = [meta_info[k]["id"] for k in sorted(meta_info.keys())]
    else:
        # si station_ids est donné, on essaie tout de même de récupérer des infos de base
        # via nearby, mais ce n'est pas critique
        meta_info = {}

    data_collected = {}

    for i, station_id in enumerate(station_ids, 1):
        print(f"Téléchargement Meteostat pour station : {station_id}")
        station_key = f"station{i}"
        station_meta = meta_info.get(station_key, {})

        try:
            df_station = _fetch_meteostat_daily_for_station(
                station_id=station_id,
                lat=lat,
                lon=lon,
                start_date=start_date,
                end_date=end_date,
                mean_correction_factor=mean_correction_factor,
                gust_correction_factor=gust_correction_factor,
                station_meta=station_meta,
            )
        except Exception as e:
            print(f"Erreur Meteostat {i} : {e}")
            continue

        if df_station.empty:
            print(f"Pas de données Meteostat pour la station {station_id}")
            continue

        filename = f"meteostat{i}_{site_name}.csv"
        filepath = os.path.join(site_folder, filename)
        df_station.to_csv(filepath, index=False)
        print(f"Données Meteostat enregistrées : {filepath}")

        data_collected[f"meteostat{i}"] = df_station

    return data_collected
