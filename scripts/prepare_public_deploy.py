"""Package only READ-ONLY real model outputs for a public demo deployment.

CAUTION: Published coordinates and modeled GEDI references are publicly visible.
Run from repository root after real-data training.
"""
from pathlib import Path
import argparse
import json
import shutil
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
    print("Prepared",len(df),"held-out observations in",args.destination)
    print("These files contain public coordinates, reference biomass estimates and model results.")
    print("Review files before: git add deployment/artifacts && git commit && git push.")

if __name__=="__main__":
    main()
