"""Package only READ-ONLY real model outputs for a public demo deployment.

CAUTION: Published coordinates and modeled GEDI references are publicly visible.
Run from repository root after real-data training.
"""
from pathlib import Path
import argparse
import json
import shutil
import joblib
import math
import pandas as pd

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",type=Path,default=Path("outputs/real"))
    parser.add_argument("--destination",type=Path,default=Path("deployment/artifacts"))
    args=parser.parse_args()
    metrics_path=args.source/"metrics.json"
    data_path=args.source/"heldout_predictions.csv"
    if not metrics_path.is_file() or not data_path.is_file():
        parser.error("Real results missing: run python -m scripts.train --input data/real_samples.csv --output outputs/real")
    metrics=json.loads(metrics_path.read_text())
    df=pd.read_csv(data_path)
    needed={"longitude","latitude","agbd","agbd_se","pred_agbd","pi_low","pi_high"}
    if not needed.issubset(df.columns) or df.empty:
        parser.error("Invalid real held-out predictions CSV")
    if not df[list(needed)].notna().all().all():
        parser.error("Null predictions/coordinates cannot be published")
    if not df.longitude.between(-180,180).all() or not df.latitude.between(-90,90).all():
        parser.error("Invalid geographic coordinates")
    args.destination.mkdir(parents=True,exist_ok=True)
    # Public API only uses these seven columns; omit shot identifiers/other data.
    df[["longitude","latitude","agbd","agbd_se","pred_agbd","pi_low","pi_high"]].to_csv(
        args.destination/"heldout_predictions.csv",index=False)
    # Preserve actual metrics but remove outdated synthetic-data note if present.
    metrics["notes"]=[n for n in metrics.get("notes",[]) if "All demo sample rows are synthetic" not in n]
    metrics.setdefault("notes",[]).append(
        "Public demonstration: real GEDI V3 satellite-derived reference labels from one granule; preliminary geographic validation, not field truth.")
    (args.destination/"metrics.json").write_text(json.dumps(metrics,indent=2))
    # Package a portable XGBoost booster, without shipping a pickle/joblib
    # artifact that a public web service would deserialize.
    source_model=args.source/"biomass_model.joblib"
    if source_model.is_file():
        bundle=joblib.load(source_model) # trusted LOCAL training output only
        expected=['B2','B3','B4','B5','B6','B7','B8','B8A','B11','B12',
                  'ndvi','ndmi','ndre','elevation','slope']
        if bundle.get('features') != expected or not hasattr(bundle.get('model'), 'get_booster'):
            parser.error("Expected terrain XGBoost training artifact and feature order")
        half_width=float(bundle['conformal_half_width'])
        fraction=float(bundle['carbon_fraction'])
        if not math.isfinite(half_width) or half_width<0 or not (0<fraction<=1):
            parser.error("Invalid conformal interval / carbon metadata")
        bundle['model'].get_booster().save_model(str(args.destination/"biomass_model.json"))
        (args.destination/"model_metadata.json").write_text(json.dumps({
            'features':expected,'conformal_half_width':half_width,
            'carbon_fraction':fraction,'model':'xgboost_optical_terrain',
            'input_provenance':'manual_optical_features',
            'limitations':'Single GEDI granule prototype; negative R2 on geographic holdout'
        }, indent=2))
        print("Prepared portable XGBoost inference model (JSON) and metadata")
    else:
        print("No model joblib found: dashboard artifacts created, but new observation inference unavailable")
    print("Prepared",len(df),"held-out observations in",args.destination)
    print("These files contain public coordinates, reference biomass estimates and model results.")
    print("Review files before: git add deployment/artifacts && git commit && git push.")

if __name__=="__main__":
    main()
