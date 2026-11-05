<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
const props=defineProps<{ models: Array<{model:string,rmse_mg_ha:number,mae_mg_ha:number,r2:number}> }>()
const el=ref<HTMLElement|null>(null)
let chart:any=null
const update=()=>{
  if(!chart)return
  const names=props.models.map(m=>m.model.replace('random_forest_','RF ').replace('xgboost_','XGB ').replaceAll('_',' '))
  chart.setOption({backgroundColor:'transparent',tooltip:{trigger:'axis',backgroundColor:'#193438',borderColor:'#355c52',textStyle:{color:'#dfefe5'}},
    grid:{left:45,right:18,top:30,bottom:60},
    xAxis:{type:'category',data:names,axisLine:{lineStyle:{color:'#3b5959'}},axisLabel:{color:'#87a29e',rotate:15,fontSize:10}},
    yAxis:{type:'value',name:'RMSE (Mg/ha)',nameTextStyle:{color:'#91aaa6',fontSize:10},splitLine:{lineStyle:{color:'#233f40'}},axisLabel:{color:'#87a29e'}},
    series:[{type:'bar',name:'RMSE',data:props.models.map(m=>m.rmse_mg_ha),barMaxWidth:48,itemStyle:{color:'#69c69d',borderRadius:[5,5,0,0]}}]
  })
}
let resize=()=>chart?.resize()
onMounted(async()=>{if(!el.value)return;const echarts=await import('echarts/core');const charts=await import('echarts/charts');const comps=await import('echarts/components');const renderers=await import('echarts/renderers');echarts.use([charts.BarChart,comps.GridComponent,comps.TooltipComponent,renderers.CanvasRenderer]);chart=echarts.init(el.value);update();window.addEventListener('resize',resize)})
watch(()=>props.models,update,{deep:true})
onBeforeUnmount(()=>{window.removeEventListener('resize',resize);chart?.dispose()})
</script>
<template><div ref="el" class="chart-area"></div></template>
