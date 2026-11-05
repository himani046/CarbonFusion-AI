"""Read-only API for CarbonFusion's trained model artifacts.

No model scores are fabricated. Run the training pipeline first.
"""
import json
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, ConfigDict
from functools import lru_cache
import math
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = Path(os.getenv("CARBONFUSION_OUTPUT_DIR", str(ROOT / "outputs"))).resolve()
app = FastAPI(title="CarbonFusion AI API", version="0.1.0")
origins = [x.strip() for x in os.getenv("CARBONFUSION_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET"], allow_headers=["*"])


def artifacts():
    metrics = RESULTS_DIR / "metrics.json"
    predictions = RESULTS_DIR / "heldout_predictions.csv"
    if not metrics.is_file() or not predictions.is_file():
        raise HTTPException(status_code=503, detail="Training outputs missing. Run python scripts/make_demo_data.py && python -m scripts.train")
    try:
        meta = json.loads(metrics.read_text(encoding="utf-8"))
        df = pd.read_csv(predictions)
    except (OSError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=500, detail="Invalid model artifacts") from exc
    return meta, df


@app.get("/api/health")
def health():
    ready = (RESULTS_DIR / "metrics.json").is_file() and (RESULTS_DIR / "heldout_predictions.csv").is_file()
    return {"service": "carbonfusion-api", "ready": ready, "mode": os.getenv("CARBONFUSION_DATA_MODE", "synthetic_demo")}


@app.get("/api/overview")
def overview():
    meta, df = artifacts()
    if df.empty:
        raise HTTPException(status_code=503, detail="No held-out predictions")
    required = {"latitude", "longitude", "agbd", "pred_agbd", "pi_low", "pi_high"}
    if not required.issubset(df.columns):
        raise HTTPException(status_code=500, detail="Missing expected prediction fields")
    uncertainty = meta.get("uncertainty", {})
    return {
        "data_mode": os.getenv("CARBONFUSION_DATA_MODE", "synthetic_demo"),
        "sample_count": int(len(df)),
        "mean_predicted_agbd_mg_ha": round(float(df["pred_agbd"].mean()), 2),
        "mean_reference_agbd_mg_ha": round(float(df["agbd"].mean()), 2),
        "mean_interval_width_mg_ha": round(float((df["pi_high"] - df["pi_low"]).mean()), 2),
        "interval_coverage": uncertainty.get("empirical_test_coverage"),
        "nominal_coverage": uncertainty.get("nominal_coverage"),
        "models": meta.get("comparison", []),
        "caveats": meta.get("notes", []),
    }


@app.get("/api/predictions")
def predictions(limit: int = Query(350, ge=1, le=1500)):
    _, df = artifacts()
    needed = ["latitude", "longitude", "pred_agbd", "agbd", "pi_low", "pi_high"]
    if not set(needed).issubset(df.columns):
        raise HTTPException(status_code=500, detail="Missing expected prediction fields")
    # Fixed uniform downsampling for map performance. Coordinates are GEDI training/test observations,
    # not a continuous biomass map.
    if len(df) > limit:
        indexes = [int(i) for i in __import__("numpy").linspace(0, len(df) - 1, limit)]
        df = df.iloc[indexes]
    features = []
    for item in df[needed].to_dict(orient="records"):
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [float(item["longitude"]), float(item["latitude"])]},
            "properties": {key: round(float(item[key]), 2) for key in ("pred_agbd", "agbd", "pi_low", "pi_high")},
        })
    return {"type": "FeatureCollection", "features": features}


@app.get("/api/model-metrics")
def model_metrics():
    meta, _ = artifacts()
    return {"models": meta.get("comparison", []), "uncertainty": meta.get("uncertainty", {}), "split": meta.get("data", {})}


# New-location inference is only available after exporting a trained XGBoost
# booster from the actual local model. Never invent model outputs.
MODEL_FEATURES = ['B2','B3','B4','B5','B6','B7','B8','B8A','B11','B12',
                  'ndvi','ndmi','ndre','elevation','slope']
