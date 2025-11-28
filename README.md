# WindDatas – Internal Wind Data Tool (Ciel & Terre International)

WindDatas is a modular Python tool designed to retrieve, normalize, and analyze historical wind data from multiple observed and modeled sources.  
It is used at Ciel & Terre International to benchmark wind models, support building code compliance studies, and generate consistent technical reports per site.

This repository corresponds to the v1 internal version used in production workflows.

--------------------------------------------------------------------------------
## Objectives
--------------------------------------------------------------------------------

WindDatas allows you to:

- Automatically retrieve wind data for multiple sites worldwide
- Combine:
  - observed sources (NOAA ISD, Meteostat)
  - modeled sources (ERA5, NASA POWER, Open-Meteo)
- Normalize datasets with different:
  - units (knots, km/h, mph → m/s)
  - averaging periods (10 min vs hourly vs daily)
  - timestamps (local time → UTC)
  - measurement heights (vertical extrapolation when possible)
- Run full statistical analysis:
  - descriptive statistics
  - outlier detection (IQR-based)
  - Weibull distribution fitting
  - Gumbel / GEV extreme value fitting
  - return period estimation (e.g. 50-year wind)
- Generate per-site outputs:
  - cleaned CSVs
  - figures and tables
  - Word reports

For scientific details, see docs/METHODOLOGY.md and docs/DATAS.md.

--------------------------------------------------------------------------------
## Repository structure (v1)
--------------------------------------------------------------------------------

Wind-Data-v1/
  README.md
  environment.yml
  requirements.txt
  run_winddatas.bat
  script.py
  modele_sites.csv

  docs/
    INDEX.md
    CONTRIBUTING.md
    WORKFLOW.md
    DATAS.md
    METHODOLOGY.md
    ROADMAP.md
    TODO.md
    SECURITY.md
    LICENSE

  modules/
    __init__.py
    analysis_runner.py
    conversion_manager.py
    era5_fetcher.py
    meteostat_fetcher.py
    nasa_power_fetcher.py
    openmeteo_fetcher.py
    noaa_isd_fetcher.py
    noaa_station_finder.py
    stats_calculator.py
    source_manager.py
    station_profiler.py
    report_generator.py
    tkinter_ui.py
    utils.py
    visualcrossing_fetcher.py

  scripts/
    clean.py
    clean_output.py
    site_enricher.py
    test_noaa_fetcher.py

  tests/
    __init__.py
    test_noaa_api_fetcher.py
    test_noaa_isd_fetcher.py
    test_noaa_isd_fetcher_PARIS.py
    test_noaa_station_finder.py
    test_openmeteo.py
    test_utils.py

  data/
    (generated at runtime, ignored by Git)


--------------------------------------------------------------------------------
## Installation
--------------------------------------------------------------------------------

1. Clone the repository

HTTPS:
  git clone https://github.com/Ciel-et-Terre-International/Wind-Data-v1.git
  cd Wind-Data-v1

SSH (if configured):
  git clone git@github.com:Ciel-et-Terre-International/Wind-Data-v1.git
  cd Wind-Data-v1

2. Create and activate the Conda environment

  conda env create -f environment.yml
  conda activate winddatas

Alternative (not recommended for first installation):

  pip install -r requirements.txt


--------------------------------------------------------------------------------
## Usage
--------------------------------------------------------------------------------

Option A – Windows batch launcher:

  run_winddatas.bat

Option B – Direct Python execution:

  conda activate winddatas
  python script.py

You will be asked to select:

- the start date
- the end date

Then the tool will:

1. Load the site list from modele_sites.csv
2. For each site:
   - select relevant stations (NOAA, Meteostat)
   - download or reuse existing data for all sources (ERA5, NASA POWER, Open-Meteo, etc.)
3. Normalize timestamps, units, averaging periods and heights
4. Compute descriptive statistics, outliers and extreme values
5. Generate figures, tables and a Word report per site


--------------------------------------------------------------------------------
## Outputs
--------------------------------------------------------------------------------

For each site (for example: WUS242_FORT BRAGG), the tool generates under data/<SITE_CODE>_<SITE_NAME>/:

- Raw CSVs per source:
  - era5_<SITE>.csv
  - meteostat1_<SITE>.csv, meteostat2_<SITE>.csv
  - noaa_station1_<SITE>.csv, noaa_station2_<SITE>.csv
  - openmeteo_<SITE>.csv
  - nasa_power_<SITE>.csv
- Processed tables in figures_and_tables/:
  - descriptive statistics for mean wind and gusts
  - data quality summary
  - outlier tables
  - annual maxima tables
  - source comparison tables
- Figures in figures_and_tables/:
  - histograms (mean wind and gusts)
  - boxplots and outlier distributions
  - time series plots
  - Weibull / Gumbel fitting plots
  - directional radar / wind rose plots
- Report in report/:
  - fiche_<SITE_CODE>_<SITE_NAME>.docx (Word report)


--------------------------------------------------------------------------------
## Documentation
--------------------------------------------------------------------------------

All documentation is located under docs/. The entry point is:

  docs/INDEX.md

Main documents:

- INDEX.md       – documentation index and overview
- METHODOLOGY.md – scientific and methodological details (normalization, statistics, extremes)
- DATAS.md       – detailed description of all meteorological data sources
- CONTRIBUTING.md – how to contribute, branching rules, PR workflow
- WORKFLOW.md    – Git workflow and release process
- ROADMAP.md     – roadmap for v1.x and v2.x
- TODO.md        – task list grouped by priority
- SECURITY.md    – internal security and usage notes
- LICENSE        – licensing information (MIT)


--------------------------------------------------------------------------------
## License
--------------------------------------------------------------------------------

This project is used internally at Ciel & Terre International and distributed under the MIT License.

See docs/LICENSE for full details.


--------------------------------------------------------------------------------
## Contact
--------------------------------------------------------------------------------

Project lead and maintainer: Adrien Salicis  
Email: adrien.salicis@cieletterre.net
