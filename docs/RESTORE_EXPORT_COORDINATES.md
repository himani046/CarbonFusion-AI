# Restore missing coordinates in the 2022 GEDI + Sentinel-2 export

The first 1,263-row Sentinel-2 export has blank `longitude` and `latitude` properties, although the Earth Engine point geometries and optical values were present. The original `data/gedi_v3_footprints.csv` contains the correct coordinates. **Do not spend another Earth Engine export quota on a duplicate task**.

Download `real_samples (1).csv` into your Mac project `data/` directory.

```bash
git pull origin main
python -m scripts.restore_export_coordinates \
  --sentinel-csv 'data/real_samples (1).csv' \
  --gedi-csv data/gedi_v3_footprints.csv \
  --output data/real_samples.csv
python -m scripts.validate_real_data --input data/real_samples.csv
python -m scripts.train --input data/real_samples.csv --output outputs/real
```

The utility matches the pair `(shot_number, beam)`, refuses missing or duplicated keys, verifies the GEDI `agbd` and `agbd_se` values, bounds checks the resulting coordinates, validates required optical features and reports geographic block counts. It does **not** invent coordinates or modify imagery values.

**Research caveat:** All points originate from a single GEDI track and use a common Sentinel-2 composite. Geographic block splits from one flight line are not sufficient evidence of broader spatial generalization. Treat training metrics as *prototype-only* and acquire more independent granules/regions before reporting scientific performance.

For future Earth Engine exports, preserve coordinate properties explicitly before `sampleRegions`:
```javascript
var gediWithCoordinates = ee.FeatureCollection(gedi).map(function (f) {
  var xy = f.geometry().coordinates();
  return f.set({longitude: xy.get(0), latitude: xy.get(1)});
});
```
Use `gediWithCoordinates` as the `collection` for `sampleRegions`. This is a prevention fix; existing CSVs can be repaired locally using shot IDs.
