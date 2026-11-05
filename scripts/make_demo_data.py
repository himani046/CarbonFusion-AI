"""Generate synthetic, geographically correlated samples for pipeline smoke testing only."""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd


def main(output, n=2400, seed=7):
    rng = np.random.default_rng(seed)
    latitude = rng.uniform(21.4, 22.2, n)
    longitude = rng.uniform(86.1, 86.9, n)
    canopy = np.clip(0.45 + 0.22*np.sin((longitude-86.1)*7) + 0.16*np.cos((latitude-21.4)*9) + rng.normal(0,.13,n), .04, .97)
    B2=np.clip(.14-.09*canopy+rng.normal(0,.008,n),0,1)
    B3=np.clip(.16-.08*canopy+rng.normal(0,.009,n),0,1)
    B4=np.clip(.22-.16*canopy+rng.normal(0,.01,n),0,1)
    B5=.20+.03*canopy+rng.normal(0,.01,n)
    B6=.24+.09*canopy+rng.normal(0,.01,n)
    B7=.29+.14*canopy+rng.normal(0,.01,n)
    B8=.28+.26*canopy+rng.normal(0,.015,n)
    B8A=.26+.24*canopy+rng.normal(0,.013,n)
    B11=.28-.11*canopy+rng.normal(0,.015,n)
    B12=.23-.09*canopy+rng.normal(0,.015,n)
    ndvi=(B8-B4)/(B8+B4+1e-6)
    ndmi=(B8-B11)/(B8+B11+1e-6)
    ndre=(B8A-B5)/(B8A+B5+1e-6)
    elevation=300+230*(latitude-21.4)+190*np.sin((longitude-86.1)*5)+rng.normal(0,18,n)
    slope=np.clip(8+4*np.sin(longitude*19)+rng.normal(0,3,n),0,40)
    agbd=np.clip(25+185*canopy+.055*elevation-1.4*slope+rng.normal(0,18,n),3,400)
    agbd_se=rng.uniform(7,24,n)
    df=pd.DataFrame(dict(longitude=longitude,latitude=latitude,B2=B2,B3=B3,B4=B4,B5=B5,B6=B6,B7=B7,B8=B8,B8A=B8A,B11=B11,B12=B12,ndvi=ndvi,ndmi=ndmi,ndre=ndre,elevation=elevation,slope=slope,agbd=agbd,agbd_se=agbd_se))
    output=Path(output)
    output.parent.mkdir(parents=True,exist_ok=True)
    df.to_csv(output,index=False)
    print('SYNTHETIC demo dataset:',output,'rows:',len(df))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--output',default='data/demo_synthetic.csv')
    p.add_argument('--rows',type=int,default=2400)
    a=p.parse_args()
    main(a.output,a.rows)
