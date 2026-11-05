"""Extract quality-filtered NASA GEDI L4A V3 footprint data from HDF5.

This script does not download HDF5 files and does not require Earth Engine.
Run: python -m scripts.extract_gedi_l4a_v3 --inputs data/gedi_raw/*.h5
"""
import argparse
import json
from pathlib import Path
import h5py
import numpy as np
import pandas as pd

BBOX = (85.8, 21.2, 87.3, 22.7)
FIELDS = {
    "longitude": ("lon_lowestmode", "longitude", "lon"),
    "latitude": ("lat_lowestmode", "latitude", "lat"),
    "agbd": ("agbd",),
    "agbd_se": ("agbd_se",),
    "l4_quality_flag": ("l4a_quality_flag_rel3", "l4_quality_flag"),
    "degrade_flag": ("degrade_flag",),
    "degrade_include_flag": ("degrade_include_flag",),
    "elev_highestreturn_outlier_flag": ("elev_highestreturn_outlier_flag",),
    "shot_number": ("shot_number",),
    "delta_time": ("delta_time",),
}
SENTINEL_REQUIRED = ("longitude","latitude","agbd","agbd_se",
                     "l4_quality_flag")

def find_array(group, candidates, n=None):
    """Find a matching 1D dataset inside a beam (including nested groups).

    Prefer exact top-level names, then nested matching basename; reject arrays
    of inconsistent lengths instead of silently aligning unrelated datasets.
    """
    for name in candidates:
        if name in group and isinstance(group[name], h5py.Dataset):
            d=group[name]
            if d.ndim==1 and (n is None or d.shape[0]==n):
                return d, d.name
    matches=[]
    def visit(path, obj):
        if isinstance(obj,h5py.Dataset) and path.rsplit("/",1)[-1] in candidates:
            if obj.ndim==1 and (n is None or obj.shape[0]==n):
                matches.append((obj,path))
    group.visititems(visit)
    for name in candidates:
        for d,path in matches:
            if path.rsplit("/",1)[-1]==name:
                return d,d.name
    return None,None

