// CarbonFusion AI: multi-year GEDI L4A + Sentinel-2 candidate training export.
// Requested study window 2018–2026. GEDI L4A monthly Earth Engine catalog
// currently covers 2019-03-25 through 2025-07-01 (verify catalog for updates).
// 2018 and 2026 have Sentinel-2 but NO GEDI L4A monthly labels here.
// Run 1-2 years at a time if Earth Engine reaches computation/memory quotas.
// Outputs one CSV task per year. You must RUN tasks in the Tasks tab.
var YEARS = [2019,2020,2021,2022,2023,2024,2025];
var AOI = ee.Geometry.Rectangle([85.8,21.2,87.3,22.7]);
var TARGET_POINTS_PER_MONTH = 3000;
var CLOUD_WINDOW_DAYS = 45;
var APPLY_2021_TREE_MASK = true;
var BANDS = ['B2','B3','B4','B5','B6','B7','B8','B8A','B11','B12'];
var PROJECTION = ee.Projection('EPSG:32645').atScale(25);
var GEDI_ID='LARSE/GEDI/GEDI04_A_002_MONTHLY';
var GEDI_START=ee.Date('2019-03-25');
var GEDI_END_EXCLUSIVE=ee.Date('2025-07-02'); // cap at catalog availability
Map.centerObject(AOI,8);
Map.addLayer(AOI,{color:'yellow'},'Study rectangle (not official forest boundary)');
var tree=ee.ImageCollection('ESA/WorldCover/v200').first().select('Map').eq(10);
Map.addLayer(tree.selfMask().clip(AOI),{palette:['3da66b']},'2021 WorldCover trees',false);
var dem=ee.Image('USGS/SRTMGL1_003').select('elevation');
var terrain=dem.addBands(ee.Terrain.slope(dem).rename('slope'));

function clearSentinel(im) {
  var scl=im.select('SCL');
  var valid=scl.neq(0).and(scl.neq(1)).and(scl.neq(3))
    .and(scl.neq(8)).and(scl.neq(9)).and(scl.neq(10)).and(scl.neq(11));
  return im.updateMask(valid).select(BANDS).multiply(0.0001)
    .copyProperties(im,['system:time_start']);
}
function validGedi(im) {
  var agbd=im.select('agbd'), se=im.select('agbd_se');
  var valid=im.select('l4_quality_flag').eq(1)
    .and(im.select('degrade_flag').eq(0))
    .and(agbd.gt(0)).and(agbd.lt(600))
    .and(se.gte(0)).and(se.divide(agbd).lte(0.5));
  return im.select(['agbd','agbd_se']).updateMask(valid);
}
function monthSamples(year, monthIndex) {
  var from=ee.Date.fromYMD(year,1,1).advance(monthIndex,'month');
  var to=from.advance(1,'month');
  var s2=ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
    .filterBounds(AOI)
    .filterDate(from.advance(-CLOUD_WINDOW_DAYS,'day'),
                to.advance(CLOUD_WINDOW_DAYS,'day'))
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE',85))
    .map(clearSentinel).median();
  var veg=s2.normalizedDifference(['B8','B4']).rename('ndvi')
    .addBands(s2.normalizedDifference(['B8','B11']).rename('ndmi'))
    .addBands(s2.normalizedDifference(['B8A','B5']).rename('ndre'));
  var gediImages=ee.ImageCollection(GEDI_ID)
    .filterBounds(AOI)
    .filterDate(from.max(GEDI_START),to.min(GEDI_END_EXCLUSIVE))
    .map(validGedi);
  // The GEDI mission did not record measurements during part of 2023-24.
  // Empty collection fallback prevents mosaic().select() band failures.
  var empty=ee.Image.constant([0,0]).rename(['agbd','agbd_se'])
    .updateMask(ee.Image.constant(0));
  var gedi=ee.Image(ee.Algorithms.If(gediImages.size().gt(0),
    gediImages.mosaic(),empty));
  // Sample GEDI-valid pixels explicitly, instead of randomly selecting
  // almost entirely empty pixels from a very large study region.
  var gediValid=gedi.select('agbd').mask().unmask(0).rename('gedi_valid').toInt();
  var stack=s2.addBands(veg).addBands(terrain).addBands(gedi).addBands(gediValid);
  if(APPLY_2021_TREE_MASK) stack=stack.updateMask(tree);
  var fc=stack.stratifiedSample({
    numPoints:0,classBand:'gedi_valid',
    classValues:[1],classPoints:[TARGET_POINTS_PER_MONTH],
    region:AOI,projection:PROJECTION,scale:25,
    seed:42,tileScale:8,geometries:true,dropNulls:true
  });
  return fc.map(function(f) {
    var xy=f.geometry().coordinates();
    return f.set({
      longitude:xy.get(0),latitude:xy.get(1),
      reference_month:from.format('YYYY-MM'),
      reference_product:'GEDI_L4A_V2_1_EE_MONTHLY',
      sentinel_window_days:CLOUD_WINDOW_DAYS,
      tree_mask_2021:APPLY_2021_TREE_MASK ? 1 : 0
    }).setGeometry(null);
  });
}
var selectors=['longitude','latitude','reference_month','reference_product',
  'sentinel_window_days','tree_mask_2021','agbd','agbd_se']
  .concat(BANDS).concat(['ndvi','ndmi','ndre','elevation','slope']);
// Map monthly data collections server-side; export per year to reduce quotas.
YEARS.forEach(function(year) {
  var months=ee.List.sequence(0,11);
  var collections=months.map(function(i){return monthSamples(year,ee.Number(i));});
  var combined=ee.FeatureCollection(collections).flatten();
  print('Year '+year+' valid candidate count',combined.size());
  var monthStats=ee.FeatureCollection(months.map(function(i){
    i=ee.Number(i);
    return ee.Feature(null,{
      month:ee.Date.fromYMD(year,1,1).advance(i,'month').format('YYYY-MM'),
      count:ee.FeatureCollection(collections.get(i)).size()
    });
  }));
  print('Monthly counts '+year,monthStats);
  Export.table.toDrive({
    collection:combined,
    description:'carbonfusion_gedi_s2_'+year+'_targeted',
    fileNamePrefix:'carbonfusion_gedi_s2_'+year+'_targeted',
    folder:'CarbonFusionAI',fileFormat:'CSV',selectors:selectors
  });
});
// Research caveats: 25m raster cell centers are not exact GEDI footprint
// centers; modeled GEDI L4A targets are not field measurements; year-2021
// WorldCover mask is static and imperfect; need footprint-level joins,
// acquisition-date matching and independent field validation for publication.
