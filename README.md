
# WindDatas – Internal Wind Data Tool  
Ciel & Terre International – R&D

WindDatas is an internal Python tool developed to retrieve, normalize, and analyze historical wind data from multiple meteorological sources (observed and modeled).  
It is designed for engineering teams performing wind assessments, building code validations, model benchmarking, and automated reporting.

This repository corresponds to **WindDatas v1**, the stable reference implementation.

---

# Overview

WindDatas automates the full workflow for wind analysis:

1. Site selection  
2. Multi-source data acquisition  
3. Standardization and normalization  
4. Descriptive and extreme-value statistics  
5. Cross-source comparisons  
6. Automated report generation  

---

## Documentation Index

The complete project documentation is located in the `docs/` directory.  
You can navigate to any document directly using the links below:

### Core Documentation

- [METHODOLOGY.md](./docs/METHODOLOGY.md)  
  Scientific framework, normalization rules, and statistical methods.

- [DATAS.md](./docs/DATAS.md)  
  Detailed description of all meteorological data sources.

### Development & Governance

- [CONTRIBUTING.md](./docs/CONTRIBUTING.md)  
  Rules for contributing, branching, commits, and PR workflow.

- [WORKFLOW.md](./docs/WORKFLOW.md)  
  Git usage guidelines and release flow.

### Project Planning

- [ROADMAP.md](./docs/ROADMAP.md)  
  Strategic plan for v1.x → v2.x evolution.

- [TODO.md](./docs/TODO.md)  
  Technical, scientific, and maintenance tasks grouped by priority.

### Legal

- [LICENSE](./docs/LICENSE)  
  MIT License.

---

# Key Features

- Multi-source historical wind retrieval  
- Automatic preprocessing (UTC, units, heights, resampling)  
- Weibull, Gumbel, and GEV extreme-value modeling  
- Outlier detection and data quality metrics  
- Automated Word report generation  
- Modular Python architecture  

---

# System Architecture

Below is the **full pipeline diagram**, using detailed ASCII boxes and flows.

```
               +---------------------+
               |   modele_sites.csv  |
               +----------+----------+
                          |
                          v
                    +-----+-----+
                    | script.py |
                    | (main UI) |
                    +-----+-----+
                          |
                          v
             +------------+-------------+
             |   Source Manager         |
             +------------+-------------+
                          |
      -----------------------------------------------------
      |            |             |            |           |
      v            v             v            v           v
+-----------+ +-----------+ +-----------+ +-----------+ +-----------+
| NOAA ISD  | | Meteostat | |   ERA5    | | NASA POW. | | OpenMeteo |
| observed  | | observed  | |  model    | |  model    | |   model   |
+-----+-----+ +-----+-----+ +-----+-----+ +-----+-----+ +-----+-----+
      \            |             |            |            /
       \           |             |            |           /
        \          |             |            |          /
         +---------+-------------+------------+---------+
                          |
                          v
              +-----------+-------------+
              | Normalization Pipeline |
              | - timestamps (UTC)     |
              | - units (m/s)          |
              | - height correction    |
              | - averaging periods    |
              +-----------+-------------+
                          |
                          v
                 +--------+--------+
                 | Stats Engine    |
                 | (analysis_runner)|
                 +--------+--------+
                          |
                          v
          +---------------+----------------+
          | Extreme Value Module (EVT)     |
          | - Weibull                      |
          | - Gumbel                       |
          | - GEV                          |
          +---------------+----------------+
                          |
                          v
              +-----------+-----------+
              | Report Generator      |
              | (Word, figures)       |
              +-----------+-----------+
                          |
                          v
      data/<SITE>/report/fiche_<SITE>.docx
```

---

# Repository Structure

A clean, GitHub-friendly hierarchical layout:

```
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
│   ├── test_utils.py
│   └── ...
│
└── data/
    (generated automatically, ignored by Git)
```

---

# Data Sources

WindDatas integrates multiple meteorological datasets:

| Source        | Type       | Resolution | Strengths | Limitations |
|---------------|------------|------------|-----------|-------------|
| NOAA ISD      | Observed   | Hourly     | High credibility | Metadata inconsistencies |
| Meteostat     | Observed   | Hourly     | Cleaned NOAA | May inherit gaps |
| ERA5          | Model      | Hourly     | No gaps, global | Underestimates extremes |
| NASA POWER    | Model      | Daily      | Smooth climatology | Not suitable for gust extremes |
| Open-Meteo    | Model      | Hourly     | Easy API | Model-dependent gusts |

See full technical specification in `docs/DATAS.md`.

---

# Installation

Clone the repository:

```
git clone https://github.com/Ciel-et-Terre-International/Wind-Data-v1.git
cd Wind-Data-v1
```

Create environment:

```
conda env create -f environment.yml
conda activate winddatas
```

---

# Usage

Windows launcher:

```
run_winddatas.bat
```

Direct execution:

```
conda activate winddatas
python script.py
```

---

# Outputs

Each site produces:

```
data/<SITE>/
    raw CSV files per source
    figures_and_tables/
        descriptive stats
        outliers
        histograms
        time series
        Weibull/Gumbel plots
        wind roses
    report/
        fiche_<SITE>.docx
```

---

# Documentation

All documents are in:

```
docs/INDEX.md
```

Main references include:

- METHODOLOGY.md  
- DATAS.md  
- CONTRIBUTING.md  
- WORKFLOW.md  
- ROADMAP.md  
- TODO.md  

---

# License

MIT License (see `docs/LICENSE`).

---

# Contact

Project lead: Adrien Salicis  
Email: adrien.salicis@cieletterre.net