def extract_one(path, bbox, max_relative_se):
    west,south,east,north=bbox
    rows=[]
    report={"file":path.name,"beams":{},"warnings":[]}
    with h5py.File(path,"r") as h5:
        beams=[k for k in h5.keys() if k.upper().startswith("BEAM")
               and isinstance(h5[k],h5py.Group)]
        report["beam_count"]=len(beams)
        if not beams:
            report["warnings"].append("No BEAM groups found; verify file is NASA GEDI L4A.")
        for beam_name in beams:
            beam=h5[beam_name]
            lat_ds,lat_path=find_array(beam,FIELDS["latitude"])
            if lat_ds is None:
                report["beams"][beam_name]={"status":"skipped_missing_latitude"}
                continue
            n=lat_ds.shape[0]
            datasets={"latitude":(lat_ds,lat_path)}
            missing=[]
            for col,candidates in FIELDS.items():
                if col=="latitude":continue
                d,source=find_array(beam,candidates,n)
                if d is None and col in SENTINEL_REQUIRED:missing.append(col)
                datasets[col]=(d,source)
            # Count AOI coordinates before enforcing the product schema.
            # Otherwise a missing/renamed V3 quality field falsely reports 0 in AOI.
            lon_ds=datasets["longitude"][0]
            if lon_ds is None:
                report["beams"][beam_name]={"status":"skipped_missing_longitude",
                    "length":n,"paths":{k:v[1] for k,v in datasets.items()}}
                continue
            lat=np.asarray(lat_ds[...],dtype=np.float64)
            lon=np.asarray(lon_ds[...],dtype=np.float64)
            inside=(np.isfinite(lat)&np.isfinite(lon)&
                    (lat>=south)&(lat<=north)&(lon>=west)&(lon<=east))
            count_inside=int(inside.sum())
            if missing:
                report["beams"][beam_name]={"status":"skipped_missing_required",
                    "length":n,"in_bbox":count_inside,"missing":missing,
                    "paths":{k:v[1] for k,v in datasets.items()},
                    "available_top_level":list(beam.keys())}
                continue
            if count_inside==0:
                report["beams"][beam_name]={"status":"no_footprints_in_aoi",
                                           "length":n,"in_bbox":0}
                continue
            indices=np.flatnonzero(inside)
            fields={}
            for col,(ds,_) in datasets.items():
                if ds is not None:
                    # HDF5 supports sorted fancy indices; avoid loading global arrays.
                    fields[col]=np.asarray(ds[indices])
            agbd=np.asarray(fields["agbd"],dtype=np.float64)
            se=np.asarray(fields["agbd_se"],dtype=np.float64)
            quality=np.asarray(fields["l4_quality_flag"])
            good=(np.isfinite(agbd)&np.isfinite(se)&(agbd>0)&(agbd<600)&
                  (se>=0)&(se/np.maximum(agbd,1e-9)<=max_relative_se)&
                  (quality==1))
            if "degrade_include_flag" in fields:
                good &= np.asarray(fields["degrade_include_flag"])==1
            elif "degrade_flag" in fields:
                good &= np.asarray(fields["degrade_flag"])==0
            else:
                good &= False
            if "elev_highestreturn_outlier_flag" in fields:
                good &= np.asarray(fields["elev_highestreturn_outlier_flag"])==0
            frame=pd.DataFrame({key:array[good] for key,array in fields.items()})
            if not frame.empty:
                frame["beam"]=beam_name
                frame["source_granule"]=path.name
                frame["reference_product"]="GEDI_L4A_V3_FOOTPRINT"
                frame["observation_date"]=path.name.split("_")[2][:7] # YYYYDDD (granule start)
                rows.append(frame)
            report["beams"][beam_name]={"status":"processed","length":n,
                "quality_field":datasets["l4_quality_flag"][1],
                "degradation_screen":"degrade_include_flag" if "degrade_include_flag" in fields else "legacy_degrade_flag",
                "in_bbox":count_inside,"quality_passed":int(good.sum()),
                "paths":{k:v[1] for k,v in datasets.items()}}
    out=pd.concat(rows,ignore_index=True) if rows else pd.DataFrame(
        columns=list(FIELDS)+["beam","source_granule","reference_product","observation_date"])
    report["in_bbox"]=sum(x.get("in_bbox",0) for x in report["beams"].values())
    report["quality_passed"]=len(out)
    return out,report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inputs",type=Path,nargs="+",required=True)
    p.add_argument("--output",type=Path,default=Path("data/gedi_v3_footprints.csv"))
    p.add_argument("--report",type=Path,default=Path("outputs/gedi_v3_extraction_report.json"))
    p.add_argument("--bbox",type=float,nargs=4,default=list(BBOX),
                   metavar=("WEST","SOUTH","EAST","NORTH"))
    p.add_argument("--max-relative-se",type=float,default=0.5)
    args=p.parse_args()
    bbox=args.bbox
    if not (bbox[0]<bbox[2] and bbox[1]<bbox[3]):
        p.error("Expected bbox WEST SOUTH EAST NORTH.")
    files=[]
    for item in args.inputs:
        if item.is_dir():files.extend(sorted(item.glob("*.h5")))
        elif item.exists():files.append(item)
    files=list(dict.fromkeys(files))
    if not files:p.error("No HDF5 files found; pass paths or a directory.")
    pieces=[]; reports=[]
    for f in files:
        try:
            table,r=extract_one(f,bbox,args.max_relative_se)
            pieces.append(table);reports.append(r)
            print(f"{f.name}: {r['in_bbox']} in AOI, {r['quality_passed']} passed QC")
            for bn,bs in r['beams'].items():
                if bs.get('status')!='processed':
                    print(f"  {bn}: {bs.get('status')}; in AOI={bs.get('in_bbox','unknown')}; missing={bs.get('missing',[])}")
        except (OSError,ValueError,KeyError) as err:
            reports.append({"file":f.name,"error":str(err)})
            print(f"Could not read {f}: {err}")
    merged=pd.concat(pieces,ignore_index=True) if pieces else pd.DataFrame()
    dupes=0
    if not merged.empty and {"shot_number","beam"}.issubset(merged.columns):
        dupes=int(merged.duplicated(["shot_number","beam"]).sum())
        merged=merged.drop_duplicates(["shot_number","beam"])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    merged.to_csv(args.output,index=False)
    summary={"input_files":len(files),"total_in_bbox":sum(r.get("in_bbox",0) for r in reports),
             "skipped_beams":sum(1 for r in reports for v in r.get("beams",{}).values() if v.get("status","").startswith("skipped")),
             "output_rows":len(merged),
             "duplicates_removed":dupes,"bbox":bbox,
             "is_optical_model_ready":False,
             "next_step":"Join footprints with Sentinel-2 optical features before existing ML training.",
             "granules":reports}
    args.report.write_text(json.dumps(summary,indent=2,default=str),encoding="utf-8")
    print(json.dumps({k:v for k,v in summary.items() if k!="granules"},indent=2))
    print("CSV:",args.output,"report:",args.report)
    if not pieces or all("error" in r for r in reports):
        raise SystemExit("No readable granules; see report.")
if __name__=="__main__":main()
