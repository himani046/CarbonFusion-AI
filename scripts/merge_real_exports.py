"""Merge Earth Engine CSV exports with basic schema and duplication checks."""
import argparse
import json
from pathlib import Path
import pandas as pd
from src.pipeline import REQUIRED

def merge(inputs, output):
    frames=[]
    for p in inputs:
        frame=pd.read_csv(p)
        missing=sorted(set(REQUIRED)-set(frame.columns))
        if missing:
            raise ValueError(f'{p}: missing columns {missing}')
        frame['source_export']=p.name
        frames.append(frame)
    combined=pd.concat(frames,ignore_index=True,sort=False)
    before=len(combined)
    # A repeated coordinate in distinct months is NOT automatically a duplicate.
    identity=['longitude','latitude','reference_month'] if 'reference_month' in combined.columns else ['longitude','latitude']
    if combined.duplicated(subset=identity).any():
        # Multiple observations for same raster-cell/month are ambiguous in this prototype.
        combined=combined.drop_duplicates(subset=identity,keep='first')
    removed=before-len(combined)
    output.parent.mkdir(parents=True,exist_ok=True)
    combined.to_csv(output,index=False)
    report={'files':[str(p) for p in inputs],'raw_rows':before,'merged_rows':len(combined),
            'duplicate_cell_month_rows_removed':removed,
            'months':combined['reference_month'].value_counts().sort_index().to_dict() if 'reference_month' in combined else {},
            'limitations':'Cell-month deduplication is not footprint identity. Review geographic and temporal dependence before training.'}
    print(json.dumps(report,indent=2))
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--inputs',type=Path,nargs='+',required=True)
    p.add_argument('--output',type=Path,default=Path('data/real_samples.csv'))
    args=p.parse_args()
    merge(args.inputs,args.output)
