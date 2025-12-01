# ============================================================
# Statistiques descriptives regroupées (vent moyen)
# ============================================================

stats_summary = {}
for name, df in dataframes.items():
    if "windspeed_mean" in df.columns:
        stats = df["windspeed_mean"].describe(percentiles=[.05, .25, .5, .75, .95])
        stats_summary[name] = stats

df_stats = pd.DataFrame(stats_summary).T[
    ["count", "mean", "std", "min", "5%", "25%", "50%", "75%", "95%", "max"]
]

# Arrondi visuel et style professionnel
df_stats_styled = (
    df_stats.style
    .format("{:.2f}")
    .set_caption("Statistiques descriptives des vitesses moyennes du vent par source")
    .set_table_styles(
        [
            {"selector": "caption", "props": [("font-size", "16px"), ("font-weight", "bold"), ("text-align", "center")]},
            {"selector": "th", "props": [("background-color", "#f2f2f2"), ("text-align", "center")]},
            {"selector": "td", "props": [("text-align", "right")]}
        ]
    )
    .background_gradient(cmap="Blues", subset=["mean", "max"])
)

df_stats_styled

import pandas as pd
import numpy as np
from pathlib import Path

# Dossier des données
data_root = Path("../data")
stat_results = []

# Recherche des fichiers dans le site sélectionné
csv_files = list(site_path.glob("*.csv"))

# Fonction de calcul statistique par variable
def compute_stats(df, source_name, site_name):
    for col in ["windspeed_mean", "windspeed_gust", "winddirection"]:
        if col in df.columns:
            data = df[col].dropna()
            stat_results.append({
                "Site": site_name,
                "Source": source_name,
                "Variable": col,
                "Count": len(data),
                "Mean": data.mean(),
                "Median": data.median(),
                "Std": data.std(),
                "Min": data.min(),
                "Max": data.max(),
                "P90": data.quantile(0.90),
                "P95": data.quantile(0.95),
                "P99": data.quantile(0.99),
            })

# Traitement de tous les fichiers du site sélectionné
for file in csv_files:
    try:
        df = pd.read_csv(file)
        site_name = site_path.name
        source_name = file.stem.replace(f"_{site_name}", "")
        compute_stats(df, source_name, site_name)
    except Exception as e:
        print(f"Erreur lecture {file.name}: {e}")

df_stats = pd.DataFrame(stat_results)

# Affichage du tableau
df_stats.head(20)

# ============================================================
# Histogrammes côte à côte par source (vent moyen)
# ============================================================

valid_sources = [(name.split('_')[0], df["windspeed_mean"].dropna()) for name, df in dataframes.items()
                 if "windspeed_mean" in df.columns and len(df["windspeed_mean"].dropna()) >= 10]

n = len(valid_sources)
cols = 2
rows = int(np.ceil(n / cols))

fig, axes = plt.subplots(rows, cols, figsize=(14, 4.5 * rows), constrained_layout=True)
axes = axes.flatten()

for i, (name, data) in enumerate(valid_sources):
    ax = axes[i]
    sns.histplot(data, bins=40, kde=True, stat='density', color='steelblue', edgecolor='black', ax=ax)
    ax.set_title(f"{name}", fontsize=12, fontweight='bold')
    ax.set_xlabel("Vitesse moyenne du vent (m/s)")
    ax.set_ylabel("Densité de probabilité")
    ax.grid(True, linestyle='--', alpha=0.6)

# Supprimer les cases vides
for j in range(i + 1, len(axes)):
    fig.delaxes(axes[j])

fig.suptitle("Distribution des vitesses moyennes par source", fontsize=16, fontweight='bold')
plt.show()

# ============================================================
# Histogrammes groupés – rafales de vent par source
# ============================================================

valid_gust_sources = [
    (name.split('_')[0], df["windspeed_gust"].dropna())
    for name, df in dataframes.items()
    if "windspeed_gust" in df.columns and len(df["windspeed_gust"].dropna()) >= 10
]

n = len(valid_gust_sources)
cols = 2
rows = int(np.ceil(n / cols))

fig, axes = plt.subplots(rows, cols, figsize=(14, 4.5 * rows), constrained_layout=True)
axes = axes.flatten()

