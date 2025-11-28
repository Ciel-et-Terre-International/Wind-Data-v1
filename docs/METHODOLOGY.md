# METHODOLOGY – WindDatas v1

[← Back to README](../README.md)

**File:** <FILENAME>  
**Version:** v1.x  
**Last updated:** <DATE>  
**Maintainer:** Adrien Salicis  
**Related docs:** See docs/INDEX.md for full documentation index.

---

Ciel & Terre International  
Scientific and Technical Documentation

This document describes the scientific and methodological foundations of WindDatas v1.  
It combines:
- the characteristics of all meteorological data sources used,
- the normalization rules applied across datasets,
- the statistical framework for wind analysis (Weibull, Gumbel, GEV),
- the pipeline logic used to produce consistent outputs.

-------------------------------------------------------------------------------
1. Introduction
-------------------------------------------------------------------------------

WindDatas retrieves, processes and analyses historical wind data from multiple
observed and modeled sources. Because each dataset has different temporal
resolution, averaging period, reference height and metadata quality, the
pipeline applies normalization steps before combining or comparing sources.

Objectives:
- Make heterogeneous wind datasets comparable.
- Standardize timestamps, units, heights, and gust/wind definitions.
- Perform robust statistical calculations.
- Provide consistent metrics such as annual maxima and 50-year return values.

-------------------------------------------------------------------------------
2. Data Sources Overview
-------------------------------------------------------------------------------

WindDatas integrates multiple independent meteorological sources:

Observed sources:
- NOAA ISD (Integrated Surface Database)
- Meteostat (station observations)
- Local airport/station datasets when available

Modeled sources:
- ERA5 Reanalysis (hourly, pressure-level + single-level wind data)
- NASA POWER
- Open-Meteo (GFS/ICON-based models)
- Visual Crossing (optional)

Below is a detailed description of each.

-------------------------------------------------------------------------------
2.1 NOAA ISD (NOAA – Integrated Surface Database)
-------------------------------------------------------------------------------

Type: Observed, station-based  
Temporal resolution: 1h (historical variability from 20 min to 3h depending on station/year)  
Wind definition:
- Wind speed: 1-minute average (WMO standard)
- Wind gust: peak wind within 10 minutes (but often inconsistent)
- Direction: 10-minute vector average  
Metadata:
- Height often known but not guaranteed
- Quality flags included
Advantages:
- Long-term records (1950+)
- High credibility
Limitations:
- Missing gusts in many years
- Station moves/metadata changes can affect long-term consistency

-------------------------------------------------------------------------------
2.2 Meteostat
-------------------------------------------------------------------------------

Type: Observed, curated station dataset  
Temporal resolution: hourly  
Wind definition:
- Same as NOAA (WMO standard)
Notes:
- Meteostat aggregates/cleans NOAA, SYNOP and other networks.
- Gaps can still exist.
Advantages:
- Cleaner than raw NOAA ISD
- Unified metadata
Limitations:
- Strong dependence on NOAA data
- Some sources reprocessed with smoothing

-------------------------------------------------------------------------------
2.3 ERA5
-------------------------------------------------------------------------------

Type: Modeled, global reanalysis  
Spatial resolution: 0.25° (~31 km)  
Temporal resolution: hourly  
Wind definition:
- U10 / V10 (10 m u/v components)
- Reconstructed wind speed = sqrt(U10² + V10²)
- No gusts except the gust field (if downloaded)
Advantages:
- No missing data
- Physically consistent
Limitations:
- Underestimates extremes
- Coarse spatial resolution

-------------------------------------------------------------------------------
2.4 NASA POWER
-------------------------------------------------------------------------------

Type: Modeled (MERRA-2 based climatology)  
Temporal resolution: daily  
Wind definition:
- Daily mean 10 m wind speed
- No gusts
Advantages:
- Long-term smooth datasets
- Global, no gaps
Limitations:
- Too smoothed for extremes
- No intraday variability

-------------------------------------------------------------------------------
2.5 Open-Meteo
-------------------------------------------------------------------------------

Type: Modeled (deterministic forecast models such as ICON/GFS)  
Temporal resolution: hourly  
Wind definition:
- 10 m wind speed and gust fields available
Advantages:
- Easy API
- Short-term forecast structure adapted for reanalysis-like use
Limitations:
- Gust definition depends on model physics
- Not homogenized over long-term periods

-------------------------------------------------------------------------------
3. Data Normalization Strategy
-------------------------------------------------------------------------------

Different datasets use different conventions. WindDatas harmonizes them
according to the following rules:

-------------------------------------------------------------------------------
3.1 Timestamp Normalization
-------------------------------------------------------------------------------

- Convert all timestamps to UTC.  
- Reindex hourly data when needed (resampling or interpolation).
- Remove duplicated timestamps.
- Ensure monotonic time indexes.

-------------------------------------------------------------------------------
3.2 Unit Normalization
-------------------------------------------------------------------------------

All wind values converted to m/s.  
Supported detection:
- km/h
- knots
- mph
Rules:
- If units missing but data source is known, apply standard unit assumptions.

-------------------------------------------------------------------------------
3.3 Height Normalization (Vertical Extrapolation)
-------------------------------------------------------------------------------

