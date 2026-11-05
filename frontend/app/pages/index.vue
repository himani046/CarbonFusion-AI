<script setup lang="ts">
import { Activity, BarChart3, CircleHelp, Database, GitCompareArrows, Leaf, MapPinned, ShieldCheck, Satellite, FlaskConical, ArrowUpRight, RefreshCw, Layers3, BookOpen, Trees, TriangleAlert } from 'lucide-vue-next'
type Model = {model:string,rmse_mg_ha:number,mae_mg_ha:number,r2:number}
type Overview = {data_mode:string,sample_count:number,mean_predicted_agbd_mg_ha:number,mean_reference_agbd_mg_ha:number,mean_interval_width_mg_ha:number,interval_coverage:number|null,nominal_coverage:number|null,models:Model[],caveats:string[]}
const config=useRuntimeConfig()
const api=String(config.public.apiBase).replace(/\/$/,'')
const {data:health,refresh:refreshHealth}=await useFetch<{service:string,ready:boolean,mode:string}>(api+'/api/health',{server:false})
const {data:summary,error:summaryError,pending,refresh:refreshSummary}=await useFetch<Overview>(api+'/api/overview',{server:false})
const {data:points,refresh:refreshPoints}=await useFetch<{type:'FeatureCollection',features:any[]}>(api+'/api/predictions?limit=350',{server:false})
const records=computed(()=>summary.value?.models??[])
const isDemo=computed(()=>!summary.value || summary.value.data_mode!=='real')
const pct=(num:number|null|undefined)=>num==null?'—':(num*100).toFixed(1)+'%'
const num=(x:number|null|undefined,dec=1)=>x==null?'—':x.toLocaleString(undefined,{maximumFractionDigits:dec})
const friendly=(id:string)=>id.replace('random_forest','Random Forest').replace('xgboost','XGBoost').replaceAll('_',' ')
const active=ref('overview')
function navigate(section: 'overview' | 'map' | 'models') {
  active.value = section
  if (section === 'overview') {
    if (import.meta.client) window.scrollTo({ top: 0, behavior: 'smooth' })
    return
  }
  if (import.meta.client) {
    const id = section === 'map' ? 'geo-map' : 'models'
    window.requestAnimationFrame(() => window.document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
  }
}
async function reload(){await Promise.all([refreshHealth(),refreshSummary(),refreshPoints()])}
</script>

<template>
<div class="app-shell">
  <aside class="sidebar">
    <div class="brand">
      <div class="brand-icon"><Leaf :size="23"/></div>
      <div><div class="brand-name">CarbonFusion<span style="color:#82dcaa"> AI</span></div><div class="brand-sub">Research Intelligence</div></div>
    </div>
    <div class="nav-group">
      <div class="group-label">Workspace</div>
      <button class="nav-item" :class="{active:active==='overview'}" @click="navigate('overview')"><BarChart3 :size="17"/> Overview</button>
      <button class="nav-item" :class="{active:active==='map'}" @click="navigate('map')"><MapPinned :size="17"/> Geo Explorer</button>
      <button class="nav-item" :class="{active:active==='models'}" @click="navigate('models')"><FlaskConical :size="17"/> Research Lab</button>
      <button class="nav-item" disabled title="Future research module"><TriangleAlert :size="17"/> Carbon Risk <span class="nav-tag">Soon</span></button>
      <div class="group-label" style="margin-top:26px">Research assets</div>
      <a class="nav-item" href="https://github.com/himani046/CarbonFusion-AI" target="_blank" rel="noopener"><BookOpen :size="17"/> Documentation <ArrowUpRight :size="13" style="margin-left:auto"/></a>
    </div>
    <div class="sidebar-bottom">
      <div class="project-note"><strong>Research Phase 1</strong>Biomass estimation and uncertainty calibration. Future deforestation risk is planned, not yet trained.<div style="margin-top:10px;color:#73cb9c">● Scientific MVP</div></div>
    </div>
  </aside>
  <main class="main">
    <header class="topbar">
      <div class="crumb">Research Workspace <span style="color:#567673;padding:0 7px">/</span> Overview</div>
      <div class="top-actions">
        <div class="status"><span class="dot" :class="{off:!health?.ready}"></span>{{health?.ready?'Model outputs available':'Awaiting model outputs'}}</div>
        <button class="outline-button" @click="reload" title="Reload API data"><RefreshCw :size="14" style="vertical-align:middle"/> Refresh</button>
      </div>
    </header>
    <div class="eyebrow">EARTH OBSERVATION · AI RESEARCH PLATFORM</div>
    <h1 class="page-title">Forest Carbon Intelligence<span style="color:#83dba8">.</span></h1>
    <p class="intro">Explore geographically held-out forest biomass estimates, understand model accuracy and quantify prediction uncertainty. Built on Sentinel-2 features and NASA GEDI-derived reference observations.</p>
    <div class="banner" v-if="isDemo"><strong>RESEARCH DEMO:</strong> The current training outputs are synthetic or missing. These values and map points are not real forest carbon measurements. No deforestation forecast is implemented.</div>
    <div class="banner error" v-if="summaryError">The FastAPI model service is unavailable or has no training outputs. Start the backend and run the training pipeline. <span style="opacity:.8">{{summaryError.message}}</span></div>

    <div class="metrics">
      <section class="card">
        <div class="metric-label">Held-out observations <Database :size="17"/></div>
        <div class="metric-value">{{num(summary?.sample_count,0)}}</div>
        <div class="metric-unit">evaluation samples</div>
        <div class="metric-sub">Geographically separated test set</div>
      </section>
      <section class="card">
        <div class="metric-label">Mean predicted biomass <Trees :size="17"/></div>
        <div class="metric-value">{{num(summary?.mean_predicted_agbd_mg_ha)}}</div>
        <div class="metric-unit">Mg of biomass / ha</div>
        <div class="metric-sub">Not total forest carbon stock</div>
      </section>
      <section class="card">
        <div class="metric-label">Interval coverage <ShieldCheck :size="17"/></div>
        <div class="metric-value">{{pct(summary?.interval_coverage)}}</div>
        <div class="metric-unit">nominal target: {{pct(summary?.nominal_coverage)}}</div>
        <div class="metric-sub">Held-out reference observations</div>
      </section>
      <section class="card">
        <div class="metric-label">Mean interval width <Activity :size="17"/></div>
        <div class="metric-value">{{num(summary?.mean_interval_width_mg_ha)}}</div>
        <div class="metric-unit">Mg/ha</div>
        <div class="metric-sub">Uncertainty precision indicator</div>
      </section>
    </div>

    <div class="dashboard-grid">
      <section class="card" id="geo-map">
        <div class="card-heading"><div><div class="card-title">Geospatial Observation Explorer</div><div class="card-sub">Predicted biomass at held-out sample locations · not a continuous raster</div></div><span class="pill">AGBD layer</span></div>
        <ClientOnly><ForestMap :points="points as any"/><template #fallback><div class="map-container"><div class="map-skeleton">Initializing satellite research map…</div></div></template></ClientOnly>
        <div class="small-stat"><span>Dataset</span><strong>{{isDemo?'Synthetic testing data':'User-configured real-data mode'}}</strong></div>
        <div class="small-stat"><span>Prediction type</span><strong>Aboveground biomass density</strong></div>
      </section>
      <section class="card" id="models">
        <div class="card-heading"><div><div class="card-title">Model Performance</div><div class="card-sub">Lower RMSE means smaller prediction error</div></div><GitCompareArrows :size="17" color="#75cba1"/></div>
        <ClientOnly><ModelChart v-if="records.length" :models="records"/><div v-else class="empty">Run the training pipeline to see real model output metrics.</div></ClientOnly>
        <div class="small-stat"><span>Validation</span><strong>Geographic block holdout</strong></div>
        <div class="small-stat"><span>Calibration</span><strong>Split-conformal · 90%</strong></div>
        <div class="small-stat"><span>Label source</span><strong>GEDI-modeled AGBD</strong></div>
      </section>
    </div>

    <div class="bottom-grid">
      <section class="card">
        <div class="card-heading"><div><div class="card-title">Comparative Research Results</div><div class="card-sub">RMSE and MAE in Mg/ha, evaluated on held-out blocks</div></div><FlaskConical :size="17" color="#75cba1"/></div>
        <div class="table-wrap"><table><thead><tr><th>MODEL</th><th>RMSE ↓</th><th>MAE ↓</th><th>R² ↑</th></tr></thead>
          <tbody><tr v-for="m in records" :key="m.model"><td>{{friendly(m.model)}}</td><td>{{num(m.rmse_mg_ha,2)}}</td><td>{{num(m.mae_mg_ha,2)}}</td><td>{{num(m.r2,3)}}</td></tr>
            <tr v-if="!records.length"><td colspan="4">No trained model results available</td></tr>
          </tbody></table></div>
      </section>
      <section class="card">
        <div class="card-heading"><div><div class="card-title">Scientific Interpretation</div><div class="card-sub">Know exactly what your model demonstrates</div></div><CircleHelp :size="17" color="#75cba1"/></div>
        <div class="research-note">
          <p><b>Predictions:</b> Aboveground biomass density (Mg/ha), not atmospheric CO₂ emissions.</p>
          <p><b>Reference data:</b> GEDI AGBD targets are modeled estimates. Field observations are needed for independent absolute validation.</p>
          <p><b>Uncertainty:</b> The interval coverage describes agreement with held-out GEDI targets, not guaranteed true-carbon coverage.</p>
          <p><b>Coming next:</b> Real Earth Engine extraction, full raster mapping and a separate future deforestation-risk model.</p>
        </div>
      </section>
    </div>
    <footer class="footer"><span>CarbonFusion AI · Forest Carbon Research Platform</span><span>Research transparency first · © 2026</span></footer>
  </main>
</div>
</template>
