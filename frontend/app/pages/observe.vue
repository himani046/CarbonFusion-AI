<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Leaf, ArrowLeft, MapPin, Satellite, FlaskConical, Send, RotateCcw, Navigation, CalendarDays } from 'lucide-vue-next'
type Prediction = {longitude:number,latitude:number,pred_agbd_mg_ha:number,interval_low_mg_ha:number,interval_high_mg_ha:number,carbon_density_t_ha:number,ndvi:number,ndmi:number,ndre:number,warning:string}
const config=useRuntimeConfig()
const api=String(config.public.apiBase).replace(/[/]$/,'')
const names=['B2','B3','B4','B5','B6','B7','B8','B8A','B11','B12'] as const
const values=ref<Record<string,string>>({longitude:'',latitude:'',elevation:'',slope:'',...Object.fromEntries(names.map(n=>[n,'']))})
const status=ref<{available:boolean,satellite_auto_fetch:boolean}|null>(null)
const pending=ref(false)
const autoPending=ref(false)
const dateValue=ref('2022-01-01')
const autoResult=ref<any|null>(null)
const autoError=ref('')
const result=ref<Prediction|null>(null)
const error=ref('')
const ratio=(a:number,b:number)=>a+b===0?0:(a-b)/(a+b)
const derived=computed(()=>{
 const v=values.value
 const required=['B8','B4','B11','B8A','B5']
 if(required.some(k=>v[k]===''||!Number.isFinite(Number(v[k]))))return null
 const read=(k:string)=>Number(v[k])
 return {ndvi:ratio(read('B8'),read('B4')),ndmi:ratio(read('B8'),read('B11')),ndre:ratio(read('B8A'),read('B5'))}
})
onMounted(async()=>{
 try{status.value=await $fetch(api+'/api/inference-status')}catch{status.value=null}
})
const fields=[
 {id:'B2',label:'B2 · Blue'},{id:'B3',label:'B3 · Green'},
 {id:'B4',label:'B4 · Red'},{id:'B5',label:'B5 · Red Edge 1'},
 {id:'B6',label:'B6 · Red Edge 2'},{id:'B7',label:'B7 · Red Edge 3'},
 {id:'B8',label:'B8 · NIR'},{id:'B8A',label:'B8A · Narrow NIR'},
 {id:'B11',label:'B11 · SWIR 1'},{id:'B12',label:'B12 · SWIR 2'}
]
function reset(){Object.keys(values.value).forEach(k=>values.value[k]='');result.value=null;error.value='';autoResult.value=null;autoError.value=''}
const selectedLongitude=computed(()=>values.value.longitude===''?null:Number(values.value.longitude))
const selectedLatitude=computed(()=>values.value.latitude===''?null:Number(values.value.latitude))
function selectLocation(location:{longitude:number,latitude:number}){
 values.value.longitude=String(location.longitude)
 values.value.latitude=String(location.latitude)
 autoResult.value=null
 autoError.value=''
}
async function automaticAnalyze(){
 autoError.value='';autoResult.value=null;result.value=null
 const lon=selectedLongitude.value,lat=selectedLatitude.value
 if(lon===null||lat===null||!Number.isFinite(lon)||!Number.isFinite(lat)||lat < -85||lat > 85||lon < -180||lon > 180){
   autoError.value='Select a location on the map or enter valid coordinates.';return
 }
 if(!dateValue.value){autoError.value='Choose an observation date.';return}
 autoPending.value=true
 try{
   const response=await $fetch<any>(api+'/api/observations/automatic',{method:'POST',body:{longitude:lon,latitude:lat,observation_date:dateValue.value}})
   autoResult.value=response
   // Populate the manual fields with real fetched values; no guessing.
   for(const field of [...names,'elevation','slope']) values.value[field]=String(response.spectral_bands[field])
 }catch(e:any){
   autoError.value=e?.data?.detail||e?.message||'Unable to retrieve a usable satellite scene.'
 }finally{autoPending.value=false}
}
async function submit(){
 error.value='';result.value=null
 const v=values.value
 const keys=['longitude','latitude','elevation','slope',...names]
 if(keys.some(k=>v[k]===''||!Number.isFinite(Number(v[k])))){error.value='Enter a valid numeric value for every field.';return}
 const data=Object.fromEntries(keys.map(k=>[k,Number(v[k])]))
 if(data.latitude < -90 || data.latitude > 90 || data.longitude < -180 || data.longitude > 180){error.value='Latitude must be -90 to 90 and longitude -180 to 180.';return}
 if(names.some(k=>data[k] < 0 || data[k] > 1)){error.value='Enter Sentinel-2 surface reflectance as fractions between 0 and 1 (not raw integers).';return}
 pending.value=true
 try{result.value=await $fetch<Prediction>(api+'/api/observations/predict',{method:'POST',body:data})}
 catch(e:any){error.value=e?.data?.detail||e?.message||'Unable to run inference.'}
 finally{pending.value=false}
}
</script>

