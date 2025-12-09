import os
import pandas as pd

from modules.utils import load_sites_from_csv
from modules.meteostat_fetcher import get_nearest_stations_info
from modules.source_manager import fetch_observed_sources, fetch_model_source
from modules.globe_visualizer import visualize_sites_plotly
from modules.tkinter_ui import get_date_range_from_user
from modules.station_profiler import generate_station_csv, generate_station_docx

# Specific sources
from modules.noaa_station_finder import load_isd_stations, find_nearest_isd_stations
from modules.noaa_isd_fetcher import fetch_isd_series
#from modules.meteo_france_station_finder import get_mf_stations_list, find_closest_mf_station
#from modules.meteo_france_fetcher import fetch_meteo_france_data

from modules.analysis_runner import run_analysis_for_site
from modules.report_generator import generate_report


def export_site_data(site_data, site_folder):
    os.makedirs(site_folder, exist_ok=True)
    paths = []

    for key, df in site_data["data"].items():
        if df is not None and not df.empty:
            filename = f"{key}_{site_data['name']}.csv"
            filepath = os.path.join(site_folder, filename)
            df.to_csv(filepath, index=False)
            print(f"Generated file: {filepath}")
            paths.append(filepath)

            if "noaa_station" in key:
                raw_path = os.path.join(site_folder, f"raw_{filename}")
                if hasattr(df, "_raw") and isinstance(df._raw, pd.DataFrame):
                    df._raw.to_csv(raw_path, index=False)
                    print(f"NOAA ISD raw CSV saved: {raw_path}")
        else:
            print(f"No data for {key} - file not generated.")

    site_data["files"] = paths

    if paths:
        print(f"Generated files for {site_data['name']}:")
        for p in paths:
            print(f"   - {p}")


def load_existing_data(site_folder, site_name, key):
    filename = f"{key}_{site_name}.csv"
    filepath = os.path.join(site_folder, filename)
    if os.path.exists(filepath):
        print(f"File already present - reading directly: {filepath}")
        try:
            return pd.read_csv(filepath)
        except Exception:
            print(f"Error reading file {filepath}")
    return None


