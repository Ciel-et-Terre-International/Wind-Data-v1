# TODO LIST – Wind Data v1

[← Back to README](../README.md)

**File:** <FILENAME>  
**Version:** v1.x  
**Last updated:** <DATE>  
**Maintainer:** Adrien Salicis  
**Related docs:** See docs/INDEX.md for full documentation index.

---

Ciel & Terre International  
Operational, Technical and Scientific Tasks

This document contains actionable items for the Wind Data pipeline.
Items are grouped by category and priority.

-------------------------------------------------------------------------------
1. High Priority (v1.1)
-------------------------------------------------------------------------------

### 1.1 Pipeline Stability
- Fix building code “NaN” thresholds handling
- Improve source fallback (avoid pipeline crash)
- Add missing exception handling for NOAA parsing
- Ensure timestamp alignment for all sources
- Standardize column names across CSVs

### 1.2 Documentation
- Finalize README.md
- Add METHODOLOGY.md (done)
- Clean DATAS.md (optional)
- Update CONTRIBUTING and WORKFLOW (done)

### 1.3 User Workflow
- Add optional CLI inputs:
  --start YYYY-MM-DD
  --end YYYY-MM-DD
  --site <SITE_CODE>
- Add `--download-only` and `--analysis-only`

-------------------------------------------------------------------------------
2. Medium Priority (v1.2)
-------------------------------------------------------------------------------

### 2.1 Data Quality Enhancements
- Improve NOAA ISD metadata extraction
- Automated detection of unrealistic values
- Automated seasonality statistics (winter/summer winds)
- Check Open-Meteo gust definition across models

### 2.2 Performance Improvements
- Reduce memory footprint when merging large CSVs
- Add chunk-based processing
- Optimize wind rose generation (slow in some runs)
- Cache downloaded files centrally under /cache/

### 2.3 Reporting Improvements
- Add summary table for gust factors
- Add correlation matrix per source
- Compute seasonal biases between datasets
- Add “source reliability score” section in report

-------------------------------------------------------------------------------
3. Low Priority (v1.3)
-------------------------------------------------------------------------------

### 3.1 Visualization
- Add interactive Plotly time-series (zoom, filters)
- Improve PyDeck visualization
- Add terrain map overlays (optional)

### 3.2 Quality-of-Life Features
- Auto-detect wrong date formats
- Auto-detect site coordinates inconsistencies
- Add progress bars (tqdm) during downloads
- Centralized logging file under logs/run_timestamp.log

-------------------------------------------------------------------------------
4. Future (v2.x)
-------------------------------------------------------------------------------

### 4.1 Architecture
- Transform codebase into a Python package
- Split modules logically
- Add dependency injection for data sources

### 4.2 Advanced Statistics
- Full GEV fitting with confidence intervals
- POT (Peaks Over Threshold) implementation
- Seasonal extreme value analysis
- Spatial correlation metrics across neighboring stations

### 4.3 Database Layer
- Move long-term storage to Parquet
- Optional DuckDB backend for fast queries
- Store metadata manifests per run

### 4.4 Multi-Site Automation
- Batch processing across countries
- Automatic country-level summary reports
- Multi-site correlation dashboards

-------------------------------------------------------------------------------
5. Housekeeping / Cleaning
-------------------------------------------------------------------------------

### Code Cleanup
- Remove deprecated modules in /modules/0ld/
- Remove temporary notebooks and scripts no longer needed
- Consolidate duplicated code in fetchers
- Format codebase using Black or Ruff

### Testing
- Add unit tests for each fetcher
- Add integration test for full pipeline
- Add test for building code threshold behavior

-------------------------------------------------------------------------------
End of document.
