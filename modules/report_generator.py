import os
import pandas as pd
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT


def set_paragraph_font(paragraph, size=10):
    for run in paragraph.runs:
        run.font.size = Pt(size)


def insert_section_title(doc, title, level=1):
    doc.add_heading(title, level=level)


def insert_paragraph(doc, text):
    para = doc.add_paragraph(text)
    para.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT
    set_paragraph_font(para, size=9)


def insert_image_if_exists(doc, path, width=6.0):
    if os.path.exists(path):
        doc.add_picture(path, width=Inches(width))
        doc.add_paragraph().add_run().add_break()


def insert_table_from_csv(doc, csv_path, title=None):
    if not os.path.exists(csv_path):
        return

    df = pd.read_csv(csv_path)
    if df.empty:
        return

    if title:
        doc.add_heading(title, level=2)

    t = doc.add_table(rows=1, cols=len(df.columns))
    t.style = 'Table Grid'
    hdr_cells = t.rows[0].cells
    for i, col in enumerate(df.columns):
        hdr_cells[i].text = str(col)

    for _, row in df.iterrows():
        row_cells = t.add_row().cells
        for i, val in enumerate(row):
            row_cells[i].text = str(val)

    doc.add_paragraph().add_run().add_break()


def generate_report(site_data, output_folder="data"):
    site_name = f"{site_data['reference']}_{site_data['name']}"
    site_folder = os.path.join(output_folder, site_name)
    figures_dir = os.path.join(site_folder, "figures_and_tables")
    output_docx = os.path.join(site_folder, "report", f"fiche_{site_name}.docx")
    output_pdf = output_docx.replace(".docx", ".pdf")
    os.makedirs(os.path.dirname(output_docx), exist_ok=True)

    template_path = os.path.join(os.getcwd(), "template.docx")
    if os.path.exists(template_path):
        doc = Document(template_path)
    else:
        print("template.docx introuvable. Utilisation d’un document Word vierge.")
        doc = Document()


    # === PAGE DE GARDE ===
    doc.add_paragraph(f"Rapport de Synthèse – {site_name}").style = "Heading 1"

    doc.add_paragraph("Analyse statistique des données de vent issues de plusieurs sources.")
    doc.add_paragraph().add_run().add_break()

    # === 1. Qualité des données ===
    insert_section_title(doc, "1. Qualité des données")
    insert_paragraph(doc, "Ce tableau présente le nombre de jours de données disponibles, la période d'étude, et le taux de couverture pour le vent moyen et les rafales pour chaque source utilisée.")
    insert_table_from_csv(doc, os.path.join(figures_dir, "resume_qualite.csv"))

    # === 2. Statistiques descriptives ===
    insert_section_title(doc, "2. Statistiques descriptives")
    insert_paragraph(doc, "Distribution des vitesses moyennes du vent par source. Moyenne, écart-type, percentiles, min/max. Toutes les vitesses sont exprimées en m/s.")
    insert_table_from_csv(doc, os.path.join(figures_dir, "stats_windspeed_mean.csv"))

    # === 3. Histogrammes ===
    insert_section_title(doc, "3. Histogrammes")
    insert_paragraph(doc, "Histogrammes de distribution des vitesses moyennes et des rafales par source, avec visualisation du seuil réglementaire (Building Code).")
    insert_image_if_exists(doc, os.path.join(figures_dir, "histogrammes_windspeed_mean.png"))
    insert_image_if_exists(doc, os.path.join(figures_dir, "histogrammes_windspeed_gust.png"))

    # === 4. Analyse des valeurs extrêmes ===
    insert_section_title(doc, "4. Analyse des valeurs extrêmes")
    insert_paragraph(doc, "Visualisation des outliers via boxplots et histogrammes. Ces valeurs peuvent influer sur l’analyse des rafales ou des extrêmes.")
    insert_image_if_exists(doc, os.path.join(figures_dir, "boxplot_windspeed_mean.png"))
    insert_image_if_exists(doc, os.path.join(figures_dir, "outliers_hist_windspeed_mean.png"))
    insert_image_if_exists(doc, os.path.join(figures_dir, "boxplot_windspeed_gust.png"))
    insert_image_if_exists(doc, os.path.join(figures_dir, "outliers_hist_windspeed_gust.png"))

    # === 5. Ajustements statistiques ===
    '''insert_section_title(doc, "5. Ajustements statistiques (Weibull, Gumbel)")
    insert_paragraph(doc, "Chaque source est comparée à des lois statistiques standards pour estimer la forme des distributions de vent.")
    for f in sorted(os.listdir(figures_dir)):
        if f.startswith("fit_weibull_gumbel") and f.endswith(".png"):
            insert_image_if_exists(doc, os.path.join(figures_dir, f))'''

    # === 6. Comparaisons croisées ===
    '''insert_section_title(doc, "6. Comparaisons croisées entre sources")
    insert_paragraph(doc, "Tableaux de comparaison croisée entre les sources disponibles (MAE, corrélation, recouvrement temporel).")
    insert_table_from_csv(doc, os.path.join(figures_dir, "comparaison_windspeed_mean.csv"))
    insert_table_from_csv(doc, os.path.join(figures_dir, "comparaison_windspeed_gust.csv"))'''

    # === 7. Roses des vents ===
    insert_section_title(doc, "7. Analyse directionnelle – Roses des vents")
    insert_paragraph(doc, "Visualisation des directions dominantes du vent par source et en comparatif, incluant l’intensité moyenne par secteur.")
    insert_image_if_exists(doc, os.path.join(figures_dir, f"comparaison_radar_directions_{site_name}.png"))
    for f in sorted(os.listdir(figures_dir)):
        if f.startswith("radar_direction_") and f.endswith(".png"):
            insert_image_if_exists(doc, os.path.join(figures_dir, f))

    # === 8. Jours extrêmes – Rafales ===
    '''insert_section_title(doc, "8. Jours extrêmes – Rafales")
    insert_paragraph(doc, "Nombre de jours par an où les rafales dépassent le seuil réglementaire. Résumé global et répartition annuelle.")
    insert_table_from_csv(doc, os.path.join(figures_dir, "rafales_extremes_resume.csv"))
    insert_table_from_csv(doc, os.path.join(figures_dir, "rafales_extremes_par_an.csv"))'''

    # === 9. Jours extrêmes – Vent moyen ===
    '''insert_section_title(doc, "9. Jours extrêmes – Vent moyen")
    insert_paragraph(doc, "Nombre de jours par an où le vent moyen dépasse le seuil réglementaire. Résumé global et répartition annuelle.")
    insert_table_from_csv(doc, os.path.join(figures_dir, "vent_moyen_extremes_resume.csv"))
    insert_table_from_csv(doc, os.path.join(figures_dir, "vent_moyen_extremes_par_an.csv"))'''

    # === 10. Séries temporelles ===
    insert_section_title(doc, "10. Séries temporelles (long terme)")
    insert_paragraph(doc, "Visualisation des séries temporelles complètes pour le vent moyen et les rafales. Permet d’identifier les grandes tendances.")
    insert_image_if_exists(doc, os.path.join(figures_dir, "time_series_windspeed_mean.png"))
    insert_image_if_exists(doc, os.path.join(figures_dir, "time_series_windspeed_gust.png"))

    # === 11. Return period 50 ans ===
    insert_section_title(doc, "11. Analyse des niveaux pour période de retour 50 ans")
    insert_paragraph(doc, "Estimation des niveaux de vent moyen et rafales à 50 ans de retour, selon loi de Gumbel. Comparaison aux seuils réglementaires.")
    insert_table_from_csv(doc, os.path.join(figures_dir, "return_period_50y.csv"))

    # === 12. Résumé global ===
    '''insert_section_title(doc, "12. Résumé global du site")
    insert_paragraph(doc, "Tableau synthétique du site (moyennes, max, seuils dépassés, sources principales, etc.).")
    summary_path = os.path.join(figures_dir, f"site_summary_{site_name}.csv")
    insert_table_from_csv(doc, summary_path)'''

    # === Sauvegarde DOCX ===
    doc.save(output_docx)
    print(f"Rapport DOCX généré : {output_docx}")