// CarbonFusion AI — Month-matched GEDI L4A / Sentinel-2 sample extraction
// Run in https://code.earthengine.google.com/ (Earth Engine access required).
//
// Scope: research *prototype* for real, quality-filtered observations.
// Sentinel features are composited within +/-45 days of each GEDI month,
// NOT shot-level exact-time or GEDI-footprint geometry matching.
// Study extent is an illustrative rectangular selection near Similipal,
// NOT an official forest boundary. Revisit AOI and forest mask for publication.

var aoi = ee.Geometry.Rectangle([86.25, 21.65, 86.65, 22.05]);
var firstMonth = ee.Date('2022-01-01');
var monthCount = 12;
var bands = ['B2','B3','B4','B5','B6','B7','B8','B8A','B11','B12'];
var utmProjection = ee.Projection('EPSG:32645').atScale(25);
Map.centerObject(aoi, 10);
Map.addLayer(aoi,{color:'yellow'},'Illustrative study extent');

function maskSentinel(im) {
  var scl = im.select('SCL');
  // SCL: no data(0), saturated(1), shadow(3), cloud(8-10), snow(11).
  var clear = scl.neq(0).and(scl.neq(1)).and(scl.neq(3))
    .and(scl.neq(8)).and(scl.neq(9)).and(scl.neq(10)).and(scl.neq(11));
  return im.updateMask(clear).select(bands).multiply(0.0001)
    .copyProperties(im, ['system:time_start']);
}
function qualityGedi(im) {
  var valid = im.select('l4_quality_flag').eq(1)
    .and(im.select('degrade_flag').eq(0))
    .and(im.select('agbd').gt(0))
    .and(im.select('agbd').lt(600))
    .and(im.select('agbd_se').gte(0))
    .and(im.select('agbd_se').divide(im.select('agbd')).lte(0.5));
  return im.select(['agbd','agbd_se']).updateMask(valid);
}
var dem = ee.Image('USGS/SRTMGL1_003').select('elevation').rename('elevation');
var terrain = dem.addBands(ee.Terrain.slope(dem).rename('slope'));

function samplesForMonth(idx) {
  idx=ee.Number(idx);
  var start=firstMonth.advance(idx,'month');
  var stop=start.advance(1,'month');
  var s2=ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
    .filterBounds(aoi)
    .filterDate(start.advance(-45,'day'),stop.advance(45,'day'))
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE',80))
    .map(maskSentinel).median();
  var ndvi=s2.normalizedDifference(['B8','B4']).rename('ndvi');
  var ndmi=s2.normalizedDifference(['B8','B11']).rename('ndmi');
  var ndre=s2.normalizedDifference(['B8A','B5']).rename('ndre');
  var gedi=ee.ImageCollection('LARSE/GEDI/GEDI04_A_002_MONTHLY')
    .filterBounds(aoi).filterDate(start,stop).map(qualityGedi).mosaic();
  var stack=s2.addBands([ndvi,ndmi,ndre,terrain,gedi]);
  var points=stack.sample({
    region:aoi, projection:utmProjection, scale:25,
    numPixels:1500, seed:42, geometries:true, tileScale:4,
    dropNulls:true
  });
  return points.map(function(f) {
    var xy=f.geometry().coordinates();
    return f.set({
      longitude:xy.get(0),latitude:xy.get(1),
      reference_month:start.format('YYYY-MM'),
      reference_product:'GEDI_L4A_V2_1_EE_MONTHLY',
      sentinel_window_days:45
    }).setGeometry(null);
  });
}

var months=ee.List.sequence(0,monthCount-1);
var samples=ee.FeatureCollection(months.map(samplesForMonth)).flatten();
print('Quality-filtered candidate samples across 2022',samples.size());
print('First candidate',samples.first());
var preview=ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
  .filterBounds(aoi).filterDate('2022-01-01','2023-01-01')
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE',65))
  .map(maskSentinel).median();
Map.addLayer(preview,{bands:['B4','B3','B2'],min:0.02,max:0.3},'Sentinel-2 RGB 2022');

Export.table.toDrive({
  collection:samples,
  description:'carbonfusion_real_gedi_s2_monthmatched_2022',
  folder:'CarbonFusionAI',fileFormat:'CSV',
  selectors:['longitude','latitude','reference_month','reference_product','sentinel_window_days',
    'agbd','agbd_se'].concat(bands)
    .concat(['ndvi','ndmi','ndre','elevation','slope'])
});

// Notes:
// (1) Data coverage ends according to current Earth Engine catalog; use covered months.
// (2) Preserve temporal metadata, inspect disturbed / nonforest samples and shot overlap.
// (3) Exported coordinates are sampled raster-cell centers, not GEDI exact footprint locations.
// (4) Independent field data and improved geographic CV remain research requirements.
