import os
from datetime import datetime, timedelta
from typing import Union, Optional, Dict, Any

import requests
import pandas as pd
import numpy as np

# NASA POWER Daily data availability (UTC/LST) starts in 1981-01-01. 
NASA_POWER_START_DATE = datetime(1981, 1, 1)


def _to_datetime(dt: Union[str, datetime]) -> datetime:
    """
    Convert input to a datetime.date (no timezone), assuming '%Y-%m-%d' for strings.
    """
    if isinstance(dt, datetime):
        return dt
    return datetime.strptime(dt, "%Y-%m-%d")


def _create_empty_period(start_dt: datetime, end_dt: datetime) -> pd.DataFrame:
    """
    Crée un DataFrame vide entre deux dates (incluses) dans le format cible
    pour permettre de préfixer les séries avant 1981.

    Colonnes alignées avec la sortie finale.
    """
    if end_dt < start_dt:
        return pd.DataFrame(columns=[
            "time",
            "windspeed_mean",
            "windspeed_daily_avg",
            "windspeed_gust",
            "wind_direction",
            "u_component_10m",
            "v_component_10m",
            "n_hours",
        ])

    dates = pd.date_range(start=start_dt, end=end_dt, freq="D")

    return pd.DataFrame({
        "time": dates,
        "windspeed_mean": np.nan,
        "windspeed_daily_avg": np.nan,
        "windspeed_gust": np.nan,
        "wind_direction": np.nan,
        "u_component_10m": np.nan,
        "v_component_10m": np.nan,
        # Pas d’information horaire réelle avant 1981 → NaN
        "n_hours": np.nan,
    })


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
    Récupère les données NASA POWER (Daily API, communauté RE) pour le vent à 10 m
    et renvoie un CSV journalier standardisé.

    Variables NASA POWER utilisées (Daily API, point): 
      - WS10M      : Wind Speed at 10 m (daily average, m/s)
      - WS10M_MAX  : Maximum Wind Speed at 10 m (daily max, m/s)
      - WD10M      : Wind Direction at 10 m (daily average, degrees)
      - U10M       : Eastward Wind at 10 m (daily average, m/s)
      - V10M       : Northward Wind at 10 m (daily average, m/s)

    Hypothèses / Standardisation:
      - Hauteur de mesure : 10 m (dérivé de MERRA-2 / NASA POWER). 
      - time-standard=UTC pour harmoniser avec les autres fetchers. 
      - windspeed_mean       = WS10M_MAX (max journalier du vent moyen 10 m).
      - windspeed_daily_avg  = WS10M    (moyenne journalière du vent 10 m).
      - windspeed_gust :
          * NASA POWER ne fournit pas de rafales dédiées à 10 m dans cette API,
            donc on n’applique qu’un facteur de rafale optionnel:
              windspeed_gust = windspeed_mean * gust_correction_factor
            si gust_correction_factor est fourni, sinon NaN. 
      - wind_direction       = WD10M (direction moyenne, degrés 0–360, sens météo).
      - n_hours              = 24 pour les jours couverts par NASA POWER.

    Colonnes du CSV de sortie:
      - time                  : date (UTC, sans timezone)
      - windspeed_mean        : m/s, max journalier (WS10M_MAX corrigé)
      - windspeed_daily_avg   : m/s, moyenne journalière (WS10M corrigé)
      - windspeed_gust        : m/s, rafale dérivée (ou NaN)
      - wind_direction        : degrés (0–360, d’où vient le vent)
      - u_component_10m       : m/s, composante Est 10 m (moyenne journalière)
      - v_component_10m       : m/s, composante Nord 10 m (moyenne journalière)
      - n_hours               : nombre d’heures agrégées (24 sur la période NASA)
      - mean_correction_factor: facteur appliqué aux vitesses moyennes (ou 1.0)
      - gust_correction_factor: facteur rafale appliqué (ou NaN)
      - source                : 'NASA_POWER'
      - latitude, longitude   : coordonnée du point
      - timezone              : 'UTC'

    Gestion des dates:
      - Si start_date < 1981-01-01, on préfixe avec des lignes vides (NaN) jusqu’au
        1980-12-31 pour avoir une série continue. 
    """
    os.makedirs(site_folder, exist_ok=True)

    start_dt = _to_datetime(start_date)
    end_dt = _to_datetime(end_date)

    if end_dt < start_dt:
        raise ValueError("end_date doit être >= start_date")

    # Partie éventuelle avant le début de NASA POWER (1981-01-01)
    df_prefix = None
    start_real_dt = start_dt
    if start_dt < NASA_POWER_START_DATE:
        cutoff_dt = NASA_POWER_START_DATE - timedelta(days=1)
        print("Début d'étude avant 1981, ajout de valeurs vides.")
        df_prefix = _create_empty_period(start_dt, cutoff_dt)
        start_real_dt = NASA_POWER_START_DATE

    # Construction de l’URL NASA POWER Daily API (point, community=RE, UTC)
    start_str = start_real_dt.strftime("%Y%m%d")
    end_str = end_dt.strftime("%Y%m%d")

    # Daily API → paramètres par jour, valeurs moyenne / max / min selon le paramètre. 
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

    print(f"Appel API NASA POWER (Daily, 10 m) pour {site_name}...")
    response = requests.get(url, timeout=60)

    if response.status_code != 200:
        raise RuntimeError(
            f"Erreur API NASA POWER : {response.status_code} - {response.text}"
        )

    data = response.json()
    param = data["properties"]["parameter"]

    if "WS10M" not in param:
        raise KeyError("WS10M absent de la réponse NASA POWER.")

    dates_str = list(param["WS10M"].keys())
    dates_dt = pd.to_datetime(dates_str)

    # WS10M: daily average wind speed at 10 m (m/s)
    ws10m = list(param["WS10M"].values())

    # WS10M_MAX: daily maximum wind speed at 10 m (m/s), sinon fallback sur WS10M
    if "WS10M_MAX" in param:
        ws10m_max = list(param["WS10M_MAX"].values())
    else:
        print("WS10M_MAX absent de la réponse NASA POWER, fallback sur WS10M.")
        ws10m_max = ws10m

    # WD10M: daily average wind direction at 10 m (degrees), sinon NaN
    if "WD10M" in param:
        wd10m = list(param["WD10M"].values())
    else:
        print("WD10M absent de la réponse NASA POWER, wind_direction = NaN.")
        wd10m = [np.nan] * len(dates_dt)

    # U10M / V10M: daily average wind components at 10 m, sinon NaN
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
            # Max journalier (vitesse 10 m)
            "windspeed_mean": ws10m_max,
            # Moyenne journalière (vitesse 10 m)
            "windspeed_daily_avg": ws10m,
            # Gust sera construit via gust_correction_factor (pas de rafales natives)
            "windspeed_gust": np.nan,
            "wind_direction": wd10m,
            "u_component_10m": u10m,
            "v_component_10m": v10m,
        }
    )

    # n_hours: 24 h pour chaque jour couvert par NASA POWER
    df_nasa["n_hours"] = 24.0

    # Application éventuelle d’un facteur de correction sur les vitesses moyennes
    if mean_correction_factor is None:
        mean_correction_factor = 1.0

    df_nasa["windspeed_mean"] = df_nasa["windspeed_mean"] * mean_correction_factor
    df_nasa["windspeed_daily_avg"] = (
        df_nasa["windspeed_daily_avg"] * mean_correction_factor
    )
    df_nasa["mean_correction_factor"] = mean_correction_factor

    # Construction des rafales à partir d’un gust_correction_factor optionnel
    if gust_correction_factor is not None:
        df_nasa["windspeed_gust"] = (
            df_nasa["windspeed_mean"] * gust_correction_factor
        )
        df_nasa["gust_correction_factor"] = gust_correction_factor
    else:
        df_nasa["gust_correction_factor"] = np.nan

    # Préfixe avant 1981 si demandé
    if df_prefix is not None and not df_prefix.empty:
        # Aligner les colonnes
        for col in df_nasa.columns:
            if col not in df_prefix.columns:
                df_prefix[col] = np.nan

        # On garde les colonnes dans le même ordre
        df_prefix = df_prefix[df_nasa.columns]
        df = pd.concat([df_prefix, df_nasa], ignore_index=True)
    else:
        df = df_nasa

    # Métadonnées communes
    df["source"] = "NASA_POWER"
    df["latitude"] = lat
    df["longitude"] = lon
    df["timezone"] = "UTC"
    df["measurement_height_m"] = 10.0

    # Ordre des colonnes (pour rester lisible et cohérent)
    cols_order = [
        "time",
        "windspeed_mean",
        "windspeed_daily_avg",
        "windspeed_gust",
        "wind_direction",
        "u_component_10m",
        "v_component_10m",
        "n_hours",
        "mean_correction_factor",
        "gust_correction_factor",
        "source",
        "latitude",
        "longitude",
        "timezone",
        "measurement_height_m",
    ]
    # On garde aussi d'éventuelles colonnes supplémentaires à la fin
    cols_final = [c for c in cols_order if c in df.columns] + [
        c for c in df.columns if c not in cols_order
    ]
    df = df[cols_final]

    output_path = os.path.join(site_folder, f"nasa_power_{site_name}.csv")
    df.to_csv(output_path, index=False)

    print(f"Données NASA POWER enregistrées : {output_path}")

    return {
        "filename": os.path.basename(output_path),
        "filepath": output_path,
        "latitude": lat,
        "longitude": lon,
        "n_records": len(df),
    }
