# noaa_isd_fetcher.py
import os
import pandas as pd
import numpy as np
import requests
from tqdm import tqdm

def fetch_isd_series(usaf, wban, years, output_dir, site_name="site", verbose=False, return_raw=False, station_rank=None):
    """
    Récupère les données horaires NOAA ISD (format .csv via Global Hourly Access)
    et les agrège en journalier avec valeurs max pour le vent et les rafales.

    ⚠️ Ce script est conçu pour les fichiers CSV dont les vitesses sont codées en dixièmes de m/s.

    Paramètres :
        - usaf, wban : identifiants station NOAA
        - years : liste des années à traiter
        - output_dir : dossier de sortie
        - site_name : nom du site pour nommage du fichier
        - verbose : affichage détaillé
        - return_raw : retourne le DataFrame complet non agrégé
        - station_rank : rang de la station (1 ou 2), utilisé dans le nom du fichier

    Retour :
        - DataFrame journalier (ou None si aucun fichier valide)
    """

    base_url = "https://www.ncei.noaa.gov/data/global-hourly/access"
    all_data = []

    if station_rank:
        print(f"Téléchargement des données NOAA ISD pour station {station_rank} ({usaf}-{wban})")

    print(f"Téléchargement des fichiers NOAA {usaf}-{wban} sur {len(years)} an(s)...")
    for i, year in enumerate(tqdm(years, desc=f"{usaf}-{wban}", ncols=80), 1):
        file_url = f"{base_url}/{year}/{usaf}{wban}.csv"
        if verbose:
            print(f"  └─ {i}/{len(years)} : Téléchargement {file_url}")

        try:
            df = pd.read_csv(file_url)
        except Exception as e:
            if verbose:
                print(f"Erreur pour {usaf}-{wban} {year} : {e}")
            continue

        if 'DATE' not in df.columns or 'WND' not in df.columns:
            if verbose:
                print(f"Colonnes 'DATE' ou 'WND' manquantes pour {usaf}-{wban} en {year}")
            continue

        # Parsing date
        df['DATE'] = pd.to_datetime(df['DATE'], errors='coerce')
        df = df.dropna(subset=['DATE'])
        df['date'] = df['DATE'].dt.date

        # Parsing colonne WND : vitesse en dixièmes de m/s → diviser par 10
        parsed = df['WND'].str.split(',', expand=True)
        df['wind_dir_raw'] = pd.to_numeric(parsed[0], errors='coerce')
        df['wind_speed'] = pd.to_numeric(parsed[3], errors='coerce') / 10  # valeur déjà en dixièmes de m/s
        df['wind_speed'] = df['wind_speed'].mask((df['wind_speed'] > 100) | (df['wind_speed'] < 0))

        # Parsing rafales GUST si disponible (déjà en m/s, codé directement)
        if 'GUST' in df.columns:
            df['windspeed_gust'] = pd.to_numeric(df['GUST'], errors='coerce') / 10  # aussi en dixièmes de m/s
            df['windspeed_gust'] = df['windspeed_gust'].mask((df['windspeed_gust'] > 150) | (df['windspeed_gust'] < 0))
        else:
            df['windspeed_gust'] = np.nan

        # Parsing direction : DRCT prioritaire si dispo
        if 'DRCT' in df.columns:
            df['wind_direction'] = pd.to_numeric(df['DRCT'], errors='coerce')
        else:
            df['wind_direction'] = df['wind_dir_raw']

        # Filtrage des directions invalides
        df['wind_direction'] = df['wind_direction'].mask(
            (df['wind_direction'] > 360) | (df['wind_direction'] < 0) | (df['wind_direction'] == 999)
        )

        all_data.append(df[['date', 'wind_speed', 'windspeed_gust', 'wind_direction']])

    if not all_data:
        print(f"Aucune donnée récupérée pour la station {usaf}-{wban}.")
        return None

    # Fusion des années
    full_df = pd.concat(all_data, ignore_index=True)

    if return_raw:
        return full_df

    # Agrégation journalière : on prend les valeurs max et mode
    agg_df = full_df.groupby("date").agg({
        "wind_speed": "max",
        "windspeed_gust": "max",
        "wind_direction": lambda x: x.mode().iloc[0] if not x.dropna().empty else pd.NA
    }).reset_index()

    # Renommage
    agg_df.rename(columns={
        "wind_speed": "windspeed_mean"
    }, inplace=True)

    # Sauvegarde
    rank = station_rank if station_rank else "X"
    final_csv = os.path.join(output_dir, f"noaa_station{rank}_{site_name}.csv")
    agg_df.to_csv(final_csv, index=False)

    if verbose:
        print(f"\nNOAA ISD journalier sauvegardé → {final_csv}")
        print(f"   Colonnes : date, windspeed_mean (m/s), windspeed_gust (m/s), wind_direction (°)")

    return agg_df