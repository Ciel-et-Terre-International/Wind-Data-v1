# WindDatas – Internal Wind Data Tool (Ciel & Terre International)

WindDatas is a modular Python tool designed to retrieve, normalize, and analyze historical wind data from multiple observed and modeled sources.
It is used at Ciel & Terre International to benchmark wind models, support building code verifications, and generate consistent technical reports per site.

This repository corresponds to the v1 internal version (Wind-Data-v1) used in production workflows.

--------------------------------------------------------------------------------

Objectives

- Automatically retrieve wind data for multiple sites worldwide.
- Combine observed sources (NOAA ISD, Meteostat) with modeled sources (ERA5, NASA POWER, Open-Meteo, etc.).
- Normalize units, timestamps, averaging periods and heights when possible.
- Perform statistical analyses:
  - descriptive statistics
  - outlier detection
  - extreme value analysis (Weibull, Gumbel / GEV)
  - return period estimation (e.g., 50-year wind)
- Generate:
  - cleaned CSVs per source and per site
  - figures and summary tables
  - Word reports per site

For methodological details, see docs/DATAS.md and docs/Generalized_Extreme_Value.md.

--------------------------------------------------------------------------------

Repository Structure (v1)

Wind-Data-v1/
├── README.md
├── environment.yml
├── requirements.txt
├── run_winddatas.bat
├── script.py
├── docs/
│   ├── CHANGELOG.md
│   ├── CONTRIBUTING.md
│   ├── DATAS.md
│   ├── Generalized_Extreme_Value.md
│   ├── ROADMAP.md
│   ├── SECURITY.md
│   ├── TODO_LIST.md
│   └── WORKFLOW.md
├── modules/
│   ├── analysis_runner.py
│   ├── conversion_manager.py
│   ├── era5_fetcher.py
│   ├── globe_visualizer.py
│   ├── globe_visualizer_pydeck.py
│   ├── merger.py
│   ├── meteostat_fetcher.py
│   ├── nasa_power_fetcher.py
│   ├── noaa_isd_fetcher.py
│   ├── noaa_station_finder.py
│   ├── openmeteo_fetcher.py
│   ├── report_generator.py
│   ├── source_manager.py
│   ├── station_profiler.py
│   ├── stats_calculator.py
│   ├── tkinter_ui.py
│   ├── utils.py
│   └── visualcrossing_fetcher.py
├── notebooks/
│   ├── Notebook.ipynb
│   └── notebook_code_cells.py
├── scripts/
│   ├── clean.py
│   ├── clean_output.py
│   ├── debug_output.txt
│   ├── site_enricher.py
│   └── test_noaa_fetcher.py
├── tests/
│   ├── test_noaa_api_fetcher.py
│   ├── test_noaa_isd_fetcher.py
│   ├── test_noaa_isd_fetcher_PARIS.py
│   ├── test_noaa_station_finder.py
│   ├── test_openmeteo.py
│   └── test_utils.py
└── data/  (generated at runtime, ignored by Git)

--------------------------------------------------------------------------------

Installation

1. Clone the repository:

HTTPS:
git clone https://github.com/Ciel-et-Terre-International/Wind-Data-v1.git
cd Wind-Data-v1

SSH:
git clone git@github.com:Ciel-et-Terre-International/Wind-Data-v1.git
cd Wind-Data-v1

2. Create and activate the Conda environment:

conda env create -f environment.yml
conda activate winddatas

Alternative (not recommended):
pip install -r requirements.txt

--------------------------------------------------------------------------------

Usage

Option A — Windows batch launcher:
run_winddatas.bat

Option B — Direct Python execution:
conda activate winddatas
python script.py

You will be asked to select the start and end dates for the study. The tool then:

1. Loads the site list from modele_sites.csv.
2. Fetches or loads data from all available sources.
3. Normalizes units and timestamps.
4. Computes descriptive and extreme value statistics.
5. Generates figures and the final Word report.

--------------------------------------------------------------------------------

Outputs

For each site (e.g., WUS242_FORT BRAGG), the tool generates:

- Raw CSVs for ERA5, Meteostat, NOAA, Open-Meteo, NASA POWER, etc.
- Processed descriptive and quality statistics (CSV).
- Figures (histograms, outlier plots, time series, Weibull/Gumbel fits, wind roses, radar plots).
- A Word report stored in data/<SITE>/report/.

--------------------------------------------------------------------------------

Documentation

The docs/ folder contains:

- CHANGELOG.md – version history
- ROADMAP.md – planned improvements
- DATAS.md – meteorological source descriptions
- Generalized_Extreme_Value.md – statistical background
- CONTRIBUTING.md – how to contribute
- WORKFLOW.md – Git workflow
- TODO_LIST.md – remaining tasks
- SECURITY.md – security considerations

--------------------------------------------------------------------------------

License

This project is used internally at Ciel & Terre International and distributed under the MIT license.
See docs/LICENSE for full details.

--------------------------------------------------------------------------------

Contact

Project author: Adrien Salicis
Email: adrien.salicis@cieletterre.net
