# New Observation — manual satellite-feature inference

The website now includes **/observe**, with a link from the dashboard. It accepts latitude, longitude, Sentinel-2 optical surface reflectance bands B2–B12, elevation and slope; computes NDVI, NDMI and NDRE; calls the deployed XGBoost + terrain booster; and displays predicted GEDI-like aboveground biomass and a split-conformal uncertainty interval.

**This feature does NOT fetch a new satellite image, click-to-sample a map, store observations, analyze arbitrary polygons or estimate total carbon stock.** Users must supply authentic, correctly scaled and cloud-screened spectral values and terrain measurements.

## Deploy the model files (required)

The initial free deployment packaged only JSON metrics and CSV held-out predictions, not a trained inference model. Run on your Mac, from repository root:

```bash
git pull origin main
python -m scripts.prepare_public_deploy --source outputs/real --destination deployment/artifacts
ls -lh deployment/artifacts/
```

You should see:

```text
metrics.json
heldout_predictions.csv
biomass_model.json
model_metadata.json
```

The script loads your trusted local `outputs/real/biomass_model.joblib`, exports a portable **XGBoost JSON booster**, and stores a short feature-schema/uncertainty metadata JSON. The server does **not** load a pickle. Review the files; commit only these four deployment artifacts:

```bash
git add deployment/artifacts/metrics.json deployment/artifacts/heldout_predictions.csv deployment/artifacts/biomass_model.json deployment/artifacts/model_metadata.json
git commit -m "Deploy CarbonFusion real-data inference model"
git push origin main
```

Then Render automatically redeploys if auto-deploy is enabled; otherwise use **Manual Deploy → Deploy latest commit** for both API and static site.

## API

`GET /api/inference-status`: model-file availability and required features.

`POST /api/observations/predict`: body JSON (all fields required):

```json
{
  "longitude":86.16,"latitude":22.42,
  "B2":0.04,"B3":0.06,"B4":0.05,"B5":0.09,"B6":0.17,
  "B7":0.20,"B8":0.23,"B8A":0.24,"B11":0.15,"B12":0.09,
  "elevation":400,"slope":3.2
}
```

The above is a **format example only**, not a measured new observation. The API calculates spectral indices and loads `deployment/artifacts/biomass_model.json`. If not deployed, it returns 503; it never fabricates predictions.

## Research limitations

This model was trained on one GEDI granule and achieved **negative spatially held-out R²**. The user interface labels predictions as preliminary and unsuitable for authoritative carbon assessments. Intervals were calibrated against **GEDI modeled labels**, not independent field plot biomass.

Use independent GEDI passes, properly dated Sentinel-2 features and improved geographic holdouts before claiming scientific generalization. There is no persistence or user authentication. Production public POST endpoints may need abuse protection or rate limiting.
