# Nuxt research dashboard + FastAPI service

This replaces the former Streamlit UI **without deleting it**. Streamlit remains available for quick experiments.

## 1. Python API
From the repository root, with Python 3.10+:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r backend/requirements.txt
python scripts/make_demo_data.py
python -m scripts.train
uvicorn backend.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

Endpoints:
- `GET /api/health` — readiness and dataset mode
- `GET /api/overview` — held-out summary, evaluation metrics and uncertainty
- `GET /api/model-metrics` — complete model comparison and split metadata
- `GET /api/predictions?limit=350` — GeoJSON observation points (not a biomass raster)

The backend reads the existing `outputs/metrics.json` and `outputs/heldout_predictions.csv`.
Optional env vars: `CARBONFUSION_OUTPUT_DIR`, `CARBONFUSION_DATA_MODE`, `CARBONFUSION_CORS_ORIGINS`. Demo mode is the default. Only set `CARBONFUSION_DATA_MODE=real` when the training was actually run on real verified data; this flag does **not** validate provenance.

## 2. Nuxt 4 frontend
In a second terminal (Node.js 20+ recommended):

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Open http://localhost:3000. Nuxt connects to FastAPI at http://localhost:8000.

The UI includes:
- Responsive dark scientific research dashboard
- Biomass evaluation metrics
- MapLibre point map of held-out geographic biomass predictions
- ECharts RMSE comparison
- Detailed model table and transparent scientific caveats
- Server-down / outputs-missing states

**Map data warning:** The dots represent held-out samples, not actual spatially complete biomass stock. Don't use the sample point map as a forest-carbon raster or conservation-priority map.

## 3. Production considerations
- The MapLibre starter uses OpenStreetMap standard raster tiles intended for development-scale use. Use a proper production tile service that permits your traffic.
- No API credentials, real-time satellite streams, or deployed web hosting are configured.
- Nuxt and FastAPI are separate processes; reverse-proxy or deploy separately with HTTPS and configured CORS.
- Install dependencies and run `npm run build` and `pytest` in your own environment before production deployment.
- Do not publish carbon credits, carbon emissions, or future risk probabilities based solely on this demo.

## 4. Next research work
Use `earth_engine/export_samples.js` for initial GEDI–Sentinel sample acquisition, then improve footprint and temporal matching, quality control, spatially buffered evaluation, and field validation. Add real continuous biomass raster tiles only after validated inference, and implement future deforestation predictions as a separate research module.