MODEL_DIR = Path(os.getenv("CARBONFUSION_MODEL_DIR", str(RESULTS_DIR))).resolve()

class ObservationFeatures(BaseModel):
    model_config = ConfigDict(extra='forbid')
    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)
    B2: float = Field(ge=0, le=1)
    B3: float = Field(ge=0, le=1)
    B4: float = Field(ge=0, le=1)
    B5: float = Field(ge=0, le=1)
    B6: float = Field(ge=0, le=1)
    B7: float = Field(ge=0, le=1)
    B8: float = Field(ge=0, le=1)
    B8A: float = Field(ge=0, le=1)
    B11: float = Field(ge=0, le=1)
    B12: float = Field(ge=0, le=1)
    elevation: float = Field(ge=-500, le=9000)
    slope: float = Field(ge=0, le=90)

@lru_cache(maxsize=1)
def load_inference_bundle():
    meta_path = MODEL_DIR / "model_metadata.json"
    model_path = MODEL_DIR / "biomass_model.json"
    if not meta_path.is_file() or not model_path.is_file():
        raise HTTPException(status_code=503, detail="Inference model not deployed. Export it with scripts/prepare_public_deploy.py and redeploy.")
    try:
        import xgboost as xgb
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        feature_names = meta["features"]
        if feature_names != MODEL_FEATURES:
            raise ValueError("Unexpected inference feature schema")
        half_width = float(meta["conformal_half_width"])
        carbon_fraction = float(meta["carbon_fraction"])
        if not math.isfinite(half_width) or half_width < 0 or not (0 < carbon_fraction <= 1):
            raise ValueError("Invalid model uncertainty metadata")
        booster = xgb.Booster()
        booster.load_model(str(model_path))
        if booster.feature_names is not None and booster.feature_names != feature_names:
            raise ValueError("Model feature names do not match metadata")
        return booster, meta
    except (ImportError, OSError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=503, detail="Inference model files are invalid or unavailable") from exc

@app.get("/api/inference-status")
def inference_status():
    return {
        "available": (MODEL_DIR/"biomass_model.json").is_file() and
                     (MODEL_DIR/"model_metadata.json").is_file(),
        "mode": "manual_features",
        "satellite_auto_fetch": False,
        "feature_names": MODEL_FEATURES,
    }

@app.post("/api/observations/predict")
def predict_observation(payload: ObservationFeatures):
    import xgboost as xgb
    booster, meta = load_inference_bundle()
    raw = payload.model_dump()
    def norm(a, b):
        return (a-b)/(a+b) if abs(a+b)>1e-9 else 0.0
    raw["ndvi"] = norm(raw["B8"], raw["B4"])
    raw["ndmi"] = norm(raw["B8"], raw["B11"])
    raw["ndre"] = norm(raw["B8A"], raw["B5"])
    frame = pd.DataFrame([{name: raw[name] for name in MODEL_FEATURES}], columns=MODEL_FEATURES)
    value = max(0.0, float(booster.predict(xgb.DMatrix(frame, feature_names=MODEL_FEATURES))[0]))
    half_width = float(meta["conformal_half_width"])
    carbon_fraction = float(meta["carbon_fraction"])
    return {
        "longitude":raw["longitude"], "latitude":raw["latitude"],
        "pred_agbd_mg_ha":round(value,3),
        "interval_low_mg_ha":round(max(0,value-half_width),3),
        "interval_high_mg_ha":round(value+half_width,3),
        "carbon_density_t_ha":round(value*carbon_fraction,3),
        "ndvi":round(raw["ndvi"],4), "ndmi":round(raw["ndmi"],4),
        "ndre":round(raw["ndre"],4),
        "source":"user_supplied_optical_features",
        "prediction_model":"xgboost_optical_terrain",
        "warning":"Preliminary satellite-derived model trained on one GEDI granule; held-out R² is negative. Input features are manually supplied, not automatically retrieved. Intervals are calibrated against GEDI-modeled targets, not independent field truth. No area-wide carbon stock estimate."
    }
