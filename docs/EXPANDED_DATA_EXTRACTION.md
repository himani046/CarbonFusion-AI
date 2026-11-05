# Larger Real GEDI + Sentinel-2 Extraction (v2)

## Why the first export was small
The first 2022 export returned only **11 quality-filtered raster samples**, across six 0.08° blocks. This is sufficient to test the extraction schema but not for model training. The script was originally configured for a relatively small region and 1,500 requested samples per month.

## How to use the upgraded script
Open **earth_engine/export_expanded_samples.js** in the Earth Engine Code Editor. It:
- Extends the *illustrative* rectangle to `[85.8,21.2,87.3,22.7]` near the Similipal landscape.
- Keeps **one year per export** to avoid unnecessary timeouts.
- Requests up to **25,000** sampled cells per month (the number retained after masking may be much smaller).
- Optionally applies ESA WorldCover 2021 **tree cover class 10** as a baseline tree mask.
- Preserves sample month and study assumptions.
- Prints a total valid-sample count and an Earth Engine **per-month count table**.

### Start with 2022
1. Paste the upgraded script into Earth Engine and click **Run**.
2. Inspect `Candidate count for 2022` and `Per-month valid sample counts` in Console. Expand the table to see each month. Counts may be expensive to compute on a large study region.
3. In **Tasks**, click **RUN** for `carbonfusion_gedi_s2_2022_expanded`.
4. Download the exported CSV from Drive.
5. If needed, change `YEAR = 2023` (or 2021), re-run and export a *separate file*.
6. For timeouts or high processing costs, reduce `SAMPLES_PER_MONTH` to 5000, shrink the AOI, or process fewer months.

**Important:** larger samples do not guarantee valid forest samples. 2021 WorldCover is an imperfect proxy for tree cover and may omit real forests or include later-cleared areas. The exporter uses GEDI L4A Version 2.1 raster-month mosaics, and sample coordinates are 25m raster cell centers, not original GEDI laser footprint centroids. Data must be independently reviewed.

## Validate multiple exports and merge locally
From repo root:
```bash
mkdir -p data
# Move exported files into data/ and then:
python -m scripts.merge_real_exports --inputs data/carbonfusion_gedi_s2_2022_expanded.csv data/carbonfusion_gedi_s2_2023_expanded.csv --output data/real_samples.csv
python -m scripts.validate_real_data --input data/real_samples.csv
python -m scripts.train --input data/real_samples.csv --output outputs/real
```

The merge utility requires a consistent schema, rejects completely duplicated rows, and reports total and per-year counts. Never blindly merge multiple Earth Engine exports without checking footprint/sample duplication across periods.

The configured trainer requires **at least eight geographic blocks**, and the validator requires **100 valid rows** as a minimal software guard. Neither threshold guarantees publishable results. To support a scientific paper, prioritize footprint/time colocation, geographic independence, field validation and uncertainty propagation.

## Model deployment
```bash
CARBONFUSION_OUTPUT_DIR="$(pwd)/outputs/real" CARBONFUSION_DATA_MODE=real \
python -m uvicorn backend.main:app --reload --port 8001
```
Restart Nuxt after confirming `frontend/.env` points to port 8001.

## What this does NOT do yet
It does not download Earth Engine exports on your behalf, prove training accuracy against field observations, generate a continuous raster of carbon density or predict future deforestation. Those are separate implementation/research milestones.
