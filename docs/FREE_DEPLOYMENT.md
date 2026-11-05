# Free public deployment — CarbonFusion AI

Two free Render services: **FastAPI web service + Nuxt 4 generated static site**.

Current service names in `render.yaml`: `carbonfusion-ai-api`, `carbonfusion-ai-dashboard`. Render may assign a different actual domain if a name is unavailable; use **the URL shown in your Render dashboard**, never assume a URL exists.

## 0. Prepare public real-data artifacts (on your Mac)

Run from the project root (with `outputs/real` already generated):

```bash
git pull origin main
python -m scripts.prepare_public_deploy --source outputs/real --destination deployment/artifacts
ls -lh deployment/artifacts
```

**Privacy and integrity:** This publishes **274 held-out point coordinates** (based on the first real training run), GEDI-modeled biomass labels, predictions and uncertainty intervals. It does NOT publish your original full GEDI HDF5, all 1,263 rows, or the trained joblib model. Inspect before committing. Do not commit `data/` or `outputs/`.

```bash
git add deployment/artifacts/metrics.json deployment/artifacts/heldout_predictions.csv
git commit -m "data: publish reviewed real-data demonstration results"
git push origin main
```

The API is read-only; it serves precomputed model outputs, **not live model inference**.

## 1. Deploy the API (first)

- Visit https://dashboard.render.com/ and connect your GitHub repository `himani046/CarbonFusion-AI`.
- Create **New → Web Service**, choose `main`.
- **Root Directory:** leave blank (repo root).
- **Runtime:** Python.
- **Build Command:** `pip install -r backend/requirements-deploy.txt`
- **Start Command:** `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- **Instance Type:** **Free**.
- **Environment:** `CARBONFUSION_OUTPUT_DIR=deployment/artifacts`, `CARBONFUSION_DATA_MODE=real`, `CARBONFUSION_CORS_ORIGINS=*` (public read-only API; suitable only when exposing the API publicly is intentional).
- Deploy and open `https://YOUR-BACKEND.onrender.com/api/health`. It should say `"ready":true,"mode":"real"`. If not, check that artifact CSV and JSON were pushed and the service root is correct.

## 2. Deploy the dashboard

- Render **New → Static Site**, same repository and branch `main`.
- **Root Directory:** `frontend`.
- **Build Command:** `npm install && npm run generate` (repo has no package-lock.json).
- **Publish Directory:** `.output/public`.
- **Environment variable:** `NUXT_PUBLIC_API_BASE=https://YOUR-BACKEND.onrender.com` (copy exact API URL with https, no trailing slash).
- Deploy. Visit the public static-site URL. Allow the free API to wake up on first visit.

## Alternative: Blueprint

You can also create **New → Blueprint** using the root `render.yaml`. It provisions both services but requires supplying `NUXT_PUBLIC_API_BASE` for the static site. Because the backend URL may not yet exist, deploying the API first and then the static frontend is often simpler.

## Troubleshooting

- **Frontend shows 'Awaiting model outputs':** Verify API `/api/health`; if `ready:false`, outputs were not committed to `deployment/artifacts`.
- **CORS error:** API service must have `CARBONFUSION_CORS_ORIGINS=*` for this public read-only prototype; redeploy or restart.
- **Frontend calls localhost:** Set `NUXT_PUBLIC_API_BASE` in Render **Static Site** environment settings; trigger **rebuild/redeploy** because the value is embedded in generated static assets.
- **Free backend appears unavailable:** It sleeps after 15 minutes idle and may take ~1 minute to wake. Avoid constant ping services to sidestep free-plan behavior.
- **Render deployment asks for payment:** Double-check service instance type is **Free**, don't provision paid disks or database.
- **Missing package-lock:** This repository doesn't currently contain one, so the build uses `npm install`, not `npm ci`. Consider committing `frontend/package-lock.json` after local install for reproducibility.

## Research honesty

Dashboard includes real GEDI-modeled label-derived metrics; the geographic test result has **negative R²**, so this is a proof of implementation, **not a reliable area-wide biomass map**. Prediction pins are held-out observations along a single granule's laser tracks. Scientific improvements require more passes/regions, better GEDI acquisition-date matching, buffered holdouts, and field reference data.

## Useful links

- Render free tier: https://render.com/docs/free
- Render Blueprint reference: https://render.com/docs/blueprint-spec
- Nuxt prerender: https://nuxt.com/docs/4.x/getting-started/prerendering
