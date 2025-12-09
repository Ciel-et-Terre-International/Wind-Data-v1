# ============================================================
# analysis_runner.py
# Complete weather data analysis for one site (v1-audit)
#
# Key assumptions (v1-audit pipeline):
# - All fetchers produce DAILY series.
# - "windspeed_mean" = daily max of mean wind at 10 m (m/s).
# - "windspeed_gust" = daily max of gust (m/s) when available.
# - All data are in UTC.
# ============================================================

import os
from pathlib import Path
from typing import Dict, Optional, Iterable, List, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import gumbel_r

# Global plotting style
plt.rcParams["figure.dpi"] = 120
plt.rcParams["axes.grid"] = True
plt.rcParams["grid.alpha"] = 0.3
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False
sns.set_style("whitegrid")

def _get_config_float(site_config, key, default):
    """
    Safely fetch a float from site_config, falling back to default on empty/NaN.
    """
    val = site_config.get(key, default)
    try:
        f = float(val)
        # gestion des NaN float
        if np.isnan(f):
            return default
        return f
    except Exception:
        return default

# ============================================================
# 0. Generic function: return levels (Gumbel)
# ============================================================

def compute_return_level(
    series: pd.Series,
    return_period_years: float = 50.0,
    min_years: int = 10,
) -> Optional[float]:
    """
    Compute a return level for a given period using a Gumbel fit
    on daily maxima (m/s).
    """
    if series is None or series.empty:
        return None

    # Cleanup
    s = series.dropna()
    if s.empty:
        return None

    # Annual maxima grouped by calendar year
    annual_max = s.groupby(s.index.year).max()

    if len(annual_max) < min_years:
        print(
            f"  [Warning] Series too short ({len(annual_max)} years) "
            f"for a robust Gumbel fit (min {min_years} years)."
        )
        return None

    try:
        # Gumbel fit on annual maxima
        loc, scale = gumbel_r.fit(annual_max.values)
        p = 1.0 - 1.0 / float(return_period_years)
        rl = gumbel_r.ppf(p, loc=loc, scale=scale)
        return float(np.round(rl, 2))
    except Exception as e:
        print(f"  [Error] Gumbel fit failed: {e}")
        return None


# ============================================================
# 1. Fonctions utilitaires
# ============================================================

