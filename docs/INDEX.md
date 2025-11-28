# WindDatas – Documentation Index
Ciel & Terre International

Welcome to the official documentation of the WindDatas project.
This index provides a structured entry point to all technical, scientific, and
operational materials of the project.

-------------------------------------------------------------------------------
1. Introduction
-------------------------------------------------------------------------------

WindDatas is an internal tool developed by Ciel & Terre International to:
- retrieve multi-source historical wind data,
- normalize heterogeneous datasets,
- compute descriptive and extreme-value statistics,
- and generate site-level wind assessment reports.

This documentation covers:
- data sources and scientific methodology,
- developer guidelines and Git workflow,
- roadmap and future developments,
- operational and security notes.

-------------------------------------------------------------------------------
2. Documentation Structure
-------------------------------------------------------------------------------

The documentation is organized into the following categories:

### 2.1 Scientific Documentation
- **METHODOLOGY.md**  
  Full description of wind normalization, data characteristics, and statistical
  analysis (Weibull, Gumbel, GEV).

- **DATAS.md**  
  Technical specification of all meteorological data sources (NOAA, Meteostat,
  ERA5, NASA POWER, Open-Meteo, Visual Crossing).

### 2.2 Developer Documentation
- **CONTRIBUTING.md**  
  How to contribute, branching rules, commit conventions, PR workflow.

- **WORKFLOW.md**  
  Git workflow summary and release procedures.

- **TODO_LIST.md**  
  Upcoming tasks grouped by priority (v1.1 → v2.x).

- **ROADMAP.md**  
  Strategic multi-version roadmap: v1.x improvements and v2 architectural goals.

### 2.3 Operational Documentation
- **SECURITY.md**  
  Security guidelines for internal data management.

- **LICENSE**  
  Licensing terms (MIT).

-------------------------------------------------------------------------------
3. Additional Resources
-------------------------------------------------------------------------------

- Project README (root of repository)
- modules/ directory: Source code of all fetchers, parsers, and analysis tools
- scripts/ directory: Utility scripts for debugging, cleaning, enrichment

-------------------------------------------------------------------------------
4. Contributing and Governance
-------------------------------------------------------------------------------

For major architectural or scientific changes:
Contact: **Adrien Salicis**  
Email: adrien.salicis@cieletterre.net

All contributions must follow:
- CONTRIBUTING.md  
- WORKFLOW.md  

-------------------------------------------------------------------------------
5. Future Documentation Improvements
-------------------------------------------------------------------------------

Planned additions:
- diagrams of the processing pipeline
- example-based tutorials
- configuration reference (YAML schema)
- statistical validation examples
- API reference once the codebase evolves into a package (v2)

-------------------------------------------------------------------------------
End of document.
