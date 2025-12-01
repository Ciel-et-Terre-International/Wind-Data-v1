import cdsapi
import os
import zipfile
import pandas as pd
import numpy as np
from datetime import datetime


def read_era5_csv(filepath):
    """
    Lit un CSV ERA5 timeseries (reanalysis-era5-single-levels-timeseries)
    contenant au moins :
        - valid_time (ou time)
        - u10, v10

    Convention ERA5 (doc ECMWF/C3S) :
        - u10, v10 en m/s à 10 m de hauteur.
        - Temps en UTC (valid_time).

    Calculs effectués :
        - time (datetime UTC)
        - windspeed_10m = sqrt(u10^2 + v10^2)  [m/s]
        - wind_direction : direction météorologique (°), vent venant de cet angle,
          calculée à partir de u10, v10 via atan2(-u, -v).

    Retour :
        DataFrame avec colonnes :
            - time (datetime64[ns, UTC])
            - u10, v10 (m/s)
            - windspeed_10m (m/s)
            - wind_direction (°)
    """
    df = pd.read_csv(filepath)

    # Colonne temporelle : valid_time ou time
    if "valid_time" in df.columns:
        time_col = "valid_time"
    elif "time" in df.columns:
        time_col = "time"
    else:
        raise ValueError(
            "Aucune colonne temporelle 'valid_time' ou 'time' trouvée dans le CSV ERA5."
        )

    df = df.rename(columns={time_col: "time"})

    # Conversion en datetime UTC
    df["time"] = pd.to_datetime(df["time"], errors="coerce", utc=True)

    # Colonnes u10 / v10 (sortie standard ERA5 pour 10m_u/v_component_of_wind)
    for comp in ["u10", "v10"]:
        if comp not in df.columns:
            raise ValueError(f"Colonne '{comp}' manquante dans le CSV ERA5.")
        df[comp] = df[comp].astype(float)

    # Vitesse 10 m
    df["windspeed_10m"] = np.sqrt(df["u10"] ** 2 + df["v10"] ** 2)

    # Direction météo (0° = nord, 90° = est, etc.), vent venant de la direction indiquée
    # Convention ECMWF : u = -|V| sin(phi), v = -|V| cos(phi)  =>  phi = atan2(-u, -v)
    phi_deg = np.rad2deg(np.arctan2(-df["u10"], -df["v10"]))
    df["wind_direction"] = (phi_deg + 360.0) % 360.0

    # On supprime les lignes sans temps valide
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
    Agrège les données horaires ERA5 (u10, v10, windspeed_10m, wind_direction)
    en données journalières standardisées pour l'analyse statistique.

    Entrée :
        hourly_df : DataFrame issu de read_era5_csv(...)

    Sortie :
        DataFrame avec colonnes :
            - time               : date (UTC)
            - windspeed_mean     : MAXIMUM journalier de la vitesse 10 m (m/s)
                                   (max des vitesses horaires)
            - windspeed_daily_avg: moyenne journalière de la vitesse 10 m (m/s)
            - wind_direction     : direction moyenne journalière (°), moyenne vectorielle
            - windspeed_gust     : NaN par défaut (pas de variable rafale directe ici),
                                   éventuellement remplie via gust_correction_factor
                                   comme : windspeed_gust = gust_factor * windspeed_mean
            - n_hours            : nombre de pas horaires utilisés
            - source             : "era5"
            - latitude, longitude
            - elevation          : NaN (non dispo en timeseries)
            - timezone           : "UTC"
            - utc_offset_seconds : 0
            - model              : "ERA5"
            - mean_correction_factor
            - gust_correction_factor
    """
    df = hourly_df.copy()
    df["date"] = df["time"].dt.date

    grouped = df.groupby("date")

    # Moyenne journalière de la vitesse
    daily_speed_avg = grouped["windspeed_10m"].mean()

    # MAXIMUM journalier de la vitesse 10 m
    daily_speed_max = grouped["windspeed_10m"].max()

    # Moyenne vectorielle de u10/v10
    u_mean = grouped["u10"].mean()
    v_mean = grouped["v10"].mean()
    phi_daily = np.rad2deg(np.arctan2(-u_mean, -v_mean))
    daily_direction = (phi_daily + 360.0) % 360.0

    # Nombre de pas horaires (traçabilité)
    n_hours = grouped.size()

    daily_df = pd.DataFrame(
        {
            "time": pd.to_datetime(daily_speed_max.index),
            "windspeed_mean": daily_speed_max.values,         # max journalier
            "windspeed_daily_avg": daily_speed_avg.values,    # moyenne journalière
            "wind_direction": daily_direction.values,
            "windspeed_gust": np.nan,                         # pas de rafale dédiée
            "n_hours": n_hours.values,
        }
    )

    # Facteur correctif sur la moyenne (optionnel)
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

    # Gestion des rafales / fallback via gust_correction_factor
    # ERA5 ne fournit pas de rafales dédiées dans ce fetcher :
    # - si gust_correction_factor est None : windspeed_gust reste NaN.
    # - si gust_correction_factor est spécifié :
    #     windspeed_gust = gust_factor * windspeed_mean (sur les NaN).
    if gust_correction_factor is not None:
        factor = float(gust_correction_factor)
        mask_nan = daily_df["windspeed_gust"].isna()
        if mask_nan.any():
            print(
                f"[ERA5] Application gust_correction_factor={factor} pour générer "
                "des rafales pseudo à partir de windspeed_mean."
            )
            daily_df.loc[mask_nan, "windspeed_gust"] = (
                daily_df.loc[mask_nan, "windspeed_mean"] * factor
            )
        daily_df["gust_correction_factor"] = factor
    else:
        daily_df["gust_correction_factor"] = 1.0

    # Métadonnées
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
    Fonction v1 maintenue pour compatibilité :

    - Agrège un DataFrame horaire ERA5 (sorti de read_era5_csv)
      en données journalières avec les colonnes standardisées.
    - Sauvegarde dans `era5_daily_{site_name}.csv` dans site_folder.
    - Ne dispose pas de lat/lon → ceux-ci sont laissés à NaN.

    Colonnes clés :
        time, windspeed_mean (max journalier), windspeed_daily_avg,
        wind_direction, windspeed_gust (NaN ou fallback), n_hours, métadonnées.
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
    Télécharge les données ERA5 timeseries (reanalysis-era5-single-levels-timeseries)
    pour un site donné et les met au format standard pour l'analyse.

    Dataset :
        "reanalysis-era5-single-levels-timeseries"
    Variables :
        - 10m_u_component_of_wind  -> u10 (m/s)
        - 10m_v_component_of_wind  -> v10 (m/s)
    Temps :
        - Série horaire en UTC (valid_time).

    Comportement :
        - Télécharge un ZIP (csv) via CDSAPI, à partir de start_date / end_date.
        - Calcule :
            * hourly_df : données horaires avec time, u10, v10, windspeed_10m,
              wind_direction, windspeed_mean (optionnellement corrigée).
            * daily_df  : agrégat journalier standardisé :
                time, windspeed_mean (max journalier), windspeed_daily_avg,
                wind_direction, windspeed_gust (NaN ou fallback), n_hours, métadonnées.
        - Sauvegarde :
            * era5_{site_name}.csv        (horaire)
            * era5_daily_{site_name}.csv  (journalier)
    """
    print(f"[ERA5] Téléchargement timeseries pour {site_name}...")

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
        print(f"[ERA5] Erreur lors de la création du client CDSAPI : {e}")
        return None

    # Téléchargement
    try:
        result = c.retrieve(dataset, request)
        result.download(temp_zip)
    except Exception as e:
        print(f"[ERA5] Erreur API ERA5 : {e}")
        return None

    # Extraction + traitement
    try:
        with zipfile.ZipFile(temp_zip, "r") as zip_ref:
            zip_ref.extractall(site_folder)
            extracted_files = zip_ref.namelist()

        csv_files = [f for f in extracted_files if f.endswith(".csv")]
        if not csv_files:
            raise Exception("Aucun fichier CSV trouvé dans le ZIP ERA5 téléchargé.")

        temp_csv = os.path.join(site_folder, csv_files[0])

        # Données horaires brutes
        df_hourly_raw = read_era5_csv(temp_csv)
        if df_hourly_raw.empty:
            print("[ERA5] Fichier ERA5 vide après traitement.")
            return None

        # Ajout colonne windspeed_mean (horaire) pour le fichier brut
        df_hourly = df_hourly_raw.copy()
        df_hourly["windspeed_mean"] = df_hourly["windspeed_10m"]

        if mean_correction_factor is not None:
            df_hourly["windspeed_mean"] = (
                df_hourly["windspeed_mean"] * float(mean_correction_factor)
            )
            df_hourly["mean_correction_factor"] = float(mean_correction_factor)
        else:
            df_hourly["mean_correction_factor"] = 1.0

        # Métadonnées simples sur l'horaire
        df_hourly["source"] = "era5"
        df_hourly["latitude"] = float(lat)
        df_hourly["longitude"] = float(lon)
        df_hourly["timezone"] = "UTC"
        df_hourly["utc_offset_seconds"] = 0
        df_hourly["model"] = "ERA5"

        # Sauvegarde horaire
        final_csv = os.path.join(site_folder, f"era5_{site_name}.csv")
        df_hourly.to_csv(final_csv, index=False)

        # Agrégation journalière standardisée
        df_daily = _aggregate_era5_daily(
            df_hourly_raw,
            lat=lat,
            lon=lon,
            mean_correction_factor=mean_correction_factor,
            gust_correction_factor=gust_correction_factor,
        )

        daily_csv = os.path.join(site_folder, f"era5_daily_{site_name}.csv")
        df_daily.to_csv(daily_csv, index=False)
        print(f"[ERA5] Fichier journalier généré : {daily_csv}")
        print(f"[ERA5] Fichier horaire généré : {final_csv}")

        # Nettoyage
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
        print(f"[ERA5] Erreur traitement ERA5 : {e}")
        return None
