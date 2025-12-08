# ============================================================
# analysis_runner.py
# Analyse complète des données météo pour un site (v1-audit)
#
# Hypothèses clés (pipeline v1-audit) :
# - Tous les fetchers produisent des séries JOURNALIÈRES.
# - "windspeed_mean" = vitesse maximale journalière du vent moyen à 10 m (m/s).
# - "windspeed_gust" = vitesse maximale journalière des rafales (m/s) quand disponible.
# - Les données sont en UTC.
# ============================================================

import os
from pathlib import Path
from typing import Dict, Optional, Iterable, List, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import gumbel_r

# Style global sobre
plt.rcParams["figure.dpi"] = 120
plt.rcParams["axes.grid"] = True
plt.rcParams["grid.alpha"] = 0.3
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False
sns.set_style("whitegrid")

def _get_config_float(site_config, key, default):
    """
    Récupère une valeur float dans site_config en gérant les NaN / chaînes vides.
    Si la valeur est absente ou non numérique, retourne default.
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
# 0. Fonction générique : niveaux de retour (Gumbel)
# ============================================================

def compute_return_level(
    series: pd.Series,
    return_period_years: float = 50.0,
    min_years: int = 10,
) -> Optional[float]:
    """
    Calcule un niveau de retour pour une période donnée à partir d'une série
    de maxima journaliers (m/s) en s'appuyant sur une loi de Gumbel.

    Paramètres
    ----------
    series : pd.Series
        Série de vitesses (m/s), index daté (datetime64[ns]).
        On suppose que la série représente déjà des maxima journaliers.
    return_period_years : float
        Période de retour souhaitée (en années), ex. 50, 100, 200.
    min_years : int
        Nombre minimal d'années de données de maxima annuels pour faire le fit.

    Retour
    ------
    float ou None
        Niveau de retour (m/s) arrondi à 0.01, ou None si non calculable.
    """
    if series is None or series.empty:
        return None

    # Nettoyage
    s = series.dropna()
    if s.empty:
        return None

    # Maxima annuels
    # On regroupe par année civile basée sur l'index temporel
    annual_max = s.groupby(s.index.year).max()

    if len(annual_max) < min_years:
        print(
            f"  [Avertissement] Série trop courte ({len(annual_max)} ans) "
            f"pour un ajustement Gumbel robuste (min {min_years} ans)."
        )
        return None

    try:
        # Ajustement Gumbel sur les maxima annuels
        loc, scale = gumbel_r.fit(annual_max.values)
        p = 1.0 - 1.0 / float(return_period_years)
        rl = gumbel_r.ppf(p, loc=loc, scale=scale)
        return float(np.round(rl, 2))
    except Exception as e:
        print(f"  [Erreur] Ajustement Gumbel impossible : {e}")
        return None


# ============================================================
# 1. Fonctions utilitaires
# ============================================================

def _normalize_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Harmonise les colonnes minimales attendues :
    - time (datetime)
    - windspeed_mean
    - windspeed_gust
    - wind_direction

    Sans lever d'erreur si certaines colonnes sont absentes.
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

    # Normalisation des noms de colonnes vent
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
    Charge les CSV journaliers présents dans le dossier du site et les
    associe à une clé de source standardisée.

    Pour éviter les confusions, on ne charge que les fichiers journaliers
    (par exemple 'era5_daily_*' mais pas 'era5_*' horaire).

    Mapping actuel des préfixes de fichiers -> clé de source :
      - meteostat1_*      -> 'meteostat1'
      - meteostat2_*      -> 'meteostat2'
      - noaa_station1_*   -> 'noaa_station1'
      - noaa_station2_*   -> 'noaa_station2'
      - noaa_*            -> 'noaa'
      - openmeteo_*       -> 'openmeteo'
      - nasa_power_*      -> 'nasa_power'
      - era5_daily_*      -> 'era5'
      - visualcrossing_*  -> 'visualcrossing'

    Toute autre CSV est ignorée dans ce pipeline.
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
            print(f"  [Erreur] Lecture CSV échouée pour {file.name}: {e}")
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
    """
    Analyse complète des données pour un site.

    Paramètres
    ----------
    site_name : str
        Nom du site (utilisé dans les fichiers de sortie).
    site_folder : str
        Dossier de travail du site (CSV d'entrée + figures de sortie).
    site_config : dict
        Config du site (tirée de modele_sites.csv) incluant notamment :
        - building_code_windspeed_mean_50y
        - building_code_windspeed_gust_50y
        - éventuellement une clé 'return_periods_years' (liste de périodes).
    dataframes : dict[str, DataFrame] ou None
        Si fourni et non vide, permet de passer directement les DataFrames
        déjà chargés en mémoire. Sinon, les CSV sont relus dans site_folder.
    return_periods_years : Iterable[float] ou None
        Liste des périodes de retour à calculer (ex. [50, 100, 200]).
        Si None, on cherche dans site_config['return_periods_years'] ou
        on utilise [50] par défaut.
    """
    print(f"=== Analyse pour le site : {site_name} ===")

    # ------------------------------------------------------------
    # 1. Seuils Building Code (fournis par modele_sites.csv)
    # ------------------------------------------------------------
    bc_mean_threshold = _get_config_float(site_config, "building_code_windspeed_mean_50y", 25.0)
    bc_gust_threshold = _get_config_float(site_config, "building_code_windspeed_gust_50y", 25.0)


    print(f"Seuil Building Code (vent moyen) : {bc_mean_threshold:.2f} m/s")
    print(f"Seuil Building Code (rafale)     : {bc_gust_threshold:.2f} m/s")

    # Périodes de retour à calculer
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

    # Dossier de sortie pour figures & tableaux
    output_dir = os.path.join(site_folder, "figures_and_tables")
    os.makedirs(output_dir, exist_ok=True)

    # ------------------------------------------------------------
    # 2. Chargement des données (en priorité via dataframes)
    # ------------------------------------------------------------
    if dataframes:
        print("Chargement des données depuis les DataFrames fournis...")
        normalized = {}
        for name, df in dataframes.items():
            # On ignore toutes les entrées vides ou non-DataFrame
            if df is None:
                continue
            if not isinstance(df, pd.DataFrame):
                continue
            if df.empty:
                continue
            normalized[name] = _normalize_dataframe_columns(df)
        dataframes = normalized
    else:
        print("Chargement des données depuis les CSV journaliers...")
        dataframes = _load_dataframes_from_csv(site_folder)


    if not dataframes:
        print("Aucune donnée trouvée pour ce site. Analyse interrompue.")
        return

    # On retire explicitement les sources vides
    dataframes = {
        name: df for name, df in dataframes.items()
        if isinstance(df, pd.DataFrame) and not df.empty
    }

    if not dataframes:
        print("Tous les DataFrames sont vides. Analyse interrompue.")
        return

    # ------------------------------------------------------------
    # 2.b. Forcer ERA5 à utiliser la série journalière agrégée
    # ------------------------------------------------------------
    # Si une source 'era5' est présente et que le fichier
    # era5_daily_<site>.csv existe, on remplace le DataFrame
    # par la version journalière (maxima journaliers).
    if "era5" in dataframes:
        daily_path = os.path.join(site_folder, f"era5_daily_{site_name}.csv")
        if os.path.exists(daily_path):
            try:
                df_daily = pd.read_csv(daily_path)
                dataframes["era5"] = _normalize_dataframe_columns(df_daily)
                print("  [ERA5] Utilisation des données journalières (era5_daily_*.csv) pour l'analyse.")
            except Exception as e:
                print(
                    "  [ERA5] Erreur lecture fichier journalier, "
                    f"utilisation de la série fournie : {e}"
                )

    # On retire explicitement les sources vides
    dataframes = {
        name: df for name, df in dataframes.items()
        if isinstance(df, pd.DataFrame) and not df.empty
    }

    # ------------------------------------------------------------
    # 3. Statistiques descriptives (vent moyen)
    # ------------------------------------------------------------
    print("Calcul des statistiques descriptives (vent moyen)...")

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
                "count": "Nb de jours",
                "mean": "Moyenne (m/s)",
                "std": "Écart-type (m/s)",
                "min": "Min (m/s)",
                "p05": "5e percentile (m/s)",
                "p25": "25e percentile (m/s)",
                "p50": "50e percentile (m/s)",
                "p75": "75e percentile (m/s)",
                "p95": "95e percentile (m/s)",
                "max": "Max (m/s)",
            }
        )
        stats_path = os.path.join(output_dir, "stats_windspeed_mean.csv")
        df_stats.to_csv(stats_path, index=True)
        print(f"  → Statistiques sauvegardées : {stats_path}")
    else:
        print("  Aucun DataFrame éligible pour les stats descriptives.")

    if skipped_sources:
        print("  Sources ignorées pour les stats descriptives (trop peu de données ou colonne absente) :")
        for s in skipped_sources:
            print(f"    - {s}")

    # ------------------------------------------------------------
    # 4. Qualité des données (couverture)
    # ------------------------------------------------------------
    print("Évaluation de la qualité / couverture des données...")

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
                "Première date": time_min.date(),
                "Dernière date": time_max.date(),
                "Nombre de lignes": nb_lignes,
                "Couverture vent moyen (%)": round(coverage_mean, 1),
                "Couverture rafales (%)": round(coverage_gust, 1),
            }
        )

    if coverage_rows:
        df_cov = pd.DataFrame(coverage_rows)
        cov_path = os.path.join(output_dir, "resume_qualite.csv")
        df_cov.to_csv(cov_path, index=False)
        print(f"  → Taux de couverture sauvegardé : {cov_path}")
    else:
        print("  Pas de données suffisantes pour calculer la couverture.")

    # ------------------------------------------------------------
    # 5. Histogrammes distributions vent moyen / rafales
    # ------------------------------------------------------------
    print("Tracé des histogrammes de distributions...")

    def plot_histograms(variable: str, title: str, filename: str, bc_threshold: float):
        # On prépare une liste (source, série) pour les sources valides
        valid = []
        for name, df in dataframes.items():
            if variable in df.columns:
                series = df[variable].dropna()
                if len(series) >= 10:
                    valid.append((name, series))

        if not valid:
            print(f"  Aucun histogramme tracé pour {variable} (données insuffisantes).")
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
            ax.set_ylabel("Densité")

        fig.suptitle(f"Distribution des {title.lower()} par source", fontsize=13)
        fig.tight_layout(rect=[0, 0.03, 1, 0.95])

        outpath = os.path.join(output_dir, filename)
        fig.savefig(outpath, bbox_inches="tight")
        plt.close(fig)
        print(f"  → Histogrammes {variable} sauvegardés : {outpath}")

    plot_histograms(
        variable="windspeed_mean",
        title="vitesses de vent moyen (m/s)",
        filename="histogrammes_windspeed_mean.png",
        bc_threshold=bc_mean_threshold,
    )

    plot_histograms(
        variable="windspeed_gust",
        title="vitesses de vent en rafale (m/s)",
        filename="histogrammes_windspeed_gust.png",
        bc_threshold=bc_gust_threshold,
    )

    # ------------------------------------------------------------
    # 6. Boxplots + jours au-dessus du Building Code
    # ------------------------------------------------------------
    print("Tracé des boxplots et comptage des jours extrêmes...")

    def process_outliers(
        dataframes: Dict[str, pd.DataFrame],
        varname: str,
        title_label: str,
        bc_threshold: float,
        filename_box: str,
        filename_outliers_hist: str,
    ):
        # Concaténation
        all_rows = []
        for name, df in dataframes.items():
            if varname in df.columns:
                s = df[varname].dropna()
                if len(s) > 0:
                    all_rows.append(pd.DataFrame({"Source": name, varname: s.values}))

        if not all_rows:
            print(f"  Aucun boxplot tracé pour {varname} (données insuffisantes).")
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
        print(f"  → Boxplot {varname} sauvegardé : {out_box}")

        # Jours au-dessus du seuil BC
        df_extreme = df_all[df_all[varname] > bc_threshold]
        if df_extreme.empty:
            print(f"  Aucun jour au-dessus du seuil BC pour {varname}.")
            return

        counts = df_extreme["Source"].value_counts().sort_index()

        plt.figure(figsize=(6, 4))
        counts.plot(kind="bar")
        plt.ylabel("Nombre de jours au-dessus du seuil")
        plt.title(f"Jours extrêmes ({title_label}) par source\n(>{bc_threshold:.1f} m/s)")
        plt.xticks(rotation=20, ha="right")
        plt.tight_layout()
        out_hist = os.path.join(output_dir, filename_outliers_hist)
        plt.savefig(out_hist, bbox_inches="tight")
        plt.close()
        print(f"  → Histogramme de jours extrêmes {varname} sauvegardé : {out_hist}")

    process_outliers(
        dataframes=dataframes,
        varname="windspeed_mean",
        title_label="vitesses de vent moyen (m/s)",
        bc_threshold=bc_mean_threshold,
        filename_box="boxplot_windspeed_mean.png",
        filename_outliers_hist="outliers_hist_windspeed_mean.png",
    )

    process_outliers(
        dataframes=dataframes,
        varname="windspeed_gust",
        title_label="vitesses de vent en rafale (m/s)",
        bc_threshold=bc_gust_threshold,
        filename_box="boxplot_windspeed_gust.png",
        filename_outliers_hist="outliers_hist_windspeed_gust.png",
    )

    # ------------------------------------------------------------
    # 7. Séries temporelles complètes (vent moyen / rafales)
    # ------------------------------------------------------------
    print("Tracé des séries temporelles complètes (journalières)...")

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
            print(f"  Aucune série temporelle tracée pour {variable}.")
            return

        plt.axhline(bc_threshold, color="red", linestyle="--", linewidth=1.2)
        plt.xlabel("Date (UTC)")
        plt.ylabel(f"{variable} (m/s)")
        plt.title(f"Séries temporelles journalières de {variable} – {site_name}")
        plt.legend(loc="upper right", fontsize=8)
        plt.tight_layout()
        outpath = os.path.join(output_dir, f"time_series_{variable}.png")
        plt.savefig(outpath, bbox_inches="tight")
        plt.close()
        print(f"  → Série temporelle {variable} sauvegardée : {outpath}")

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
    # 8. Roses des vents directionnelles (max + occurrences)
    # ------------------------------------------------------------
    print("Calcul et tracé des roses des vents (vent moyen)...")

    def _compute_direction_bins(series_dir: pd.Series, series_ws: pd.Series, bin_width_deg: int = 20):
        """
        Regroupe les données par intervalles de direction de largeur bin_width_deg.

        Retourne :
        - centers_deg : centre de chaque bin (en degrés)
        - max_speeds  : vitesse max (windspeed_mean) dans chaque bin
        - counts      : nombre d'occurrences dans chaque bin
        """
        df = pd.DataFrame({"dir": series_dir, "ws": series_ws}).dropna()
        if df.empty:
            return np.array([]), np.array([]), np.array([])

        # Réduction de dir dans [0,360)
        df["dir"] = df["dir"] % 360.0

        edges = np.arange(0, 360 + bin_width_deg, bin_width_deg)
        centers = edges[:-1] + bin_width_deg / 2.0

        max_speeds = []
        counts = []
        for i in range(len(edges) - 1):
            low = edges[i]
            high = edges[i + 1]
            # Dernier bin [340,360] inclusif sur 360
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
        Pour chaque source :
            - calcule la vitesse maximale journalière par intervalle directionnel,
            - trace une rose des vents où le rayon = vitesse max (m/s)
              pour chaque bin de direction.
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
            ax.set_theta_direction(-1)  # sens horaire

            width = np.deg2rad(bin_width_deg) * 0.9  # léger recouvrement
            ax.bar(theta, max_speeds, width=width, align="center", edgecolor="black")

            ax.set_title(
                f"Rose des vents – vitesses max par direction\n"
                f"{site_name} – {name}",
                fontsize=11,
            )
            ax.set_rlabel_position(225)
            ax.set_ylabel("Vitesse maximale (m/s)")

            outpath = os.path.join(output_dir, f"rose_max_windspeed_{name}.png")
            plt.tight_layout()
            plt.savefig(outpath, bbox_inches="tight")
            plt.close()
            print(f"  → Rose des vents (max) sauvegardée : {outpath}")

    def plot_wind_rose_frequency(
        dataframes: Dict[str, pd.DataFrame],
        site_name: str,
        output_dir: str,
        bin_width_deg: int = 20,
    ):
        """
        Pour chaque source :
            - compte le nombre d'occurrences par bin directionnel,
            - trace une rose des vents où le rayon = nombre d'occurrences.
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
                f"Rose des vents – nombre d'occurrences par direction\n"
                f"{site_name} – {name}",
                fontsize=11,
            )
            ax.set_rlabel_position(225)
            ax.set_ylabel("Nombre de jours")

            outpath = os.path.join(output_dir, f"rose_frequency_{name}.png")
            plt.tight_layout()
            plt.savefig(outpath, bbox_inches="tight")
            plt.close()
            print(f"  → Rose des vents (occurrences) sauvegardée : {outpath}")

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
    # 9. Jours extrêmes (vent moyen / rafales) au-dessus du Building Code
    # ------------------------------------------------------------
    print("Analyse des jours extrêmes (au-dessus des seuils Building Code)...")

    def analyse_jours_extremes(
        dataframes: Dict[str, pd.DataFrame],
        varname: str,
        bc_threshold: float,
        output_dir: str,
    ):
        """
        Pour chaque source, identifie les jours où varname > seuil BC,
        calcule quelques indicateurs et produit des tableaux.
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
                # On peut quand même garder une ligne avec 0 jour extrême
                summary_rows.append(
                    {
                        "Source": name,
                        "Variable": varname,
                        "Seuil_BC (m/s)": bc_threshold,
                        "Nb_jours_extremes": 0,
                        "Valeur_max_extreme (m/s)": np.nan,
                        "Date_valeur_max": "",
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
                    "Seuil_BC (m/s)": bc_threshold,
                    "Nb_jours_extremes": nb_extreme,
                    "Valeur_max_extreme (m/s)": max_val,
                    "Date_valeur_max": date_max,
                }
            )

            # Comptage par année
            yearly_counts = extreme.groupby("year").size()
            for year, count in yearly_counts.items():
                per_year_rows.append(
                    {
                        "Source": name,
                        "Variable": varname,
                        "Année": int(year),
                        "Nb_jours_extremes": int(count),
                    }
                )

        if summary_rows:
            df_summary = pd.DataFrame(summary_rows)

            # Nom des fichiers suivant la variable
            if varname == "windspeed_gust":
                summary_name = "rafales_extremes_resume.csv"
            else:
                summary_name = "vent_moyen_extremes_resume.csv"

            out_summary = os.path.join(output_dir, summary_name)
            df_summary.to_csv(out_summary, index=False)
            print(f"  → Résumé jours extrêmes ({varname}) : {out_summary}")

        if per_year_rows:
            df_year = pd.DataFrame(per_year_rows)
            # Tableau pivot : index = année, colonnes = source, valeurs = nb_jours_extremes
            pivot = df_year.pivot_table(
                index="Année",
                columns="Source",
                values="Nb_jours_extremes",
                aggfunc="sum",
                fill_value=0,
            ).sort_index()

            if varname == "windspeed_gust":
                year_name = "rafales_extremes_par_an.csv"
            else:
                year_name = "vent_moyen_extremes_par_an.csv"

            out_year = os.path.join(output_dir, year_name)
            pivot.to_csv(out_year)
            print(f"  → Jours extrêmes par année ({varname}) : {out_year}")

    analyse_jours_extremes(
        dataframes=dataframes,
        varname="windspeed_mean",
        bc_threshold=bc_mean_threshold,
        output_dir=output_dir,
    )

    analyse_jours_extremes(
        dataframes=dataframes,
        varname="windspeed_gust",
        bc_threshold=bc_gust_threshold,
        output_dir=output_dir,
    )

    # ------------------------------------------------------------
    # 10. Périodes de retour (Gumbel) pour toutes les sources
    # ------------------------------------------------------------
    print("Calcul des niveaux de retour (Gumbel) pour toutes les sources...")

    def export_annual_max(series: pd.Series, output_path: str):
        """
        Exporte les maxima annuels d'une série sous forme de CSV simple :
        Année, Max_value.
        """
        s = series.dropna()
        if s.empty:
            return False

        annual_max = s.groupby(s.index.year).max()
        df_annual = pd.DataFrame(
            {"Année": annual_max.index.astype(int), "Max_value (m/s)": annual_max.values}
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

            # Niveaux de retour pour toutes les périodes demandées
            for rp in return_periods_years:
                rl = compute_return_level(series, return_period_years=rp)
                results_rows.append(
                    {
                        "Source": name,
                        "Variable": varname,
                        "Return_period (ans)": rp,
                        "Return_level (m/s)": rl,
                        "Seuil_BuildingCode (m/s)": bc_threshold,
                    }
                )

    if results_rows:
        df_ret = pd.DataFrame(results_rows)
        ret_all_path = os.path.join(output_dir, "return_periods_gumbel.csv")
        df_ret.to_csv(ret_all_path, index=False)
        print(f"  → Niveaux de retour (toutes périodes) : {ret_all_path}")

        # Pour compatibilité v1 : on exporte encore un fichier 50 ans si 50 est demandé
        if any(abs(rp - 50.0) < 1e-6 for rp in return_periods_years):
            df_50 = df_ret[df_ret["Return_period (ans)"] == 50.0].copy()
            ret_50_path = os.path.join(output_dir, "return_period_50y.csv")
            df_50.to_csv(ret_50_path, index=False)
            print(f"  → Fichier compatibilité v1 (50 ans) : {ret_50_path}")

    # ------------------------------------------------------------
    # 11. Résumé final par site (INACTIF pour le moment)
    # ------------------------------------------------------------
    """
    # Section désactivée volontairement.
    # L'ancienne version produisait un site_summary_*.csv mêlant
    # plusieurs indicateurs mais dans un format jugé peu utile.
    #
    # À réécrire plus tard si besoin, à partir de :
    # - df_cov (couverture),
    # - df_stats (statistiques descriptives),
    # - df_ret (niveaux de retour).
    """

    print(f"=== Fin de l'analyse pour le site : {site_name} ===")
