"""Fixed 2-degree India-land region lattice, coverage enforcement, and aggregation."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(frozen=True)
class RegionDefinition:
    region_id: str
    center_lat: float
    center_lon: float
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float
    coverage_fraction: float | None = None
    is_land_supported: bool | None = None

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        """Return (lat_min, lat_max, lon_min, lon_max)."""
        return (self.lat_min, self.lat_max, self.lon_min, self.lon_max)

    @property
    def geojson_geometry(self) -> dict[str, Any]:
        """Return GeoJSON Polygon geometry coordinates [lon, lat] closed counter-clockwise."""
        return {
            "type": "Polygon",
            "coordinates": [
                [
                    [self.lon_min, self.lat_min],
                    [self.lon_max, self.lat_min],
                    [self.lon_max, self.lat_max],
                    [self.lon_min, self.lat_max],
                    [self.lon_min, self.lat_min],
                ]
            ],
        }

    def to_geojson_feature(self, properties: dict[str, Any] | None = None) -> dict[str, Any]:
        props: dict[str, Any] = {
            "region_id": self.region_id,
            "center_lat": self.center_lat,
            "center_lon": self.center_lon,
            "lat_min": self.lat_min,
            "lat_max": self.lat_max,
            "lon_min": self.lon_min,
            "lon_max": self.lon_max,
        }
        if self.coverage_fraction is not None:
            props["coverage_fraction"] = self.coverage_fraction
        if self.is_land_supported is not None:
            props["is_land_supported"] = self.is_land_supported
        if properties:
            props.update(properties)
        return {
            "type": "Feature",
            "properties": props,
            "geometry": self.geojson_geometry,
        }


def has_sufficient_coverage(coverage_fraction: float | None, minimum: float = 0.80) -> bool:
    """Return True if coverage_fraction meets or exceeds the minimum threshold."""
    return coverage_fraction is not None and coverage_fraction >= minimum


def parse_region_id(region_id: str) -> tuple[float, float]:
    """Parse a deterministic region ID (e.g. 'R20N-078E') into (center_lat, center_lon)."""
    match = re.match(r"^R(\d{2})N-(\d{3})E$", region_id)
    if not match:
        raise ValueError(f"Invalid region ID format: {region_id!r}; expected 'R{{lat:02d}}N-{{lon:03d}}E'")
    return float(match.group(1)), float(match.group(2))


def create_region(
    center_lat: float,
    center_lon: float,
    coverage_fraction: float | None = None,
    is_land_supported: bool | None = None,
) -> RegionDefinition:
    """Create a 2° regular region box centered at (center_lat, center_lon).

    Cell boundaries are half-open intervals [center - 1.0, center + 1.0)
    to form a non-overlapping spatial partition on gridded data.
    """
    region_id = f"R{round(center_lat):02d}N-{round(center_lon):03d}E"
    lat_min = float(center_lat - 1.0)
    lat_max = float(center_lat + 1.0)
    lon_min = float(center_lon - 1.0)
    lon_max = float(center_lon + 1.0)
    return RegionDefinition(
        region_id=region_id,
        center_lat=float(center_lat),
        center_lon=float(center_lon),
        lat_min=lat_min,
        lat_max=lat_max,
        lon_min=lon_min,
        lon_max=lon_max,
        coverage_fraction=coverage_fraction,
        is_land_supported=is_land_supported,
    )


def generate_candidate_lattice(
    lat_centers: tuple[int, ...] = tuple(range(8, 38, 2)),
    lon_centers: tuple[int, ...] = tuple(range(68, 100, 2)),
) -> list[RegionDefinition]:
    """Generate all candidate 2° regular cells over the India regional domain.

    Default lattice spans center latitudes 8°N..36°N and longitudes 68°E..98°E in steps of 2°.
    center_lat=38 is excluded because the audited IMD grid terminates at 38.5°N, leaving incomplete 7x8 geometry.
    This produces 15x16 = 240 regular non-overlapping cells covering [7, 37)°N x [67, 99)°E.
    """
    regions = []
    for c_lat in sorted(lat_centers):
        for c_lon in sorted(lon_centers):
            regions.append(create_region(float(c_lat), float(c_lon)))
    return regions


def validate_grid_geometry(
    region: RegionDefinition,
    lats: np.ndarray,
    lons: np.ndarray,
    expected_points_per_cell: int = 64,
) -> tuple[np.ndarray, np.ndarray]:
    """Validate that the given grid coordinates over the region form an exact 8x8 grid at 0.25° resolution.

    Rejects:
    - Grids with non-0.25° spacing.
    - Slices that do not have exactly 8 latitude points and 8 longitude points.
      Every intersecting cell must have complete 8x8 geometry; edge-clipped regions are strictly rejected.
    """
    lat_idx = np.where((lats >= region.lat_min) & (lats < region.lat_max))[0]
    lon_idx = np.where((lons >= region.lon_min) & (lons < region.lon_max))[0]

    # If completely disjoint from the grid domain:
    if len(lat_idx) == 0 or len(lon_idx) == 0:
        return lat_idx, lon_idx

    # Check grid resolution spacing
    if len(lat_idx) > 1:
        lat_diffs = np.diff(lats[lat_idx])
        if not np.allclose(lat_diffs, 0.25, atol=1e-3):
            raise ValueError(
                f"Region {region.region_id} latitude resolution is not 0.25°; detected spacing: {lat_diffs}"
            )
    if len(lon_idx) > 1:
        lon_diffs = np.diff(lons[lon_idx])
        if not np.allclose(lon_diffs, 0.25, atol=1e-3):
            raise ValueError(
                f"Region {region.region_id} longitude resolution is not 0.25°; detected spacing: {lon_diffs}"
            )

    # Every intersecting cell must have exactly 8 latitude points and 8 longitude points (8x8 = 64 points).
    # No edge-clipped bypass is permitted.
    if len(lat_idx) != 8 or len(lon_idx) != 8:
        raise ValueError(
            f"Region {region.region_id} bounds [{region.lat_min}, {region.lat_max}) x [{region.lon_min}, {region.lon_max}) "
            f"intersected {len(lat_idx)}x{len(lon_idx)} grid points ({len(lat_idx)*len(lon_idx)} total); "
            f"expected exact 8x8={expected_points_per_cell} geometry for a nominal 2° cell at 0.25° resolution."
        )

    return lat_idx, lon_idx


def compute_region_coverage(
    region: RegionDefinition,
    lats: np.ndarray,
    lons: np.ndarray,
    land_mask: np.ndarray,
    nominal_points_per_cell: int = 64,
) -> dict[str, Any]:
    """Compute the valid land coverage fraction for a 2° region against a 2D boolean land mask.

    - land_mask is True for valid land points, False for missing / ocean / NaN.
    - Rejects grids whose intersecting shape is not exactly 8x8.
    """
    if nominal_points_per_cell != 64:
        raise ValueError(
            f"nominal_points_per_cell must be 64 for 2° cell at 0.25° resolution; got {nominal_points_per_cell}"
        )

    lat_idx, lon_idx = validate_grid_geometry(region, lats, lons, expected_points_per_cell=nominal_points_per_cell)

    if len(lat_idx) == 0 or len(lon_idx) == 0:
        valid_points = 0
    else:
        sub_mask = land_mask[np.ix_(lat_idx, lon_idx)]
        valid_points = int(np.sum(sub_mask))

    coverage_fraction = valid_points / float(nominal_points_per_cell)

    return {
        "region_id": region.region_id,
        "valid_points": valid_points,
        "total_points": nominal_points_per_cell,
        "coverage_fraction": coverage_fraction,
        "has_sufficient_coverage": has_sufficient_coverage(coverage_fraction, minimum=0.80),
        "lat_indices": lat_idx,
        "lon_indices": lon_idx,
    }


def aggregate_imd_daily_region(
    region: RegionDefinition,
    lats: np.ndarray,
    lons: np.ndarray,
    rainfall_2d: np.ndarray,
    minimum_coverage: float = 0.80,
    nominal_points_per_cell: int = 64,
) -> dict[str, Any]:
    """Aggregate a daily 2D IMD rainfall field over a 2° land region.

    Scientific rules:
    - Missing cells (NaN) represent ocean/unobserved points and are NEVER treated as zero.
    - If valid land points / nominal_points < minimum_coverage (default 0.80),
      o_imd_mm is None (explicit no-data outcome) and reason is documented.
    - If coverage >= minimum_coverage, o_imd_mm is the unweighted spatial mean of valid land points.
    - Rejects non-8x8 coordinate slices intersecting the region.
    """
    if nominal_points_per_cell != 64:
        raise ValueError(
            f"nominal_points_per_cell must be 64 for 2° cell at 0.25° resolution; got {nominal_points_per_cell}"
        )

    lat_idx, lon_idx = validate_grid_geometry(region, lats, lons, expected_points_per_cell=nominal_points_per_cell)

    if len(lat_idx) == 0 or len(lon_idx) == 0:
        return {
            "region_id": region.region_id,
            "valid_points": 0,
            "total_points": nominal_points_per_cell,
            "coverage_fraction": 0.0,
            "has_sufficient_coverage": False,
            "o_imd_mm": None,
            "min_mm": None,
            "max_mm": None,
            "no_data_reason": "No grid points found within region bounds",
        }

    sub_vals = rainfall_2d[np.ix_(lat_idx, lon_idx)]
    valid_mask = ~np.isnan(sub_vals)
    valid_points = int(np.sum(valid_mask))
    coverage_fraction = valid_points / float(nominal_points_per_cell)

    if not has_sufficient_coverage(coverage_fraction, minimum=minimum_coverage):
        return {
            "region_id": region.region_id,
            "valid_points": valid_points,
            "total_points": nominal_points_per_cell,
            "coverage_fraction": coverage_fraction,
            "has_sufficient_coverage": False,
            "o_imd_mm": None,
            "min_mm": float(np.nanmin(sub_vals)) if valid_points > 0 else None,
            "max_mm": float(np.nanmax(sub_vals)) if valid_points > 0 else None,
            "no_data_reason": f"coverage_fraction {coverage_fraction:.4f} is below minimum {minimum_coverage:.2f}",
        }

    valid_values = sub_vals[valid_mask]
    mean_mm = float(np.mean(valid_values))
    min_mm = float(np.min(valid_values))
    max_mm = float(np.max(valid_values))

    return {
        "region_id": region.region_id,
        "valid_points": valid_points,
        "total_points": nominal_points_per_cell,
        "coverage_fraction": coverage_fraction,
        "has_sufficient_coverage": True,
        "o_imd_mm": mean_mm,
        "min_mm": min_mm,
        "max_mm": max_mm,
        "no_data_reason": None,
    }


def load_regions_geojson(
    geojson_path: str | Path | None = None,
    supported_only: bool = False,
) -> list[RegionDefinition]:
    """Load and strictly validate region definitions from config/regions_2deg.geojson.

    If supported_only is True, return only regions where is_land_supported is True.
    Rejects malformed geometries, missing properties, or invalid bounds.
    """
    if geojson_path is None:
        geojson_path = Path(__file__).resolve().parents[3] / "config/regions_2deg.geojson"
    path = Path(geojson_path)
    if not path.exists():
        raise FileNotFoundError(f"Regions GeoJSON not found: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise ValueError(f"Invalid JSON in regions file {path}: {err}") from err

    if not isinstance(data, dict) or data.get("type") != "FeatureCollection":
        raise ValueError(f"Expected GeoJSON FeatureCollection in {path}; got {type(data)!r}")

    features = data.get("features")
    if not isinstance(features, list) or len(features) == 0:
        raise ValueError(f"GeoJSON in {path} contains no features list")

    required_props = {
        "region_id",
        "center_lat",
        "center_lon",
        "lat_min",
        "lat_max",
        "lon_min",
        "lon_max",
        "coverage_fraction",
        "is_land_supported",
    }

    regions = []
    seen_ids = set()

    for idx, feature in enumerate(features):
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise ValueError(f"Feature index {idx} is not a valid GeoJSON Feature")

        props = feature.get("properties")
        if not isinstance(props, dict):
            raise TypeError(f"Feature index {idx} has missing or non-dict properties")

        missing = required_props - set(props.keys())
        if missing:
            raise ValueError(f"Feature index {idx} missing required properties: {sorted(missing)}")

        reg_id = props["region_id"]
        if reg_id in seen_ids:
            raise ValueError(f"Duplicate region_id detected in {path}: {reg_id}")
        seen_ids.add(reg_id)

        parsed_lat, parsed_lon = parse_region_id(reg_id)
        c_lat = float(props["center_lat"])
        c_lon = float(props["center_lon"])

        if parsed_lat != c_lat or parsed_lon != c_lon:
            raise ValueError(
                f"Region ID {reg_id} does not match center coordinates ({c_lat}, {c_lon})"
            )

        lat_min = float(props["lat_min"])
        lat_max = float(props["lat_max"])
        lon_min = float(props["lon_min"])
        lon_max = float(props["lon_max"])

        if (
            abs(lat_min - (c_lat - 1.0)) > 1e-6
            or abs(lat_max - (c_lat + 1.0)) > 1e-6
            or abs(lon_min - (c_lon - 1.0)) > 1e-6
            or abs(lon_max - (c_lon + 1.0)) > 1e-6
        ):
            raise ValueError(f"Region {reg_id} bounds do not match [center - 1, center + 1)")

        # Validate geometry
        geom = feature.get("geometry")
        if not isinstance(geom, dict) or geom.get("type") != "Polygon":
            raise ValueError(f"Region {reg_id} geometry must be a Polygon; got {geom!r}")

        coords = geom.get("coordinates")
        if not isinstance(coords, list) or len(coords) != 1 or len(coords[0]) != 5:
            raise ValueError(f"Region {reg_id} polygon coordinates must be a closed 5-point ring")

        ring = coords[0]
        # Check closed ring
        if ring[0] != ring[4]:
            raise ValueError(f"Region {reg_id} polygon coordinate ring is not closed: {ring[0]} != {ring[4]}")

        if supported_only and not props.get("is_land_supported", True):
            continue

        cov_frac = float(props["coverage_fraction"]) if "coverage_fraction" in props else None
        is_supp = bool(props["is_land_supported"]) if "is_land_supported" in props else None
        regions.append(create_region(c_lat, c_lon, coverage_fraction=cov_frac, is_land_supported=is_supp))

    return regions
