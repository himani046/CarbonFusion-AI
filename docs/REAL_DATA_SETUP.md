# Real Sentinel-2 + GEDI data integration

## Current status
The dashboard connects to working Python models trained on **synthetic test data**. Real training requires Google Earth Engine access and a CSV export. This repository cannot access your personal Earth Engine project automatically.

## 1. Export observations
1. Open https://code.earthengine.google.com/ and sign into a Google account registered with Earth Engine.
2. Create a script and paste `earth_engine/export_real_monthly_samples.js`.
3. Select your Earth Engine Cloud project if requested.
4. Run. Check `Candidate samples` in Console; this depends on regional coverage.
5. Go to **Tasks**, click **Run** on the export, and save the CSV to your Google Drive `CarbonFusionAI` folder.
6. Download to the repository at `data/real_samples.csv` (the CSV is gitignored).

The script uses 2022 monthly GEDI Version 2.1 raster products and +/-45-day Sentinel-2 composites near an illustrative Similipal landscape rectangle. Sample coordinates are raster grid centers, **not exact GEDI shot locations**. Inspect monthly counts and data quality.

## 2. Validate the export
From the repository root:

```bash
python -m scripts.validate_real_data --input data/real_samples.csv
```

It checks columns, QC survival, unique geographic blocks and biomass range and writes `outputs/real_validation.json`. Do not interpret this as scientific field validation.

## 3. Train the prototype on real extracted data
```bash
python -m scripts.train --input data/real_samples.csv --output outputs/real
```

Keep the existing synthetic run outputs untouched. To tell FastAPI which artifacts to load:

```bash
CARBONFUSION_OUTPUT_DIR="$(pwd)/outputs/real" CARBONFUSION_DATA_MODE=real python -m uvicorn backend.main:app --reload --port 8001
```

Ensure `frontend/.env` has `NUXT_PUBLIC_API_BASE=http://localhost:8001`, then restart the Nuxt dev server. The mode label `real` indicates the operator selected these outputs; it is not independent provenance verification.

## 4. Scientific checklist before making research claims
- Replace rectangle with an appropriate forest-only study-area definition.
- Use spatial/temporal GEDI-footprint matching rather than only monthly rasters at 25 m.
- Inspect cloud coverage, terrain, nonforest data, revisit period and any sample duplicates.
- Ensure reference samples, training data, validation and test areas are geographically independent.
- Use buffered spatial cross-validation and investigate GEDI observation error and sample selection bias.
- Evaluate measured field plots if available; otherwise describe accuracy against GEDI-derived labels.
- Don't interpret AGBD as carbon emissions or a complete ecosystem carbon budget.

## 5. Verify map & frontend
The geospatial explorer now includes a coordinate-based SVG fallback if MapLibre/WebGL tiles cannot load. Its plotted dots represent **sample predictions**, not a continuous biomass raster. Visit `http://localhost:8001/api/predictions` to verify GeoJSON contains features. Check browser network settings if the online basemap is blocked.
