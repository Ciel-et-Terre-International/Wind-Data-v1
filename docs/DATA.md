
# DATA – Meteorological Sources Used in Wind Data

This document details all meteorological data sources used in the Wind Data project. It focuses on precise definitions, units, wind averaging durations, and conversion rules applied to ensure consistent and rigorous comparisons between sources.

---

[← Back to README](../README.md)

## Weather Data Sources

### 1. NOAA – ISD (Integrated Surface Dataset)

- [NOAA ISD Format Document (PDF)](https://www.ncei.noaa.gov/pub/data/noaa/isd-lite/isd-format-document.pdf)
- [CWOP/WMO8 Observer Guide](https://www.weather.gov/media/epz/mesonet/CWOP-WMO8.pdf)

### 2. Meteostat

- [Meteostat Hourly Format](https://dev.meteostat.net/formats/hourly.html#wind)

### 3. Open-Meteo

- [Open-Meteo API Documentation](https://open-meteo.com/en/docs#parameter-wind_speed_10m)

### 4. ERA5 (ECMWF)

- [ERA5: Data Documentation](https://confluence.ecmwf.int/display/CKB/ERA5%3A+data+documentation)

### 5. NASA POWER

- [NASA POWER Methodology – Wind Speed](https://power.larc.nasa.gov/docs/methodology/parameters/#windspeed-at-10m)

---

## Wind Averaging Duration Conversions

### Why is conversion necessary?

Wind speeds depend heavily on the averaging duration. One cannot directly compare 1-hour values with 10-minute or 2-minute measurements. All sources must be harmonized to a common temporal base before any comparison.

### Typical Conversion Factors

| From   | To        | Typical Factor | References                   |
|--------|-----------|----------------|------------------------------|
| 1 h    | 10 min    | × 1.05 – 1.10  | WMO Guide No. 8, IEC 61400-1 |
| 10 min | 3s Gust   | × 1.35 – 1.50  | WMO, IEC standards           |
| 2 min  | 10 min    | × 0.95 – 1.00  | NWS/WMO (flat terrain)       |
| 1 h    | 2 min     | × 1.10 – 1.15  | Empirical, WMO studies       |

### Official References

- **WMO Guide No. 8 (Instruments and Observing Methods)**:  
  [https://community.wmo.int/en/activity-areas/imop/wmo-no_8](https://community.wmo.int/en/activity-areas/imop/wmo-no_8)

- **WMO Wind Averaging Conventions**:  
  [WMO_TC_Wind_Averaging_2010.pdf](https://www.systemsengineeringaustralia.com.au/download/WMO_TC_Wind_Averaging_27_Aug_2010.pdf)

- **IEC 61400-1 / IEC 61400-3-1 – Wind Turbine Design Standards**:  
  [IEC/WES Reference PDF](https://wes.copernicus.org/preprints/wes-2023-35/wes-2023-35-ATC1.pdf)

---

## Full Bibliography

1. WMO (2021). *Guide to Meteorological Instruments and Methods of Observation – WMO No. 8*. Geneva: World Meteorological Organization.  
2. WMO (2010). *Wind Averaging Conventions and Gust Factors*, WMO Technical Conference, Australia.  
3. IEC (2019). *IEC 61400-1: Wind turbines – Design requirements*.  
4. ECMWF (2024). *ERA5 Climate Reanalysis Dataset Documentation*. ECMWF.  
5. NASA (2023). *NASA POWER Project Methodology – Wind Parameters*. NASA LaRC.  
6. Meteostat (2024). *Data Format & API Reference*. [https://dev.meteostat.net](https://dev.meteostat.net)  
7. Open-Meteo (2024). *API Reference & Parameters*. [https://open-meteo.com](https://open-meteo.com)  
8. NOAA/NCEI (2023). *ISD Data Format Documentation*. [https://www.ncei.noaa.gov](https://www.ncei.noaa.gov)

---

## 1. Meteostat – Observed Data from Weather Stations

**API Link**: [https://dev.meteostat.net/](https://dev.meteostat.net/)

### Source Profile: Meteostat

#### Data Type
- **Observed**, sourced from official weather stations (SYNOP, METAR, national networks).
- Data collected from sources such as NOAA ISD, DWD (Germany), Environment Canada, etc.
- Aggregation and harmonization managed by the Meteostat team.

Raw Meteostat data is retrieved in km/h (API native unit), and then converted to m/s (1 m/s = 3.6 km/h) upon import into Wind Data to ensure consistency with other sources.

#### Measurement Height
- **Typically: 10 meters above ground**, in line with WMO recommendations.
- **⚠️ However**, there is **no guarantee** of uniform sensor height; individual stations may vary.
- Meteostat does **not provide** exact instrument height via API but follows the WMO standard when the source specifies it.

#### Averaging Period
- **Mean wind (`windspeed_mean`)**: 10-minute moving average, in line with **WMO No. 8**.
  - This period applies mainly to SYNOP and METAR stations, which dominate the Meteostat database.

#### Gusts (`gust`)
- Represent the **maximum 3-second wind speed** observed during the previous period (often 10 min).
- If available, Meteostat includes this 3-second gust value per WMO standards.

#### Wind Direction
- Wind **origin direction**, expressed in azimuth degrees:
  - `0°` = from North, `90°` = from East, `180°` = from South, `270°` = from West
- Measured over the same 10-minute period as the mean speed.

#### Typical Variables (when available)

| Variable         | Description                         | Unit  |
|------------------|-------------------------------------|-------|
| `windspeed_mean` | 10-minute average wind speed        | km/h  |
| `wind_direction` | 10-minute average wind direction    | deg   |
| `gust`           | Max 3-second gust during interval   | km/h  |

#### Technical Summary

| Element             | Detail                                         |
|---------------------|------------------------------------------------|
| Source              | Meteostat (observed data)                      |
| Anemometer height   | ~10 m (WMO standard if known, else unknown)    |
| Mean wind           | 10-minute moving average                       |
| Gusts               | 3-second max (if provided by source)           |
| Direction           | Wind origin azimuth                            |
| Time resolution     | Usually hourly or half-hourly                  |
| Followed standard   | WMO No. 8                                      |

#### Acquisition Method

```python
from meteostat import Stations, Daily

# Select nearby stations
stations = Stations().nearby(lat, lon).fetch(2)

# Download daily data
data = Daily(station_id, start, end).fetch().reset_index()

# Rename columns
df = df[["time", "wspd", "wpgt", "wdir"]]
df = df.rename(columns={
    "wspd": "windspeed_mean",
    "wpgt": "windspeed_gust",
    "wdir": "wind_direction"
})
```

---



## 2. NOAA ISD – Raw Hourly Observational Data

**Data link**: [https://www.ncei.noaa.gov/data/global-hourly/](https://www.ncei.noaa.gov/data/global-hourly/)

### Source Profile: NOAA ISD (Integrated Surface Dataset)

#### Data Type
- **Observed**, collected from official weather stations worldwide.
- Primary source: **ISD**, maintained by NOAA (NCEI).
- Derived from METAR, SYNOP, and AUTO messages, aggregated from over **35,000 stations**.

#### Measurement Height
- The **instrument height** varies by station.
- NOAA’s recommended anemometer height is **10 meters**, but it is **not always explicitly listed** in CSV files from the public portal.
- To estimate the measurement context → refer to `isd-history.csv` (field `ELEV` ≠ anemometer height but useful for terrain).

#### Frequency and Averaging Period
- **Typical frequency**: hourly (sometimes sub-hourly).
- **Wind speed (`WND`)**:  
  - Represents a **10-minute average** prior to the observation time.  
  - Source: [NOAA ISH Format Documentation (PDF)](https://www.ncei.noaa.gov/pub/data/noaa/ish-format-document.pdf), section WND.
- **Wind direction**: average over the same 10-minute period.

#### Gusts (`GUST`)
- When present, **GUST** represents the **maximum 5-second gust** within the hour preceding observation.
- ⚠️ Not all stations report this variable (often missing in older or regional files).

#### Wind Direction
- Expressed in **azimuth degrees**, WMO standard:
  - `0°` = from North, `90°` = from East, etc.
- Invalid values are encoded as `999`.

#### Example of NOAA ISD CSV format

| Field     | Description                          | Example              |
|-----------|--------------------------------------|----------------------|
| `DATE`    | UTC timestamp                        | `2023-01-01T12:00:00`|
| `WND`     | 10-min avg direction and speed       | `270,15,9999,1`      |
| `GUST`    | Max 5-second gust (if available)     | `25.1`               |
| `DRCT`    | Wind direction (alternative field)   | `270`                |

#### Typical Variables Extracted for Wind Data

| Variable         | Description                           | Unit  |
|------------------|---------------------------------------|--------|
| `windspeed_mean` | 10-min average (`WND`)                | m/s    |
| `wind_direction` | Avg direction from `WND` or `DRCT`    | degrees|
| `gust`           | Max 5-sec gust (`GUST`)               | m/s    |

#### Technical Summary

| Element             | Detail                                                     |
|---------------------|------------------------------------------------------------|
| Source              | NOAA ISD (hourly station-level files)                      |
| Anemometer height   | Typically 10 m, but often not specified                    |
| Mean wind           | 10-min average before observation                          |
| Gusts               | 5-second max during previous hour (if available)           |
| Direction           | Azimuth (wind origin)                                      |
| Temporal frequency  | Hourly                                                     |
| Standard followed   | WMO / NOAA ISD official format                             |

#### Official References

- Dataset: [NOAA Global Hourly Data](https://www.ncei.noaa.gov/data/global-hourly/)
- Format: [ISH Format PDF](https://www.ncei.noaa.gov/pub/data/noaa/ish-format-document.pdf)

#### Acquisition Method

```python
# Check availability
HEAD https://www.ncei.noaa.gov/data/global-hourly/access/{year}/{usaf}{wban}.csv

# Download and parse
df = pd.read_csv(file_url)

# Extract wind data
parsed = df['WND'].str.split(',', expand=True)
df['wind_dir'] = parsed[0].astype(float)
df['wind_speed'] = parsed[3].astype(float) / 10

# Gust and direction
df['gust'] = df['GUST'].astype(float) / 10 if 'GUST' in df.columns else np.nan
df['wind_direction'] = df['DRCT'].astype(float) if 'DRCT' in df.columns else df['wind_dir']

# Daily aggregation
df_daily = df.groupby('date').agg({
    'wind_speed': 'max',
    'gust': 'max',
    'wind_direction': lambda x: x.mode().iloc[0] if not x.dropna().empty else np.nan
})
```

---

## 3. Open-Meteo – Modeled Data via API

**API Link**: [https://open-meteo.com/](https://open-meteo.com/)

### Source Profile: Open-Meteo

#### Data Type
- **Modeled data**, derived from open-source numerical weather models.
- Provided by the **Open-Meteo API**, which aggregates several public datasets.
- These are **not observations**, but **interpolated forecasts or reanalyses**.

Raw Open-Meteo data is retrieved in km/h and converted to m/s (1 m/s = 3.6 km/h) within Wind Data for consistency.

#### Models Used
Depending on the variable, hour, and location, Open-Meteo uses:
- **ICON** (DWD – Germany)
- **ECMWF HRES**
- **GFS** (NOAA global model)

For historical weather, Open-Meteo uses archived forecasts or reanalyses (exact details not always disclosed).

#### Measurement Height
- All wind variables are standardized at **10 meters above ground**, per WMO guidelines.
- ⚠️ These are **modeled values at 10 m**, not direct sensor measurements.

#### Temporal Frequency and Averaging
- Data frequency: **hourly**
- `windspeed_10m`: hourly modeled mean wind
- `windgusts_10m`: hourly modeled maximum gust

#### Gusts (`windgusts_10m`)
- Represents **modeled maximum wind gust** over the hour.
- May **underestimate peaks** due to model smoothing and horizontal resolution (~10–20 km).

#### Wind Direction
- `winddirection_10m`: wind origin direction in **azimuth degrees** (`0°` = North, `90°` = East, etc.)
- Represents hourly average from the model.

#### Typical Variables

| Variable            | Description                            | Unit  |
|---------------------|----------------------------------------|--------|
| `windspeed_10m`     | Hourly mean modeled wind at 10 m       | km/h   |
| `windgusts_10m`     | Hourly max modeled gust at 10 m        | km/h   |
| `winddirection_10m` | Hourly modeled average direction       | degrees|

#### Technical Summary

| Element             | Detail                                                         |
|---------------------|----------------------------------------------------------------|
| Source              | Open-Meteo API                                                 |
| Type                | Numerical model / reanalysis                                   |
| Height              | 10 m (standardized)                                            |
| Mean wind           | Hourly modeled mean (`windspeed_10m`)                          |
| Gusts               | Hourly modeled max gust (`windgusts_10m`)                      |
| Direction           | Hourly modeled azimuthal origin (`winddirection_10m`)          |
| Temporal frequency  | Hourly                                                        |
| Standard followed   | WMO height conventions (model → not equivalent to measurements)|

#### ⚠️ Why Open-Meteo May Underestimate Wind Speeds

Even though Open-Meteo delivers reasonably accurate average wind data, it can **underestimate peak values** compared to real station measurements, due to:

- **Model parametrization**: Grid-scale simulations (~10 km) smooth localized accelerations.
- **Generalized surface roughness**: Land-use variations (urban, forest, coastlines) are averaged across grid cells.
- **Energy conservation tuning**: Numerical stability sometimes dampens peaks.
- **No microclimate detection**: Models do not "see" specific effects like valleys, passes, or coastal gaps.
- **Temporal smoothing**: Hourly values are averaged over time steps (~1h), hiding sub-hourly variability.

#### Official References

- Docs: [https://open-meteo.com/en/docs](https://open-meteo.com/en/docs)
- Historical API: [https://open-meteo.com/en/docs/historical-weather-api](https://open-meteo.com/en/docs/historical-weather-api)

#### Acquisition Method

```python
# Daily gusts + means
url_daily = f"...&daily=windspeed_10m_max,windspeed_10m_mean"

# Hourly direction
url_hourly = f"...&hourly=winddirection_10m"

# Merge both
df = pd.merge(df_daily, df_dir, on="time", how="left")
```

---


## 4. ERA5 – Reanalysis Data from ECMWF

**Copernicus CDS Link**: [ERA5 Single Levels Dataset](https://cds.climate.copernicus.eu/cdsapp#!/dataset/reanalysis-era5-single-levels)

### Source Profile: ERA5 (Copernicus / ECMWF)

#### Data Type
- **Modeled climate reanalysis**, produced by the **European Centre for Medium-Range Weather Forecasts (ECMWF)**.
- Distributed via the **Copernicus Climate Data Store (CDS)**.
- Combines a global numerical weather model (IFS) with assimilation of millions of observations (stations, satellites, radiosondes...).

#### Measurement Height
- Winds are provided at **10 meters above ground**:
  - `10m_u_component_of_wind`
  - `10m_v_component_of_wind`
- These components are interpolated from model levels over grid cell surfaces.

#### Temporal Frequency and Averaging
- **Hourly data**, with a **1-hour resolution**.
- Wind speeds are derived as:  
  `windspeed = sqrt(u² + v²)`
- These values represent a **spatial average over a 31 km grid cell**.

Wind Data uses ERA5 Single Levels Timeseries via CDSAPI because it delivers clean CSV files ready for automated processing.

**Advantages:**
- Fast and easy download
- No need for GRIB/NetCDF parsing
- Fully compatible with Wind Data automation

**Known Limitation:**  
This product **does not provide wind gusts** (`10m_wind_gust_since_previous_post_processing` is not available here).

Gusts are only available in:
- ERA5 hourly on single levels (GRIB/NetCDF)
- ERA5-Land hourly (GRIB/NetCDF)

**Strategic Choice:**  
Wind Data prioritizes CSV-based automation and consistency, even if that means omitting ERA5 gusts for now.  
This trade-off is documented and assumed for full transparency.

#### Wind Direction
- Computed from U/V components:  
  `direction = arctan2(-u, -v)`
- Wind **origin direction**, expressed in azimuth degrees (`0°` = North, `90°` = East...).

#### Typical Variables

| Variable                      | Description                         | Unit |
|-------------------------------|-------------------------------------|------|
| `10m_u_component_of_wind`     | Zonal (west-east) wind component    | m/s  |
| `10m_v_component_of_wind`     | Meridional (south-north) component  | m/s  |

#### Technical Summary

| Element             | Detail                                              |
|---------------------|-----------------------------------------------------|
| Source              | ERA5 via Copernicus CDS                             |
| Type                | Modeled reanalysis                                  |
| Temporal resolution | 1 hour                                              |
| Spatial resolution  | ~31 km (ERA5-Land ~9 km)                            |
| Height              | 10 m above ground                                   |
| Mean wind           | Hourly grid-based mean                              |
| Gusts               | Not available in CSV version                        |
| Direction           | From U/V components (azimuth origin)                |

#### ⚠️ Limitations and Notes (ECMWF)

> “Yes, the underestimation is related to the limited spatial resolution of ERA5, and the fact that ERA5 represents an area average.”  
> — *Hans Hersbach, ECMWF*

- **ERA5 tends to smooth extreme winds**, especially local gusts.
- **Stations give point measurements**, while ERA5 provides **area means over 31 km²**.
- **Empirical correction** is possible and encouraged when comparing with observed data.
- **ERA6** is under development with higher resolution (expected ~late 2026).

#### References

- [Copernicus Climate Data Store](https://cds.climate.copernicus.eu/)
- [ERA5 documentation](https://confluence.ecmwf.int/display/CKB/ERA5)
- Official reply from ECMWF (Hans Hersbach, June 2025)

#### Acquisition Method (via CDSAPI)

```python
request = {
  "variable": ["10m_u_component_of_wind", "10m_v_component_of_wind"],
  "date": f"{start}/{end}",
  "location": {"latitude": lat, "longitude": lon},
  "data_format": "csv"
}
c.retrieve("reanalysis-era5-single-levels-timeseries", request).download(...)
```

---

## 5. NASA POWER – NASA Modeled Reanalysis Data

**API Link**: [https://power.larc.nasa.gov/](https://power.larc.nasa.gov/)

### Retrieved Variables

| Variable           | Description                      | Unit | Temporal Aggregation |
|--------------------|----------------------------------|------|-----------------------|
| windspeed_mean     | Daily average wind speed         | m/s  | daily                 |
| windspeed_gust     | Daily gusts (if available)       | m/s  | daily                 |
| wind_direction     | Daily average direction          | °    | daily                 |
| u_component_10m    | Zonal (U) wind component         | m/s  | daily                 |
| v_component_10m    | Meridional (V) wind component    | m/s  | daily                 |

### Technical Characteristics

- **Modeled height**: 10 m
- **Grid resolution**: 0.5° (~55 km)
- **Type**: satellite-based reanalysis (MERRA)
- **Period**: since 1981
- **Limitation**: gust data often missing before 2001

### Acquisition Method

```python
url = (
  f"https://power.larc.nasa.gov/api/temporal/daily/point?parameters=WS10M,WD10M,U10M,V10M"
  f"&latitude={lat}&longitude={lon}&start={start}&end={end}&format=JSON"
)
response = requests.get(url)
data = response.json()['properties']['parameter']
```

---

## Weather Station Metadata – Technical Profile

### Why Metadata Is Essential

Wind measurements (observed or modeled) depend on:
- **Measurement height**
- **Terrain and surrounding environment**
- **Instrument quality and exposure**

⇒ Without metadata, any source comparison is biased or incomplete.

---

### Key Metadata Fields to Capture

| Field                  | Description                                                  |
|------------------------|--------------------------------------------------------------|
| `station_id`           | Unique identifier (WMO, ISD, Meteostat…)                     |
| `name`                 | Station name                                                 |
| `latitude / longitude` | Geographic coordinates                                       |
| `elevation`            | Altitude above sea level                                     |
| `anemometer_height`    | Anemometer height (usually 10 m if unknown)                  |
| `station_type`         | Airport, military base, automated station, etc.              |
| `data_availability`    | Period of operation / temporal coverage                      |
| `variables_available`  | Mean wind, gusts, direction, temperature...                  |
| `distance_to_site`     | Distance from station to site (in km)                        |
| `roughness_context`    | Terrain type: urban, rural, forest, mountain, coastal…       |
| `exposure_score`       | Qualitative or semi-quantitative wind exposure rating        |

---

### Common Metadata Issues

| Issue                             | Explanation                                                            |
|----------------------------------|------------------------------------------------------------------------|
| Unknown anemometer height        | Default assumption: 10 m (WMO), but actual height may vary (6–15 m)    |
| Sheltered station                | Nearby obstacles (trees, buildings, terrain) reduce wind measurement   |
| No documented environment        | Terrain, roughness, exposure not always described                      |
| Missing/incomplete variables     | `GUST` or `DRCT` fields often absent in older files                    |
| Imprecise location               | Lat/lon rounded to 2 decimals → large uncertainty on real position     |
| Unknown station type             | May impact calibration, maintenance and data quality                   |

---

### How to Assess Roughness & Terrain Context

#### 1. Visual Inspection (Google Earth, Street View)
- Identify forests, buildings, terrain orientation
- Match land cover to Eurocode **z0 roughness classes**:

| Terrain Type             | Typical `z0` Roughness | Example                                |
|--------------------------|------------------------|----------------------------------------|
| Sea / lake               | 0.0002 – 0.003          | ocean, large open water                |
| Open flat terrain        | 0.01 – 0.03             | fields, plains, deserts                |
| Semi-open countryside    | 0.05 – 0.1              | farmland, isolated villages            |
| Suburban / low urban     | 0.2 – 0.5               | subdivisions, small towns              |
| Dense urban core         | 1.0 – 2.0               | large cities, skyscrapers              |
| Forest / mountainous     | > 0.5                   | hills, forests, ridges                 |

#### 2. Satellite and Open Data
- Use CORINE Land Cover, Copernicus, SRTM rasters to estimate land use
- Automatic roughness classification may be possible in the future via GIS/API

#### 3. Qualitative Score in Wind Data
- Wind Data allows assigning an **exposure score from 1 to 5**:
  - 5 = very exposed (plateau, coast)
  - 1 = very sheltered (valley, forest, city center)

---

### Integration in Wind Data

For each station (Meteostat, NOAA, etc.), Wind Data stores:
- **Measurement height** (default: 10 m if unknown)
- **Distance to the site** (in km)
- **Estimated terrain type / roughness**
- **Available variables** (to determine comparison feasibility)
- **Exposure score (1–5)** and optional comment field

---

### Final Goal

> Provide for each station a **clear technical fact sheet**, including:
> - Measurement and environmental metadata
> - Missing or uncertain data fields
> - Roughness and exposure estimates
> - Station reliability for wind analysis
