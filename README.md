# CarbonFusion AI — Research MVP (Phase 1)

**Theme B — AI/ML & Data-Driven Models for Climate Prediction**  
**Project:** Uncertainty-aware forest aboveground biomass and carbon estimation using Sentinel-2 imagery and NASA GEDI L4A.

> **Research status:** Phase 1 is an offline, reproducible **synthetic-data test harness** plus a Google Earth Engine export script for sourcing real observations. **The models have not yet been validated with real forest observations.** This repository does NOT yet include the future-deforestation forecast model.

## Research objectives
1. Estimate aboveground biomass density (AGBD, Mg/ha) using Sentinel-2 spectral and vegetation features, supervised by GEDI-modeled biomass observations.
2. Evaluate Random Forest and XGBoost baselines using geographically separated train/calibration/test groups.
3. Estimate prediction uncertainty with a 90% split-conformal interval, report coverage and interval width.
4. Prepare future research on spatial carbon-stock mapping and time-forward deforestation-risk prediction.

## Scientific framing
- **Main research question:** Can uncertainty-aware, spatially validated models improve reliability of satellite-derived forest biomass estimates?
- **H1:** Optical + terrain features may improve AGBD estimation over optical-only baselines.
- **H2:** Separately calibrated prediction intervals can quantify held-out reference prediction uncertainty.
- **H3:** Spatial holdouts offer a tougher test of geographic generalization than random point splitting.

GEDI AGBD is a **modeled reference**, not direct field truth. Using GEDI targets in both experiments alone does not establish gains due to LiDAR-derived predictors. The implemented models use GEDI as labels; no continuous GEDI structural-predictor fusion is currently claimed.

## Implemented modules
- Synthetic sample generator for testing processing only.
- Dataset validation and GEDI quality filters.
- Random Forest on Sentinel-2 optical features.
- XGBoost on optical features.
- XGBoost on optical and terrain features.
- Geographic block splits into model-fitting, calibration, and test groups.
- RMSE / MAE / R² model comparisons and split-conformal 90% prediction intervals.
- Estimated aboveground carbon density from biomass (illustrative fraction 0.47).
- Streamlit visualization of held-out predictions.
- Earth Engine JavaScript for Sentinel-2 + GEDI L4A V2.1 sample CSV export.
- Small automated tests.

