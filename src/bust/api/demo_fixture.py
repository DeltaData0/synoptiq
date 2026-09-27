"""Local-only illustrative replay payload for recording the prototype walkthrough.

This module deliberately produces ``data_mode='fixture'`` responses.  It is
not a model, training artifact, observation set, or source of evaluation
metrics.  The payload exists so the frontend can be exercised across its full
interaction flow while the real replay corpus is still being built.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


DEMO_INITS = ("2018-08-01", "2018-08-08", "2019-07-18")


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _supported_regions() -> list[dict[str, Any]]:
    """Load the frozen geography; only the illustrative score values are synthetic."""
    geojson = json.loads((_project_root() / "config" / "regions_2deg.geojson").read_text(encoding="utf-8"))
    return [feature for feature in geojson["features"] if feature["properties"].get("is_land_supported")]


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _tier(probability: float) -> str:
    if probability >= 0.50:
        return "high"
    if probability >= 0.30:
        return "watch"
    return "low"


def _illustrative_probability(region_index: int, init_index: int, lead: int) -> float:
    """Deterministic display-only variation; never an inferred model score."""
    return round(0.14 + ((region_index * 17 + init_index * 13 + lead * 11) % 62) / 100, 2)


def _feature(
    region: dict[str, Any],
    region_index: int,
    init: str,
    init_index: int,
    lead: int,
) -> dict[str, Any]:
    props = region["properties"]
    init_dt = datetime.strptime(init, "%Y-%m-%d").replace(tzinfo=UTC)

    if lead == 10:
        feature_props = {
            "region_id": props["region_id"],
            "valid_start_utc": None,
            "valid_end_utc": None,
            "p_bust": None,
            "tier": "no_data",
            "threshold_mm": None,
            "window_quality": "unavailable",
            "provenance": "guided-prototype-fixture-v1",
            "no_data_reason": "Day 10 is unavailable because the exact +240–+243-hour accumulation is not evidenced.",
        }
    else:
        start = init_dt + timedelta(hours=24 * lead - 21)
        end = start + timedelta(hours=24)
        probability = _illustrative_probability(region_index, init_index, lead)
        feature_props = {
            "region_id": props["region_id"],
            "valid_start_utc": _iso(start),
            "valid_end_utc": _iso(end),
            "p_bust": probability,
            "tier": _tier(probability),
            "threshold_mm": round(12.0 + ((region_index * 3 + lead) % 10), 1),
            "window_quality": "exact",
            "provenance": "guided-prototype-fixture-v1",
            "no_data_reason": None,
        }

    return {"type": "Feature", "geometry": region["geometry"], "properties": feature_props}


def _region_detail(feature: dict[str, Any], init: str, lead: int) -> dict[str, Any]:
    props = feature["properties"]
    if lead == 10:
        return {
            "region_id": props["region_id"],
            "init_utc": f"{init}T00:00:00Z",
            "lead_day": lead,
            "p_bust": None,
            "confidence_complement": None,
            "forecast_mm": None,
            "observed_mm": None,
            "threshold_mm": None,
            "window_quality": "unavailable",
            "data_mode": "fixture",
            "provenance": "guided-prototype-fixture-v1",
            "reasons": [],
            "analogs": [],
            "caveats": [props["no_data_reason"], "Illustrative prototype response; no model, forecast, or observation claim."],
        }

    probability = props["p_bust"]
    return {
        "region_id": props["region_id"],
        "init_utc": f"{init}T00:00:00Z",
        "lead_day": lead,
        "p_bust": probability,
        "confidence_complement": round(1 - probability, 2),
        "forecast_mm": None,
        "observed_mm": None,
        "threshold_mm": props["threshold_mm"],
        "window_quality": "exact",
        "data_mode": "fixture",
        "provenance": "guided-prototype-fixture-v1",
        "reasons": [
            {
                "group": "ensemble_disagreement",
                "direction": "illustrative score increase",
                "feature": "rain_member_std",
                "value": None,
                "train_range": None,
                "caption": "Illustrative interface payload; measured ensemble features are produced only after real feature extraction.",
                "evidence_layer": "fixture",
            },
            {
                "group": "lead_season",
                "direction": "illustrative score context",
                "feature": "lead_bucket",
                "value": None,
                "train_range": None,
                "caption": "Display-only example of the planned grouped-evidence layout.",
                "evidence_layer": "fixture",
            },
        ],
        "analogs": [],
        "caveats": [
            "Illustrative prototype response; no model, forecast, observation, analog, or evaluation claim.",
            "The real replay artifact replaces this fixture only after the audited corpus and model gates pass.",
        ],
    }


def build_demo_store() -> dict[str, Any]:
    """Return a richer, explicitly fixture-only local walkthrough store."""
    regions = _supported_regions()
    replays: dict[str, dict[str, dict[str, Any]]] = {}
    details: dict[str, dict[str, Any]] = {}

    for init_index, init in enumerate(DEMO_INITS):
        replays[init] = {}
        for lead in range(1, 11):
            features = [_feature(region, index, init, init_index, lead) for index, region in enumerate(regions)]
            replays[init][str(lead)] = {
                "type": "FeatureCollection",
                "data_mode": "fixture",
                "model": "guided-prototype-fixture-v1",
                "truth_source": "illustrative interface data — not IMD observations",
                "features": features,
            }
            for feature in features:
                region_id = feature["properties"]["region_id"]
                details[f"{init}:{lead}:{region_id}"] = _region_detail(feature, init, lead)

    return {
        "data_mode": "fixture",
        "model": "guided-prototype-fixture-v1",
        "truth_source": "illustrative interface data — not IMD observations",
        "available_inits": list(DEMO_INITS),
        "replays": replays,
        "regions": details,
        "evaluation": {
            "data_mode": "fixture",
            "status": "prototype_walkthrough_only",
            "message": "Illustrative interface walkthrough only. No held-out evaluation or validated model metrics are available yet.",
            "metrics": None,
        },
    }
