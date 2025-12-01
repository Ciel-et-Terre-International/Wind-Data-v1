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
    Récupère les données horaires NOAA ISD (Global Hourly access en CSV)
    et les agrège en journalier avec les colonnes standardisées pour l'analyse.

    Références techniques NOAA ISD :
    - DATE/time : heure d'observation en UTC. 
    - WND (WIND-OBSERVATION speed rate) : vitesse en m/s avec facteur d'échelle 10,
      donc speed_m/s = valeur / 10. 

    Hypothèses et conventions :
    - On lit les fichiers CSV :
        https://www.ncei.noaa.gov/data/global-hourly/access/{year}/{usaf}{wban}.csv
    - On utilise :
        * DATE : timestamp (UTC)
        * WND  : direction brute + vitesse de vent (en dixièmes de m/s)
        * GUST : rafale (en dixièmes de m/s) si présente
        * DRCT : direction du vent (°) si présente
    - On convertit systématiquement la vitesse en m/s.

    Agrégats journaliers produits :
        * time                : date (UTC, naïve)
        * windspeed_mean      : MAXIMUM journalier de la vitesse horaire (m/s)
        * windspeed_daily_avg : moyenne journalière de la vitesse horaire (m/s)
        * wind_direction      : direction moyenne journalière (°), moyenne vectorielle
        * windspeed_gust      : MAXIMUM journalier des rafales horaires (m/s)
        * n_hours             : nombre de pas horaires utilisés (compte de lignes)

    Facteurs optionnels :
    - mean_correction_factor :
        * Si spécifié (float), multiplie windspeed_mean ET windspeed_daily_avg
          par ce facteur (ex. correction empirique).
    - gust_correction_factor :
        * NOAA fournit des rafales via la colonne GUST.
        * Si gust_correction_factor est None :
            - on utilise les rafales journalières telles quelles (max des GUST).
        * Si gust_correction_factor est spécifié :
            - on NE modifie PAS les rafales existantes (valeurs non NaN),
            - pour les jours où windspeed_gust est NaN, on crée un fallback :
              windspeed_gust = gust_correction_factor * windspeed_mean.

    Métadonnées optionnelles :
    - station_metadata : dict optionnel, typiquement issu de noaa_station_finder, pouvant contenir :
        {
            "name": str,
            "country": str,
            "latitude": float,
            "longitude": float,
            "elevation_m": float,
            "distance_km": float,
            ...
        }

    Paramètres
    ----------
    usaf : str
        Identifiant USAF de la station.
    wban : str
        Identifiant WBAN de la station.
    years : list[int] ou list[str]
        Liste des années à traiter (ex. [2010, 2011, 2012]).
    output_dir : str
        Dossier de sortie pour le CSV journalier.
    site_name : str, optionnel
        Nom du site pour le nommage du fichier.
    verbose : bool, optionnel
        Affichage détaillé des étapes.
    return_raw : bool, optionnel
        Si True, retourne le DataFrame horaire concaténé (non agrégé) et ne fait
        PAS d'agrégation ni de sauvegarde journalière.
    station_rank : int ou None, optionnel
        Rang de la station (1, 2, ...) utilisé dans le nom du fichier.
    gust_correction_factor : float ou None, optionnel
        Facteur multiplicatif utilisé UNIQUEMENT en fallback lorsque les rafales
        journalières sont NaN (gust = factor * windspeed_mean).
    mean_correction_factor : float ou None, optionnel
        Facteur multiplicatif appliqué à windspeed_mean et windspeed_daily_avg.
    station_metadata : dict ou None, optionnel
        Métadonnées station optionnelles (voir ci-dessus).

    Retour
    ------
    - Si return_raw=True :
        DataFrame horaire concaténé (colonnes : time, date, wind_speed,
        windspeed_gust, wind_direction).
    - Sinon :
        DataFrame journalier agrégé avec colonnes :
            time, windspeed_mean, windspeed_daily_avg,
            wind_direction, windspeed_gust, n_hours,
            mean_correction_factor, gust_correction_factor,
            source, usaf, wban, station_id, station_name, country,
            station_latitude, station_longitude, station_elevation,
            station_distance_km, timezone, utc_offset_seconds.
    """
    base_url = "https://www.ncei.noaa.gov/data/global-hourly/access"
    all_data = []

    if station_rank:
        print(
            f"Téléchargement des données NOAA ISD pour station {station_rank} "
            f"({usaf}-{wban})"
        )

    years = list(years)
    print(f"Téléchargement des fichiers NOAA {usaf}-{wban} sur {len(years)} an(s)...")

    for i, year in enumerate(tqdm(years, desc=f"{usaf}-{wban}", ncols=80), 1):
        file_url = f"{base_url}/{year}/{usaf}{wban}.csv"
        if verbose:
            print(f"  └─ {i}/{len(years)} : {file_url}")

        try:
            df = pd.read_csv(file_url)
        except Exception as e:
            if verbose:
                print(f"Erreur pour {usaf}-{wban} {year} : {e}")
            continue

        if "DATE" not in df.columns or "WND" not in df.columns:
            if verbose:
                print(
                    f"Colonnes 'DATE' ou 'WND' manquantes pour {usaf}-{wban} en {year}"
                )
            continue

        # DATE en datetime (UTC) d'après la doc ISD
        df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce", utc=True)
        df = df.dropna(subset=["DATE"])
        df["date"] = df["DATE"].dt.date

        # Parsing colonne WND : "dir,dir_qc,speed,speed_qc,type"
        parsed = df["WND"].astype(str).str.split(",", expand=True)
        df["wind_dir_raw"] = pd.to_numeric(parsed[0], errors="coerce")

        # Vitesse en dixièmes de m/s → m/s
        df["wind_speed"] = pd.to_numeric(parsed[3], errors="coerce") / 10.0
        # Filtrage valeurs aberrantes
        df["wind_speed"] = df["wind_speed"].mask(
            (df["wind_speed"] > 100) | (df["wind_speed"] < 0)
        )

        # Rafales : colonne GUST en dixièmes de m/s selon la doc ISD
        if "GUST" in df.columns:
            df["windspeed_gust"] = pd.to_numeric(df["GUST"], errors="coerce") / 10.0
            df["windspeed_gust"] = df["windspeed_gust"].mask(
                (df["windspeed_gust"] > 150) | (df["windspeed_gust"] < 0)
            )
        else:
            df["windspeed_gust"] = np.nan

        # Direction : DRCT prioritaire si dispo, sinon direction brute WND
        if "DRCT" in df.columns:
            df["wind_direction"] = pd.to_numeric(df["DRCT"], errors="coerce")
        else:
            df["wind_direction"] = df["wind_dir_raw"]

        # Filtrage des directions invalides (999, <0, >360)
        df["wind_direction"] = df["wind_direction"].mask(
            (df["wind_direction"] > 360)
            | (df["wind_direction"] < 0)
            | (df["wind_direction"] == 999)
        )

        # On stocke seulement les colonnes utiles pour agrégation
        subset = df[["DATE", "date", "wind_speed", "windspeed_gust", "wind_direction"]].copy()
        subset = subset.rename(columns={"DATE": "time"})  # horodatage complet
        all_data.append(subset)

    if not all_data:
        print(f"Aucune donnée récupérée pour la station {usaf}-{wban}.")
        return None

    # Fusion des années
    full_df = pd.concat(all_data, ignore_index=True)

    if return_raw:
        # Tri temporel + retour des séries horaires standardisées
        full_df = full_df.sort_values("time").reset_index(drop=True)
        return full_df

    # -------------------------------------------------------------------------
    # Agrégation journalière : max et moyenne sur la vitesse, max sur les rafales,
    # moyenne vectorielle pour la direction.
    # -------------------------------------------------------------------------
    # On s'assure que la date est bien de type datetime/Date
    full_df["date"] = pd.to_datetime(full_df["date"])

    # On ignore les lignes sans vitesse pour les stats de vent
    full_df_speed = full_df.dropna(subset=["wind_speed"]).copy()
    grouped = full_df_speed.groupby("date", sort=True)

    daily_speed_max = grouped["wind_speed"].max()
    daily_speed_avg = grouped["wind_speed"].mean()
    daily_gust_max = grouped["windspeed_gust"].max()
    n_hours = grouped.size()

    # Direction moyenne vectorielle (on ne garde que les directions valides)
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
        # Réindexage sur l'ensemble des jours ayant des vitesses
        daily_direction = dir_deg.reindex(daily_speed_max.index)
    else:
        daily_direction = pd.Series(
            index=daily_speed_max.index, data=np.nan, dtype=float
        )

    # Construction DataFrame journalier
    daily_df = pd.DataFrame(
        {
            "time": pd.to_datetime(daily_speed_max.index),  # date (UTC)
            "windspeed_mean": daily_speed_max.values,
            "windspeed_daily_avg": daily_speed_avg.values,
            "wind_direction": daily_direction.values,
            "windspeed_gust": daily_gust_max.values,
            "n_hours": n_hours.values,
        }
    )

    # -------------------------------------------------------------------------
    # Facteur correctif sur la moyenne (optionnel)
    # -------------------------------------------------------------------------
    if mean_correction_factor is not None:
        factor_mean = float(mean_correction_factor)
        if verbose:
            print(
                f"Application mean_correction_factor={factor_mean} "
                "sur windspeed_mean et windspeed_daily_avg."
            )
        daily_df["windspeed_mean"] = daily_df["windspeed_mean"] * factor_mean
        daily_df["windspeed_daily_avg"] = (
            daily_df["windspeed_daily_avg"] * factor_mean
        )
        daily_df["mean_correction_factor"] = factor_mean
    else:
        daily_df["mean_correction_factor"] = 1.0

    # -------------------------------------------------------------------------
    # Gust factor : uniquement fallback si rafales manquantes
    # -------------------------------------------------------------------------
    if gust_correction_factor is not None:
        factor_gust = float(gust_correction_factor)
        mask_nan = daily_df["windspeed_gust"].isna()
        if mask_nan.any() and verbose:
            print(
                f"Application gust_correction_factor={factor_gust} "
                "sur les jours sans rafales (windspeed_gust NaN) "
                "à partir de windspeed_mean."
            )
        # Fallback uniquement pour les NaN
        daily_df.loc[mask_nan, "windspeed_gust"] = (
            daily_df.loc[mask_nan, "windspeed_mean"] * factor_gust
        )
        daily_df["gust_correction_factor"] = factor_gust
    else:
        daily_df["gust_correction_factor"] = 1.0

    # -------------------------------------------------------------------------
    # Métadonnées
    # -------------------------------------------------------------------------
    meta = station_metadata or {}

    daily_df["source"] = "noaa-isd"
    daily_df["usaf"] = usaf
    daily_df["wban"] = wban
    daily_df["station_id"] = f"{usaf}-{wban}"

    daily_df["station_name"] = meta.get("name", "")
    daily_df["country"] = meta.get("country", "")

    # Coordonnées / altitude / distance (si fournies dans station_metadata)
    daily_df["station_latitude"] = float(meta["latitude"]) if "latitude" in meta else np.nan
    daily_df["station_longitude"] = float(meta["longitude"]) if "longitude" in meta else np.nan
    daily_df["station_elevation"] = float(meta["elevation_m"]) if "elevation_m" in meta else np.nan
    daily_df["station_distance_km"] = (
        float(meta["distance_km"]) if "distance_km" in meta else np.nan
    )

    # NOAA ISD Global Hourly : temps en UTC
    daily_df["timezone"] = "UTC"
    daily_df["utc_offset_seconds"] = 0

    # -------------------------------------------------------------------------
    # Sauvegarde CSV journalier
    # -------------------------------------------------------------------------
    os.makedirs(output_dir, exist_ok=True)
    rank = station_rank if station_rank is not None else "X"
    final_csv = os.path.join(output_dir, f"noaa_station{rank}_{site_name}.csv")
    daily_df.to_csv(final_csv, index=False)

    if verbose:
        print(f"\nNOAA ISD journalier sauvegardé → {final_csv}")
        print(
            "   Colonnes principales : time, windspeed_mean, windspeed_daily_avg, "
            "wind_direction, windspeed_gust, n_hours"
        )

    return daily_df
