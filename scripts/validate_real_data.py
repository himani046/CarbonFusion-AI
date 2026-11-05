"""Validate a candidate Earth Engine CSV before training.

Runs locally, requires no Earth Engine credentials. This does not establish
field-based truth or remove every potential spatial / temporal sampling bias.
"""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from src.pipeline import OPTICAL, TERRAIN, prepare

def validate(path: Path, output: Path):
    raw = pd.read_csv(path)
    prepared = prepare(raw)
    report = {
        'input': str(path),
        'source': 'user_supplied_real_data_candidate',
        'raw_rows': len(raw),
        'rows_after_basic_qc': len(prepared),
        'rows_removed_by_basic_qc': len(raw)-len(prepared),
        'unique_spatial_blocks': int(prepared.spatial_block.nunique()),
        'reference_month_present': 'reference_month' in raw.columns,
        'reference_product_present': 'reference_product' in raw.columns,
        'label_agbd_mg_ha': {
            'min': round(float(prepared.agbd.min()),2),
            'median': round(float(prepared.agbd.median()),2),
            'max': round(float(prepared.agbd.max()),2),
        },
        'warnings': [
            'GEDI L4A AGBD labels are modeled predictions, not ground truth.',
            'Current month-matched export is not GEDI footprint or acquisition-exact.',
            'Use region-specific forest masks, buffered spatial validation and field verification before scientific claims.'
        ],
        'ready_for_demo_training': bool(len(prepared)>=100 and prepared.spatial_block.nunique()>=8),
    }
    if 'reference_month' in raw.columns:
        report['months'] = sorted(raw['reference_month'].dropna().astype(str).unique().tolist())
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
    if not report['ready_for_demo_training']:
        raise SystemExit('Insufficient valid rows or geographic blocks for prototype training.')

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--report',type=Path,default=Path('outputs/real_validation.json'))
    args=parser.parse_args()
    validate(args.input,args.report)
