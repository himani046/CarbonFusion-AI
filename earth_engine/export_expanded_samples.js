// CarbonFusion AI — expanded candidate training-sample extractor (v2)
// Earth Engine Code Editor: https://code.earthengine.google.com/
// IMPORTANT: candidate raster-cell samples, NOT GEDI footprint-exact collocation.
//
// Start with ONE YEAR to control Earth Engine resource usage. Change YEAR and
// re-run for subsequent years, exporting a separate CSV each time.
var YEAR = 2022;
var AOI = ee.Geometry.Rectangle([85.8, 21.2, 87.3, 22.7]);
var SAMPLES_PER_MONTH = 25000; // requested; actual valid pixels may be much fewer
var CLOUD_WINDOW_DAYS = 45;
var APPLY_TREE_MASK = true;   // 2021 WorldCover trees class; excludes some real forest
var BANDS = ['B2','B3','B4','B5','B6','B7','B8','B8A','B11','B12'];
var PROJECTION = ee.Projection('EPSG:32645').atScale(25);
var startOfYear = ee.Date.fromYMD(YEAR,1,1);
Map.centerObject(AOI,8);
Map.addLayer(AOI,{color:'yellow'},'Illustrative study rectangle');
var worldcover=ee.ImageCollection('ESA/WorldCover/v200').first().select('Map');
var treeMask=worldcover.eq(10);
Map.addLayer(treeMask.selfMask().clip(AOI),{palette:['4aa36a']},'WorldCover 2021 tree mask',false);

function sentinelMask(image) {
  var s=image.select('SCL');
  var valid=s.neq(0).and(s.neq(1)).and(s.neq(3))
    .and(s.neq(8)).and(s.neq(9)).and(s.neq(10)).and(s.neq(11));
  return image.updateMask(valid).select(BANDS).multiply(0.0001)
    .copyProperties(image,['system:time_start']);
}
function gediQuality(image) {
  var agb=image.select('agbd');
  var se=image.select('agbd_se');
  var good=image.select('l4_quality_flag').eq(1)
    .and(image.select('degrade_flag').eq(0))
    .and(agb.gt(0)).and(agb.lt(600))
    .and(se.gte(0)).and(se.divide(agb).lte(0.5));
  return image.select(['agbd','agbd_se']).updateMask(good);
}
var dem=ee.Image('USGS/SRTMGL1_003').select('elevation');
var terrain=dem.addBands(ee.Terrain.slope(dem).rename('slope'));

function extractMonth(index) {
  index=ee.Number(index);
  var from=startOfYear.advance(index,'month');
  var to=from.advance(1,'month');
  var s2=ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
    .filterBounds(AOI)
    .filterDate(from.advance(-CLOUD_WINDOW_DAYS,'day'),
                to.advance(CLOUD_WINDOW_DAYS,'day'))
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE',85))
    .map(sentinelMask).median();
  var veg=s2.normalizedDifference(['B8','B4']).rename('ndvi')
    .addBands(s2.normalizedDifference(['B8','B11']).rename('ndmi'))
    .addBands(s2.normalizedDifference(['B8A','B5']).rename('ndre'));
  var gedi=ee.ImageCollection('LARSE/GEDI/GEDI04_A_002_MONTHLY')
    .filterBounds(AOI).filterDate(from,to).map(gediQuality).mosaic();
  var stack=s2.addBands(veg).addBands(terrain).addBands(gedi);
  if(APPLY_TREE_MASK) stack=stack.updateMask(treeMask);
  var samples=stack.sample({
    region:AOI,projection:PROJECTION,scale:25,
    numPixels:SAMPLES_PER_MONTH,seed:2022,
    geometries:true,dropNulls:true,tileScale:8
  });
  return samples.map(function(f) {
    var xy=f.geometry().coordinates();
    return f.set({longitude:xy.get(0),latitude:xy.get(1),
      reference_month:from.format('YYYY-MM'),
      reference_product:'GEDI_L4A_V2_1_EE_MONTHLY',
      sentinel_window_days:CLOUD_WINDOW_DAYS,
      tree_mask_2021:APPLY_TREE_MASK?1:0}).setGeometry(null);
  });
}
// Use a constant PRNG seed for server-side iteration; monthly source images differ.
var months=ee.List.sequence(0,11);
var monthlyCollections=months.map(extractMonth);
var all=ee.FeatureCollection(monthlyCollections).flatten();
print('Candidate count for '+YEAR,all.size());
print('First candidate',all.first());
// Diagnostic monthly sample counts, computed lazily on server.
var monthlyCounts=ee.FeatureCollection(months.map(function(i){
  i=ee.Number(i);
  return ee.Feature(null,{month:startOfYear.advance(i,'month').format('YYYY-MM'),
    count:ee.FeatureCollection(monthlyCollections.get(i)).size()});
}));
print('Per-month valid sample counts',monthlyCounts);
var rgb=ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
  .filterBounds(AOI).filterDate(startOfYear,startOfYear.advance(1,'year'))
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE',65))
  .map(sentinelMask).median();
Map.addLayer(rgb.clip(AOI),{bands:['B4','B3','B2'],min:.02,max:.3},'Sentinel-2 annual RGB');
Export.table.toDrive({
  collection:all,
  description:'carbonfusion_gedi_s2_'+YEAR+'_expanded',
  folder:'CarbonFusionAI',
  fileNamePrefix:'carbonfusion_gedi_s2_'+YEAR+'_expanded',
  fileFormat:'CSV',
  selectors:['longitude','latitude','reference_month','reference_product',
    'sentinel_window_days','tree_mask_2021','agbd','agbd_se']
    .concat(BANDS).concat(['ndvi','ndmi','ndre','elevation','slope'])
});
// Warnings: raster-cell centers are NOT shot centroids; mosaics can obscure
// multiple observations, and WorldCover 2021 is not an invariant forest label.
// For publication, use direct footprint-level GEDI joins, independent plot data,
// and blocked/buffered spatial CV.