for i, (name, data) in enumerate(valid_gust_sources):
    ax = axes[i]
    sns.histplot(data, bins=40, kde=True, stat='density', color='salmon', edgecolor='black', ax=ax)
    ax.set_title(name, fontsize=12, fontweight='bold')
    ax.set_xlabel("Vitesse des rafales (m/s)")
    ax.set_ylabel("Densité de probabilité")
    ax.grid(True, linestyle='--', alpha=0.4)

for j in range(i + 1, len(axes)):
    fig.delaxes(axes[j])

fig.suptitle("Distribution des rafales de vent par source", fontsize=16, fontweight='bold')
plt.show()


def process_outliers(dataframes, varname, title_label):
    df_all = pd.concat([
        df.assign(source=name.split("_")[0])
        for name, df in dataframes.items()
        if varname in df.columns
    ], ignore_index=True)

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

    # Boxplot
    fig, ax = plt.subplots(figsize=(max(10, len(outlier_df) * 1.5), 6))
    sns.boxplot(
        data=df_all,
        x="source",
        y=varname,
        order=outlier_df.index,
        showfliers=True,
        flierprops=dict(marker='o', markersize=3, alpha=0.4),
        palette="pastel",
        ax=ax
    )
    ax.set_title(f"Boxplot – {title_label} par source (avec outliers visibles)", fontsize=14, fontweight="bold")
    ax.set_ylabel(f"{title_label} (m/s)")
    ax.set_xlabel("Source")
    plt.xticks(rotation=30)
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.show()

    # Histogramme des outliers
    fig, ax = plt.subplots(figsize=(10, 4))
    sns.barplot(
        x=outlier_df.index,
        y=outlier_df["outliers"],
        palette="rocket",
        ax=ax
    )
    ax.set_title(f"Nombre de valeurs extrêmes pour {title_label} (> Q3 + 1.5×IQR)", fontsize=13, fontweight="bold")
    ax.set_ylabel("Nombre de valeurs extrêmes")
    ax.set_xlabel("Source")
    plt.xticks(rotation=30)
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.show()

# Appels
process_outliers(dataframes, "windspeed_mean", "Vitesse moyenne du vent")
process_outliers(dataframes, "windspeed_gust", "Rafales de vent")


# Valeurs de référence issues du building code (à adapter selon le site)
bc_reference = {
    "windspeed_mean": 10,   # exemple valeur normative vent moyen (m/s)
    "windspeed_gust": 22    # exemple valeur normative rafale (m/s)
}

seuils_min = {
    "windspeed_mean": 8,
    "windspeed_gust": 15
}

results_mean = []
results_gust = []

for name, df in dataframes.items():
    for var, result_list in [("windspeed_mean", results_mean), ("windspeed_gust", results_gust)]:
        if var in df.columns:
            data = df[var].dropna()
            if data.empty:
                continue

            seuil = max(seuils_min[var], data.quantile(0.95))
            extremes = df[df[var] > seuil].copy()

            result_list.append({
                "Source": name,
                "Seuil utilisé (m/s)": round(seuil, 2),
                "Max observé (m/s)": round(data.max(), 2),
                "Valeur code bâtiment (m/s)": bc_reference[var],
                "Nb valeurs > seuil": len(extremes),
                "Dates des extrêmes": ", ".join(extremes["time"].dt.strftime("%Y-%m-%d").head(3)) if not extremes.empty else ""
            })

df_ext_mean = pd.DataFrame(results_mean).sort_values(by="Max observé (m/s)", ascending=False)
df_ext_gust = pd.DataFrame(results_gust).sort_values(by="Max observé (m/s)", ascending=False)

# Affichage
display(df_ext_mean.style.set_caption("Vent moyen – valeurs extrêmes par source"))
display(df_ext_gust.style.set_caption("Vent rafale – valeurs extrêmes par source"))



# ============================================================
# Ajustement statistique – lois de Weibull et Gumbel
# ============================================================

