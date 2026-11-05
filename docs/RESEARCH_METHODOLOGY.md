# CarbonFusion AI — Research Design

## Context
Submitted as a Theme B project concept for the MFSS Sustainability Conclave, IIT Indore. Current code is a proof-of-concept research infrastructure, not evidence of real-world accuracy.

## Research questions
- **RQ1:** How accurately can Sentinel-2 spectral features predict GEDI-derived aboveground biomass density (AGBD)?
- **RQ2:** Do additional terrain predictors improve geographically held-out AGBD prediction?
- **RQ3:** Can prediction intervals be calibrated to give useful coverage on withheld geographic blocks?
- **RQ4 (future):** Can a separately validated deforestation-probability model identify carbon stocks potentially at risk?

## Method
1. Extract cloud-masked Sentinel-2 optical bands, indices NDVI/NDMI/NDRE and DEM features.
2. Filter GEDI L4A observations for reference quality, uncertainty and degradation.
3. Align footprints, acquisition periods, resolution and forest masks (currently simplified in export demo).
4. Train Random Forest optical, XGBoost optical, XGBoost optical + terrain.
5. Use spatial grouping for fit, independent calibration and test, with a future upgrade to buffered CV.
6. Evaluate RMSE, MAE, R², empirical 90% interval coverage and mean interval width.
7. Create AGBD rasters and carbon conversion maps only after real-data validation.

## Scientific integrity
- GEDI L4A AGBD is a model-derived reference; field measurements are desirable for absolute validation.
- GEDI targets in every model are *not* proof that using LiDAR as an additional predictor boosts accuracy.
- The first-phase split-conformal intervals are calibrated to GEDI reference error, not all uncertainty.
- AGBD (Mg/ha) × documented carbon fraction gives aboveground carbon density (tC/ha). It does not estimate soil carbon, total ecosystem carbon, or directly verify CO2 emissions.
- Synthetic scores must not be reported as empirical climate-science findings.

## Proposed deforestation extension (not yet implemented)
Train a temporal forest-loss model on historical forest-cover labels, roads, settlements, terrain and climate drivers. Validate on later years; report PR-AUC, recall and probability calibration. Combining predicted forest-loss probability with forest carbon-stock estimates and conditional loss-severity assumptions gives *scenario-based potential carbon at risk*, not verified emissions.

## Research deliverables
Reproducible preprocessing and models; geographic evaluation; ablation table; uncertainty diagnostics; biomass and carbon maps; limitations and model cards; interactive geographic visualization.

## Suggested study landscape
A bounded part of the Similipal landscape in Odisha, conditional on usable GEDI coverage and quality. The current Earth Engine rectangle is illustrative, not an official protected-area boundary.

## Source datasets
- https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED
- https://developers.google.com/earth-engine/datasets/catalog/LARSE_GEDI_GEDI04_A_002_MONTHLY
- https://daac.ornl.gov/GEDI/guides/GEDI_L4A_AGB_Density_V3.html
