<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import type { FeatureCollection } from 'geojson'
type Point = {lng:number,lat:number,biomass:number,low:number,high:number}
const props = defineProps<{ points: FeatureCollection | null }>()
const el = ref<HTMLElement|null>(null)
const mapError = ref('')
const loaded = ref(false)
const selection = ref<Point|null>(null)
let map: any = null
let alive = true
const parsed = computed<Point[]>(() => (props.points?.features ?? []).flatMap((f: any) => {
  const [lng,lat] = f.geometry?.coordinates ?? []
  const biomass = Number(f.properties?.pred_agbd)
  if (![lng,lat,biomass].every(Number.isFinite)) return []
  return [{ lng,lat,biomass,low:Number(f.properties?.pi_low),high:Number(f.properties?.pi_high) }]
}))
const bounds = computed(() => {
  const xs=parsed.value.map(p=>p.lng),ys=parsed.value.map(p=>p.lat)
  return {minX:Math.min(...xs,86.15),maxX:Math.max(...xs,86.85),minY:Math.min(...ys,21.3),maxY:Math.max(...ys,22.3)}
})
const dots = computed(()=>parsed.value.map(p=>({
  ...p,
  x:24+652*(p.lng-bounds.value.minX)/Math.max(.01,bounds.value.maxX-bounds.value.minX),
  y:24+330*(bounds.value.maxY-p.lat)/Math.max(.01,bounds.value.maxY-bounds.value.minY)
})))
const color = (v:number)=>v>=200?'#e58d62':v>=140?'#e0cc78':v>=80?'#92c796':'#68b7b8'
const empty: FeatureCollection = {type:'FeatureCollection',features:[]}
function synchronize(data: FeatureCollection|null) {
  if (!map || !loaded.value) return
  const source=map.getSource('samples')
  if (!source) return
  source.setData(data || empty)
  const pts=parsed.value
  if (pts.length) {
    const xs=pts.map(p=>p.lng),ys=pts.map(p=>p.lat)
    map.fitBounds([[Math.min(...xs),Math.min(...ys)],[Math.max(...xs),Math.max(...ys)]],{padding:55,maxZoom:11,duration:450})
  }
}
onMounted(async()=>{
  if (!el.value) return
  try {
    const lib=await import('maplibre-gl')
    if(!alive||!el.value)return
    map=new lib.Map({
      container:el.value,
      style:{version:8,sources:{osm:{type:'raster',tiles:['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],tileSize:256,attribution:'© OpenStreetMap contributors'}},layers:[{id:'osm',type:'raster',source:'osm'}]},
      center:[86.5,21.9],zoom:8,attributionControl:true
    })
    map.on('error',(event:any)=>{if(!loaded.value)mapError.value=event.error?.message||'Basemap could not load'})
    map.addControl(new lib.NavigationControl({showCompass:false}),'top-right')
    map.on('load',()=>{
      if(!map)return
      loaded.value=true
      mapError.value=''
      map.addSource('samples',{type:'geojson',data:props.points||empty})
      map.addLayer({id:'samples-halo',type:'circle',source:'samples',paint:{'circle-radius':11,'circle-color':'#86d6a6','circle-opacity':.15}})
      map.addLayer({id:'sample-points',type:'circle',source:'samples',paint:{
        'circle-radius':6,'circle-stroke-width':1.2,'circle-stroke-color':'#102820','circle-opacity':.95,
        'circle-color':['interpolate',['linear'],['get','pred_agbd'],40,'#78b6bc',100,'#9acb8b',180,'#dfc56c',260,'#e78a60']
      }})
      map.on('click','sample-points',(event:any)=>{
        const p=event.features?.[0]?.properties
        if (!p)return
        selection.value={lng:event.lngLat.lng,lat:event.lngLat.lat,biomass:Number(p.pred_agbd),low:Number(p.pi_low),high:Number(p.pi_high)}
      })
      synchronize(props.points)
    })
    // Detect a blocked or non-WebGL basemap rather than leaving a silent blank panel.
    window.setTimeout(()=>{if(alive&&!loaded.value)mapError.value='Basemap unavailable; geographic fallback enabled'},7000)
  } catch(error:any){mapError.value=error?.message || 'WebGL map unavailable'}
})
watch(()=>props.points,(v)=>synchronize(v))
onBeforeUnmount(()=>{alive=false;map?.remove();map=null})
</script>
<template>
  <div class="map-container">
    <div ref="el" class="map-element" :style="{visibility:loaded&&!mapError?'visible':'hidden'}"></div>
    <div v-if="!loaded||mapError" class="geo-fallback">
      <svg viewBox="0 0 700 380" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Geographic plot of held-out biomass observations">
        <defs>
          <pattern id="geo-lines" width="44" height="44" patternUnits="userSpaceOnUse"><path d="M44 0H0V44" fill="none" stroke="#3b6660" stroke-width=".65" opacity=".45"/></pattern>
        </defs>
        <rect width="700" height="380" fill="#102a2a"/>
        <rect width="700" height="380" fill="url(#geo-lines)"/>
        <path d="M0 130 Q140 80 245 155 T520 100 T700 120" stroke="#294d4c" fill="none" stroke-width="40" opacity=".35"/>
        <path d="M80 380 Q200 210 345 245 T700 60" stroke="#4c7264" fill="none" stroke-width="5" opacity=".4"/>
        <g v-for="(p,i) in dots" :key="i" @click="selection=p">
          <circle :cx="p.x" :cy="p.y" r="5.7" :fill="color(p.biomass)" fill-opacity=".85" stroke="#112b2a" stroke-width=".8"/>
        </g>
        <text x="20" y="29" fill="#c8e3d5" font-size="13" font-weight="600">Geographic sample view</text>
        <text x="20" y="47" fill="#8db0aa" font-size="10">Illustrative base grid · point coordinates from model outputs</text>
        <text x="14" y="368" fill="#9cb6ae" font-size="11">{{bounds.minX.toFixed(2)}}° E</text>
        <text x="625" y="368" fill="#9cb6ae" font-size="11">{{bounds.maxX.toFixed(2)}}° E</text>
      </svg>
      <div v-if="!dots.length" class="geo-empty">No prediction coordinates received. Run training and check the FastAPI /api/predictions endpoint.</div>
      <div v-if="mapError" class="geo-map-status">Map tiles unavailable; showing coordinate-based sample plot</div>
    </div>
    <div class="map-overlay"><b>Held-out biomass predictions (Mg/ha)</b><div class="legend-ramp"></div><div class="legend-labels"><span>40</span><span>100</span><span>180</span><span>260+</span></div></div>
    <div v-if="selection" class="geo-selection"><button class="geo-close" aria-label="Close sample details" @click="selection=null">×</button><b>Selected held-out sample</b><div>Predicted AGBD: {{selection.biomass.toFixed(1)}} Mg/ha</div><div>Interval: {{selection.low.toFixed(1)}}–{{selection.high.toFixed(1)}} Mg/ha</div></div>
  </div>
</template>
<style scoped>
.geo-fallback{position:absolute;inset:0;background:#112a2b}.geo-fallback svg{width:100%;height:100%;display:block}.geo-fallback circle{cursor:pointer}.geo-fallback circle:hover{stroke:#e5fff3;stroke-width:2}
.geo-empty{position:absolute;top:48%;left:50%;transform:translate(-50%,-50%);text-align:center;color:#c3dbd1;font-size:12px;width:80%}
.geo-map-status{position:absolute;top:10px;right:12px;padding:8px;background:#10282bcc;color:#b8d4c9;border:1px solid #476b65;border-radius:6px;font-size:10px}
.geo-selection{position:absolute;top:15px;left:15px;background:#0d2829f2;padding:13px 16px;border:1px solid #4b8270;border-radius:9px;font-size:12px;line-height:1.8;color:#c9e8d9;z-index:4;min-width:205px}.geo-selection b{color:#8de0b0}.geo-close{position:absolute;right:7px;top:4px;background:transparent;border:0;color:#aad2c3;font-size:20px}
</style>