for name, df in dataframes.items():
    # On privilégie les rafales si elles sont disponibles
    col = "windspeed_gust" if "windspeed_gust" in df.columns else "windspeed_mean"
    if col not in df.columns:
        continue

    data = df[col].dropna()
    if len(data) < 30:
        continue  # Pas assez de données pour un ajustement fiable

    x_vals = np.linspace(data.min(), data.max(), 200)

    # Ajustement Weibull
    c, loc_w, scale_w = weibull_min.fit(data, floc=0)
    weibull_pdf = weibull_min.pdf(x_vals, c, loc_w, scale_w)

    # Ajustement Gumbel
    loc_g, scale_g = gumbel_r.fit(data)
    gumbel_pdf = gumbel_r.pdf(x_vals, loc_g, scale_g)

    # Tracé
    plt.figure(figsize=(8, 4))
    sns.histplot(data, bins=40, stat='density', color='lightgray', edgecolor="black", label="Données empiriques")
    plt.plot(x_vals, weibull_pdf, label=f"Weibull\nc={c:.2f}, scale={scale_w:.2f}", color="royalblue")
    plt.plot(x_vals, gumbel_pdf, label=f"Gumbel\nloc={loc_g:.2f}, scale={scale_g:.2f}", color="darkorange")
    plt.title(f"Ajustement de lois – {name} ({col})", fontsize=13, fontweight="bold")
    plt.xlabel("Vitesse (m/s)")
    plt.ylabel("Densité de probabilité")
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.legend()
    plt.tight_layout()
    plt.show()



# ============================================================
# Comparaison croisée – séparée pour windspeed_mean et windspeed_gust
# ============================================================

def compare_sources_by_variable(dataframes, variable):
    results = []
    # Filtrer les sources pertinentes
    keys = [k for k in dataframes.keys() if variable in dataframes[k].columns and "statistics" not in k]

    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            df1 = dataframes[keys[i]]
            df2 = dataframes[keys[j]]
            label1 = keys[i].split('_')[0]
            label2 = keys[j].split('_')[0]

            # Éviter de comparer deux sources nommées pareil
            if label1 == label2:
                label1 += "_1"
                label2 += "_2"

            # Jointure sur les dates
            df1r = df1[["time", variable]].rename(columns={variable: label1}).dropna()
            df2r = df2[["time", variable]].rename(columns={variable: label2}).dropna()
            merged = pd.merge(df1r, df2r, on="time").dropna()

            if merged.empty or len(merged) < 10:
                print(f"[INFO] Données insuffisantes ou vides entre {label1} et {label2} ({variable})")
                continue

            # Calculs des indicateurs
            mae = (merged[label1] - merged[label2]).abs().mean()
            corr = merged[label1].corr(merged[label2])
            results.append({
                "Source 1": label1,
                "Source 2": label2,
                "MAE (m/s)": round(mae, 2),
                "Corrélation": round(corr, 3),
                "Jours communs": len(merged),
                "Variable": variable
            })

    return pd.DataFrame(results)


# Comparaisons séparées
df_mean_comp = compare_sources_by_variable(dataframes, "windspeed_mean")
df_gust_comp = compare_sources_by_variable(dataframes, "windspeed_gust")


def show_comparison(df, titre):
    if df.empty:
        print(f"Aucune comparaison valide pour {titre}")
        return

    styled = (
        df.sort_values(by="MAE (m/s)")
        .style
        .format({"MAE (m/s)": "{:.2f}", "Corrélation": "{:.3f}", "Jours communs": "{:,}"})
        .background_gradient(subset=["MAE (m/s)"], cmap="Reds")
        .background_gradient(subset=["Corrélation"], cmap="Blues")
        .set_caption(f"Comparaison croisée – {titre}")
        .set_properties(**{"text-align": "center"})
        .set_table_styles([{
            'selector': 'caption',
            'props': [('caption-side', 'top'), ('font-weight', 'bold')]
        }])
    )
    display(styled)


# Affichage des résultats
show_comparison(df_mean_comp, "Vitesses moyennes (windspeed_mean)")
show_comparison(df_gust_comp, "Rafales (windspeed_gust)")



# ============================================================
# Résumé qualité des données – taux de couverture (%)
# ============================================================

resume_qualite = []

for name, df in dataframes.items():
    if "time" not in df.columns:
        continue

    nb_jours = len(df)
    date_min = df["time"].min().date()
    date_max = df["time"].max().date()

    if "windspeed_mean" in df.columns:
        coverage_mean = 100 * (1 - df['windspeed_mean'].isna().mean())
        coverage_mean_str = f"{coverage_mean:.1f}%"
    else:
        coverage_mean_str = "—"

    if "windspeed_gust" in df.columns:
        coverage_gust = 100 * (1 - df['windspeed_gust'].isna().mean())
        coverage_gust_str = f"{coverage_gust:.1f}%"
    else:
        coverage_gust_str = "—"

    resume_qualite.append({
        "Source": name.split("_")[0],
        "Nb jours": nb_jours,
        "Début": date_min,
        "Fin": date_max,
        "Couverture vent moyen": coverage_mean_str,
        "Couverture rafales": coverage_gust_str
    })

