"""Build the frozen 2° India-land regional GeoJSON and web grid from audited IMD pilot files."""

from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import xarray as xr

from _run_context import ROOT, emit
from bust.data.regions import (
    compute_region_coverage,
    generate_candidate_lattice,
)

IMD_DIR = ROOT / "data/raw/imd"
FILE_2017 = IMD_DIR / "ind2017_rfp25.nc"
FILE_2018 = IMD_DIR / "ind2018_rfp25.nc"
OUTPUT_GEOJSON = ROOT / "config/regions_2deg.geojson"
OUTPUT_WEB_JSON = ROOT / "web/src/regions_grid.json"


def main() -> None:
    emit("build_regions", "config/regions_2deg.geojson", manifest_id="imd-2017-pilot; imd-2018-pilot")

    if not FILE_2017.exists() or not FILE_2018.exists():
        raise FileNotFoundError(
            f"Audited pilot files not found. Expected {FILE_2017} and {FILE_2018}."
        )

    # 1. Open datasets and verify coordinates
    with xr.open_dataset(FILE_2017) as ds17, xr.open_dataset(FILE_2018) as ds18:
        lats17 = ds17["LATITUDE"].values
        lons17 = ds17["LONGITUDE"].values
        lats18 = ds18["LATITUDE"].values
        lons18 = ds18["LONGITUDE"].values

        if not np.array_equal(lats17, lats18):
            raise ValueError("Latitude coordinates between 2017 and 2018 differ")
        if not np.array_equal(lons17, lons18):
            raise ValueError("Longitude coordinates between 2017 and 2018 differ")

        # Verify exact 0.25° spacing and boundaries
        if len(lats17) != 129:
            raise ValueError(f"Expected 129 lat points; got {len(lats17)}")
        if len(lons17) != 135:
            raise ValueError(f"Expected 135 lon points; got {len(lons17)}")
        if not (np.isclose(lats17[0], 6.5) and np.isclose(lats17[-1], 38.5)):
            raise ValueError(f"Unexpected latitude boundary: [{lats17[0]}, {lats17[-1]}]")
        if not (np.isclose(lons17[0], 66.5) and np.isclose(lons17[-1], 100.0)):
            raise ValueError(f"Unexpected longitude boundary: [{lons17[0]}, {lons17[-1]}]")

        diffs_lat = np.diff(lats17)
        diffs_lon = np.diff(lons17)
        if not np.allclose(diffs_lat, 0.25):
            raise ValueError("Latitude grid spacing is not uniformly 0.25°")
        if not np.allclose(diffs_lon, 0.25):
            raise ValueError("Longitude grid spacing is not uniformly 0.25°")

        # 2. Derive and compare static land masks across all days
        rf17 = ds17["RAINFALL"].values
        rf18 = ds18["RAINFALL"].values

        mask17_all = ~np.isnan(rf17)
        mask18_all = ~np.isnan(rf18)

        # Static invariant: land mask must be invariant across all days within each year
        mask17_static = mask17_all[0]
        mask18_static = mask18_all[0]

        if not np.array_equal(mask17_all.all(axis=0), mask17_all.any(axis=0)):
            raise RuntimeError("2017 land mask varies across days")
        if not np.array_equal(mask18_all.all(axis=0), mask18_all.any(axis=0)):
            raise RuntimeError("2018 land mask varies across days")
        if not np.array_equal(mask17_static, mask18_static):
            raise RuntimeError("Land mask changed between 2017 and 2018")

        total_land_points = int(np.sum(mask17_static))
        if total_land_points != 4964:
            raise ValueError(f"Expected 4,964 land points; got {total_land_points}")

    # 3. Generate candidate lattice (15 lat centers 8..36 x 16 lon centers 68..98)
    lattice = generate_candidate_lattice()
    if len(lattice) != 240:
        raise ValueError(f"Expected 240 lattice cells; got {len(lattice)}")

    features = []
    supported_count = 0
    peripheral_count = 0
    partitioned_points = 0

    for reg in lattice:
        cov = compute_region_coverage(reg, lats17, lons17, mask17_static, nominal_points_per_cell=64)
        valid_pts = cov["valid_points"]
        fraction = cov["coverage_fraction"]

        if valid_pts == 0:
            continue  # Discard ocean cells

        is_supported = cov["has_sufficient_coverage"]  # >= 0.80
        if is_supported:
            supported_count += 1
        else:
            peripheral_count += 1

        partitioned_points += valid_pts

        feat = reg.to_geojson_feature(
            {
                "land_points": valid_pts,
                "total_points": 64,
                "coverage_fraction": round(fraction, 4),
                "is_land_supported": is_supported,
            }
        )
        features.append(feat)

    # 4. Invariant checks
    # The audited IMD grid terminates at 38.5°N. The 13 observed land points in the clipped
    # northern source edge ([37.0, 38.5]°N) are excluded because no complete 2° source cell exists there.
    # Every included region in the frozen lattice has an exact, complete 8x8 = 64-point IMD geometry.
    expected_partitioned_points = 4964 - 13  # 4,951 land points
    if partitioned_points != expected_partitioned_points:
        raise ValueError(
            f"Partition mismatch: partitioned {partitioned_points} points vs expected {expected_partitioned_points} "
            f"(total IMD points: {total_land_points}, excluded northern edge points: 13)"
        )
    if len(features) != 112:
        raise ValueError(f"Expected 112 regions; got {len(features)}")
    if supported_count != 65:
        raise ValueError(f"Expected 65 supported regions; got {supported_count}")
    if peripheral_count != 47:
        raise ValueError(f"Expected 47 peripheral regions; got {peripheral_count}")

    geojson_payload = {
        "type": "FeatureCollection",
        "description": "Fixed 2-degree India-land region definitions partitioned from audited IMD 0.25° grid.",
        "geometry_contract": "half_open_lat_lon_box [center-1, center+1)",
        "features": features,
    }

    # 5. Write source-of-truth config/regions_2deg.geojson
    formatted_json = json.dumps(geojson_payload, indent=2)
    OUTPUT_GEOJSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_GEOJSON.write_text(formatted_json + "\n", encoding="utf-8")
    print(f"wrote_source_of_truth={OUTPUT_GEOJSON}")

    # 6. Generate web/src/regions_grid.json from source-of-truth
    OUTPUT_WEB_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_WEB_JSON.write_text(formatted_json + "\n", encoding="utf-8")
    print(f"wrote_web_asset={OUTPUT_WEB_JSON}")
    print(
        f"summary: total_regions={len(features)} (supported={supported_count}, peripheral={peripheral_count}), "
        f"land_points={partitioned_points}/4964 ({partitioned_points/4964*100:.2f}%; 13 northern-edge points excluded)"
    )


if __name__ == "__main__":
    main()
