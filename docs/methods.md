# Method and limitations

- **Image year:** 2021, passed explicitly to the feature builder. Sentinel-2 SR Harmonized scenes are filtered to 2021 and screened with Cloud Score+ `cs_cdf >= 0.58`; Sentinel-1 GRD VV/VH annual medians and SRTM terrain are auxiliary features. The canopy-height asset represents 2020.
- **Features and model:** 41 selected bands from 72 candidate seasonal, temporal-difference, radar, texture, terrain, and canopy variables; 100-tree, four-class random forest with `variablesPerSplit=6`, `minLeafPopulation=1`, `bagFraction=0.632`, seed 42. The source configuration used in this public workflow excludes older model metrics that do not evaluate this 2021 province-wide export.
- **Training:** 19,706 manually interpreted records from five cities were joined to 2021 feature tables by stable `point_id` and checked for matching coordinates before uploading as 16 FeatureCollection shards. These records are not shared here.
- **Output:** one 10 m EPSG:32650 image per city, with probability scaled to 0–10,000 and a separate WorldCover tree reference band. No tea probability threshold or WorldCover hard mask is applied at export.
- **Validation:** leave-one-city-out checks of the available five-city training population were exploratory transfer tests. They do not establish independent accuracy for the other eight cities. A 2023 validation label is not automatically valid ground truth for 2021 imagery.
- **Area:** threshold sensitivity and final area accounting must sum `ee.Image.pixelArea()` under a specified projection and region. A fixed 100 m² per pixel must not be assumed for arbitrary geographic rasters. Map extent and tea area are not interchangeable.
- **Environmental interpretation:** a tea map alone does not measure carbon sequestration, biodiversity change, deforestation, or policy impact. Those require separate change analysis, reference data, and validation.

The feature expressions in `src/tea_features.py` were extracted from the original research engine. The command-line export script exposes the input assets and Cloud project rather than embedding private research asset IDs.
