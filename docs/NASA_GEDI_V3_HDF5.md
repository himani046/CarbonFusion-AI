# Direct NASA GEDI L4A V3 footprint extraction

## What this solves

Avoids the **Google Earth Engine export quota** for the GEDI *reference-label acquisition* step. Uses user-downloaded NASA GEDI L4A V3 footprint HDF5 granules, rather than sparse raster-cell sampling from Earth Engine.

## First HDF5 file

User-tested granule filename: `GEDI04_A_2022001173830_O17305_02_T00880_02_004_01_V003.h5`.

This repository does **not** contain the actual file. Download it from NASA Earthdata (requires NASA authentication), then place it in `data/gedi_raw/`. Do not commit large raw satellite files to Git.

## Install and run

```bash
pip install h5py pandas numpy
mkdir -p data/gedi_raw outputs
# Move .h5 granule files to data/gedi_raw/
python -m scripts.extract_gedi_l4a_v3 --inputs data/gedi_raw \
  --output data/gedi_v3_footprints.csv \
  --report outputs/gedi_v3_extraction_report.json
```

The script processes all beam groups it finds. It reads beam footprint arrays, filters to lon 85.8–87.3 E / lat 21.2–22.7 N, and applies `l4_quality_flag=1`, `degrade_flag=0`, `0<agbd<600`, `agbd_se>=0`, and `agbd_se/agbd<=0.5`. It writes a detailed **per-beam diagnostic report** including paths to discovered datasets and row counts.

Inspect this report before interpreting an empty result: NASA CMR metadata gives a **granule/orbit intersection**, not a guarantee that a particular beam has valid footprints in your region. Beam datasets vary between product versions; diagnostics flag missing fields rather than silently inventing data.

### Important research limitations
- The labels are NASA **modeled biomass predictions** and their uncertainties, not new ground field measurements.
- This output is **GEDI-only**. It does not contain Sentinel-2 bands, NDVI, NDMI or NDRE. **Do not run `scripts.train` on it directly.**
- For training CarbonFusion AI, implement an accurate footprint-level Sentinel-2 spatial/temporal join and then validate geographic holdouts; the existing training schema assumes optical bands.
- The `observation_date` column records the **granule start date in year/day-of-year format** as traceable metadata; precise shot time is in `delta_time` and requires conversion using NASA's epoch definition. It must not be represented as a per-shot timestamp.
- Large full-orbit .h5 granules can be hundreds of MB; using only intersecting footprints saves output size but full files are downloaded.
- GEDI L4A V3 labels are **not interchangeable** with GEDI L4A V2.1; do not silently mix versions.

### NASA search and documentation
- [NASA CMR API](https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html)
- [GEDI L4A V3 product](https://doi.org/10.3334/ORNLDAAC/2508)
- [V3 data dictionary](https://data.ornldaac.earthdata.nasa.gov/public/gedi/GEDI_L4A_AGB_Density_V3/comp/GEDI_L4A_V3_Product_Data_Dictionary.pdf)

## Expected CSV schema

`latitude, longitude, agbd, agbd_se, l4_quality_flag, degrade_flag, shot_number, delta_time, beam, source_granule, reference_product, observation_date` (optional fields may be absent according to the source HDF5).

Output may legitimately be empty for a particular granule; download additional intersecting granules.
