# ============================================================
# analysis_runner.py
# Analyse complète des données météo pour un site
# Version finale complète avec toutes sections 1 à 12
# Ajouts Building Code, Time Series, Return Level 50 ans
# ============================================================

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
import seaborn as sns
from scipy.stats import weibull_min, gumbel_r
from pathlib import Path
from windrose import WindroseAxes  # Nécessite windrose: pip install windrose

# ------------------------------------------------------------
#  Fonction utilitaire : calcul niveau pour période de retour 50 ans
# ------------------------------------------------------------
def compute_return_level_50y(series):
    """
    Estime la valeur de vent moyenne ou rafale correspondant à une période de retour de 50 ans,
    en ajustant une loi de Gumbel sur les maxima annuels.

    Paramètres :
        - series : pd.Series avec index temporel (datetime), en m/s

    Retour :
        - valeur estimée pour un retour 50 ans (float), ou None si échec
    """
    try:
        series = series.dropna()
        annual_max = series.resample('YE').max().dropna()
    except Exception as e:
        print(f"Erreur lors du resample annuel pour Gumbel : {e}")
        return None

    if len(annual_max) < 2:
        return None  # pas assez de données pour fit

    if len(annual_max) < 10:
        print(f"Estimation Return Period sur {len(annual_max)} années → forte incertitude.")

    try:
        loc, scale = gumbel_r.fit(annual_max)
        p = 1 - (1 / 50)
        return_level = gumbel_r.ppf(p, loc=loc, scale=scale)
        return round(return_level, 2)
    except Exception as e:
        print(f"Erreur d'ajustement Gumbel : {e}")
        return None

# ============================================================
# analysis_runner.py - PARTIE 2/8
# Début de la fonction principale : run_analysis_for_site
# ============================================================

