# CarbonFusion AI: 2018–2026 observation window

## Data availability (checked 2026-11-05)

**Requested calendar window: 2018 through 2026 (inclusive).** For this particular **GEDI L4A Version 2.1 monthly raster collection**, the Google Earth Engine catalog currently reports **2019-03-25 to 2025-07-01**. There are **no 2018 or 2026 GEDI biomass labels in this product**. Sentinel-2 imagery from 2018 and 2026 can still be useful for separate optical-only historical baselines or predictions, but **must never be presented as paired GEDI training samples**.

GEDI was suspended March 2023–April 2024; therefore some months have no GEDI acquisitions. The script safely handles empty monthly GEDI collections.

- Dataset catalog: https://developers.google.com/earth-engine/datasets/catalog/LARSE_GEDI_GEDI04_A_002_MONTHLY
- GEDI mission timeline: https://gedi.umd.edu/mission/timeline/

## How to run

Open `earth_engine/export_2018_2026_window.js` in Google Earth Engine Code Editor. It makes up to **seven annual CSV export tasks**, for **2019, 2020, 2021, 2022, 2023, 2024 and 2025**. It prints valid candidate counts per year and monthly diagnostics.

Unlike the earlier random-in-area approach, this script uses `stratifiedSample()` on a **GEDI-valid mask**. This preferentially samples pixels with a valid GEDI L4A label and should sharply reduce wasted samples from GEDI-empty parts of the area; it does not guarantee any particular count.

Earth Engine tasks do **not** start automatically: go to **Tasks** and click **RUN** for each desired export.

### Avoid Earth Engine timeouts

For a first test change `YEARS` to `[2022]`; if it runs, try `[2019,2020]` and so on. Lower `TARGET_POINTS_PER_MONTH` (3000 by default) to 1000 for quota pressure, or narrow AOI. Counts themselves may take substantial computation time. Each export is separate to allow reruns and incremental downloads.

The original small 2022 CSV can remain in `data/` but should **not** be combined with the new 2022 targeted export without reviewing overlap.

## Merge downloaded CSV files (local project root)

```bash
mkdir -p data
python -m scripts.merge_real_exports \
  --inputs data/carbonfusion_gedi_s2_2019_targeted.csv \
           data/carbonfusion_gedi_s2_2020_targeted.csv \
           data/carbonfusion_gedi_s2_2021_targeted.csv \
           data/carbonfusion_gedi_s2_2022_targeted.csv \
           data/carbonfusion_gedi_s2_2023_targeted.csv \
           data/carbonfusion_gedi_s2_2024_targeted.csv \
           data/carbonfusion_gedi_s2_2025_targeted.csv \
  --output data/real_samples.csv
python -m scripts.validate_real_data --input data/real_samples.csv
python -m scripts.train --input data/real_samples.csv --output outputs/real
```

Use only filenames that were actually exported. The merge utility removes duplicate raster-cell/month pairs, but **does not** establish original GEDI shot independence.

## Scientific limitations

- The Google monthly raster uses **GEDI L4A modeled biomass**, not independent ground truth.
- Raster-sampling coordinates are **not original GEDI shot centers**; the 25m pixel may have mixed observations.
- Sentinel-2 is median-composited within the surrounding period, not acquired at the exact GEDI shot instant.
- ESA WorldCover 2021 trees class is a static approximate forest mask, not a time-consistent land cover mask for 2019–2025.
- Quality-filtered samples may be uneven across months, blocks and forest types. Repeated nearby pixels create spatial dependence.
- These limitations must be addressed for scientifically publishable area-wide carbon inference.

The script does not currently create optical-only 2018/2026 prediction maps. That requires a trained model and a separate inference workflow.
