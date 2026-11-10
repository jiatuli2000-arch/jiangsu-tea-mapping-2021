# Jiangsu tea plantation mapping: 2021 research workflow

This repository documents the 10 m, 2021 tea plantation probability mapping workflow used for Jiangsu Province, China. The project is led by a student researcher at Nanjing Agricultural University with faculty supervision. It is a **research baseline**, not a validated operational tea plantation map.

## Current state

The research workflow exports one probability image for each of Jiangsu's 13 prefecture-level cities. The image has two bands: `p_tea_x10000` (tea-class probability multiplied by 10,000) and `esa_tree_2021` (an ESA WorldCover tree-class reference). The WorldCover band is not used as a hard mask. A probability threshold, independent province-wide accuracy assessment, final area estimate, and forest-conversion analysis are separate steps. See [methods and limitations](docs/methods.md) and [compute evidence](docs/compute_evidence.md).

## Reproduce the export with authorized assets

The original manually interpreted samples and administrative boundary asset are not distributed. The code can be run with a boundary FeatureCollection accessible to your Earth Engine account and one or more training FeatureCollections with the documented schema.

1. Install Python 3.12 and `pip install -r requirements.txt`; authenticate Earth Engine for your own registered Cloud project.
2. Prepare a boundary FeatureCollection with one feature per city and a `name` property. Prepare training FeatureCollections with `landcover` values 1–4 and all 41 bands in [`config/jiangsu_2021_rf.json`](config/jiangsu_2021_rf.json). Class 1 is tea; other classes represent non-tea comparison groups.
3. Copy [`examples/training_assets.example.json`](examples/training_assets.example.json) and replace the placeholder with your own training asset IDs.
4. Run one export, using your own project and asset IDs:

```bash
python scripts/export_2021_city_probability.py \
  --project YOUR_REGISTERED_PROJECT \
  --boundary-asset projects/YOUR_PROJECT/assets/jiangsu_cities \
  --city-name 南京市 \
  --training-assets training_assets.json \
  --output-asset projects/YOUR_PROJECT/assets/jiangsu_2021_nanjing_ptea \
  --description jiangsu_2021_nanjing_ptea \
  --check-only
```

`--check-only` checks the model configuration, boundary match and output name; it does not verify access to the listed training assets. Remove it after checking the training asset IDs and permissions. The export script refuses to overwrite an existing output asset. It explicitly builds 2021 imagery, trains a 100-tree random forest, and exports at 10 m in EPSG:32650. Earth Engine task submission is asynchronous; a submitted task is not a completed map.

## Data and provenance

The feature builder uses [Sentinel-2 SR Harmonized](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED), [Cloud Score+](https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_CLOUD_SCORE_PLUS_V1_S2_HARMONIZED), Sentinel-1 GRD, SRTM, a 2020 canopy-height asset, and the [2021 ESA WorldCover reference](https://developers.google.com/earth-engine/datasets/catalog/ESA_WorldCover_v200). The exact source image year and output year are 2021. The original workflow used 16 training-table shards containing 19,706 manually interpreted samples across five Jiangsu cities. Those were training inputs, not an independent province-wide accuracy set.

This repository intentionally contains no credentials, the researcher's GEE account identifiers, private asset IDs, sample coordinates, or full-resolution map rasters. The source code is visible for review; a reuse license has not yet been selected.