def run_analysis_for_site(site_name: str, site_folder: str, site_config: dict, dataframes):
    """
    Analyse complète des données météo pour un site.
    Génère tous les graphiques et tableaux statistiques
    dans le sous-dossier 'figures_and_tables'.
    """
    print(f"\nAnalyse en cours pour le site : {site_name}")
    output_dir = os.path.join(site_folder, "figures_and_tables")
    os.makedirs(output_dir, exist_ok=True)

    # === Lecture des seuils Building Code avec fallback 25 m/s ===
    try:
        bc_mean_threshold = float(site_config.get("building_code_windspeed_mean_50y", 25)) or 25
    except Exception:
        bc_mean_threshold = 25

    try:
        bc_gust_threshold = float(site_config.get("building_code_windspeed_gust_50y", 25)) or 25
    except Exception:
        bc_gust_threshold = 25

    print(f"Seuil Building Code - vent moyen : {bc_mean_threshold} m/s")
    print(f"Seuil Building Code - rafales : {bc_gust_threshold} m/s")

    # ------------------------------------------------------------
    # 1 Chargement des fichiers CSV disponibles
    # ------------------------------------------------------------
    print("Chargement des fichiers CSV du site...")
    dataframes = {}

    expected_prefixes = [
        "meteostat1", "meteostat2",
        "noaa_station1", "noaa_station2",
        "openmeteo", "nasa_power", "era5", "era5_daily", "noaa"
    ]

    for file in Path(site_folder).iterdir():
        if not file.is_file() or not file.name.endswith(".csv"):
            continue
        if not any(file.stem.startswith(prefix) for prefix in expected_prefixes):
            continue

        try:
            df = pd.read_csv(file)

            # Harmonisation de la colonne temporelle
            if "time" in df.columns:
                df["time"] = pd.to_datetime(df["time"], errors='coerce')
            elif "date" in df.columns:
                df.rename(columns={"date": "time"}, inplace=True)
                df["time"] = pd.to_datetime(df["time"], errors='coerce')

            # Harmonisation des colonnes de vent (ex : NOAA)
            if "wind_speed" in df.columns and "windspeed_mean" not in df.columns:
                df.rename(columns={"wind_speed": "windspeed_mean"}, inplace=True)
            if "wind_gust" in df.columns and "windspeed_gust" not in df.columns:
                df.rename(columns={"wind_gust": "windspeed_gust"}, inplace=True)

            # Harmonisation de la clé (supprime suffixe comme _PIOLENC)
            key = file.stem
            for src in expected_prefixes:
                if key.startswith(src):
                    key = src
                    break

            dataframes[key] = df
            print(f"• {file.name} chargé ({len(df)} lignes)")

        except Exception as e:
            print(f"Erreur lecture {file.name} : {e}")

    if not dataframes:
        print("Aucun fichier CSV trouvé. Analyse stoppée.")
        return

    print(f"{len(dataframes)} sources chargées pour {site_name}")


    # ------------------------------------------------------------
    # 2 STATISTIQUES DESCRIPTIVES
    # ------------------------------------------------------------
    print("Calcul des statistiques descriptives...")

    stats_summary = {}
    skipped_sources = []

    for name, df in dataframes.items():
        if "windspeed_mean" in df.columns:
            valid_values = df["windspeed_mean"].dropna()
            if len(valid_values) >= 5:
                stats = valid_values.describe(percentiles=[.05, .25, .5, .75, .95])
                stats_summary[name] = stats
            else:
                skipped_sources.append(name)
        else:
            skipped_sources.append(name)

    if stats_summary:
        df_stats = pd.DataFrame(stats_summary).T

        # Colonnes finales à afficher (en conservant l’ordre)
        final_cols = ["count", "mean", "std", "min", "5%", "25%", "50%", "75%", "95%", "max"]
        df_stats = df_stats.loc[:, final_cols].round(2)

        # Renommer colonnes en français + unités
        df_stats = df_stats.rename(columns={
            "count": "Nbr valeurs",
            "mean": "Moyenne (m/s)",
            "std": "Écart-type (m/s)",
            "min": "Min (m/s)",
            "5%": "5% (m/s)",
            "25%": "25% (m/s)",
            "50%": "Médiane (m/s)",
            "75%": "75% (m/s)",
            "95%": "95% (m/s)",
            "max": "Max (m/s)"
        })

        stats_file = os.path.join(output_dir, "stats_windspeed_mean.csv")
        df_stats.to_csv(stats_file)
        print(f"Statistiques descriptives sauvegardées : {stats_file}")
    else:
        print("Aucune donnée suffisante pour stats descriptives.")

    if skipped_sources:
        print(f"Sources ignorées (données insuffisantes ou absentes) : {', '.join(skipped_sources)}")


    # ------------------------------------------------------------
    # 3 QUALITÉ DES DONNÉES – taux de couverture (%)
    # ------------------------------------------------------------
    print("Résumé qualité des données...")
    resume_qualite = []

    for name, df in dataframes.items():
        if "time" not in df.columns:
            continue

        try:
            nb_jours = len(df)
            date_min = df["time"].min().date()
            date_max = df["time"].max().date()

            coverage_mean = (
                100 * (1 - df["windspeed_mean"].isna().mean())
                if "windspeed_mean" in df.columns else None
            )
            coverage_gust = (
                100 * (1 - df["windspeed_gust"].isna().mean())
                if "windspeed_gust" in df.columns else None
            )

            resume_qualite.append({
                "Source": name,
                "Nombre de jours de données": nb_jours,
                "Date début": date_min,
                "Date fin": date_max,
                "Taux de couverture vent moyen (%)": f"{coverage_mean:.1f}%" if coverage_mean is not None else "—",
                "Taux de couverture rafales (%)": f"{coverage_gust:.1f}%" if coverage_gust is not None else "—"
            })
        except Exception as e:
            print(f"Erreur sur la source {name} : {e}")

    if resume_qualite:
        df_resume = pd.DataFrame(resume_qualite).sort_values(by="Source")
        qualite_file = os.path.join(output_dir, "resume_qualite.csv")
        df_resume.to_csv(qualite_file, index=False)
        print(f"Résumé qualité sauvegardé : {qualite_file}")
    else:
        print("Aucune donnée suffisante pour résumé qualité.")

    # ------------------------------------------------------------
    # 4 HISTOGRAMMES CÔTE À CÔTE – vent moyen
    # ------------------------------------------------------------
    print("Génération des histogrammes vent moyen...")
    valid_sources = [
        (name, df["windspeed_mean"].dropna())
        for name, df in dataframes.items()
        if "windspeed_mean" in df.columns and df["windspeed_mean"].dropna().shape[0] >= 10
    ]

    if valid_sources:
        n = len(valid_sources)
        cols = 2
        rows = int(np.ceil(n / cols))
        fig, axes = plt.subplots(rows, cols, figsize=(14, 4.5 * rows), constrained_layout=True)
        axes = axes.flatten()

        for i, (name, data) in enumerate(valid_sources):
            ax = axes[i]
            sns.histplot(data, bins=40, kde=True, stat='density',
                        color='steelblue', edgecolor='black', ax=ax)
            ax.set_title(f"{name}", fontsize=12, fontweight='bold')
            ax.set_xlabel("Vitesse moyenne du vent (m/s)")
            ax.set_ylabel("Densité de probabilité")
            ax.grid(True, linestyle='--', alpha=0.6)
            ax.axvline(bc_mean_threshold, color='red', linestyle='--', label='Seuil Building Code')
            ax.legend()

        for j in range(i + 1, len(axes)):
            fig.delaxes(axes[j])

        fig.suptitle("Distribution des vitesses moyennes par source", fontsize=16, fontweight='bold')
        plt.savefig(os.path.join(output_dir, "histogrammes_windspeed_mean.png"))
        plt.close()
        print("Histogrammes vent moyen sauvegardés.")
    else:
        print("Pas de données suffisantes pour histogrammes vent moyen.")

    # ------------------------------------------------------------
    # 5 HISTOGRAMMES – rafales
    # ------------------------------------------------------------
    print("Génération des histogrammes rafales...")
    valid_gust_sources = [
        (name, df["windspeed_gust"].dropna())
        for name, df in dataframes.items()
        if "windspeed_gust" in df.columns and df["windspeed_gust"].dropna().shape[0] >= 10
    ]

    if valid_gust_sources:
        n = len(valid_gust_sources)
        cols = 2
        rows = int(np.ceil(n / cols))
        fig, axes = plt.subplots(rows, cols, figsize=(14, 4.5 * rows), constrained_layout=True)
        axes = axes.flatten()

        for i, (name, data) in enumerate(valid_gust_sources):
            ax = axes[i]
            sns.histplot(data, bins=40, kde=True, stat='density',
                        color='salmon', edgecolor='black', ax=ax)
            ax.set_title(name, fontsize=12, fontweight='bold')
            ax.set_xlabel("Vitesse des rafales (m/s)")
            ax.set_ylabel("Densité de probabilité")
            ax.grid(True, linestyle='--', alpha=0.4)
            ax.axvline(bc_gust_threshold, color='red', linestyle='--', label='Seuil Building Code')
            ax.legend()

        for j in range(i + 1, len(axes)):
            fig.delaxes(axes[j])

        fig.suptitle("Distribution des rafales de vent par source", fontsize=16, fontweight='bold')
        plt.savefig(os.path.join(output_dir, "histogrammes_windspeed_gust.png"))
        plt.close()
        print("Histogrammes rafales sauvegardés.")
    else:
        print("Pas de données suffisantes pour histogrammes rafales.")

    # ------------------------------------------------------------
    # 6 BOXPLOTS + OUTLIERS
    # ------------------------------------------------------------
    print("Analyse des outliers et boxplots...")

    def process_outliers(dataframes, varname, title_label, bc_threshold):
        df_all = pd.concat([
            df.assign(source=name)
            for name, df in dataframes.items()
            if varname in df.columns and not df[varname].dropna().empty
        ], ignore_index=True)

        if df_all.empty:
            print(f"Aucune donnée pour {varname}")
            return

        # === Calcul des outliers par source ===
        outlier_counts = {}
        for source in df_all["source"].unique():
            data = df_all[df_all["source"] == source][varname].dropna()
            if len(data) < 10:
                continue
            q1, q3 = np.percentile(data, [25, 75])
            iqr_val = q3 - q1
            upper = q3 + 1.5 * iqr_val
            outlier_counts[source] = (data > upper).sum()

        outlier_df = pd.DataFrame.from_dict(outlier_counts, orient="index", columns=["outliers"])
        outlier_df = outlier_df.sort_values(by="outliers", ascending=False)

        csv_path = os.path.join(output_dir, f"outliers_{varname}.csv")
        outlier_df.to_csv(csv_path)
        print(f"Tableau outliers sauvegardé : {csv_path}")

        # === Boxplot par source ===
        fig, ax = plt.subplots(figsize=(max(10, len(outlier_df) * 1.6), 6))
        sns.boxplot(
            data=df_all,
            x="source",
            y=varname,
            order=outlier_df.index,
            showfliers=True,
            flierprops=dict(marker='o', markersize=3, alpha=0.4),
            color="skyblue",
            ax=ax
        )
        ax.set_title(f"Boxplot – {title_label} par source", fontsize=14, fontweight="bold")
        ax.set_ylabel(f"{title_label} (m/s)")
        ax.set_xlabel("Source")
        plt.xticks(rotation=30)
        ax.axhline(bc_threshold, color='red', linestyle='--', label='Seuil Building Code')
        ax.legend()
        ax.grid(axis='y', linestyle='--', alpha=0.5)
        plt.tight_layout()

        boxplot_path = os.path.join(output_dir, f"boxplot_{varname}.png")
        plt.savefig(boxplot_path)
        plt.close()
        print(f"Boxplot sauvegardé : {boxplot_path}")

        # === Histogramme des outliers ===
        fig, ax = plt.subplots(figsize=(max(10, len(outlier_df) * 0.8), 4))
        sns.barplot(
            x=outlier_df.index,
            y=outlier_df["outliers"],
            color="coral",
            ax=ax
        )
        ax.set_title(f"Nombre de valeurs extrêmes – {title_label}", fontsize=13, fontweight="bold")
        ax.set_ylabel("Nombre de valeurs extrêmes")
        ax.set_xlabel("Source")
        plt.xticks(rotation=30)
        ax.grid(axis='y', linestyle='--', alpha=0.5)
        plt.tight_layout()

        hist_outliers_path = os.path.join(output_dir, f"outliers_hist_{varname}.png")
        plt.savefig(hist_outliers_path)
        plt.close()
        print(f"Histogramme outliers sauvegardé : {hist_outliers_path}")


    # Appels avec seuil BC
    process_outliers(dataframes, "windspeed_mean", "Vitesse moyenne du vent", bc_mean_threshold)
    process_outliers(dataframes, "windspeed_gust", "Rafales de vent", bc_gust_threshold)

    # ------------------------------------------------------------
    # 11 NOUVELLE SECTION : Graphiques temporels sur toute la période
    # ------------------------------------------------------------
    print("Tracé des séries temporelles complètes...")

    def plot_timeseries_all_sources(dataframes, variable, bc_threshold, site_name, output_dir):
        plt.figure(figsize=(14, 6))
        found = False
        for name, df in dataframes.items():
            if variable not in df.columns or "time" not in df.columns:
                continue
            plt.plot(df["time"], df[variable], label=name, linewidth=0.8)
            found = True

        if not found:
            print(f"Pas de données disponibles pour {variable} sur la période.")
            return

        plt.axhline(bc_threshold, color='red', linestyle='--', label=f'Seuil Building Code ({bc_threshold} m/s)')
        plt.title(f"{variable} – Données brutes par source ({site_name})", fontsize=14, fontweight='bold')
        plt.xlabel("Date")
        plt.ylabel("Vitesse (m/s)")
        plt.legend()
        plt.grid(True, linestyle='--', alpha=0.4)
        plt.tight_layout()

        fname = os.path.join(output_dir, f"time_series_{variable}.png")
        plt.savefig(fname)
        plt.close()
        print(f"Graphique temporel sauvegardé : {fname}")


    # Appels pour chaque variable
    plot_timeseries_all_sources(dataframes, "windspeed_mean", bc_mean_threshold, site_name, output_dir)
    plot_timeseries_all_sources(dataframes, "windspeed_gust", bc_gust_threshold, site_name, output_dir)

    # ------------------------------------------------------------
    # 7 AJUSTEMENTS STATISTIQUES
    # ------------------------------------------------------------
    '''print("Ajustements statistiques Weibull / Gumbel...")

    for name, df in dataframes.items():
        col = "windspeed_gust" if "windspeed_gust" in df.columns else "windspeed_mean"
        if col not in df.columns:
            continue

        data = df[col].dropna()
        if len(data) < 30:
            continue

        try:
            x_vals = np.linspace(data.min(), data.max(), 200)
            c, loc_w, scale_w = weibull_min.fit(data, floc=0)
            weibull_pdf = weibull_min.pdf(x_vals, c, loc_w, scale_w)

            loc_g, scale_g = gumbel_r.fit(data)
            gumbel_pdf = gumbel_r.pdf(x_vals, loc_g, scale_g)

            plt.figure(figsize=(8, 4.5))
            sns.histplot(data, bins=40, stat='density', color='lightgray',
                        edgecolor="black", label="Données empiriques")
            plt.plot(x_vals, weibull_pdf, label=f"Weibull\nc={c:.2f}, scale={scale_w:.2f}", color="royalblue", linewidth=2)
            plt.plot(x_vals, gumbel_pdf, label=f"Gumbel\nloc={loc_g:.2f}, scale={scale_g:.2f}", color="darkorange", linewidth=2)

            plt.title(f"Ajustement de lois – {name} ({col})", fontsize=13, fontweight="bold")
            plt.xlabel("Vitesse (m/s)")
            plt.ylabel("Densité de probabilité")
            plt.grid(True, linestyle='--', alpha=0.5)
            plt.legend()
            plt.tight_layout()

            fit_path = os.path.join(output_dir, f"fit_weibull_gumbel_{name}_{col}.png")
            plt.savefig(fit_path)
            plt.close()
            print(f"Ajustement stats sauvegardé : {fit_path}")

        except Exception as e:
            print(f"Erreur ajustement statistique pour {name} : {e}")'''

    # ------------------------------------------------------------
    # 8 COMPARAISONS CROISÉES – MAE / corrélation
    # ------------------------------------------------------------
    '''print("Comparaisons croisées entre sources...")

    def compare_sources_by_variable(dataframes, variable):
        results = []
        keys = [
            k for k, df in dataframes.items()
            if variable in df.columns and "time" in df.columns
        ]

        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                df1 = dataframes[keys[i]]
                df2 = dataframes[keys[j]]
                label1 = keys[i]
                label2 = keys[j]

                if df1.empty or df2.empty:
                    print(f"Données vides pour la paire {label1} / {label2}.")
                    continue

                df1r = df1[["time", variable]].dropna().rename(columns={variable: label1})
                df2r = df2[["time", variable]].dropna().rename(columns={variable: label2})

                merged = pd.merge(df1r, df2r, on="time").dropna()
                n_points = len(merged)

                if n_points == 0:
                    print(f"Aucune intersection de dates pour {label1} / {label2}.")
                    continue
                if n_points < 10:
                    print(f"Très peu de points communs ({n_points}) pour {label1} / {label2}.")

                mae = (merged[label1] - merged[label2]).abs().mean()
                corr = merged[label1].corr(merged[label2])

                results.append({
                    "Source 1": label1,
                    "Source 2": label2,
                    "MAE (m/s)": round(mae, 2) if not np.isnan(mae) else "N/A",
                    "Corrélation": round(corr, 3) if not np.isnan(corr) else "N/A",
                    "Jours communs": n_points,
                    "Variable": variable
                })

        return pd.DataFrame(results)

    # Comparaisons par variable
    df_mean_comp = compare_sources_by_variable(dataframes, "windspeed_mean")
    df_gust_comp = compare_sources_by_variable(dataframes, "windspeed_gust")

    # Sauvegarde CSV
    if not df_mean_comp.empty:
        comp_mean_file = os.path.join(output_dir, "comparaison_windspeed_mean.csv")
        df_mean_comp.to_csv(comp_mean_file, index=False)
        print(f"Comparaison vent moyen sauvegardée : {comp_mean_file}")
    else:
        print("Aucune comparaison valide pour windspeed_mean.")

    if not df_gust_comp.empty:
        comp_gust_file = os.path.join(output_dir, "comparaison_windspeed_gust.csv")
        df_gust_comp.to_csv(comp_gust_file, index=False)
        print(f"Comparaison rafales sauvegardée : {comp_gust_file}")
    else:
        print("Aucune comparaison valide pour windspeed_gust.")'''



    # ------------------------------------------------------------
    # 9 ROSES DES VENTS – comparaison directionnelle
    # ------------------------------------------------------------


    def plot_comparative_wind_directions(dataframes, site_name, output_dir):
        """
        Affiche la direction moyenne pondérée par la vitesse pour chaque source,
        avec un faisceau représentant l'intensité moyenne.
        """
        results = []

        for name, df in dataframes.items():
            if "wind_direction" not in df.columns or "windspeed_mean" not in df.columns:
                continue

            df_clean = df.dropna(subset=["wind_direction", "windspeed_mean"]).copy()
            if df_clean.empty:
                continue

            theta = np.deg2rad(df_clean["wind_direction"].values)
            speeds = df_clean["windspeed_mean"].values

            # Moyenne vectorielle directionnelle
            x = np.cos(theta) * speeds
            y = np.sin(theta) * speeds
            mean_dir_rad = np.arctan2(y.mean(), x.mean())
            mean_dir_deg = np.rad2deg(mean_dir_rad) % 360
            mean_speed = speeds.mean()

            results.append((name, mean_dir_deg, mean_speed))

        if not results:
            print("Aucune donnée suffisante pour graphique radar des directions moyennes.")
            return

        # Tracé radar
        fig = plt.figure(figsize=(8, 8))
        ax = fig.add_subplot(111, polar=True)

        for name, dir_deg, speed in results:
            angle_rad = np.deg2rad(dir_deg)
            ax.bar(
                angle_rad,
                speed,
                width=np.deg2rad(25),  # largeur de faisceau
                label=f"{name} ({speed:.1f} m/s)",
                alpha=0.75
            )

        ax.set_theta_zero_location('N')
        ax.set_theta_direction(-1)
        ax.set_title(f"Comparaison des directions moyennes – {site_name}", fontsize=14, fontweight='bold', pad=20)
        ax.set_rlabel_position(225)
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.05), fontsize=8)
        ax.grid(alpha=0.4)
        plt.tight_layout()

        fname = os.path.join(output_dir, f"comparaison_radar_directions_{site_name}.png")
        plt.savefig(fname, dpi=300)
        plt.close()
        print(f"Graphique radar des directions sauvegardé : {fname}")

    # Appel
    plot_comparative_wind_directions(dataframes, site_name, output_dir)

    def plot_individual_wind_direction_radars(dataframes, site_name, output_dir):
        """
        Génère une rose des vents complète par source météo.
        Affiche la fréquence pour chaque bin directionnel et classe de vitesse.
        """
        for name, df in dataframes.items():
            if "wind_direction" not in df.columns or "windspeed_mean" not in df.columns:
                continue

            df_clean = df.dropna(subset=["wind_direction", "windspeed_mean"]).copy()
            if df_clean.empty:
                print(f"Données absentes pour la rose des vents : {name}")
                continue

            directions = df_clean["wind_direction"]
            speeds = df_clean["windspeed_mean"]

            # Nettoyage des valeurs négatives
            speeds = speeds[speeds >= 0]
            directions = directions.loc[speeds.index]  # aligne avec vitesses valides

            if speeds.empty or directions.empty:
                print(f"Données invalides ou vides pour : {name}")
                continue

            # Définition robuste des bins
            bins = [0, 2, 4, 6, 8, 10, 12, 15, 20]
            if speeds.min() < bins[0]:
                bins = [0] + bins

            fig = plt.figure(figsize=(8, 8))
            ax = WindroseAxes.from_ax(fig=fig)
            ax.bar(
                directions,
                speeds,
                normed=True,
                opening=0.8,
                edgecolor='black',
                bins=bins,
                cmap=plt.cm.viridis
            )
            ax.set_legend(loc='upper right', bbox_to_anchor=(1.3, 1.05), fontsize=8)
            ax.set_title(f"Rose des vents – {name.upper()}", fontsize=14, fontweight='bold', pad=20)

            fname = os.path.join(output_dir, f"radar_direction_{name}.png")
            plt.tight_layout()
            plt.savefig(fname, dpi=300)
            plt.close()
            print(f"Radar directionnel sauvegardé : {fname}")
    # Appel
    plot_individual_wind_direction_radars(dataframes, site_name, output_dir)


    # ------------------------------------------------------------
    # 10 ANALYSE DES JOURS À RAFALES EXTRÊMES
    # ------------------------------------------------------------
    '''print(f"Analyse des jours extrêmes (>{bc_gust_threshold} m/s rafales)...")
    summary_extremes = []
    yearly_counts_all = []

    for name, df in dataframes.items():
        if "windspeed_gust" not in df.columns or "time" not in df.columns:
            continue

        df_clean = df.dropna(subset=["windspeed_gust", "time"]).copy()
        df_clean = df_clean[df_clean["windspeed_gust"] > bc_gust_threshold]

        if df_clean.empty:
            continue

        summary_extremes.append({
            "Source": name,
            "Nombre de jours > seuil (rafales)": len(df_clean),
            "Max rafale (m/s)": round(df_clean["windspeed_gust"].max(), 2),
            "Date max": df_clean.loc[df_clean["windspeed_gust"].idxmax(), "time"].date()
        })

        df_clean["Year"] = df_clean["time"].dt.year
        yearly = df_clean.groupby("Year").size().reset_index(name="Jours extrêmes (rafales)")
        yearly["Source"] = name
        yearly_counts_all.append(yearly)

    # Sauvegarde des résumés
    if summary_extremes:
        df_sum = pd.DataFrame(summary_extremes).sort_values(by="Nombre de jours > seuil (rafales)", ascending=False)
        df_sum.to_csv(os.path.join(output_dir, "rafales_extremes_resume.csv"), index=False)
        print("Résumé rafales extrêmes sauvegardé.")

    if yearly_counts_all:
        df_years = pd.concat(yearly_counts_all, ignore_index=True)
        df_pivot = df_years.pivot(index="Year", columns="Source", values="Jours extrêmes (rafales)").fillna(0).astype(int)
        df_pivot.to_csv(os.path.join(output_dir, "rafales_extremes_par_an.csv"))
        print("Données annuelles sauvegardées.")
    else:
        print("Aucune journée extrême détectée (rafales).")'''

    # ------------------------------------------------------------
    # 11 ANALYSE DES JOURS À VENTS MOYENS EXTRÊMES
    # ------------------------------------------------------------
    '''print(f"Analyse des jours extrêmes (>{bc_mean_threshold} m/s vent moyen)...")
    summary_extremes_mean = []
    yearly_counts_all_mean = []

    for name, df in dataframes.items():
        if "windspeed_mean" not in df.columns or "time" not in df.columns:
            continue

        df_clean = df.dropna(subset=["windspeed_mean", "time"]).copy()
        df_clean = df_clean[df_clean["windspeed_mean"] > bc_mean_threshold]

        if df_clean.empty:
            continue

        summary_extremes_mean.append({
            "Source": name,
            "Nombre de jours > seuil (moyenne)": len(df_clean),
            "Max vent moyen (m/s)": round(df_clean["windspeed_mean"].max(), 2),
            "Date max": df_clean.loc[df_clean["windspeed_mean"].idxmax(), "time"].date()
        })

        df_clean["Year"] = df_clean["time"].dt.year
        yearly = df_clean.groupby("Year").size().reset_index(name="Jours extrêmes (vent moyen)")
        yearly["Source"] = name
        yearly_counts_all_mean.append(yearly)

    # Sauvegarde
    if summary_extremes_mean:
        df_sum_mean = pd.DataFrame(summary_extremes_mean).sort_values(by="Nombre de jours > seuil (moyenne)", ascending=False)
        df_sum_mean.to_csv(os.path.join(output_dir, "vent_moyen_extremes_resume.csv"), index=False)
        print("Résumé vent moyen extrêmes sauvegardé.")

    if yearly_counts_all_mean:
        df_years_mean = pd.concat(yearly_counts_all_mean, ignore_index=True)
        df_pivot_mean = df_years_mean.pivot(index="Year", columns="Source", values="Jours extrêmes (vent moyen)").fillna(0).astype(int)
        df_pivot_mean.to_csv(os.path.join(output_dir, "vent_moyen_extremes_par_an.csv"))
        print("Données annuelles vent moyen sauvegardées.")
    else:
        print("Aucune journée extrême détectée (vent moyen).")'''

    # ------------------------------------------------------------
    # 12 NIVEAU POUR PÉRIODE DE RETOUR 50 ANS (Gumbel)
    # ------------------------------------------------------------
    print("Calcul des valeurs pour période de retour 50 ans (Gumbel)...")
    results_50y = []

    def export_annual_max(series: pd.Series, output_path: str):
        annual_max = series.resample('YE').max().dropna()
        df_export = pd.DataFrame({
            'year': annual_max.index.year,
            'max_value': annual_max.values
        })
        df_export.to_csv(output_path, index=False)
        print(f"Export des maxima annuels : {output_path}")

    for name, df in dataframes.items():

        # Ignorer les sources NOAA pour l'estimation 50 ans
        if name.startswith("noaa"):
            continue

        for varname, bc_threshold in [
            ("windspeed_mean", bc_mean_threshold),
            ("windspeed_gust", bc_gust_threshold)
        ]:
            # Harmonisation automatique pour NOAA
            if name.startswith("noaa"):
                if varname == "windspeed_mean" and "wind_speed" in df.columns:
                    df = df.rename(columns={"wind_speed": "windspeed_mean"})
                if varname == "windspeed_gust" and "wind_gust" in df.columns:
                    df = df.rename(columns={"wind_gust": "windspeed_gust"})

            if varname not in df.columns or "time" not in df.columns:
                continue

            df_clean = df.dropna(subset=[varname, "time"]).copy()
            if df_clean.empty:
                val_50y = None
            else:
                df_clean["time"] = pd.to_datetime(df_clean["time"])
                df_clean.set_index("time", inplace=True)

                series = df_clean[varname]

                # Nettoyage : exclusion des zéros, NaN
                series = series[(series > 0)]
                if name.startswith("noaa"):
                    series = series.replace(999, np.nan).dropna()

                if series.empty:
                    val_50y = None
                else:
                    # Export des maxima annuels
                    export_annual_max(
                        series,
                        os.path.join(output_dir, f"annual_max_{name}_{varname}.csv")
                    )
                    val_50y = compute_return_level_50y(series)

            results_50y.append({
                "Source": name,
                "Variable": varname,
                "Return_Period_50y (m/s)": val_50y if val_50y is not None else "N/A",
                "Seuil_BuildingCode (m/s)": bc_threshold
            })

    if results_50y:
        df_50y = pd.DataFrame(results_50y)
        df_50y.to_csv(os.path.join(output_dir, "return_period_50y.csv"), index=False)
        print("Valeurs 50 ans sauvegardées.")
    else:
        print("Aucune estimation 50 ans n'a pu être calculée.")


    # ------------------------------------------------------------
    # 13 EXPORT FINAL – Résumé global du site
    # ------------------------------------------------------------

    print("Export d’un résumé global du site (site_summary.csv)...")

    summary_rows = []

    for name, df in dataframes.items():
        row = {
            "site_name": site_name,
            "source": name,
            "has_windspeed_mean": "windspeed_mean" in df.columns,
            "has_windspeed_gust": "windspeed_gust" in df.columns,
            "nb_values_mean": df["windspeed_mean"].count() if "windspeed_mean" in df.columns else 0,
            "nb_values_gust": df["windspeed_gust"].count() if "windspeed_gust" in df.columns else 0,
            "max_mean": df["windspeed_mean"].max() if "windspeed_mean" in df.columns else None,
            "max_gust": df["windspeed_gust"].max() if "windspeed_gust" in df.columns else None,
            "mean_mean": df["windspeed_mean"].mean() if "windspeed_mean" in df.columns else None,
            "mean_gust": df["windspeed_gust"].mean() if "windspeed_gust" in df.columns else None,
            "coverage_mean_percent": 100 * (1 - df["windspeed_mean"].isna().mean()) if "windspeed_mean" in df.columns else 0,
            "coverage_gust_percent": 100 * (1 - df["windspeed_gust"].isna().mean()) if "windspeed_gust" in df.columns else 0,
            "return_period_50y_mean": None,
            "return_period_50y_gust": None,
            "bc_threshold_mean": bc_mean_threshold,
            "bc_threshold_gust": bc_gust_threshold
        }

        # Ajouter les valeurs issues du calcul 50 ans
        match_mean = next((r for r in results_50y if r["Source"] == name and r["Variable"] == "windspeed_mean"), None)
        match_gust = next((r for r in results_50y if r["Source"] == name and r["Variable"] == "windspeed_gust"), None)
        if match_mean:
            row["return_period_50y_mean"] = match_mean["Return_Period_50y (m/s)"]
        if match_gust:
            row["return_period_50y_gust"] = match_gust["Return_Period_50y (m/s)"]

        summary_rows.append(row)

    # Création du DataFrame final
    df_site_summary = pd.DataFrame(summary_rows)

    # Sauvegarde dans figures_and_tables
    summary_path = os.path.join(output_dir, f"site_summary_{site_name}.csv")
    df_site_summary.to_csv(summary_path, index=False)
    print(f"Fichier résumé sauvegardé : {summary_path}")
