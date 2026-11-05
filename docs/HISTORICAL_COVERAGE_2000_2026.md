# CarbonFusion AI | Historical interval 2000–2026

**The study can span 2000–2026, but no sensor provides GEDI biomass labels throughout that period.**

- 2000–2012: Landsat 5 and 7 provide optical observations.
- 2013–2018: Landsat 7/8, with Sentinel-2 beginning in 2015.
- 2019–2025: GEDI L4A biomass observations where available (Earth Engine monthly V2.1 currently through July 2025); train biomass models separately on overlapping optical and GEDI records.
- 2026: Landsat/Sentinel-2 observations available up to the actual imagery acquisition date. This is a partial year, not an annual completion, and Earth Engine GEDI V2.1 does not establish 2026 biomass labels.

## Run historical extraction
1. Open the Earth Engine Code Editor and paste `earth_engine/export_landsat_history_2000_2026.js`.
2. Click Run and inspect yearly NDVI, NDMI, NBR regional averages and scene counts.
3. In Tasks, run `carbonfusion_landsat_history_2000_2026`.
4. Download the CSV locally into `data/landsat_history_2000_2026.csv`.
5. **Do not train `scripts/train.py` on this file.** There is no `agbd` label.

The script exports **27 annual rows**, not 27 years of biomass measurements. Metrics are means across an illustrative Odisha study rectangle (not an official forest boundary). Mixed Landsat sensor data require cross-sensor harmonization before a publication-grade quantitative time trend. Masking and cloud availability can bias annual comparisons. Landsat 7 has scan-line artifacts in some years.

## Continue actual biomass model training
Use `earth_engine/export_expanded_samples.js` for individual GEDI-era years where source records exist, then merge and validate the exported sample files. Because we must not invent missing GEDI data, pre-2019 carbon reconstructions require a **separately validated transfer model** using historical Landsat features, land-cover-change constraints and external reference data.

## Research goal
- Landsat historical change: investigate how vegetation and forest land cover changed from 2000 to the available 2026 observations.
- GEDI + Sentinel-2 biomass estimation: train an uncertainty-aware AGBD model using overlapping reference years.
- Future carbon risk: separate, temporally validated forest-loss modeling and conditional stock-loss scenarios; not implemented yet.

Sources:
https://developers.google.com/earth-engine/datasets/catalog/landsat
https://developers.google.com/earth-engine/datasets/catalog/LARSE_GEDI_GEDI04_A_002_MONTHLY
https://developers.google.com/earth-engine/guides/landsat