<template>
<div class="app-shell">
  <aside class="sidebar">
    <div class="brand"><div class="brand-icon"><Leaf :size="23"/></div><div><div class="brand-name">CarbonFusion<span style="color:#82dcaa"> AI</span></div><div class="brand-sub">Research Intelligence</div></div></div>
    <div class="nav-group">
      <div class="group-label">Workspace</div>
      <NuxtLink to="/" class="nav-item"><ArrowLeft :size="17"/> Dashboard</NuxtLink>
      <NuxtLink to="/observe" class="nav-item active"><Satellite :size="17"/> New Observation</NuxtLink>
      <div class="group-label" style="margin-top:26px">Research assets</div>
      <a class="nav-item" href="https://github.com/himani046/CarbonFusion-AI" target="_blank" rel="noopener">Project documentation</a>
    </div>
    <div class="sidebar-bottom"><div class="project-note"><strong>Manual feature inference</strong>Click a location to retrieve real Sentinel-2 imagery and terrain. It does not save observations, validate land cover, or calculate total forest carbon stock.</div></div>
  </aside>
  <main class="main">
    <header class="topbar"><div class="crumb">Research Workspace / New Observation</div><NuxtLink class="outline-button" to="/">← Back to overview</NuxtLink></header>
    <div class="eyebrow">EXPLORE · RESEARCH PROTOTYPE</div>
    <h1 class="page-title">New Forest Observation<span style="color:#83dba8">.</span></h1>
    <p class="intro">Click a forest location on the map, choose a date and let CarbonFusion AI retrieve Sentinel-2 surface reflectance and terrain automatically. You can also supply optical features manually.</p>
    <div class="banner"><strong>Research limitation:</strong> The trained model has negative held-out R² and is not scientifically validated for new regions. Automated imagery sampling may fail if public services are unavailable or no clear pixel exists. Do not interpret outputs as authoritative forest carbon measurements.</div>
    <div v-if="status&&!status.available" class="banner error">Inference model is not deployed yet. Re-run the public-artifact packaging script and redeploy the API. This form cannot produce predictions until a real model is available.</div>
    <div v-if="!status" class="banner error">Backend connection unavailable or initializing. Check API hosting and /api/inference-status.</div>
    <div class="observation-layout">
      <form class="card" @submit.prevent="submit">
        <div class="card-heading"><div><div class="card-title">Observation inputs</div><div class="card-sub">All fields required · raw surface reflectance is scaled 0–1</div></div><MapPin :size="18" color="#82dcaa"/></div>
        <div class="observation-section-title">1 · Click to select a forest location</div>
        <ClientOnly><LocationPicker :longitude="selectedLongitude" :latitude="selectedLatitude" @select="selectLocation"/><template #fallback><div class="map-skeleton" style="height:250px">Loading location map...</div></template></ClientOnly>
        <div class="observation-section-title">2 · Requested observation date</div>
        <label class="observation-field" style="max-width:300px"><CalendarDays :size="15"/> Date (2018 onward; imagery within ±45 days)<input v-model="dateValue" type="date" min="2018-01-01" required/></label>
        <div class="observation-section-title">3 · Selected point</div>
        <div class="observation-fields">
          <label class="observation-field">Latitude (°)<input v-model="values.latitude" type="number" step="any" min="-90" max="90" placeholder="e.g. 22.42" required/></label>
          <label class="observation-field">Longitude (°)<input v-model="values.longitude" type="number" step="any" min="-180" max="180" placeholder="e.g. 86.16" required/></label>
          <label class="observation-field">Elevation (m)<input v-model="values.elevation" type="number" step="any" min="-500" max="9000" placeholder="SRTM elevation" required/></label>
          <label class="observation-field">Slope (°)<input v-model="values.slope" type="number" step="any" min="0" max="90" placeholder="SRTM slope" required/></label>
        </div>
        <div class="observation-actions">
          <button type="button" class="observation-primary" :disabled="autoPending||status?.available!==true" @click="automaticAnalyze"><Navigation :size="16"/> {{autoPending?'Retrieving satellite imagery...':'Analyze location automatically'}}</button>
        </div>
        <p v-if="autoError" class="observation-error" role="alert">{{autoError}}</p>
        <p class="observation-help">Click-based analysis uses a real cloud-screened Sentinel-2 pixel and public elevation tiles. Satellite services may be temporarily unavailable; no result is fabricated. After a successful lookup, the manual features below are filled automatically.</p>
        <div class="observation-section-title">Alternative · Manually enter Sentinel-2 bands</div>
        <p class="observation-help">Enter cloud-masked surface reflectance fractions for each band, matching the original training workflow. These values must come from actual measurements, not guessed numbers.</p>
        <div class="observation-fields">
          <label v-for="f in fields" :key="f.id" class="observation-field">{{f.label}}<input v-model="values[f.id]" type="number" step="any" min="0" max="1" placeholder="0.000–1.000" required/></label>
        </div>
        <div class="observation-section-title">Calculated vegetation indices</div>
        <div class="observation-indices"><span>NDVI <b>{{derived?.ndvi.toFixed(3)??'—'}}</b></span><span>NDMI <b>{{derived?.ndmi.toFixed(3)??'—'}}</b></span><span>NDRE <b>{{derived?.ndre.toFixed(3)??'—'}}</b></span></div>
        <p v-if="error" role="alert" class="observation-error">{{error}}</p>
        <div class="observation-actions">
          <button class="observation-primary" type="submit" :disabled="pending||status?.available!==true"><Send :size="16"/> {{pending?'Analyzing...':'Predict biomass'}}</button>
          <button class="outline-button" type="button" @click="reset"><RotateCcw :size="15"/> Clear</button>
        </div>
      </form>
      <div class="observation-side">
        <section class="card">
          <div class="card-heading"><div><div class="card-title">Prediction result</div><div class="card-sub">Satellite-derived biomass estimate</div></div><FlaskConical :size="18" color="#82dcaa"/></div>
          <template v-if="autoResult">
            <div class="observation-result-label">Automatically retrieved Sentinel-2 observation</div>
            <div class="observation-result-value">{{autoResult.pred_agbd_mg_ha.toFixed(1)}} <small>Mg/ha</small></div>
            <div class="small-stat"><span>Source image date</span><strong>{{autoResult.satellite.acquired_at?.slice(0,10)??'Unavailable'}}</strong></div>
            <div class="small-stat"><span>Scene cloud coverage</span><strong>{{autoResult.satellite.scene_cloud_cover_pct??'—'}}%</strong></div>
            <div class="small-stat"><span>Pixel cloud class</span><strong>{{autoResult.satellite.scl_class_at_point}}</strong></div>
            <div class="small-stat"><span>Prediction interval</span><strong>{{autoResult.interval_low_mg_ha.toFixed(1)}}–{{autoResult.interval_high_mg_ha.toFixed(1)}} Mg/ha</strong></div>
            <div class="small-stat"><span>Carbon density estimate</span><strong>{{autoResult.carbon_density_t_ha.toFixed(1)}} t/ha</strong></div>
            <div class="small-stat"><span>NDVI</span><strong>{{autoResult.ndvi.toFixed(3)}}</strong></div>
            <div class="observation-disclaimer">{{autoResult.warning}}</div>
          </template>
          <template v-else-if="result">
            <div class="observation-result-label">Estimated aboveground biomass</div>
            <div class="observation-result-value">{{result.pred_agbd_mg_ha.toFixed(1)}} <small>Mg/ha</small></div>
            <div class="small-stat"><span>90% nominal prediction interval</span><strong>{{result.interval_low_mg_ha.toFixed(1)}}–{{result.interval_high_mg_ha.toFixed(1)}} Mg/ha</strong></div>
            <div class="small-stat"><span>Estimated carbon density (factor 0.47)</span><strong>{{result.carbon_density_t_ha.toFixed(1)}} t/ha</strong></div>
            <div class="small-stat"><span>Coordinates</span><strong>{{result.latitude.toFixed(4)}}, {{result.longitude.toFixed(4)}}</strong></div>
            <div class="observation-disclaimer">{{result.warning}}</div>
          </template>
          <template v-else><div class="observation-placeholder"><Satellite :size="32"/><p>Enter the satellite measurements and run the model to see the result.</p><small>No example numbers are presented as real measurements.</small></div></template>
        </section>
        <section class="card">
          <div class="card-title">What this feature does</div>
          <p class="observation-help">For automatic analysis, click the map and choose a date. The backend searches public Sentinel-2 scenes, reads a cloud-screened pixel, samples global terrain tiles and runs the same XGBoost model. Manual feature entry remains available.</p>
          <div class="small-stat"><span>Automatic Sentinel-2 point retrieval</span><strong>Enabled (public STAC)</strong></div>
          <div class="small-stat"><span>Drawing polygon / area total</span><strong>Not available</strong></div>
          <div class="small-stat"><span>Model training data</span><strong>GEDI V3 + Sentinel-2</strong></div>
        </section>
      </div>
    </div>
    <footer class="footer"><span>CarbonFusion AI · New Observation</span><span>Experimental estimates only · © 2026</span></footer>
  </main>
</div>
</template>
