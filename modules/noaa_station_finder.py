import pandas as pd
import requests
from geopy.distance import geodesic


def load_isd_stations(csv_path):
    """
    Load and clean the isd-history.csv (NOAA ISD station history).

    - Strip extra spaces in headers and values.
    - Normalize common column names: ELEV, BEGIN, END.
    - Convert LAT, LON, ELEV, BEGIN, END to numeric when present.
    - Drop rows without latitude / longitude.
    """
    df = pd.read_csv(csv_path, dtype=str)
    df.columns = df.columns.str.strip()
    df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)

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

    # Convert numeric columns when present
    for col in ["LAT", "LON", "ELEV", "BEGIN", "END"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Keep only rows with valid coordinates
    df = df.dropna(subset=["LAT", "LON"])
    return df


def test_isd_station_availability(usaf, wban, year):
    """
    Check if the NOAA ISD file for a given station (USAF+WBAN) and year
    actually exists on the Global Hourly server (HEAD request on CSV URL).
    """
    url = f"https://www.ncei.noaa.gov/data/global-hourly/access/{year}/{usaf}{wban}.csv"
    try:
        response = requests.head(url, timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False


def find_nearest_isd_stations(site_lat, site_lon, isd_df, max_distance_km=80, n=5):
    """
    Find the n closest ISD stations within max_distance_km using the
    already-loaded isd-history DataFrame.

    This function does NOT hit NOAA APIs; it relies on LAT/LON and BEGIN/END
    metadata to build a structured list.
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

    # Sort by distance and return the first n
    station_list.sort(key=lambda x: x["distance_km"])
    return station_list[:n]
