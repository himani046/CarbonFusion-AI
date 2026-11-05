<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import type { FeatureCollection } from 'geojson'
const props = defineProps<{ points: FeatureCollection | null }>()
const el = ref<HTMLElement | null>(null)
const error = ref('')
let map: any = null
const refresh = (points: FeatureCollection | null) => {
  if (!map || !points) return
  const source = map.getSource('samples')
  if (source) source.setData(points)
  else return
  const coords = points.features.map((f: any) => f.geometry.coordinates as number[])
  if (coords.length) {
    const xs=coords.map(x=>x[0]), ys=coords.map(x=>x[1])
    const box:[[number,number],[number,number]]=[[Math.min(...xs),Math.min(...ys)],[Math.max(...xs),Math.max(...ys)]]
    map.fitBounds(box,{padding:55,maxZoom:10,duration:400})
  }
}
onMounted(async () => {
  if (!el.value) return
  try {
    const lib=await import('maplibre-gl')
    map=new lib.Map({
      container:el.value,
      style:{version:8,sources:{osm:{type:'raster',tiles:['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],tileSize:256,attribution:'© OpenStreetMap contributors'}},layers:[{id:'osm',type:'raster',source:'osm'}]},
      center:[86.5,21.9],zoom:8,attributionControl:true
    })
    map.addControl(new lib.NavigationControl({showCompass:false}),'top-right')
    map.on('load',()=>{
      map.addSource('samples',{type:'geojson',data:props.points || {type:'FeatureCollection',features:[]}})
      map.addLayer({id:'samples-halo',type:'circle',source:'samples',paint:{'circle-radius':11,'circle-color':'#86d6a6','circle-opacity':0.10}})
      map.addLayer({id:'sample-points',type:'circle',source:'samples',paint:{
        'circle-radius':5.5,'circle-stroke-width':1,'circle-stroke-color':'#102820','circle-opacity':0.88,
        'circle-color':['interpolate',['linear'],['get','pred_agbd'],40,'#78b6bc',100,'#9acb8b',180,'#dfc56c',260,'#e78a60']
      }})
      map.on('click','sample-points',(event:any)=>{
        const feat=event.features?.[0]; if(!feat) return
        const p=feat.properties
        new lib.Popup({offset:12,closeButton:false}).setLngLat(event.lngLat)
          .setHTML('<div style="color:#142b29;font:12px sans-serif"><b>Held-out prediction</b><br/>AGBD: '+Number(p.pred_agbd).toFixed(1)+' Mg/ha<br/>Interval: '+Number(p.pi_low).toFixed(1)+'–'+Number(p.pi_high).toFixed(1)+' Mg/ha</div>')
          .addTo(map)
      })
      refresh(props.points)
    })
  } catch { error.value='Map failed to initialize. Check browser and map network access.' }
})
watch(()=>props.points,refresh)
onBeforeUnmount(()=>{map?.remove(); map=null})
</script>
<template><div class="map-container"><div v-if="error" class="map-skeleton">{{ error }}</div><div v-else ref="el" class="map-element"></div><div class="map-overlay"><b>Held-out sample predictions (Mg/ha)</b><div class="legend-ramp"></div><div class="legend-labels"><span>40</span><span>100</span><span>180</span><span>260+</span></div></div></div></template>