def main():
    print("Current working directory:", os.getcwd())
    print("Loading sites from modele_sites.csv...")
    sites = load_sites_from_csv("modele_sites.csv")
    start, end = get_date_range_from_user()
    if not start or not end:
        print("Invalid dates. Exiting.")
        return

    isd_df = load_isd_stations("data/isd-history.csv")
    all_sites_data = []

    for site in sites:
        name = site["name"]
        country = site["country"]
        lat = float(site["latitude"])
        lon = float(site["longitude"])

        print(f"\nProcessing site: {name} ({country})")

        site_ref = f"{site['reference']}_{name}"
        site_folder = os.path.join("data", site_ref)
        os.makedirs(site_folder, exist_ok=True)

        report_docx_path = os.path.join(site_folder, "report", f"{site_ref}.docx")
        site_data = {
            "name": name,
            "country": country,
            "latitude": lat,
            "longitude": lon,
            "start": start,
            "end": end,
            "reference": site["reference"],
            "meteostat1": None,
            "meteostat2": None,
            "noaa1": None,
            "noaa2": None,
            "data": {},
        }

        already_processed = os.path.exists(report_docx_path)
        if already_processed:
            print(f"Analysis already done for {name} - skipping analysis and report.")
        else:
            stations = get_nearest_stations_info(lat, lon)
            station1 = stations["station1"]
            station2 = stations["station2"]

            noaa_candidates = find_nearest_isd_stations(lat, lon, isd_df)
            noaa_station1 = noaa_candidates[0] if len(noaa_candidates) > 0 else None
            noaa_station2 = noaa_candidates[1] if len(noaa_candidates) > 1 else None
            print(f"NOAA station 1 candidate: {noaa_station1}")
            print(f"NOAA station 2 candidate: {noaa_station2}")

            noaa_data = {}
            for i, station in enumerate([noaa_station1, noaa_station2], 1):
                if station:
                    try:
                        filename = f"noaa_station{i}_{name}.csv"
                        filepath = os.path.join(site_folder, filename)
                        if os.path.exists(filepath):
                            print(f"NOAA file already present - reusing without download: {filepath}")
                            df = pd.read_csv(filepath)
                        else:
                            print(f"Downloading NOAA Station {i}...")
                            df = fetch_isd_series(
                                site_name=name,
                                usaf=station["usaf"],
                                wban=station["wban"],
                                years=list(range(int(start[:4]), int(end[:4]) + 1)),
                                output_dir=site_folder,
                                verbose=True,
                                return_raw=True,
                                station_rank=i,
                            )
                        noaa_data[f"noaa_station{i}"] = df
                    except Exception as e:
                        print(f"Error NOAA station {i}: {e}")

            observed = {}
            for key in ["meteostat1", "meteostat2"]:
                df = load_existing_data(site_folder, name, key)
                if df is not None:
                    observed[key] = {"data": df}

            if not all(k in observed for k in ["meteostat1", "meteostat2"]):
                try:
                    fetched_observed = fetch_observed_sources(
                        site_info=site,
                        site_name=name,
                        site_folder=site_folder,
                        lat=lat,
                        lon=lon,
                        start_date=start,
                        end_date=end,
                        meteostat_id1=station1["id"],
                        meteostat_id2=station2["id"],
                    )
                    observed.update(fetched_observed)
                except Exception as e:
                    print(f"Error fetching observed sources: {e}")

            model = {}
            for key in ["openmeteo", "nasa_power", "era5"]:
                df = load_existing_data(site_folder, name, key)
                if df is not None:
                    model[key] = {"data": df}

            if not all(k in model for k in ["openmeteo", "nasa_power", "era5"]):
                try:
                    fetched_model = fetch_model_source(
                        site_info=site,
                        site_name=name,
                        site_folder=site_folder,
                        lat=lat,
                        lon=lon,
                        start_date=start,
                        end_date=end,
                        openmeteo_model=None,
                        gust_correction_factor=None,
                    )
                    model.update(fetched_model)
                except Exception as e:
                    print(f"Error fetching model source: {e}")

            site_data.update(
                {
                    "meteostat1": station1,
                    "meteostat2": station2,
                    "noaa1": noaa_station1,
                    "noaa2": noaa_station2,
                    "data": {
                        "meteostat1": observed.get("meteostat1", {}).get("data"),
                        "meteostat2": observed.get("meteostat2", {}).get("data"),
                        "noaa_station1": noaa_data.get("noaa_station1"),
                        "noaa_station2": noaa_data.get("noaa_station2"),
                        "openmeteo": model.get("openmeteo", {}).get("data"),
                        "nasa_power": model.get("nasa_power", {}).get("data"),
                        "era5": model.get("era5", {}).get("data"),
                    },
                }
            )

            export_site_data(site_data, site_folder)

            required_sources = [
                "meteostat1",
                "meteostat2",
                "noaa_station1",
                "noaa_station2",
                "openmeteo",
                "nasa_power",
                "era5",
            ]

            missing_sources = [
                key for key in required_sources if site_data["data"].get(key) is None
            ]

            if missing_sources:
                print(
                    f"Missing sources for {name}: {missing_sources} - analysis and report still generated."
                )

            dataframes = {
                "meteostat1": site_data["data"].get("meteostat1"),
                "meteostat2": site_data["data"].get("meteostat2"),
                "noaa_station1": site_data["data"].get("noaa_station1"),
                "noaa_station2": site_data["data"].get("noaa_station2"),
                "openmeteo": site_data["data"].get("openmeteo"),
                "nasa_power": site_data["data"].get("nasa_power"),
                "era5": site_data["data"].get("era5"),
            }

            run_analysis_for_site(name, site_folder, site, dataframes)
            generate_report(site_data, output_folder="data")

        # Append in all cases, even when skipping analysis
        all_sites_data.append(site_data)

    visualize_sites_plotly(all_sites_data, "visualisation_plotly.html")

    #generate_station_csv(all_sites_data)
    #generate_station_docx(all_sites_data)


if __name__ == "__main__":
    main()