When the measurement height is known (H1) and differs from the target height (H2 = 10 m),
WindDatas uses the WMO logarithmic wind profile:

U(H2) = U(H1) * (ln(H2 / z0) / ln(H1 / z0))

where:
- z0 is surface roughness (default = 0.03 m unless improved metadata is available).

If height metadata is missing:
- No correction applied (documented in output metadata).

-------------------------------------------------------------------------------
3.4 Wind and Gust Definitions
-------------------------------------------------------------------------------

Wind:
- ERA5 / NASA / Open-Meteo: modeled 10 m wind speed (no correction applied)
- NOAA / Meteostat: WMO 10-min average

Gust:
- NOAA: true gusts when available
- ERA5: gust field used if downloaded (optional)
- Open-Meteo: gust defined by the model physics
- NASA: no gusts

Gust normalization:
- Gust factor G = gust / mean wind can be computed but is not forced across datasets.

-------------------------------------------------------------------------------
4. Statistical Framework
-------------------------------------------------------------------------------

WindDatas computes:

1. Descriptive statistics  
2. Data completeness and quality indicators  
3. Outlier detection  
4. Annual/maxima extraction  
5. Extreme value fits (Weibull, Gumbel, GEV)  
6. Return values (notably the 50-year wind)

Below are the methodological details.

-------------------------------------------------------------------------------
4.1 Outlier Detection
-------------------------------------------------------------------------------

Method:
- Z-score method  
- IQR method (default)  

For each dataset:
- Compute Q1, Q3 and IQR
- Any value outside [Q1 - 1.5 IQR ; Q3 + 1.5 IQR] is flagged
- No deletion by default; flagged for user review

-------------------------------------------------------------------------------
4.2 Annual Maxima Series (AMS)
-------------------------------------------------------------------------------

For each year Y:
- max(mean wind)
- max(gust)

This produces a series {M1, M2, …, Mn} used for extreme value modeling (Gumbel/GEV).

-------------------------------------------------------------------------------
4.3 Weibull Distribution
-------------------------------------------------------------------------------

Wind speed WD is often approximated by Weibull(k, A).

PDF:
f(u) = (k / A) * (u / A)^(k-1) * exp(-(u/A)^k)

Parameters:
- k (shape)
- A (scale)

WindDatas uses:
- Maximum-likelihood estimation (MLE)
- SciPy fitting routines

Use:
- Good for global distribution shape
- Not ideal for extremes → Gumbel preferred

-------------------------------------------------------------------------------
4.4 Gumbel Distribution (Extreme Value Type I)
-------------------------------------------------------------------------------

Used for return period calculations of maxima.

CDF:
F(x) = exp(-exp(-(x - μ)/β))

Return level for T years:
x_T = μ - β * ln(-ln(1 - 1/T))

WindDatas:
- Fits (μ, β) via MLE
- Computes 50-year wind for each dataset

Strengths:
- Simple and robust
- Standard for AMS

Limitations:
- Less flexible than full GEV

-------------------------------------------------------------------------------
4.5 Generalized Extreme Value (GEV)
-------------------------------------------------------------------------------

GEV unifies:
- Gumbel (k=0)
- Fréchet (k>0)
- Weibull (k<0)

CDF:
F(x) = exp(-(1 + k*(x - μ)/σ)^(-1/k))

Parameters:
- μ (location)
- σ (scale)
- k (shape)

WindDatas:
- Provides optional GEV fitting
- Defaults to Gumbel for stability

Notes:
- For k ≈ 0 → GEV ≈ Gumbel
- GEV sensitive to sample size; AMS length is critical

-------------------------------------------------------------------------------
5. Comparing Datasets Across Sources
-------------------------------------------------------------------------------

Comparability rules:
- At least 1 full year of overlap for correlation
- Ideally ≥ 5 years
- If no intersection → flagged and excluded from plots

For each source pair:
- Compute Pearson correlation
- Compute mean bias
- Compute ratio of means and gusts
- Produce radar wind direction plots (if direction available)

-------------------------------------------------------------------------------
6. Limitations and Known Issues
-------------------------------------------------------------------------------

- NOAA metadata height inconsistencies affect normalization.
- ERA5 underestimates short-term gusts.
- NASA POWER too smooth for extremes.
- Meteostat inherits gaps from NOAA.
- Open-Meteo definition of gust is model-dependent.
- Extreme value fits require ≥ 10 AMS points for stability.

WindDatas reports these limitations in logs and documentation.

-------------------------------------------------------------------------------
7. Summary of the Scientific Pipeline
-------------------------------------------------------------------------------

1. Acquire raw data  
2. Normalize (units, timestamps, heights)  
3. Consolidate per-source time series  
4. Compute descriptive stats  
5. Compute outliers and data quality metrics  
6. Compute Weibull + Gumbel fits  
7. Extract annual maxima  
8. Estimate 50-year return levels  
9. Generate plots and report

-------------------------------------------------------------------------------
8. References
-------------------------------------------------------------------------------

- WMO Guide to Meteorological Instruments and Methods of Observation  
- ERA5 Documentation (Copernicus Climate Data Store)  
- NOAA ISD Documentation  
- SciPy Statistical Methods  
- MERRA-2 / NASA POWER Technical Notes  

-------------------------------------------------------------------------------
End of document.
