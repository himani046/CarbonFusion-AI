// CarbonFusion AI: annual Landsat vegetation history, 2000–2026 inclusive.
// Paste into https://code.earthengine.google.com/ and run.
// This export measures spectral vegetation indicators, NOT historical carbon stock.
// 2026 ends on 2026-11-05 and is therefore a PARTIAL year.
// AOI is an illustrative study rectangle around the Similipal landscape, not a
// legally verified forest boundary. Cloud masking and cross-sensor harmonization
// require further validation for publication.

var AOI = ee.Geometry.Rectangle([85.8, 21.2, 87.3, 22.7]);
var START_YEAR = 2000;
var END_YEAR = 2026;
var LAST_DATE_EXCLUSIVE = '2026-11-06';
var PIXEL_SCALE = 30;
var COMMON = ['blue', 'green', 'red', 'nir', 'swir1', 'swir2'];
Map.centerObject(AOI, 8);
Map.addLayer(AOI, {color:'yellow'}, 'Study rectangle');

function qaMask(img) {
  var qa = img.select('QA_PIXEL');
  // Bits 0 fill, 1 dilated cloud, 2 cirrus, 3 cloud, 4 cloud shadow,
  // 5 snow. Clear if all are 0. Saturated pixels removed too.
  var clear = qa.bitwiseAnd(1).eq(0)
    .and(qa.bitwiseAnd(1 << 1).eq(0))
    .and(qa.bitwiseAnd(1 << 2).eq(0))
    .and(qa.bitwiseAnd(1 << 3).eq(0))
    .and(qa.bitwiseAnd(1 << 4).eq(0))
    .and(qa.bitwiseAnd(1 << 5).eq(0))
    .and(img.select('QA_RADSAT').eq(0));
  return img.updateMask(clear);
}
function prep57(img) {
  return qaMask(img)
    .select(['SR_B1','SR_B2','SR_B3','SR_B4','SR_B5','SR_B7'], COMMON)
    .multiply(0.0000275).add(-0.2)
    .copyProperties(img, ['system:time_start']);
}
function prep89(img) {
  return qaMask(img)
    .select(['SR_B2','SR_B3','SR_B4','SR_B5','SR_B6','SR_B7'], COMMON)
    .multiply(0.0000275).add(-0.2)
    .copyProperties(img, ['system:time_start']);
}
function collection(id, start, end, processor) {
  return ee.ImageCollection(id).filterBounds(AOI).filterDate(start, end)
    .map(processor);
}
function annual(year) {
  year = ee.Number(year);
  var start = ee.Date.fromYMD(year, 1, 1);
  var end = ee.Date.fromYMD(year.add(1), 1, 1);
  end = ee.Date(ee.Algorithms.If(year.eq(2026), ee.Date(LAST_DATE_EXCLUSIVE), end));

  // Landsat 5/7/8/9 Tier 1 Level 2. Empty collections are harmless.
  var l5 = collection('LANDSAT/LT05/C02/T1_L2', start, end, prep57);
  var l7 = collection('LANDSAT/LE07/C02/T1_L2', start, end, prep57);
  var l8 = collection('LANDSAT/LC08/C02/T1_L2', start, end, prep89);
  var l9 = collection('LANDSAT/LC09/C02/T1_L2', start, end, prep89);
  var images = l5.merge(l7).merge(l8).merge(l9);
  var count = images.size();
  // Named bands ensure the annual median remains defined when data absent.
  var empty = ee.Image.constant([0,0,0,0,0,0])
    .rename(COMMON).updateMask(ee.Image(0));
  var composite = ee.Image(ee.Algorithms.If(count.gt(0), images.median(), empty));
  var ndvi = composite.normalizedDifference(['nir', 'red']).rename('ndvi');
  var ndmi = composite.normalizedDifference(['nir', 'swir1']).rename('ndmi');
  var nbr  = composite.normalizedDifference(['nir', 'swir2']).rename('nbr');
  var indices = ndvi.addBands(ndmi).addBands(nbr);
  var means = indices.reduceRegion({
    reducer: ee.Reducer.mean(),
    geometry: AOI,
    scale: PIXEL_SCALE,
    maxPixels: 1e9,
    tileScale: 8,
    bestEffort: true
  });
  var validArea = ee.Image.constant(1).updateMask(ndvi.mask())
    .multiply(ee.Image.pixelArea()).reduceRegion({
      reducer: ee.Reducer.sum(), geometry: AOI, scale: PIXEL_SCALE,
      maxPixels: 1e9, tileScale: 8, bestEffort: true
    }).get('constant');

  return ee.Feature(null, {
    year: year,
    year_status: ee.Algorithms.If(year.eq(2026), 'partial_through_2026_11_05', 'full_year'),
    satellite_scenes: count,
    mean_ndvi: means.get('ndvi'),
    mean_ndmi: means.get('ndmi'),
    mean_nbr: means.get('nbr'),
    valid_observed_area_ha: ee.Number(ee.Algorithms.If(validArea, validArea, 0)).divide(10000),
    region: 'illustrative_similipal_rectangle',
    data_source: 'USGS_Landsat_C2_L2_T1',
    outcome_type: 'vegetation_indices_not_carbon'
  });
}

var records = ee.FeatureCollection(ee.List.sequence(START_YEAR, END_YEAR).map(annual));
print('Annual Landsat records (should be 27):', records.size());
print('Yearly index results:', records);
print('Check 2026 is partial and compare sensor transitions separately.');
var chart = ui.Chart.feature.byFeature(records, 'year', ['mean_ndvi','mean_ndmi','mean_nbr'])
  .setChartType('LineChart')
  .setOptions({title:'Landsat vegetation indices 2000–2026 (2026 partial)',
               hAxis:{title:'Year'},vAxis:{title:'Mean index'}});
print(chart);
Export.table.toDrive({
  collection: records,
  description: 'carbonfusion_landsat_vegetation_2000_2026',
  fileNamePrefix:'carbonfusion_landsat_vegetation_2000_2026',
  folder:'CarbonFusionAI',
  fileFormat:'CSV',
  selectors:['year','year_status','satellite_scenes','mean_ndvi','mean_ndmi','mean_nbr',
    'valid_observed_area_ha','region','data_source','outcome_type']
});

// Interpretation precautions:
// 1. This uses scene-level median composites; no harmonization between TM,
//    ETM+ and OLI beyond matching corresponding spectral bands. Sensor/season
//    differences and Landsat 7 SLC-off artifacts can bias time-series trends.
// 2. NDVI/NDMI/NBR are vegetation indices; do not label them as carbon stock,
//    annual carbon loss or deforestation without validation and classifications.
// 3. Valid observed area may change with cloud and sensor coverage.
// 4. No GEDI information exists before 2019; train biomass on modern GEDI
//    separately. Retrospective biomass backcasting is a new research experiment.
