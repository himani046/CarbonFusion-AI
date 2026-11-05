# CarbonFusion AI historical analysis: 2000–2026

## Why separate the data streams?
Your research can cover **2000–2026**, but a single GEDI + Sentinel-2 supervised dataset cannot cover all those years.

- **2000–2026:** USGS Landsat Collection 2 Level-2 surface reflectance can provide annual vegetation/land-cover information (Landsat 5, 7, 8, and 9, depending on date).
- **2015 onward:** Sentinel-2 imagery becomes available, though product coverage differs by level and processing era.
- **2019 onward:** GEDI provides sampled laser structural observations and modeled aboveground biomass density estimates, with temporal gaps and mission-specific coverage.

**This repository does not claim measured forest carbon stock for 2000–2018.**

## Run the historical extraction
1. Open [earth_engine/export_landsat_history_2000_2026.js](../earth_engine/export_landsat_history_2000_2026.js).
2. Copy the script into a new Google Earth Engine Code Editor file.
3. Run it and inspect the table and line chart in Console.
4. Under Tasks, start `carbonfusion_landsat_vegetation_2000_2026`.
5. Download the CSV from your Google Drive folder `CarbonFusionAI`.

The code exports **27 annual aggregate records** (2000–2026 inclusive), with NDVI, NDMI and NBR, image-count and valid-area diagnostics. **2026 is incomplete, only through November 5, 2026**. Annual summaries over an illustrative rectangle are not forest-only change maps, and year-to-year changes may be influenced by cloud sampling, sensors and seasons.

## Do not combine the two CSV types
- `carbonfusion_landsat_vegetation_2000_2026.csv`: yearly regional statistics, *no AGBD labels*. Use for a historical visualization module.
- `carbonfusion_gedi_s2_YYYY_expanded.csv`: present-era pixel/footprint-proxy GEDI biomass training candidates, from existing export scripts. Use those for `scripts.merge_real_exports`, `scripts.validate_real_data`, and `scripts.train`.

**Do not pass the annual Landsat CSV to `scripts.train`**. It does not have the target variable `agbd` or the required Sentinel-2 predictors.

## Research plan to extend beyond index trends
1. Produce consistent Landsat composites and evaluate sensor harmonization.
2. Build **validated** historical land-cover and forest-loss maps for selected years, keeping forest definitions stable.
3. Establish modern GEDI + Sentinel-2 biomass reference model with geographic validation and uncertainty.
4. For 2000–2018 carbon estimates, develop a **separate retrospective model** using harmonized Landsat features and modern GEDI supervised targets; test whether this extrapolation across decades is defensible. Do not present it as measured historical biomass without independent historical/field references.
5. Predict future deforestation with a separate time-based model only once reliable historical labels exist.

Official resources:
- USGS Landsat Collection 2 surface reflectance: https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-reflectance
- Sentinel-2 mission: https://www.esa.int/Applications/Observing_the_Earth/Copernicus/Sentinel-2/
- GEDI data: https://gedi.umd.edu/
