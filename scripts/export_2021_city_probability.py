"""Export one city of the Jiangsu 2021 direct pooled RF probability workflow.

The private boundary and training assets are supplied by the researcher at runtime.
No sample coordinates or credentials are distributed with this repository.
"""

import argparse
import json
import sys
from pathlib import Path

import ee

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tea_features import build_v5_feature_image  # noqa: E402


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="Registered Earth Engine Cloud project")
    parser.add_argument("--boundary-asset", required=True, help="FeatureCollection with a name property")
    parser.add_argument("--city-name", required=True, help="Exact name in the boundary asset")
    parser.add_argument("--training-assets", required=True, type=Path, help="JSON array of FeatureCollection asset IDs")
    parser.add_argument("--output-asset", required=True, help="New image asset ID")
    parser.add_argument("--description", required=True, help="Unique Earth Engine task description")
    parser.add_argument("--check-only", action="store_true", help="Check configuration, boundary and output name without export")
    return parser.parse_args()


def main():
    args = parse_args()
    config = json.loads((ROOT / "config/jiangsu_2021_rf.json").read_text())
    training_ids = json.loads(args.training_assets.read_text())
    if not isinstance(training_ids, list) or not training_ids or not all(
        isinstance(asset_id, str) and asset_id for asset_id in training_ids
    ):
        raise ValueError("training-assets must be a nonempty JSON array of asset IDs")
    if len(config["selected_bands"]) != config["feature_count"] or config["image_year"] != 2021:
        raise ValueError("Invalid 2021 model configuration")

    ee.Initialize(project=args.project)
    try:
        ee.data.getAsset(args.output_asset)
    except ee.EEException as exc:
        if "does not exist" not in str(exc).lower():
            raise
    else:
        raise ValueError(f"Output asset already exists: {args.output_asset}")

    city_fc = ee.FeatureCollection(args.boundary_asset).filter(ee.Filter.eq("name", args.city_name))
    if city_fc.size().getInfo() != 1:
        raise ValueError(f"Expected one boundary named {args.city_name}")
    if args.check_only:
        print(json.dumps({"city": args.city_name, "training_shards": len(training_ids),
                          "bands": len(config["selected_bands"]), "year": 2021,
                          "output_asset": args.output_asset}, ensure_ascii=False))
        return

    region = city_fc.geometry()
    bands = config["selected_bands"]
    params = config["rf_params"]
    features = build_v5_feature_image(region.bounds(), selected_bands=bands, year=2021)
    training = ee.FeatureCollection([ee.FeatureCollection(asset_id) for asset_id in training_ids]).flatten()
    classifier = (
        ee.Classifier.smileRandomForest(
            numberOfTrees=int(params["numberOfTrees"]),
            variablesPerSplit=int(params["variablesPerSplit"]),
            minLeafPopulation=int(params["minLeafPopulation"]),
            bagFraction=float(params["bagFraction"]),
            seed=int(config["seed"]),
        )
        .setOutputMode("MULTIPROBABILITY")
        .train(training, "landcover", bands)
    )
    tea_probability = (
        features.classify(classifier)
        .arrayFlatten([[f"p_class_{value}" for value in config["class_order"]]])
        .select("p_class_1").multiply(10000).round().toUint16().rename("p_tea_x10000")
    )
    tree_reference = (
        ee.ImageCollection("ESA/WorldCover/v200").first().select("Map")
        .eq(10).toUint16().rename("esa_tree_2021")
    )
    output = ee.Image.cat([tea_probability, tree_reference]).clip(region)
    task = ee.batch.Export.image.toAsset(
        image=output,
        description=args.description,
        assetId=args.output_asset,
        region=region,
        crs=config["export_crs"],
        scale=config["export_scale_m"],
        maxPixels=1e13,
        pyramidingPolicy={".default": "mean", "esa_tree_2021": "mode"},
    )
    task.start()
    print(json.dumps({"city": args.city_name, "image_year": 2021,
                      "output_asset": args.output_asset, "task_id": task.id,
                      "initial_status": task.status()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