# DataFrame
df_resume = pd.DataFrame(resume_qualite).sort_values(by="Source")

# Résumé des périodes
plages = df_resume[["Début", "Fin"]].drop_duplicates()
if len(plages) == 1:
    date_info = f"Période commune : {plages.iloc[0]['Début']} → {plages.iloc[0]['Fin']}"
else:
    date_info = "Périodes variables selon les sources"

# Mise en forme conditionnelle
def highlight_low_coverage(val):
    try:
        pct = float(val.strip('%'))
        if pct < 90:
            return "background-color: #f8d7da; color: #721c24;"
    except:
        pass
    return ""

# Affichage stylisé
styled = (
    df_resume
    .style
    .format(precision=0, subset=["Nb jours"])
    .applymap(highlight_low_coverage, subset=["Couverture vent moyen", "Couverture rafales"])
    .set_caption(f"Résumé de la couverture des données – {date_info}")
    .set_properties(**{"text-align": "center"})
    .set_table_styles([
        {'selector': 'caption', 'props': [('caption-side', 'top'), ('font-weight', 'bold'), ('font-size', '14px')]}
    ])
)

display(styled)


import plotly.graph_objects as go

def plot_interactive_clean_brut(dataframes, variable, site_name="Site étudié"):
    """
    Visualisation interactive Plotly des données brutes, sans lissage,
    avec nettoyage des labels et clipping intelligent.
    """

    fig = go.Figure()
    added_traces = 0

    # Couleurs harmonisées
    color_palette = [
        "#636EFA", "#EF553B", "#00CC96", "#AB63FA",
        "#FFA15A", "#19D3F3", "#FF6692", "#B6E880",
        "#FF97FF", "#FECB52"
    ]
    color_index = 0

    # Seuil de clipping (éviter les valeurs aberrantes)
    clip_threshold = 80 if variable == "windspeed_gust" else 50

    for name, df in dataframes.items():
        if "time" not in df.columns or variable not in df.columns:
            continue

        trace_name = name.replace("_", " ").split(" lat")[0].strip()

        series = df[["time", variable]].dropna().sort_values("time")
        if series.empty:
            continue

        # Clip des valeurs aberrantes extrêmes
        series[variable] = series[variable].clip(upper=clip_threshold)

        fig.add_trace(go.Scattergl(
            x=series["time"],
            y=series[variable],
            mode="lines",
            name=trace_name,
            line=dict(width=1.2, color=color_palette[color_index % len(color_palette)]),
            opacity=0.85,
            hovertemplate=(
                f"<b>{trace_name}</b><br>"
                "Date : %{x|%Y-%m-%d}<br>"
                "Vitesse : %{y:.2f} m/s<extra></extra>"
            )
        ))
        color_index += 1
        added_traces += 1

    if added_traces == 0:
        print(f"Aucune donnée disponible pour la variable '{variable}'.")
        return

    # Mise en page finale
    titre_clean = variable.replace("_", " ").capitalize()
    fig.update_layout(
        title=f"{titre_clean} – Données brutes par source ({site_name})",
        xaxis_title="Date",
        yaxis_title="Vitesse (m/s)",
        template="plotly_white",
        hovermode="x unified",
        legend_title="Sources",
        height=650,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=10)
        ),
        margin=dict(l=40, r=40, t=80, b=40)
    )

    fig.show()

# Exemple d'utilisation
plot_interactive_clean_brut(dataframes, "windspeed_mean", selected_site)
plot_interactive_clean_brut(dataframes, "windspeed_gust", selected_site)


# ============================================================
# Analyse des jours à rafales extrêmes (> 25 m/s)
# ============================================================

seuil_extreme = 25  # seuil de rafale en m/s
summary_extremes = []
yearly_counts_all = []