## Quick start
Python 3.10+:
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python scripts/make_demo_data.py
python -m scripts.train
streamlit run app.py
```
Results are written to `outputs/metrics.json`, `outputs/heldout_predictions.csv` and `outputs/biomass_model.joblib`. These are ignored by Git.

## Real satellite data
1. Open https://code.earthengine.google.com/ and paste `earth_engine/export_samples.js`.
2. Adjust the illustrative Similipal-region rectangle, dates, and sampling configuration.
3. Run the Earth Engine script and start its Drive CSV export.
4. Download the CSV into `data/real_samples.csv`.
5. Train using:
```bash
python -m scripts.train --input data/real_samples.csv --output outputs/real
```
**Research precautions:** The export is a convenience prototype using yearly Sentinel-2 and mosaicked GEDI data, not rigorous footprint-by-footprint temporal matching. Before reporting scientific results, align acquisition dates, footprints, resolution and forest types; evaluate sampling bias, buffered spatial CV, field validation and carbon-stock aggregation uncertainty.

### Expected CSV fields
`longitude, latitude, agbd, agbd_se, B2, B3, B4, B5, B6, B7, B8, B8A, B11, B12, ndvi, ndmi, ndre, elevation, slope`

Optical bands are unit-scaled reflectance. AGBD and its standard error are in Mg/ha.

## Research architecture
Sentinel-2 optical data + GEDI sampled AGBD + elevation/slope → quality filtering & feature matching → grouped geographic model training → independent calibration → held-out evaluation → AGBD estimates + prediction intervals → approximate aboveground carbon density.

**Future extension (not implemented):** Historical forest-loss labels + environmental and accessibility covariates → time-forward deforestation probability model → carbon-at-risk scenario analysis.

## Key limitations
- The block size (`--block-deg 0.08`) uses latitude/longitude bins, not equal-area or spatially buffered CV.
- Conformal coverage is calculated against GEDI-modeled reference values and does not automatically incorporate all GEDI errors or spatial distribution shift.
- Carbon fraction 0.47 is illustrative and must be justified for selected forest types.
- CO₂-equivalent *stock* is not actual emissions or automatically verified carbon credits.
- All generated example performance values are **synthetic test outcomes**, not real research results.

## Files
```
app.py
src/pipeline.py
scripts/train.py
scripts/make_demo_data.py
earth_engine/export_samples.js
tests/test_pipeline.py
requirements.txt
.gitignore
```

## Next steps
- **Phase 1B:** Acquire real GEDI + Sentinel-2 samples with verified spatial/temporal matching.
- **Phase 2:** Spatially buffered CV, calibrated uncertainty, ablation/SHAP experiments and independent validation.
- **Phase 3:** Produce spatial biomass and carbon-stock maps, propagate aggregate uncertainty.
- **Phase 4:** Train and validate a distinct future-deforestation-risk model, then calculate scenario-based carbon at risk.

## Official data
- [Sentinel-2 SR Harmonized](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED)
- [GEDI L4A V2.1 monthly Earth Engine data](https://developers.google.com/earth-engine/datasets/catalog/LARSE_GEDI_GEDI04_A_002_MONTHLY)
- [NASA GEDI L4A V3 documentation](https://daac.ornl.gov/GEDI/guides/GEDI_L4A_AGB_Density_V3.html)


## New: Nuxt/Vue research dashboard (Phase 1 frontend)

The project now includes a **Nuxt 4 + Vue 3 + MapLibre + Apache ECharts** frontend and a **FastAPI** read-only model-artifact service. The previous Streamlit demo remains intact.

Setup and screenshots guidance: [Frontend setup](docs/FRONTEND_SETUP.md).

Run from repository root:

```bash
pip install -r requirements.txt -r backend/requirements.txt
python scripts/make_demo_data.py
python -m scripts.train
uvicorn backend.main:app --reload --port 8000
```

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Visit http://localhost:3000. Demo model results are **synthetic** until you import and validate real GEDI + Sentinel-2 samples. The map displays held-out **sample points**, not a forest-wide raster. Future deforestation-risk forecasting is **not yet implemented**.


## Phase 1B — Real satellite observations and resilient geospatial explorer

A new Earth Engine script is available at [earth_engine/export_real_monthly_samples.js](earth_engine/export_real_monthly_samples.js). It extracts monthly quality-filtered GEDI L4A V2.1 modeled biomass targets with optical composites from nearby Sentinel-2 acquisition dates, plus terrain features. It is a **research prototype**, not exact GEDI footprint/time colocation.

Follow [docs/REAL_DATA_SETUP.md](docs/REAL_DATA_SETUP.md) to export candidate CSV training data, validate it and train the prototype on actual Earth Engine observations. Real data are not included in the repo because Earth Engine requires user access and cloud exports.

The map includes a coordinate-plot fallback if MapLibre's online basemap tiles cannot load, with interactive held-out sample values. The map is **not a continuous biomass surface**.

```bash
# After placing your exported data at data/real_samples.csv:
python -m scripts.validate_real_data --input data/real_samples.csv
python -m scripts.train --input data/real_samples.csv --output outputs/real
CARBONFUSION_OUTPUT_DIR="$(pwd)/outputs/real" CARBONFUSION_DATA_MODE=real python -m uvicorn backend.main:app --reload --port 8001
```

For Nuxt, set `NUXT_PUBLIC_API_BASE=http://localhost:8001` in `frontend/.env`.


## Expanded real-observation sampling (Phase 1B update)

The initial Earth Engine CSV contained **11** observations for 2022. Use the new [expanded Earth Engine extractor](earth_engine/export_expanded_samples.js) to collect more candidate samples with a larger study area, configurable annual exports, an optional tree-cover mask and diagnostic monthly counts. See [expanded extraction guide](docs/EXPANDED_DATA_EXTRACTION.md).

```bash
# Once exported CSVs have been downloaded into data/:
python -m scripts.merge_real_exports --inputs data/carbonfusion_gedi_s2_2022_expanded.csv data/carbonfusion_gedi_s2_2023_expanded.csv --output data/real_samples.csv
python -m scripts.validate_real_data --input data/real_samples.csv
python -m scripts.train --input data/real_samples.csv --output outputs/real
```

The extraction/merge scripts cannot automatically download data from your Google account. Sample counts and eventual model accuracy are not guaranteed. GEDI L4A labels remain modeled references; this is not field-validated forest carbon monitoring.


### Extended 2018–2026 study window

[Multi-year Earth Engine extraction script](earth_engine/export_2018_2026_window.js) and [availability / run guide](docs/OBSERVATION_WINDOW_2018_2026.md). GEDI L4A monthly labels are currently available only for 2019–mid-2025 in Earth Engine; 2018 and 2026 are **not** GEDI-labeled training periods. Annual exports use GEDI-targeted stratified pixel sampling and need manual task execution in Earth Engine.
