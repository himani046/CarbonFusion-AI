# Automatic Satellite Observation — click a map point

This feature adds a working `/api/observations/automatic` endpoint and the **Analyze location automatically** button on the `/observe` page.

## How it works
1. User clicks a point on OpenStreetMap/MapLibre, or enters longitude and latitude.
2. User chooses an observation date (2018 onward).
3. FastAPI searches **Element84 Earth Search STAC V1** for Sentinel-2 Level-2A scenes within ±45 days, cloud cover <=80%.
4. Backend samples the **SCL scene classification layer at the exact point** and discards cloud/shadow/no-data classifications.
5. It samples the 10 required public Sentinel-2 Level-2A Cloud Optimized GeoTIFF assets from the selected scene.
6. It samples public AWS **Terrarium global elevation tiles** for elevation and a locally derived slope approximation.
7. It derives NDVI, NDMI and NDRE and predicts biomass density + conformal interval using the deployed trained **XGBoost model**.
8. UI displays the source scene acquisition date, cloud information, indices, biomass and uncertainty.

**This does not use Google Earth Engine or require user credentials.** Public STAC/COG/terrain services can throttle requests, error, or change access without notice. A request returns an informative 503 rather than inventing imagery when unavailable.

## API request
```http
POST /api/observations/automatic
Content-Type: application/json

{"longitude":86.16,"latitude":22.42,"observation_date":"2022-01-01"}
```

Call `GET /api/inference-status` first to ensure real trained model JSON files are deployed.

## Deployment requirements
Backend `backend/requirements-deploy.txt` now includes Rasterio, Pillow and Requests for network-based GeoTIFF and terrain-tile sampling. Render Free web service needs a rebuild after these dependency changes.

The model must first be packaged locally:
```bash
git pull origin main
python -m scripts.prepare_public_deploy --source outputs/real --destination deployment/artifacts
git add deployment/artifacts/metrics.json deployment/artifacts/heldout_predictions.csv deployment/artifacts/biomass_model.json deployment/artifacts/model_metadata.json
git commit -m "Publish reviewed inference model"
git push origin main
```
Redeploy both Render services. Check Render API logs if satellite I/O is unavailable or long-running.

## Limits / accuracy warnings
- The current XGBoost + terrain model has **negative spatial held-out R²**, trained from one GEDI granule. Predictions are experimental and do not establish credible regional carbon estimates.
- Training used an Earth Engine Sentinel-2 median composite and **SRTM elevation/slope**; this endpoint uses a **single Sentinel-2 image** and **Mapzen terrain tiles**. These processing differences introduce model input distribution shift.
- Observations and carbon are **point estimates**, not polygon areas or stocks; no forest/nonforest classification occurs.
- No automatic observation database; results are returned to requesting browser.
- Cloud-screening uses single-pixel SCL only; cloud adjacency, mosaicking, shadows and quality can still affect results.
- Live COG access can fail on Render's free network or resource limits. Expect and report 503 instead of false results.
- No cloud/feature values are invented. A failed search is not a zero-biomass observation.
- Add explicit rate limiting / throttling before significant public traffic; repeated requests may burden free service.

Sources: https://earth-search.aws.element84.com/v1 , https://registry.opendata.aws/sentinel-2-l2a-cogs/ , https://registry.opendata.aws/terrain-tiles/
