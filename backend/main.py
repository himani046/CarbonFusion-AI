"""Read-only API for CarbonFusion's trained model artifacts.

No model scores are fabricated. Run the training pipeline first.
"""
import json
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
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