def _normalize_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize minimal expected columns (time, windspeed_mean/gust, wind_direction)
    without failing if some are missing.
    """
    df = df.copy()

    # Colonne temporelle
    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"], errors="coerce", utc=True)
    elif "date" in df.columns:
        df["time"] = pd.to_datetime(df["date"], errors="coerce", utc=True)
    else:
        # On laisse sans time ; les sections qui en ont besoin passeront
        return df

    # Normalize wind column names
    col_map = {}
    if "wind_speed" in df.columns and "windspeed_mean" not in df.columns:
        col_map["wind_speed"] = "windspeed_mean"
    if "wind_gust" in df.columns and "windspeed_gust" not in df.columns:
        col_map["wind_gust"] = "windspeed_gust"
    if col_map:
        df = df.rename(columns=col_map)

    # Tri temporel
    df = df.sort_values("time").reset_index(drop=True)

    return df


def _load_dataframes_from_csv(site_folder: str) -> Dict[str, pd.DataFrame]:
    """
    Load daily CSV files in the site folder and map them to a standard source key.
    Only daily files are loaded (e.g., era5_daily_*, not hourly).
    """
    prefix_mappings: List[Tuple[str, str]] = [
        ("meteostat1", "meteostat1"),
        ("meteostat2", "meteostat2"),
        ("noaa_station1", "noaa_station1"),
        ("noaa_station2", "noaa_station2"),
        ("noaa", "noaa"),
        ("openmeteo", "openmeteo"),
        ("nasa_power", "nasa_power"),
        ("era5_daily", "era5"),
        ("visualcrossing", "visualcrossing"),
    ]

    dataframes: Dict[str, pd.DataFrame] = {}

    for file in Path(site_folder).iterdir():
        if not file.is_file() or not file.name.endswith(".csv"):
            continue

        stem = file.stem

        key = None
        for prefix, src_key in prefix_mappings:
            if stem.startswith(prefix):
                key = src_key
                break

        if key is None:
            continue

        try:
            df = pd.read_csv(file)
        except Exception as e:
            print(f"  [Error] Failed to read CSV {file.name}: {e}")
            continue

        df = _normalize_dataframe_columns(df)
        dataframes[key] = df

    return dataframes


# ============================================================
# 2. Fonction principale : run_analysis_for_site
# ============================================================

def run_analysis_for_site(
    site_name: str,
    site_folder: str,
    site_config: dict,
    dataframes: Optional[Dict[str, pd.DataFrame]] = None,
    return_periods_years: Optional[Iterable[float]] = None,
) -> None:
    """Run the full analysis for one site.
    - Expects daily CSVs per source in site_folder (or in-memory DataFrames).
    - Uses building code thresholds from site_config (mean/gust 50y).
    - Computes coverage, stats, plots, extremes, roses, return levels.
    """
    print(f"=== Analysis for site: {site_name} ===")

    # ------------------------------------------------------------
    # 1. Building Code thresholds (from modele_sites.csv)
    # ------------------------------------------------------------
    bc_mean_threshold = _get_config_float(site_config, "building_code_windspeed_mean_50y", 25.0)
    bc_gust_threshold = _get_config_float(site_config, "building_code_windspeed_gust_50y", 25.0)


    print(f"Building Code threshold (mean wind) : {bc_mean_threshold:.2f} m/s")
    print(f"Building Code threshold (gust)     : {bc_gust_threshold:.2f} m/s")

    # Return periods to compute
    if return_periods_years is None:
        # dans la config, on peut stocker quelque chose comme "50,100,200"
        conf_rp = site_config.get("return_periods_years", None)
        if isinstance(conf_rp, str):
            try:
                return_periods_years = [float(x) for x in conf_rp.split(",") if x.strip()]
            except Exception:
                return_periods_years = [50.0]
        elif isinstance(conf_rp, (list, tuple)):
            return_periods_years = [float(x) for x in conf_rp]
        else:
            return_periods_years = [50.0]

    return_periods_years = list(return_periods_years)

    # Output folder for figures & tables
    output_dir = os.path.join(site_folder, "figures_and_tables")
    os.makedirs(output_dir, exist_ok=True)

    # ------------------------------------------------------------
    # 2. Load data (prefer in-memory DataFrames)
    # ------------------------------------------------------------
    if dataframes:
        print("Loading data from provided DataFrames...")
        normalized = {}
        for name, df in dataframes.items():
            # Skip empty / non-DataFrame entries
            if df is None:
                continue
            if not isinstance(df, pd.DataFrame):
                continue
            if df.empty:
                continue
            normalized[name] = _normalize_dataframe_columns(df)
        dataframes = normalized
    else:
        print("Loading data from daily CSV files...")
        dataframes = _load_dataframes_from_csv(site_folder)


    if not dataframes:
        print("No data found for this site. Analysis stopped.")
        return

    # On retire explicitement les sources vides
    dataframes = {
        name: df for name, df in dataframes.items()
        if isinstance(df, pd.DataFrame) and not df.empty
    }

    if not dataframes:
        print("All DataFrames are empty. Analysis stopped.")
        return

    # ------------------------------------------------------------
    # 2.b. Force ERA5 to use the aggregated daily series
    # ------------------------------------------------------------
    # If 'era5' is present and era5_daily_<site>.csv exists, replace the DataFrame
    # with the daily maxima version.
    if "era5" in dataframes:
        daily_path = os.path.join(site_folder, f"era5_daily_{site_name}.csv")
        if os.path.exists(daily_path):
            try:
                df_daily = pd.read_csv(daily_path)
                dataframes["era5"] = _normalize_dataframe_columns(df_daily)
                print("  [ERA5] Using daily series (era5_daily_*.csv) for analysis.")
            except Exception as e:
                print(
                    "  [ERA5] Error reading daily file, "
                    f"using provided series: {e}"
                )

    # Drop explicitly empty sources
    dataframes = {
        name: df for name, df in dataframes.items()
        if isinstance(df, pd.DataFrame) and not df.empty
    }

    # ------------------------------------------------------------
    # 3. Descriptive stats (mean wind)
    # ------------------------------------------------------------
    print("Computing descriptive statistics (mean wind)...")

    stats_rows = []
    skipped_sources = []

    for name, df in dataframes.items():
        if "windspeed_mean" not in df.columns or df["windspeed_mean"].dropna().shape[0] < 5:
            skipped_sources.append(name)
            continue

        desc = df["windspeed_mean"].describe(percentiles=[0.05, 0.25, 0.5, 0.75, 0.95])
        stats_rows.append(
            {
                "Source": name,
                "count": desc["count"],
                "mean": desc["mean"],
                "std": desc["std"],
                "min": desc["min"],
                "p05": desc["5%"],
                "p25": desc["25%"],
                "p50": desc["50%"],
                "p75": desc["75%"],
                "p95": desc["95%"],
                "max": desc["max"],
            }
        )

    if stats_rows:
        df_stats = pd.DataFrame(stats_rows)
        df_stats = df_stats.set_index("Source").round(2)
        df_stats = df_stats.rename(
            columns={
                "count": "Nb of days",
                "mean": "Mean (m/s)",
                "std": "Std dev (m/s)",
                "min": "Min (m/s)",
                "p05": "5th percentile (m/s)",
                "p25": "25th percentile (m/s)",
                "p50": "50th percentile (m/s)",
                "p75": "75th percentile (m/s)",
                "p95": "95th percentile (m/s)",
                "max": "Max (m/s)",
            }
        )
        stats_path = os.path.join(output_dir, "stats_windspeed_mean.csv")
        df_stats.to_csv(stats_path, index=True)
        print(f"  -> Saved stats: {stats_path}")
    else:
        print("  No DataFrame eligible for descriptive stats.")

    if skipped_sources:
        print("  Sources skipped for descriptive stats (not enough data or missing columns):")
        for s in skipped_sources:
            print(f"    - {s}")

    # ------------------------------------------------------------
    # 4. Data quality (coverage)
    # ------------------------------------------------------------
    print("Evaluating data quality / coverage...")

    coverage_rows = []
    for name, df in dataframes.items():
        if "time" not in df.columns:
            continue

        df_non_null_time = df.dropna(subset=["time"])
        if df_non_null_time.empty:
            continue

        time_min = df_non_null_time["time"].min()
        time_max = df_non_null_time["time"].max()
        nb_lignes = len(df_non_null_time)

        if "windspeed_mean" in df_non_null_time.columns:
            coverage_mean = df_non_null_time["windspeed_mean"].notna().mean() * 100.0
        else:
            coverage_mean = np.nan

        if "windspeed_gust" in df_non_null_time.columns:
            coverage_gust = df_non_null_time["windspeed_gust"].notna().mean() * 100.0
        else:
            coverage_gust = np.nan

        coverage_rows.append(
            {
                "Source": name,
                "First date": time_min.date(),
                "Last date": time_max.date(),
                "Row count": nb_lignes,
                "Mean wind coverage (%)": round(coverage_mean, 1),
                "Gust coverage (%)": round(coverage_gust, 1),
            }
        )

    if coverage_rows:
        df_cov = pd.DataFrame(coverage_rows)
        cov_path = os.path.join(output_dir, "resume_qualite.csv")
        df_cov.to_csv(cov_path, index=False)
        print(f"  -> Coverage saved: {cov_path}")
    else:
        print("  Not enough data to compute coverage.")

    # ------------------------------------------------------------
    # 5. Histograms for mean wind / gust distributions
    # ------------------------------------------------------------
    print("Plotting distribution histograms...")

    def plot_histograms(variable: str, title: str, filename: str, bc_threshold: float):
        # Build list of (source, series) for valid sources
        valid = []
        for name, df in dataframes.items():
            if variable in df.columns:
                series = df[variable].dropna()
                if len(series) >= 10:
                    valid.append((name, series))

        if not valid:
            print(f"  No histogram plotted for {variable} (not enough data).")
            return

        n = len(valid)
        ncols = 2
        nrows = int(np.ceil(n / ncols))

        fig, axes = plt.subplots(
            nrows=nrows,
            ncols=ncols,
            figsize=(6 * ncols, 3.5 * nrows),
            squeeze=False,
        )

        for ax in axes.flat:
            ax.set_visible(False)

        for idx, (name, series) in enumerate(valid):
            r = idx // ncols
            c = idx % ncols
            ax = axes[r][c]
            ax.set_visible(True)

            sns.histplot(
                series,
                bins=40,
                stat="density",
                kde=False,
                ax=ax,
            )
            ax.axvline(bc_threshold, color="red", linestyle="--", linewidth=1.2)
            ax.set_title(f"{name}", fontsize=10)
            ax.set_xlabel(title)
            ax.set_ylabel("Density")

        fig.suptitle(f"Distribution des {title.lower()} par source", fontsize=13)
        fig.tight_layout(rect=[0, 0.03, 1, 0.95])

        outpath = os.path.join(output_dir, filename)
        fig.savefig(outpath, bbox_inches="tight")
        plt.close(fig)
        print(f"  -> Histograms {variable} saved: {outpath}")

    plot_histograms(
        variable="windspeed_mean",
        title="mean wind speeds (m/s)",
        filename="histogrammes_windspeed_mean.png",
        bc_threshold=bc_mean_threshold,
    )

    plot_histograms(
        variable="windspeed_gust",
        title="wind gust speeds (m/s)",
        filename="histogrammes_windspeed_gust.png",
        bc_threshold=bc_gust_threshold,
    )

    # ------------------------------------------------------------
    # 6. Boxplots + days above Building Code thresholds
    # ------------------------------------------------------------
    print("Plotting boxplots and counting extreme days...")

    def process_outliers(
        dataframes: Dict[str, pd.DataFrame],
        varname: str,
        title_label: str,
        bc_threshold: float,
        filename_box: str,
        filename_outliers_hist: str,
    ):
        # Concatenation
        all_rows = []
        for name, df in dataframes.items():
            if varname in df.columns:
                s = df[varname].dropna()
                if len(s) > 0:
                    all_rows.append(pd.DataFrame({"Source": name, varname: s.values}))

        if not all_rows:
            print(f"  No boxplot plotted for {varname} (not enough data).")
            return

        df_all = pd.concat(all_rows, ignore_index=True)

        # Boxplot
        plt.figure(figsize=(8, 5))
        sns.boxplot(
            data=df_all,
            x="Source",
            y=varname,
            width=0.6,
            showfliers=False,
        )
        plt.axhline(bc_threshold, color="red", linestyle="--", linewidth=1.2)
        plt.ylabel(title_label)
        plt.xticks(rotation=20, ha="right")
        plt.title(f"Distribution des {title_label.lower()} par source")
        plt.tight_layout()
        out_box = os.path.join(output_dir, filename_box)
        plt.savefig(out_box, bbox_inches="tight")
        plt.close()
        print(f"  -> Boxplot saved: {out_box}")

        # Days above BC threshold
        df_extreme = df_all[df_all[varname] > bc_threshold]
        if df_extreme.empty:
            print(f"  No days above BC threshold for {varname}.")
            return

        counts = df_extreme["Source"].value_counts().sort_index()

        plt.figure(figsize=(6, 4))
        counts.plot(kind="bar")
        plt.ylabel("Number of days above threshold")
        plt.title(f"Extreme days ({title_label}) by source\n(>{bc_threshold:.1f} m/s)")
        plt.xticks(rotation=20, ha="right")
        plt.tight_layout()
        out_hist = os.path.join(output_dir, filename_outliers_hist)
        plt.savefig(out_hist, bbox_inches="tight")
        plt.close()
        print(f"  -> Extreme-days histogram saved: {out_hist}")

    process_outliers(
        dataframes=dataframes,
        varname="windspeed_mean",
        title_label="mean wind speeds (m/s)",
        bc_threshold=bc_mean_threshold,
        filename_box="boxplot_windspeed_mean.png",
        filename_outliers_hist="outliers_hist_windspeed_mean.png",
    )

    process_outliers(
        dataframes=dataframes,
        varname="windspeed_gust",
        title_label="wind gust speeds (m/s)",
        bc_threshold=bc_gust_threshold,
        filename_box="boxplot_windspeed_gust.png",
        filename_outliers_hist="outliers_hist_windspeed_gust.png",
    )

    # ------------------------------------------------------------
    # 7. Full time series (mean wind / gusts)
    # ------------------------------------------------------------
    print("Plotting full daily time series...")

    def plot_timeseries_all_sources(
        dataframes: Dict[str, pd.DataFrame],
        variable: str,
        bc_threshold: float,
        site_name: str,
        output_dir: str,
    ):
        plt.figure(figsize=(14, 6))
        found = False
        for name, df in dataframes.items():
            if variable not in df.columns or "time" not in df.columns:
                continue
            s = df.dropna(subset=["time", variable])
            if s.empty:
                continue
            plt.plot(s["time"], s[variable], label=name, linewidth=0.9)
            found = True

        if not found:
            plt.close()
            print(f"  No time series plotted for {variable}.")
            return

        plt.axhline(bc_threshold, color="red", linestyle="--", linewidth=1.2)
        plt.xlabel("Date (UTC)")
        plt.ylabel(f"{variable} (m/s)")
        plt.title(f"Daily time series of {variable} - {site_name}")
        plt.legend(loc="upper right", fontsize=8)
        plt.tight_layout()
        outpath = os.path.join(output_dir, f"time_series_{variable}.png")
        plt.savefig(outpath, bbox_inches="tight")
        plt.close()
        print(f"  -> Time series saved: {outpath}")

    plot_timeseries_all_sources(
        dataframes=dataframes,
        variable="windspeed_mean",
        bc_threshold=bc_mean_threshold,
        site_name=site_name,
        output_dir=output_dir,
    )

    plot_timeseries_all_sources(
        dataframes=dataframes,
        variable="windspeed_gust",
        bc_threshold=bc_gust_threshold,
        site_name=site_name,
        output_dir=output_dir,
    )

    # ------------------------------------------------------------
    # 8. Directional wind roses (max + occurrences)
    # ------------------------------------------------------------
    print("Computing and plotting wind roses (mean wind)...")

    def _compute_direction_bins(series_dir: pd.Series, series_ws: pd.Series, bin_width_deg: int = 20):
        """
        Group data by direction bins of width bin_width_deg.

        Returns:
        - centers_deg : bin centers (degrees)
        - max_speeds  : max windspeed_mean per bin
        - counts      : occurrences per bin
        """
        df = pd.DataFrame({"dir": series_dir, "ws": series_ws}).dropna()
        if df.empty:
            return np.array([]), np.array([]), np.array([])

        # Reduce direction into [0, 360)
        df["dir"] = df["dir"] % 360.0

        edges = np.arange(0, 360 + bin_width_deg, bin_width_deg)
        centers = edges[:-1] + bin_width_deg / 2.0

        max_speeds = []
        counts = []
        for i in range(len(edges) - 1):
            low = edges[i]
            high = edges[i + 1]
            # Last bin [340,360] inclusive on 360
            if i == len(edges) - 2:
                mask = (df["dir"] >= low) & (df["dir"] <= high)
            else:
                mask = (df["dir"] >= low) & (df["dir"] < high)

            subset = df.loc[mask, "ws"]
            if subset.empty:
                max_speeds.append(0.0)
                counts.append(0)
            else:
                max_speeds.append(float(subset.max()))
                counts.append(int(subset.shape[0]))

        return np.deg2rad(centers), np.array(max_speeds), np.array(counts)

    def plot_wind_rose_max_speed(
        dataframes: Dict[str, pd.DataFrame],
        site_name: str,
        output_dir: str,
        bin_width_deg: int = 20,
    ):
        """
        For each source:
            - compute daily max speed per direction bin,
            - plot wind rose where radius = max speed (m/s) per bin.
        """
        for name, df in dataframes.items():
            if "wind_direction" not in df.columns or "windspeed_mean" not in df.columns:
                continue

            dirs = df["wind_direction"].astype(float)
            ws = df["windspeed_mean"].astype(float)

            theta, max_speeds, counts = _compute_direction_bins(dirs, ws, bin_width_deg)
            if theta.size == 0:
                continue

            fig = plt.figure(figsize=(6, 6))
            ax = plt.subplot(111, polar=True)
            ax.set_theta_zero_location("N")
            ax.set_theta_direction(-1)  # clockwise

            width = np.deg2rad(bin_width_deg) * 0.9  # slight overlap
            ax.bar(theta, max_speeds, width=width, align="center", edgecolor="black")

            ax.set_title(f"Wind rose - max speed by direction\n{site_name} - {name}", fontsize=11)
            ax.set_rlabel_position(225)
            ax.set_ylabel("Max speed (m/s)")

            outpath = os.path.join(output_dir, f"rose_max_windspeed_{name}.png")
            plt.tight_layout()
            plt.savefig(outpath, bbox_inches="tight")
            plt.close()
            print(f"  -> Wind rose (max) saved: {outpath}")

    def plot_wind_rose_frequency(
        dataframes: Dict[str, pd.DataFrame],
        site_name: str,
        output_dir: str,
        bin_width_deg: int = 20,
    ):
        """
        For each source:
            - count occurrences per direction bin,
            - plot wind rose where radius = number of occurrences.
        """
        for name, df in dataframes.items():
            if "wind_direction" not in df.columns or "windspeed_mean" not in df.columns:
                continue

            dirs = df["wind_direction"].astype(float)
            ws = df["windspeed_mean"].astype(float)

            theta, _, counts = _compute_direction_bins(dirs, ws, bin_width_deg)
            if theta.size == 0:
                continue

            fig = plt.figure(figsize=(6, 6))
            ax = plt.subplot(111, polar=True)
            ax.set_theta_zero_location("N")
            ax.set_theta_direction(-1)

            width = np.deg2rad(bin_width_deg) * 0.9
            ax.bar(theta, counts, width=width, align="center", edgecolor="black")

            ax.set_title(
                f"Wind rose - number of occurrences per direction\n{site_name} - {name}",
                fontsize=11,
            )
            ax.set_rlabel_position(225)
            ax.set_ylabel("Number of days")

            outpath = os.path.join(output_dir, f"rose_frequency_{name}.png")
            plt.tight_layout()
            plt.savefig(outpath, bbox_inches="tight")
            plt.close()
            print(f"  -> Wind rose (occurrences) saved: {outpath}")

    plot_wind_rose_max_speed(
        dataframes=dataframes,
        site_name=site_name,
        output_dir=output_dir,
        bin_width_deg=20,
    )

    plot_wind_rose_frequency(
        dataframes=dataframes,
        site_name=site_name,
        output_dir=output_dir,
        bin_width_deg=20,
    )

    # ------------------------------------------------------------
    # 9. Extreme days (mean wind / gusts) above Building Code thresholds
    # ------------------------------------------------------------
    print("Analyzing extreme days above Building Code thresholds...")

    def analyze_extreme_days(
        dataframes: Dict[str, pd.DataFrame],
        varname: str,
        bc_threshold: float,
        output_dir: str,
    ):
        """
        For each source, identify days with varname > BC threshold,
        compute indicators and export tables.
        """
        summary_rows = []
        per_year_rows = []

        for name, df in dataframes.items():
            if varname not in df.columns or "time" not in df.columns:
                continue

            d = df.dropna(subset=["time", varname]).copy()
            if d.empty:
                continue

            d["year"] = d["time"].dt.year
            extreme = d[d[varname] > bc_threshold]

            if extreme.empty:
                # Keep a row with 0 extreme days for completeness
                summary_rows.append(
                    {
                        "Source": name,
                        "Variable": varname,
                        "BC_threshold (m/s)": bc_threshold,
                        "Nb_extreme_days": 0,
                        "Max_extreme_value (m/s)": np.nan,
                        "Date_max_value": "",
                    }
                )
                continue

            nb_extreme = len(extreme)
            max_val = float(extreme[varname].max())
            idx_max = extreme[varname].idxmax()
            date_max = extreme.loc[idx_max, "time"].date()

            summary_rows.append(
                {
                    "Source": name,
                    "Variable": varname,
                    "BC_threshold (m/s)": bc_threshold,
                    "Nb_extreme_days": nb_extreme,
                    "Max_extreme_value (m/s)": max_val,
                    "Date_max_value": date_max,
                }
            )

            # Per-year counts
            yearly_counts = extreme.groupby("year").size()
            for year, count in yearly_counts.items():
                per_year_rows.append(
                    {
                        "Source": name,
                        "Variable": varname,
                        "Year": int(year),
                        "Nb_extreme_days": int(count),
                    }
                )

        if summary_rows:
            df_summary = pd.DataFrame(summary_rows)

            # File names per variable
            if varname == "windspeed_gust":
                summary_name = "rafales_extremes_resume.csv"
            else:
                summary_name = "vent_moyen_extremes_resume.csv"

            out_summary = os.path.join(output_dir, summary_name)
            df_summary.to_csv(out_summary, index=False)
            print(f"  -> Extreme days summary ({varname}): {out_summary}")

        if per_year_rows:
            df_year = pd.DataFrame(per_year_rows)
            # Pivot: index = year, columns = source, values = Nb_extreme_days
            pivot = df_year.pivot_table(
                index="Year",
                columns="Source",
                values="Nb_extreme_days",
                aggfunc="sum",
                fill_value=0,
            ).sort_index()

            if varname == "windspeed_gust":
                year_name = "rafales_extremes_par_an.csv"
            else:
                year_name = "vent_moyen_extremes_par_an.csv"

            out_year = os.path.join(output_dir, year_name)
            pivot.to_csv(out_year)
            print(f"  -> Extreme days per year ({varname}): {out_year}")

    analyze_extreme_days(
        dataframes=dataframes,
        varname="windspeed_mean",
        bc_threshold=bc_mean_threshold,
        output_dir=output_dir,
    )

    analyze_extreme_days(
        dataframes=dataframes,
        varname="windspeed_gust",
        bc_threshold=bc_gust_threshold,
        output_dir=output_dir,
    )

    # ------------------------------------------------------------
    # 10. Return periods (Gumbel) for all sources
    # ------------------------------------------------------------
    print("Computing return levels (Gumbel) for all sources...")

    def export_annual_max(series: pd.Series, output_path: str):
        """
        Export annual maxima of a series as a simple CSV: Year, Max_value.
        """
        s = series.dropna()
        if s.empty:
            return False

        annual_max = s.groupby(s.index.year).max()
        df_annual = pd.DataFrame(
            {"Year": annual_max.index.astype(int), "Max_value (m/s)": annual_max.values}
        )
        df_annual.to_csv(output_path, index=False)
        return True

    results_rows = []

    for name, df in dataframes.items():
        if "time" not in df.columns:
            continue

        df_non_null_time = df.dropna(subset=["time"]).copy()
        df_non_null_time = df_non_null_time.set_index("time")

        for varname, bc_threshold in [
            ("windspeed_mean", bc_mean_threshold),
            ("windspeed_gust", bc_gust_threshold),
        ]:
            if varname not in df_non_null_time.columns:
                continue

            series = df_non_null_time[varname].astype(float)

            # Export des maxima annuels pour diagnostic
            out_annual = os.path.join(
                output_dir, f"annual_max_{varname}_{name}.csv"
            )
            export_annual_max(series, out_annual)

            # Return levels for all requested periods
            for rp in return_periods_years:
                rl = compute_return_level(series, return_period_years=rp)
                results_rows.append(
                    {
                        "Source": name,
                        "Variable": varname,
                        "Return_period (years)": rp,
                        "Return_level (m/s)": rl,
                        "BC_threshold (m/s)": bc_threshold,
                    }
                )

    if results_rows:
        df_ret = pd.DataFrame(results_rows)
        ret_all_path = os.path.join(output_dir, "return_periods_gumbel.csv")
        df_ret.to_csv(ret_all_path, index=False)
        print(f"  -> Return levels (all periods): {ret_all_path}")

        # v1 compatibility: still export a 50y file when requested
        if any(abs(rp - 50.0) < 1e-6 for rp in return_periods_years):
            df_50 = df_ret[df_ret["Return_period (years)"] == 50.0].copy()
            ret_50_path = os.path.join(output_dir, "return_period_50y.csv")
            df_50.to_csv(ret_50_path, index=False)
            print(f"  -> v1 compatibility file (50y): {ret_50_path}")

    # ------------------------------------------------------------
    # 11. Final site summary (currently inactive)
    # ------------------------------------------------------------
    """
    # Disabled on purpose.
    # Previous version produced site_summary_*.csv combining multiple indicators
    # in a format considered not very useful.
    # Can be rewritten later if needed from df_cov / df_stats / df_ret.
    """

    print(f"=== Analysis finished for site: {site_name} ===")
