// CarbonFusion AI — Earth Engine Code Editor JavaScript
// Proof-of-concept extraction only. Temporal / footprint matching must improve before publication.
// Broad illustrative rectangle near Similipal; NOT an official forest boundary.
var aoi = ee.Geometry.Rectangle([86.25, 21.65, 86.65, 22.05]);
var start = '2022-01-01', end = '2023-01-01';
Map.centerObject(aoi, 10);
Map.addLayer(aoi, {color:'yellow'}, 'Demo AOI');

var bands = ['B2','B3','B4','B5','B6','B7','B8','B8A','B11','B12'];
function maskS2(img) {
  var scl = img.select('SCL');
  var valid = scl.neq(0).and(scl.neq(1)).and(scl.neq(3))
    .and(scl.neq(8)).and(scl.neq(9)).and(scl.neq(10)).and(scl.neq(11));
  return img.updateMask(valid).select(bands).multiply(0.0001)
    .copyProperties(img, ['system:time_start']);
}
var s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
  .filterBounds(aoi).filterDate(start,end)
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE',70)).map(maskS2).median();
var ndvi = s2.normalizedDifference(['B8','B4']).rename('ndvi');
var ndmi = s2.normalizedDifference(['B8','B11']).rename('ndmi');
var ndre = s2.normalizedDifference(['B8A','B5']).rename('ndre');
var dem = ee.Image('USGS/SRTMGL1_003').select('elevation').rename('elevation');
var slope = ee.Terrain.slope(dem).rename('slope');
var predictors = s2.addBands([ndvi,ndmi,ndre,dem,slope]);

function gediQC(img) {
  var valid = img.select('l4_quality_flag').eq(1)
    .and(img.select('degrade_flag').eq(0))
    .and(img.select('agbd').gt(0))
    .and(img.select('agbd_se').gte(0))
    .and(img.select('agbd_se').divide(img.select('agbd')).lte(0.5));
  return img.select(['agbd','agbd_se']).updateMask(valid);
}
var gedi = ee.ImageCollection('LARSE/GEDI/GEDI04_A_002_MONTHLY')
   .filterBounds(aoi).filterDate(start,end).map(gediQC).mosaic();
var stack = predictors.addBands(gedi);
var samples = stack.sample({
  region:aoi, scale:25, projection:'EPSG:32645',
  numPixels:5000, seed:42, geometries:true, tileScale:4
});
samples = samples.map(function(f) {
  var pt = f.geometry().coordinates();
  return f.set({longitude:pt.get(0),latitude:pt.get(1)}).setGeometry(null);
});
print('Candidate samples',samples.size());
Map.addLayer(s2,{bands:['B4','B3','B2'],min:0,max:0.3},'Sentinel-2 RGB');
Map.addLayer(gedi.select('agbd'),{min:0,max:250,palette:['yellow','green','darkgreen']},'GEDI AGBD');
Export.table.toDrive({
  collection:samples,
  description:'carbonfusion_gedi_sentinel_samples_2022',
  folder:'CarbonFusionAI',fileFormat:'CSV',
  selectors:['longitude','latitude','agbd','agbd_se'].concat(bands)
    .concat(['ndvi','ndmi','ndre','elevation','slope'])
});
// Real-science upgrades:
// 1. GEDI footprint/time matching against Sentinel-2 observations.
// 2. Authoritative forest masks, forest type strata and sample QC.
// 3. Buffered spatial cross-validation and independent field validation.
// 4. Examine nonrandom GEDI footprint sampling and uncertainty.
