"""Restore GEDI footprint coordinates on a Sentinel-2 Earth Engine CSV export.

Usage:
 python -m scripts.restore_export_coordinates \
   --sentinel-csv 'data/real_samples_export.csv' \
   --gedi-csv data/gedi_v3_footprints.csv \
   --output data/real_samples.csv

Does NOT regenerate satellite values or run Earth Engine.
"""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd

KEYS = ["shot_number", "beam"]
COORDS = ["longitude", "latitude"]

def restore(sentinel_csv: Path, gedi_csv: Path, output: Path, report: Path):
    # Read shot IDs as strings to avoid accidental precision loss.
    optical = pd.read_csv(sentinel_csv, dtype={"shot_number": "string", "beam": "string"})
    reference = pd.read_csv(gedi_csv, dtype={"shot_number": "string", "beam": "string"})
    for name, df, needed in [
        ("Sentinel export", optical, KEYS + ["agbd", "agbd_se"]),
        ("GEDI reference", reference, KEYS + COORDS + ["agbd", "agbd_se"]),
    ]:
        missing = sorted(set(needed) - set(df.columns))
        if missing:
            raise ValueError(f"{name} missing columns: {missing}")
        if df[KEYS].isna().any().any():
            raise ValueError(f"{name} contains null shot/beam identifiers")
        if df.duplicated(KEYS).any():
            raise ValueError(f"{name} contains duplicate (shot_number, beam) identifiers")
    merged = optical.drop(columns=COORDS, errors="ignore").merge(
        reference[KEYS + COORDS + ["agbd", "agbd_se"]],
        how="left", on=KEYS, validate="one_to_one",
        indicator=True, suffixes=("", "_gedi")
    )
    unmatched = int((merged["_merge"] != "both").sum())
    if unmatched:
        raise ValueError(f"{unmatched} optical rows do not match a GEDI shot; refusing partial repair")
    merged = merged.drop(columns="_merge")
    # Check biomass targets were not accidentally joined to different shots.
    for field in ["agbd", "agbd_se"]:
        a = pd.to_numeric(merged[field], errors="coerce").to_numpy(dtype=float)
        b = pd.to_numeric(merged[field+"_gedi"], errors="coerce").to_numpy(dtype=float)
        if not np.isfinite(a).all() or not np.isfinite(b).all() or not np.allclose(a,b,rtol=1e-5,atol=1e-4):
            raise ValueError(f"{field} does not match the original GEDI reference; refusing repair")
        merged = merged.drop(columns=field+"_gedi")
    for field in COORDS:
        merged[field] = pd.to_numeric(merged[field],errors="coerce")
    valid = merged.longitude.between(85.8,87.3) & merged.latitude.between(21.2,22.7)
    if not bool(valid.all()):
        raise ValueError(f"{int((~valid).sum())} restored points outside study AOI or invalid")
    # Explicitly validate every optical/model feature, not just coordinate restoration.
    from src.pipeline import REQUIRED, prepare
    prepared = prepare(merged)
    if len(prepared)!=len(merged):
        raise ValueError(f"{len(merged)-len(prepared)} rows dropped by model QC; inspect export")
    output.parent.mkdir(parents=True,exist_ok=True)
    report.parent.mkdir(parents=True,exist_ok=True)
    merged.to_csv(output,index=False)
    summary={"sentinel_export":str(sentinel_csv),"gedi_reference":str(gedi_csv),
             "rows":int(len(merged)),"coordinate_matches":int(len(merged)),
             "unique_spatial_blocks":int(prepared.spatial_block.nunique()),
             "reference_product":"GEDI_L4A_V3_FOOTPRINT",
             "warnings":["Single GEDI granule/track may have strong spatial autocorrelation.",
                         "Satellite reflectance is a time-window composite, not exact acquisition-time matching.",
                         "GEDI AGBD labels are modeled estimates, not independent field ground truth."]}
    report.write_text(json.dumps(summary,indent=2),encoding="utf-8")
    print(json.dumps(summary,indent=2))
    print("Saved",output)
    return summary

if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sentinel-csv",type=Path,required=True)
    parser.add_argument("--gedi-csv",type=Path,required=True)
    parser.add_argument("--output",type=Path,default=Path("data/real_samples.csv"))
    parser.add_argument("--report",type=Path,default=Path("outputs/coordinate_repair_report.json"))
    a=parser.parse_args()
    restore(a.sentinel_csv,a.gedi_csv,a.output,a.report)
