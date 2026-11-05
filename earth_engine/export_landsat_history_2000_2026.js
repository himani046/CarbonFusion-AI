// CarbonFusion AI — Landsat annual vegetation history, 2000-2026.
// This exports 27 annual regional index summaries, NOT forest carbon estimates.
// 2026 is incomplete; data are only as recent as Earth's currently ingested imagery.
var aoi=ee.Geometry.Rectangle([85.8,21.2,87.3,22.7]);
var fromYear=2000, toYear=2026, analysisScale=120;
var outBands=['blue','green','red','nir','swir1','swir2'];
Map.centerObject(aoi,8); Map.addLayer(aoi,{color:'yellow'},'Study rectangle');
function maskScale(im,sourceBands){
  var qa=im.select('QA_PIXEL');
  var clear=qa.bitwiseAnd(1).eq(0)
    .and(qa.bitwiseAnd(2).eq(0))
    .and(qa.bitwiseAnd(8).eq(0))
    .and(qa.bitwiseAnd(16).eq(0))
    .and(qa.bitwiseAnd(32).eq(0))
    .and(im.select('QA_RADSAT').eq(0));
  return im.select(sourceBands,outBands).multiply(0.0000275).add(-0.2)
    .updateMask(clear).copyProperties(im,['system:time_start']);
}
function older(im){return maskScale(im,['SR_B1','SR_B2','SR_B3','SR_B4','SR_B5','SR_B7']);}
function newer(im){return maskScale(im,['SR_B2','SR_B3','SR_B4','SR_B5','SR_B6','SR_B7']);}
var all=ee.ImageCollection('LANDSAT/LT05/C02/T1_L2').filterBounds(aoi).map(older)
  .merge(ee.ImageCollection('LANDSAT/LE07/C02/T1_L2').filterBounds(aoi).map(older))
  .merge(ee.ImageCollection('LANDSAT/LC08/C02/T1_L2').filterBounds(aoi).map(newer))
  .merge(ee.ImageCollection('LANDSAT/LC09/C02/T1_L2').filterBounds(aoi).map(newer));
function yearRow(y){
  y=ee.Number(y);
  var start=ee.Date.fromYMD(y,1,1), end=start.advance(1,'year');
  var scenes=all.filterDate(start,end);
  var img=scenes.median();
  var indices=img.normalizedDifference(['nir','red']).rename('ndvi')
    .addBands(img.normalizedDifference(['nir','swir1']).rename('ndmi'))
    .addBands(img.normalizedDifference(['nir','swir2']).rename('nbr'));
  var means=indices.reduceRegion({reducer:ee.Reducer.mean(),
    geometry:aoi,scale:analysisScale,maxPixels:1e10,tileScale:4,bestEffort:true});
  var coverage=indices.select('ndvi').mask().unmask(0).reduceRegion({
    reducer:ee.Reducer.mean(),geometry:aoi,scale:analysisScale,
    maxPixels:1e10,tileScale:4,bestEffort:true
  }).get('ndvi');
  return ee.Feature(null,{year:y,ndvi_mean:means.get('ndvi'),
    ndmi_mean:means.get('ndmi'),nbr_mean:means.get('nbr'),
    scene_count:scenes.size(),approximate_valid_fraction:coverage,
    incomplete_year:y.eq(2026)});
}
var annual=ee.FeatureCollection(ee.List.sequence(fromYear,toYear).map(yearRow));
print('Annual vegetation index history 2000–2026',annual);
print(ui.Chart.feature.byFeature(annual,'year',['ndvi_mean','ndmi_mean','nbr_mean'])
  .setOptions({title:'Annual Landsat vegetation indices (NOT biomass)',
    hAxis:{title:'Year'},vAxis:{title:'Mean index'},pointSize:3,lineWidth:2}));
var recent=all.filterDate('2025-01-01','2026-11-06').median();
Map.addLayer(recent.clip(aoi),{bands:['red','green','blue'],min:.02,max:.3},'Recent Landsat RGB');
Export.table.toDrive({collection:annual,
  description:'carbonfusion_landsat_history_2000_2026',
  fileNamePrefix:'carbonfusion_landsat_history_2000_2026',
  folder:'CarbonFusionAI',fileFormat:'CSV',
  selectors:['year','ndvi_mean','ndmi_mean','nbr_mean','scene_count',
    'approximate_valid_fraction','incomplete_year']});
// Limitations: whole rectangular AOI, not forest-only area; mixed sensors not
// cross-calibrated; uneven coverage, seasonal composition, Landsat 7 gaps.
// Do NOT use as GEDI supervised biomass labels or verified deforestation rates.
