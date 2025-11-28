# WindDatas – Internal Wind Data Tool
Ciel & Terre International – R&D

WindDatas is an internal Python tool developed to retrieve, normalize, and analyze historical wind data from multiple meteorological sources (observed and modeled).
It is used within Ciel & Terre International to support:
- wind resource assessments
- building code wind analysis
- engineering decision-making
- cross-source wind model comparisons
- automated wind reporting for site studies

This repository corresponds to WindDatas v1, the stable reference implementation.

--------------------------------------------------------------------------------
## Overview
--------------------------------------------------------------------------------

WindDatas automates the full workflow for historical wind analysis:
1. Site selection
2. Automatic data retrieval
3. Normalization of wind datasets
4. Descriptive and extreme-value statistics
5. Cross-source comparisons
6. Report generation

--------------------------------------------------------------------------------
## Key Features
--------------------------------------------------------------------------------

### Multi-source wind data acquisition
Observed sources:
- NOAA ISD
- Meteostat

Modeled sources:
- ERA5
- NASA POWER
- Open-Meteo

### Automatic normalization
- Units converted to m/s
- Timestamps in UTC
- Vertical extrapolation when metadata is available
- Standardized averaging periods
- Consistent handling of gusts vs mean wind

### Statistical analysis
- Descriptive statistics
- Missing-data and completeness assessment
- Outlier detection
- Weibull fitting
- Gumbel and GEV extreme-value fitting
- 50-year return period wind estimation

### Report generation
- Figures
- Tables
- Word report for each site

--------------------------------------------------------------------------------
## System Architecture
--------------------------------------------------------------------------------

Pipeline diagram:

               +---------------------+
               |   modele_sites.csv  |
               +----------+----------+
                          |
                          v
                    +-----+-----+
                    | script.py |
                    +-----+-----+
                          |
     -------------------------------------------------
     |            |             |            |        |
     v            v             v            v        v
  NOAA ISD    Meteostat       ERA5      NASA POWER  Open-Meteo
 (observed)  (observed)     (model)      (model)     (model)
     \            |             |            |          /
      \           |             |            |         /
       \          |             |            |        /
        +---------+-------------+------------+-------+
                          |
                          v
                +---------+-----------+
                |  analysis_runner.py |
                +---------+-----------+
                          |
                          v
                +---------+-----------+
                | report_generator.py |
                +---------+-----------+
                          |
                          v
          data/<SITE>/report/fiche_<SITE>.docx


--------------------------------------------------------------------------------
## Data Sources
--------------------------------------------------------------------------------

NOAA ISD  
Observed, hourly, long historical records  
https://www.ncei.noaa.gov/products/integrated-surface-database

Meteostat  
Observed, hourly, curated  
https://meteostat.net

ERA5  
Reanalysis, hourly, global  
https://cds.climate.copernicus.eu

NASA POWER  
Daily modeled climatology  
https://power.larc.nasa.gov

Open-Meteo  
Hourly modeled wind and gusts  
https://open-meteo.com

--------------------------------------------------------------------------------
## Repository Structure
--------------------------------------------------------------------------------

Wind-Data-v1/
│
├── README.md
├── environment.yml
├── requirements.txt
├── run_winddatas.bat
├── script.py
├── modele_sites.csv
│
├── docs/
│   ├── INDEX.md
│   ├── CONTRIBUTING.md
│   ├── WORKFLOW.md
│   ├── METHODOLOGY.md
│   ├── DATAS.md
│   ├── ROADMAP.md
│   ├── TODO.md
│   ├── SECURITY.md
│   └── LICENSE
│
├── modules/
│   ├── analysis_runner.py
│   ├── conversion_manager.py
│   ├── era5_fetcher.py
│   ├── meteostat_fetcher.py
│   ├── nasa_power_fetcher.py
│   ├── openmeteo_fetcher.py
│   ├── noaa_isd_fetcher.py
│   ├── noaa_station_finder.py
│   ├── stats_calculator.py
│   ├── source_manager.py
│   ├── station_profiler.py
│   ├── report_generator.py
│   ├── tkinter_ui.py
│   ├── utils.py
│   └── visualcrossing_fetcher.py
│
├── scripts/
│   ├── clean.py
│   ├── clean_output.py
│   └── site_enricher.py
│
├── tests/
│   ├── test_openmeteo.py
│   └── test_utils.py
│
└── data/
    (generated automatically, ignored by Git)


--------------------------------------------------------------------------------
## Installation
--------------------------------------------------------------------------------

Clone the repository:

    git clone https://github.com/Ciel-et-Terre-International/Wind-Data-v1.git
    cd Wind-Data-v1

Create the environment:

    conda env create -f environment.yml
    conda activate winddatas

--------------------------------------------------------------------------------
## Usage
--------------------------------------------------------------------------------

Windows launcher:

    run_winddatas.bat

Direct execution:

    conda activate winddatas
    python script.py

--------------------------------------------------------------------------------
## Outputs
--------------------------------------------------------------------------------

For each site:

    data/<SITE>/
        era5_<SITE>.csv
        meteostat_<SITE>.csv
        noaa_station1_<SITE>.csv
        noaa_station2_<SITE>.csv
        openmeteo_<SITE>.csv
        nasa_power_<SITE>.csv

        figures_and_tables/
            statistical tables
            outlier tables
            time series
            histograms
            boxplots
            Weibull and Gumbel fitting plots
            wind rose

        report/
            fiche_<SITE>.docx

--------------------------------------------------------------------------------
## Documentation
--------------------------------------------------------------------------------

All documentation is located under docs/, the entry point is:

    docs/INDEX.md

Main documents:
- METHODOLOGY.md
- DATAS.md
- CONTRIBUTING.md
- WORKFLOW.md
- ROADMAP.md
- TODO.md
- SECURITY.md
- LICENSE

--------------------------------------------------------------------------------
## License
--------------------------------------------------------------------------------

WindDatas is distributed internally under the MIT License.
See docs/LICENSE.

--------------------------------------------------------------------------------
## Contact
--------------------------------------------------------------------------------

Project lead and maintainer:  
Adrien Salicis  
adrien.salicis@cieletterre.net
