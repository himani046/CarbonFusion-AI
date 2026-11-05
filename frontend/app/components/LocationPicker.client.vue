<script setup lang="ts">
import {ref,onMounted,onBeforeUnmount,watch} from 'vue'
const props=defineProps<{longitude:number|null,latitude:number|null}>()
const emit=defineEmits<{(e:'select',position:{longitude:number,latitude:number}):void}>()
const target=ref<HTMLElement|null>(null)
const problem=ref('')
let map:any=null
let marker:any=null
onMounted(async()=>{
  try{
    const lib=await import('maplibre-gl')
    if(!target.value)return
    map=new lib.Map({
      container:target.value,
      style:{version:8,sources:{osm:{type:'raster',tiles:['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],tileSize:256,attribution:'© OpenStreetMap contributors'}},layers:[{id:'osm',type:'raster',source:'osm'}]},
      center:[86.16,22.42],zoom:9
    })
    map.addControl(new lib.NavigationControl({showCompass:false}),'top-right')
    map.on('click',(evt:any)=>{
      emit('select',{longitude:Number(evt.lngLat.lng.toFixed(6)),latitude:Number(evt.lngLat.lat.toFixed(6))})
    })
    map.on('error',(evt:any)=>{problem.value=evt.error?.message||'Map tile loading error'})
  }catch(e:any){problem.value=e?.message||'Map unavailable'}
})
watch(()=>[props.longitude,props.latitude],(loc)=>{
  if(!map || loc.some(x=>x===null||!Number.isFinite(x as number)))return
  const longitude=loc[0] as number,latitude=loc[1] as number
  import('maplibre-gl').then(lib=>{
    if(!map)return
    marker?.remove()
    marker=new lib.Marker({color:'#8fe6b5'}).setLngLat([longitude,latitude]).addTo(map)
    map.easeTo({center:[longitude,latitude],zoom:Math.max(map.getZoom(),10)})
  })
})
onBeforeUnmount(()=>{marker?.remove();map?.remove();map=null})
</script>
<template>
  <div class="location-picker">
    <div ref="target" class="location-picker-map"></div>
    <div class="location-picker-hint">Click a location to select it · or enter coordinates manually</div>
    <div v-if="problem" class="location-picker-warning">Map tiles unavailable. Enter coordinates below instead.</div>
  </div>
</template>
<style scoped>
.location-picker{position:relative;border:1px solid #31554c;border-radius:12px;overflow:hidden;background:#0a2528;height:285px}
.location-picker-map{width:100%;height:100%}
.location-picker-hint{position:absolute;left:10px;bottom:10px;background:#082322df;border:1px solid #3c5b53;padding:8px 12px;border-radius:8px;color:#d4f3df;font-size:11px;pointer-events:none;z-index:1}
.location-picker-warning{position:absolute;left:10px;right:10px;top:10px;background:#402e24;padding:8px;color:#f1c1a2;font-size:11px;z-index:1}
</style>
