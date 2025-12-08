import pandas as pd
import requests
from geopy.distance import geodesic


def load_isd_stations(csv_path):
    """
    Charge et nettoie le fichier isd-history.csv (NOAA ISD station history).

    - Supprime les espaces en trop dans les en-têtes et les valeurs.
    - Normalise les noms de colonnes usuelles : ELEV, BEGIN, END.
    - Convertit LAT, LON, ELEV, BEGIN, END en numériques lorsque présents.
    - Supprime les lignes sans latitude / longitude.

    Paramètres
    ----------
    csv_path : str
        Chemin vers le fichier isd-history.csv.

    Retour
    ------
    DataFrame pandas nettoyé.
    """
    df = pd.read_csv(csv_path, dtype=str)
    df.columns = df.columns.str.strip()
    df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)

    # Détection automatique des noms de colonnes possibles pour les champs clés
    elevation_col = next(
        (col for col in df.columns if col.strip().upper() in ["ELEV", "ELEV(M)"]),
        None,
    )
    begin_col = next(
        (col for col in df.columns if col.strip().upper() == "BEGIN"),
        None,
    )
    end_col = next(
        (col for col in df.columns if col.strip().upper() == "END"),
        None,
    )

    rename_map = {}
    if elevation_col:
        rename_map[elevation_col] = "ELEV"
    if begin_col:
        rename_map[begin_col] = "BEGIN"
    if end_col:
        rename_map[end_col] = "END"

    df.rename(columns=rename_map, inplace=True)

    # Conversion en numérique des colonnes utiles si elles existent
    for col in ["LAT", "LON", "ELEV", "BEGIN", "END"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # On garde uniquement les stations avec coordonnées valides
    df = df.dropna(subset=["LAT", "LON"])
    return df


def test_isd_station_availability(usaf, wban, year):
    """
    Vérifie si le fichier NOAA ISD pour un identifiant (USAF+WBAN) et une année
    existe réellement sur le serveur Global Hourly (HEAD sur l'URL CSV).

    Paramètres
    ----------
    usaf : str
        Identifiant USAF de la station.
    wban : str
        Identifiant WBAN de la station.
    year : int ou str
        Année à tester.

    Retour
    ------
    bool
        True si le fichier existe (HTTP 200), False sinon.
    """
    url = f"https://www.ncei.noaa.gov/data/global-hourly/access/{year}/{usaf}{wban}.csv"
    try:
        response = requests.head(url, timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False


def find_nearest_isd_stations(site_lat, site_lon, isd_df, max_distance_km=80, n=5):
    """
    Trouve les n stations ISD les plus proches dans un rayon max_distance_km
    à partir d'un DataFrame isd-history déjà chargé.

    NOTE : Cette fonction NE fait pas d'appel réseau NOAA. Elle se base
    uniquement sur la position (LAT, LON) et les colonnes BEGIN/END de
    isd-history pour construire une liste structurée.

    Paramètres
    ----------
    site_lat : float
        Latitude du site étudié.
    site_lon : float
        Longitude du site étudié.
    isd_df : pandas.DataFrame
        DataFrame issu de load_isd_stations, contenant au moins LAT, LON, USAF, WBAN.
    max_distance_km : float, optionnel
        Rayon maximal de recherche en kilomètres (par défaut 80 km).
    n : int, optionnel
        Nombre maximum de stations retournées (par défaut 5).

    Retour
    ------
    list[dict]
        Liste de dictionnaires avec métadonnées station :
        - usaf, wban, station_id, name, country, latitude, longitude,
          elevation_m, distance_km, begin, end, years_available (liste d'années).
    """
    station_list = []

    for _, row in isd_df.iterrows():
        station_coord = (row["LAT"], row["LON"])
        site_coord = (site_lat, site_lon)
        dist_km = geodesic(site_coord, station_coord).km

        if dist_km <= max_distance_km:
            begin = int(row["BEGIN"]) if "BEGIN" in row and not pd.isna(row["BEGIN"]) else None
            end = int(row["END"]) if "END" in row and not pd.isna(row["END"]) else None

            years_available = None
            if begin and end:
                begin_year = int(str(begin)[:4])
                end_year = int(str(end)[:4])
                years_available = list(range(begin_year, end_year + 1))

            station_list.append(
                {
                    "usaf": row.get("USAF"),
                    "wban": row.get("WBAN"),
                    "station_id": f"{row.get('USAF')}-{row.get('WBAN')}",
                    "name": row.get("STATION NAME", "Unknown").title(),
                    "country": row.get("CTRY"),
                    "latitude": float(row["LAT"]),
                    "longitude": float(row["LON"]),
                    "elevation_m": row.get("ELEV", None),
                    "distance_km": round(dist_km, 2),
                    "begin": begin,
                    "end": end,
                    "years_available": years_available,
                }
            )

    # Trier par distance et retourner les n premiers
    station_list.sort(key=lambda x: x["distance_km"])
    return station_list[:n]
