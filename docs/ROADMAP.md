# ROADMAP – WindDatas (Ciel & Terre International)

[← Back to README](../README.md)

**File:** <FILENAME>  
**Version:** v1.x  
**Last updated:** <DATE>  
**Maintainer:** Adrien Salicis  
**Related docs:** See docs/INDEX.md for full documentation index.

---

This document describes the strategic development plan for WindDatas.
It is structured into four layers:
- v1.x maintenance
- v1.x feature improvements
- v2 large architectural changes
- long-term research & innovation

-------------------------------------------------------------------------------
1. Vision
-------------------------------------------------------------------------------

WindDatas aims to become a robust internal tool for:
- historical wind characterization,
- building code compliance studies,
- comparison of modeled and observed datasets,
- automated report generation.

The roadmap prioritizes:
- reliability,
- transparency of methodology,
- reproducibility,
- scalability for larger country-level analyses,
- integration with future cloud-based tools.

-------------------------------------------------------------------------------
2. Roadmap Summary
-------------------------------------------------------------------------------

v1.0 → DONE  
Core pipeline, multi-source retrieval, normalisation, stats, report generation.

v1.1 → STABILIZATION  
Bug fixes, documentation, comparisons, better error handling.

v1.2 → DATA & PERFORMANCE IMPROVEMENTS  
Better interpolation, flexible configuration, cleaned API interactions.

v1.3 → UI & USABILITY  
Command-line interface, batch mode, multi-site workflows.

v2.0 → ARCHITECTURAL REVISION  
Refactor into a modular package with unit tests, plugin-based architecture.

v2.1+ → ADVANCED FEATURES  
Improved statistical modelling, interactive dashboards, cloud deployment.

-------------------------------------------------------------------------------
3. v1.x – Maintenance and Short-Term Improvements
-------------------------------------------------------------------------------

### 3.1 Code Quality and Cleaning
- Remove unused modules (old NOAA API fetchers, temp files)
- Improve module-level docstrings
- Enforce consistent directory naming
- Switch from print() to logging

### 3.2 Data Normalization Improvements
- Unified height correction logic
- Metadata extraction per source
- Optional roughness-based adjustments
- Better detection of units & anomalies

### 3.3 Performance Optimizations
- Speed up merges (chunked reading for large CSVs)
- Parallel download option (NOAA/Meteostat/ERA5)
- Cache management for repeated runs

### 3.4 Reliability and Error Handling
- Graceful fallback when a source fails
- More robust timestamp alignment
- Automatic gap detection & reporting
- Improved NOAA parsing exceptions

### 3.5 User Interface & CLI Improvements
- Add `--start` and `--end` CLI flags
- Add `--site` filter
- Add `--download-only` and `--analysis-only`
- Add global config file (YAML)

-------------------------------------------------------------------------------
4. v2.0 – Architectural Evolution
-------------------------------------------------------------------------------

### 4.1 Packaging and Modularity
- Convert WindDatas into a proper Python package (`pip install winddatas`)
- Split pipeline into subpackages:
  * winddatas.sources
  * winddatas.stats
  * winddatas.normalization
  * winddatas.reporting
- Plugin-based architecture for new data sources
- Deprecation of monolithic script.py

### 4.2 Test Coverage & CI
- Full PyTest coverage
- Automated tests for:
  * all fetchers
  * normalization routines
  * extreme value fitting
  * report generation
- GitHub Actions CI pipeline

### 4.3 Configuration System
- Site profiles in structured JSON/YAML
- Unified global settings
- Auto-validation of input schema via Pydantic or Marshmallow

### 4.4 Data Storage Layer
- Replace CSV with Parquet for multi-run efficiency
- Create metadata manifests for reproducibility
- Optional SQLite or DuckDB backend

-------------------------------------------------------------------------------
5. v2.1+ – Advanced & Research Features
-------------------------------------------------------------------------------

### 5.1 Improved Statistical Models
- Full GEV optimization with confidence intervals
- Bayesian estimation of extremes
- Block maxima vs. peaks-over-threshold (POT)

### 5.2 Interactive Visualization
- Streamlit or Dash integration
- Wind roses with filtering
- Temporal zoom and seasonal analyses

### 5.3 Cloud Integration
- Dedicated server for mass batch processing
- Remote execution and scheduling
- Data caching and shared storage

### 5.4 Geospatial Enhancements
- Terrain-based height corrections
- Orographic adjustments
- Distance-based weighting of stations

-------------------------------------------------------------------------------
6. Dependencies Management
-------------------------------------------------------------------------------

v1.x:
- Prioritize reproducibility
- Pin versions of critical libs (pandas, xarray, windrose)
- Migrate deprecated APIs (ERA5 CDS tokens, Meteostat updates)

v2.x:
- Replace deprecated libs
- Remove technical debt
- Introduce environment lock files

-------------------------------------------------------------------------------
7. Release Schedule (Tentative)
-------------------------------------------------------------------------------

v1.1 – Q1 2025  
v1.2 – Q2 2025  
v1.3 – Q3 2025  
v2.0 – Q4 2025 / Q1 2026

-------------------------------------------------------------------------------
8. Governance
-------------------------------------------------------------------------------

Project Lead: Adrien Salicis  
Contributors: Internal R&D – Ciel & Terre International

All major decisions (architecture, API changes, source additions) must be
validated by the project lead before integration.

-------------------------------------------------------------------------------
End of document.
