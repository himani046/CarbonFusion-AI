"""Minimal local Streamlit research dashboard for completed model outputs."""
from pathlib import Path
import json
import pandas as pd
import streamlit as st

st.set_page_config(page_title='CarbonFusion AI',layout='wide')
st.title('CarbonFusion AI')
st.caption('Research MVP • Aboveground biomass estimation • Spatial holdout • Uncertainty')
st.warning('Demo results are synthetic unless you run training on verified Earth Engine exports. GEDI AGBD is modeled reference data, not field ground truth.')
out=Path('outputs')
if not (out/'metrics.json').exists():
    st.info('Run: python scripts/make_demo_data.py && python -m scripts.train')
    st.stop()
metrics=json.loads((out/'metrics.json').read_text())
df=pd.read_csv(out/'heldout_predictions.csv')
a,b,c=st.columns(3)
a.metric('Held-out points',len(df))
b.metric('Mean predicted AGBD',f'{df.pred_agbd.mean():.1f} Mg/ha')
c.metric('90% interval coverage',f"{metrics['uncertainty']['empirical_test_coverage']:.1%}")
st.subheader('Model comparison')
st.dataframe(pd.DataFrame(metrics['comparison']),use_container_width=True,hide_index=True)
st.subheader('Held-out predicted biomass map')
map_df=df[['latitude','longitude','pred_agbd']].rename(columns={'pred_agbd':'Biomass (Mg/ha)'})
st.map(map_df,latitude='latitude',longitude='longitude',size=18,color='#15803d')
st.subheader('Prediction sample')
st.dataframe(df.head(100),use_container_width=True,hide_index=True)
st.subheader('Scientific caveats')
for note in metrics['notes']:
    st.write('• '+note)