for name, df in dataframes.items():
    if "windspeed_gust" not in df.columns or "time" not in df.columns:
        continue

    df_clean = df.dropna(subset=["windspeed_gust", "time"]).copy()
    df_clean = df_clean[df_clean["windspeed_gust"] > seuil_extreme]

    if df_clean.empty:
        continue

    # Résumé global
    nb_jours_extremes = len(df_clean)
    top_rafale = df_clean["windspeed_gust"].max()
    top_date = df_clean.loc[df_clean["windspeed_gust"].idxmax(), "time"].date()

    summary_extremes.append({
        "Source": name.replace("_", " "),
        "Nombre de jours > 25 m/s": nb_jours_extremes,
        "Max rafale observée (m/s)": round(top_rafale, 2),
        "Date max": top_date
    })

    # Résumé annuel
    df_clean["Year"] = df_clean["time"].dt.year
    yearly_counts = df_clean.groupby("Year").size().reset_index(name="Nb jours > 25 m/s")
    yearly_counts["Source"] = name.replace("_", " ")
    yearly_counts_all.append(yearly_counts)

# 📊 Tableau synthétique des sources
if summary_extremes:
    df_summary_extremes = pd.DataFrame(summary_extremes).sort_values(by="Nombre de jours > 25 m/s", ascending=False)
    display(df_summary_extremes.style.set_caption("Résumé des jours à rafales extrêmes (> 25 m/s) par source"))
else:
    print("Aucune rafale > 25 m/s trouvée dans les sources.")

# 📆 Résumé annuel consolidé
if yearly_counts_all:
    df_yearly = pd.concat(yearly_counts_all, ignore_index=True)
    pivot_yearly = df_yearly.pivot(index="Year", columns="Source", values="Nb jours > 25 m/s").fillna(0).astype(int)
    display(pivot_yearly.style.set_caption("Nombre de jours à rafales extrêmes (> 25 m/s) par an et par source"))
else:
    print("Pas de données annuelles sur les jours extrêmes à afficher.")




import matplotlib.pyplot as plt
import numpy as np

def plot_rose_of_wind(dataframes, bins_speed=None, bins_dir=30):
    """
    Affiche la rose des vents pour chaque source disposant de wind_direction et windspeed_mean.
    - bins_speed : classes de vitesses
    - bins_dir : largeur des secteurs directionnels en degrés
    """
    if bins_speed is None:
        bins_speed = [0, 2, 4, 6, 8, 10, 12, 15, 20]

    sources_plotted = 0

    for name, df in dataframes.items():
        # Utilisation stricte des noms d'origine
        if "wind_direction" not in df.columns or "windspeed_mean" not in df.columns:
            continue

        df_clean = df.dropna(subset=["wind_direction", "windspeed_mean"]).copy()
        if df_clean.empty:
            continue

        directions = df_clean["wind_direction"].values
        speeds = df_clean["windspeed_mean"].values

        # Conversion en radians
        directions_rad = np.deg2rad(directions)

        # Binning directionnel
        dir_bins = np.arange(0, 360 + bins_dir, bins_dir)
        dir_centers = dir_bins[:-1] + bins_dir/2

        hist_matrix = np.zeros((len(bins_speed)-1, len(dir_bins)-1))

        # Histogramme 2D par classe de vitesse et direction
        for i in range(len(bins_speed)-1):
            mask_speed = (speeds >= bins_speed[i]) & (speeds < bins_speed[i+1])
            hist, _ = np.histogram(directions[mask_speed], bins=dir_bins)
            hist_matrix[i, :] = hist

        # Tracé polaire
        fig, ax = plt.subplots(subplot_kw=dict(polar=True), figsize=(8, 6))
        bottom = np.zeros(len(dir_bins)-1)

        colors = plt.cm.viridis(np.linspace(0, 1, len(bins_speed)-1))

        for i in range(len(bins_speed)-1):
            ax.bar(
                np.deg2rad(dir_centers),
                hist_matrix[i],
                width=np.deg2rad(bins_dir),
                bottom=bottom,
                color=colors[i],
                edgecolor='k',
                label=f"{bins_speed[i]}–{bins_speed[i+1]} m/s"
            )
            bottom += hist_matrix[i]

        ax.set_theta_zero_location('N')
        ax.set_theta_direction(-1)
        ax.set_title(f"Rose des vents – {name.replace('_', ' ')}", fontsize=14, fontweight="bold")
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
        plt.tight_layout()
        plt.show()

        sources_plotted += 1

    if sources_plotted == 0:
        print("❌ Aucune source valide avec wind_direction et windspeed_mean pour générer une rose des vents.")

# ✅ Exécution sur toutes les sources
plot_rose_of_wind(dataframes)
