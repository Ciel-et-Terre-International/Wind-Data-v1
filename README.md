
# Wind Data – Internal Wind Data Tool  
Ciel & Terre International – R&D

Wind Data is an internal Python tool developed to retrieve, normalize, and analyze historical wind data from multiple meteorological sources (observed and modeled).  
It is designed for engineering teams performing wind assessments, building code validations, model benchmarking, and automated reporting.

This repository corresponds to **Wind Data v1**, the stable reference implementation.

---

# Overview

Wind Data automates the full workflow for wind analysis:

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
- [DATA.md](./docs/DATA.md)  
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
├── wind_data.bat
├── script.py
├── modele_sites.csv   # needs to be filled by user
│
├── docs/
│   ├── INDEX.md
│   ├── CONTRIBUTING.md
│   ├── WORKFLOW.md
│   ├── METHODOLOGY.md
│   ├── DATA.md
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

Wind Data integrates multiple meteorological datasets:

| Source        | Type       | Resolution | Strengths | Limitations |
|---------------|------------|------------|-----------|-------------|
| NOAA ISD      | Observed   | Hourly     | High credibility | Metadata inconsistencies |
| Meteostat     | Observed   | Hourly     | Cleaned NOAA | May inherit gaps |
| ERA5          | Model      | Hourly     | No gaps, global | Underestimates extremes |
| NASA POWER    | Model      | Daily      | Smooth climatology | Not suitable for gust extremes |
| Open-Meteo    | Model      | Hourly     | Easy API | Model-dependent gusts |

See full technical specification in - [DATA.md](./docs/DATA.md).

---

# Installation


The project is located on the SharePoint
`[Lien](https://cielterre.sharepoint.com/:f:/s/RD-Ressources/EsJXg3QcLeVBi4HyLlOAcQcBdlN-OUI6me08iRINvX17Dg?e=HzSON8)`
There is also a GitHub, to see all documentation about and have better interface.
`[GitHub Wind Data](https://github.com/Ciel-et-Terre-International/Wind-Data-v1)`


**REQUIREMENTS**

- Need to install Conda
[Anaconda](https://www.anaconda.com/download)
Miniconda is a free, miniature installation of Anaconda Distribution that includes only conda, Python, the packages they both depend on, and a small number of other useful packages. If you need more packages, use the `conda install` command to install from thousands of packages available by default in Anaconda’s public repo, or from other channels, like conda-forge or bioconda.
**!! Careful, add conda to PATH during the installation !!**

- Need to install VS Code
[Visual Studio Code](https://code.visualstudio.com/)
After installation, you'll have to set the **command prompt as the default terminal**.
Then, you can open directly the project from the SharePoint (Syncing)

- Need to download the .cdsapirc file for ERA5
[.cdsapirc](https://cielterre.sharepoint.com/:u:/s/RD-Ressources/EWLk54v_WV1Ek66YAr1vQR4BD9u6Kqv1d54DQ9U0SR-4Ug?e=6xAa3G)
It has to be located at : C:\Users\%USER%
Example : C:\Users\AdrienSALICIS

[Optional]
You can clone the repository (or download it from SharePoint) to your local, for example, on your desktop. Performance can be optimised when the files are not located on the network.

```
git clone https://github.com/Ciel-et-Terre-International/Wind-Data-v1.git
cd Wind-Data-v1
```

**Before running the tool, you must install dependencies and packages.**
This has to be done with Conda (Anaconda or Miniconda, doesn't matter).
A virtual environnement has to be created, and the environment.yml files described its characteristics.
Command to create the environment:

```
conda env create -f environment.yml
conda activate wind_data
```

[Optional] 
This can be done with a "pip" installation, but conda is a cleanest way.

---

# Usage

On VS Code, open a new terminal (need to be Command Prompt) :

1.
```
conda activate wind_data
```
2.
````
wind_data.bat
```
3. Fill the dates for your study

Direct execution (not recommended) :

```
conda activate wind_data
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

# Contact

Project lead: Adrien Salicis  
Email: adrien.salicis@cieletterre.net
