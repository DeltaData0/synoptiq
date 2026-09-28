"""Guarded export of a small, real held-out replay asset.

The export is deliberately a read-only consumer of the frozen candidate,
validation-only calibrator, aligned Parquet rows, and geometry contract.  It
does not retrain, refit, or choose cases by observed outcome.
"""

from __future__ import annotations

import json
import os
import subprocess
import uuid
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from bust.data.dataset import get_manifest_fingerprint
from bust.features.analogs import retrieve_c00_earlier_analogs
from bust.model.train import (
    DEFERRED_FEATURE_GROUPS,
    PERMITTED_CANDIDATE_FEATURES,
    apply_reduced_c00_candidate,
    load_reduced_c00_candidate,
)

FROZEN_SPLIT_ID = "2010-2015/2016-2017/2018-2019"
MODEL_NAME = "reduced_c00_only_candidate"
MINIMUM_COVERAGE = 0.80
SELECTION_COUNT = 3


@dataclass(frozen=True)
class ReplayInputs:
    """Paths to the frozen inputs used by one replay export."""

    dataset_path: Path
    candidate_model_path: Path
    frozen_run_path: Path
    calibrator_path: Path
    evaluation_path: Path
    manifest_path: Path
    regions_path: Path


def _read_json(path: Path, label: str) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required {label} does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Required {label} is not valid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Required {label} must be a JSON object: {path}")  # noqa: TRY004
    return payload


def _nested_run(payload: dict[str, Any], label: str) -> dict[str, Any]:
    run = payload.get("run")
    if not isinstance(run, dict):
        raise ValueError(f"{label} has no run metadata.")  # noqa: TRY004
    return run


def validate_replay_inputs(inputs: ReplayInputs) -> dict[str, Any]:
    """Validate every frozen dependency before reading a test row.

    This check binds the export to the exact saved Booster and manifest.  It is
    intentionally separate from scoring so regression tests can prove that a
    mismatch blocks export before any replay file is written.
    """
    if not inputs.dataset_path.exists():
        raise FileNotFoundError(f"Processed dataset does not exist: {inputs.dataset_path}")
    if not inputs.regions_path.exists():
        raise FileNotFoundError(f"Region geometry does not exist: {inputs.regions_path}")

    candidate = _read_json(inputs.candidate_model_path, "candidate model metadata")
    frozen = _read_json(inputs.frozen_run_path, "frozen-run metadata")
    calibrator = _read_json(inputs.calibrator_path, "calibrator")
    evaluation = _read_json(inputs.evaluation_path, "evaluation")
    booster_path = inputs.candidate_model_path.with_suffix(".txt")
    if not booster_path.exists():
        raise FileNotFoundError(f"Candidate Booster does not exist: {booster_path}")

    expected_features = list(PERMITTED_CANDIDATE_FEATURES)
    for label, payload in (("candidate model", candidate), ("frozen run", frozen)):
        if payload.get("model_name") != MODEL_NAME:
            raise ValueError(f"{label} is not {MODEL_NAME!r}.")
        if payload.get("feature_columns") != expected_features:
            raise ValueError(f"{label} feature columns do not match the approved reduced c00 set.")

    frozen_manifest = frozen.get("manifest_id")
    actual_manifest = get_manifest_fingerprint(inputs.manifest_path)
    if frozen_manifest != actual_manifest:
        raise ValueError(
            "Manifest fingerprint mismatch: "
            f"frozen run has {frozen_manifest!r}, current manifest is {actual_manifest!r}."
        )
    if frozen.get("split_id") != FROZEN_SPLIT_ID:
        raise ValueError("Frozen run split does not match the project chronological split.")
    if frozen.get("frozen_before_test_access") is not True:
        raise ValueError("Frozen run does not prove it was written before test access.")

    booster_sha256 = sha256(booster_path.read_bytes()).hexdigest()
    if frozen.get("model_file_sha256") != booster_sha256:
        raise ValueError("Candidate Booster SHA-256 does not match frozen-run metadata.")

    for label, payload in (("calibrator", calibrator), ("evaluation", evaluation)):
        run = _nested_run(payload, label)
        if run.get("manifest_id") != actual_manifest:
            raise ValueError(f"{label} manifest fingerprint does not match the current manifest.")
        if run.get("model_file_sha256") != booster_sha256:
            raise ValueError(f"{label} Booster SHA-256 does not match the saved Booster.")
        if run.get("feature_columns") != expected_features:
            raise ValueError(f"{label} feature columns do not match the approved reduced c00 set.")

    if calibrator.get("status") != "ready" or calibrator.get("method") != "sigmoid_platt":
        raise ValueError("Replay export requires a ready validation-only sigmoid calibrator.")
    parameters = calibrator.get("parameters")
    if not isinstance(parameters, dict) or not parameters.get("coef") or not parameters.get("intercept"):
        raise ValueError("Ready calibrator is missing Platt coefficient/intercept parameters.")
    if evaluation.get("status") != "eligible_test_metrics":
        raise ValueError("Replay export requires an honest held-out evaluation artifact.")

    return {
        "candidate": candidate,
        "frozen": frozen,
        "calibrator": calibrator,
        "evaluation": evaluation,
        "manifest_id": actual_manifest,
        "booster_path": booster_path,
        "booster_sha256": booster_sha256,
    }


def select_replay_inits(dataset_path: Path, count: int = SELECTION_COUNT) -> list[str]:
    """Select first/middle/last real test initializations by availability only."""
    if count != SELECTION_COUNT:
        raise ValueError(f"The replay selection contract requires exactly {SELECTION_COUNT} dates.")
    table = pq.read_table(dataset_path, columns=["init_utc", "split"], filters=[("split", "==", "test")])
    dates = sorted({str(value)[:10] for value in table.column("init_utc").to_pylist()})
    if len(dates) < count:
        raise ValueError(f"At least {count} held-out initialization dates are required; found {len(dates)}.")
    indices = (0, len(dates) // 2, len(dates) - 1)
    selected = [dates[index] for index in indices]
    if len(set(selected)) != count:
        raise ValueError("Availability-only selection did not produce three distinct dates.")
    return selected


def _load_geometry(regions_path: Path) -> dict[str, dict[str, Any]]:
    payload = _read_json(regions_path, "region geometry")
    features = payload.get("features")
    if not isinstance(features, list) or not features:
        raise ValueError("Region geometry must contain non-empty GeoJSON features.")
    geometry: dict[str, dict[str, Any]] = {}
    for feature in features:
        region_id = feature.get("properties", {}).get("region_id")
        if not isinstance(region_id, str) or not region_id or not isinstance(feature.get("geometry"), dict):
            raise ValueError("Every frozen region feature requires region_id and geometry.")
        if region_id in geometry:
            raise ValueError(f"Duplicate region geometry for {region_id}.")
        geometry[region_id] = feature["geometry"]
    return geometry


def _calibrate(raw_scores: pd.Series, calibrator: dict[str, Any]) -> pd.Series:
    """Apply saved Platt parameters without fitting or reading labels."""
    coef = float(calibrator["parameters"]["coef"][0][0])
    intercept = float(calibrator["parameters"]["intercept"][0])
    result = pd.Series(np.nan, index=raw_scores.index, dtype=float)
    valid = raw_scores.notna()
    logits = (coef * raw_scores.loc[valid].astype(float) + intercept).clip(-700.0, 700.0)
    result.loc[valid] = 1.0 / (1.0 + np.exp(-logits))
    return result


def tier_for_probability(probability: float | None) -> str:
    """Use the dashboard's established server tier boundaries."""
    if probability is None or not np.isfinite(probability):
        return "no_data"
    if probability >= 0.50:
        return "high"
    if probability >= 0.30:
        return "watch"
    return "low"


def _as_optional_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def _no_data_reason(row: pd.Series) -> str | None:
    if int(row["lead_day"]) == 10 or row["window_quality"] == "unavailable":
        return "Day 10 is unavailable because the exact +240–+243-hour accumulation is not evidenced."
    coverage = _as_optional_float(row.get("coverage_fraction"))
    if coverage is None:
        return "Regional IMD coverage is not available for this replay row."
    if coverage < MINIMUM_COVERAGE:
        return f"Regional IMD coverage {coverage:.4f} is below the required {MINIMUM_COVERAGE:.2f}."
    if _as_optional_float(row.get("threshold_mm")) is None:
        return "No train-only regional threshold is available for this replay row."
    if _as_optional_float(row.get("f_control_mm")) is None:
        return "Control forecast rainfall is missing for this replay row."
    return None


def _provenance(manifest_id: str, booster_sha256: str) -> str:
    return (
        f"model={MODEL_NAME}; manifest_id={manifest_id}; "
        f"booster_sha256={booster_sha256}; calibration=validation_only_sigmoid"
    )


def _contribution_reasons(
    row: pd.Series,
    contributions: np.ndarray | None,
) -> list[dict[str, Any]]:
    """Return truthful saved-model contribution evidence, not causal claims."""
    if contributions is None:
        return []
    mapping = {
        "f_control_mm": "forecast_control",
        "region_id": "regional_context",
        "season": "lead_season",
        "lead_day": "lead_season",
        "lead_bucket": "lead_season",
    }
    reasons: list[dict[str, Any]] = []
    for index, feature in enumerate(PERMITTED_CANDIDATE_FEATURES):
        contribution = float(contributions[index])
        value = _as_optional_float(row.get(feature)) if feature in {"f_control_mm", "lead_day"} else None
        direction = "increases model score" if contribution >= 0 else "decreases model score"
        reasons.append(
            {
                "group": mapping[feature],
                "direction": direction,
                "feature": feature,
                "value": value,
                "train_range": None,
                "caption": (
                    f"Saved LightGBM score contribution {contribution:+.4f}; "
                    "score evidence, not a proven meteorological cause."
                ),
                "evidence_layer": "saved_lightgbm_score_contribution",
            }
        )
    return reasons


def _analog_records(query_row: pd.Series, pool: pd.DataFrame) -> tuple[list[dict[str, Any]], str]:
    """Retrieve only earlier c00 analogs; observed values are post-hoc evidence."""
    selection = retrieve_c00_earlier_analogs(query_row, pool, limit=5)
    records: list[dict[str, Any]] = []
    for _, analog in selection.analogs.iterrows():
        records.append(
            {
                "init_utc": str(analog["init_utc"]),
                "lead_day": int(analog["lead_day"]),
                "forecast_mm": _as_optional_float(analog.get("f_control_mm")),
                "error_mm": _as_optional_float(analog.get("error_mm")),
                "bust": None if pd.isna(analog.get("bust")) else bool(analog["bust"]),
                "post_hoc_disclosure": "Observed error and bust are post-hoc evidence, never ranking inputs.",
            }
        )
    return records, selection.message


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp_{os.getpid()}_{uuid.uuid4().hex}")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def export_replay_asset(
    *,
    inputs: ReplayInputs,
    replay_output_path: Path,
    metadata_output_path: Path,
    replace: bool = False,
    seed: int = 42,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Export a deterministic, real 2018–2019 historical replay slice."""
    if not replace:
        for output in (replay_output_path, metadata_output_path):
            if output.exists():
                raise FileExistsError(f"Refusing to overwrite replay artifact: {output}. Use --replace to allow.")

    verified = validate_replay_inputs(inputs)
    selected_inits = select_replay_inits(inputs.dataset_path)
    geometry = _load_geometry(inputs.regions_path)

    source_columns = [
        "init_utc",
        "lead_day",
        "valid_start_utc",
        "valid_end_utc",
        "region_id",
        "season",
        "lead_bucket",
        "f_control_mm",
        "o_imd_mm",
        "coverage_fraction",
        "error_mm",
        "threshold_mm",
        "bust",
        "source_key",
        "grib_steps",
        "imd_year",
        "window_quality",
        "split",
    ]
    rows = pq.read_table(
        inputs.dataset_path,
        columns=source_columns,
        filters=[("split", "==", "test"), ("init_utc", "in", [f"{item}T00:00:00Z" for item in selected_inits])],
    ).to_pandas()
    if rows.empty:
        raise ValueError("Availability-selected held-out replay dates had no source rows.")
    if set(rows["region_id"]) - set(geometry):
        raise ValueError("Replay rows include region IDs absent from frozen region geometry.")

    expected_rows = len(selected_inits) * len(geometry) * 10
    if len(rows) != expected_rows:
        raise ValueError(
            f"Replay slice is incomplete: expected {expected_rows} rows for all regions/leads, found {len(rows)}."
        )
    duplicate_keys = rows.duplicated(["init_utc", "lead_day", "region_id"])
    if duplicate_keys.any():
        raise ValueError("Replay slice contains duplicate init/lead/region rows.")

    model = load_reduced_c00_candidate(inputs.candidate_model_path, verified["booster_path"])
    rows["_row_id"] = rows.index
    scored = apply_reduced_c00_candidate(rows, model, probability_column="p_candidate")
    scored["p_bust"] = _calibrate(scored["p_candidate"], verified["calibrator"])

    score_eligible = (
        scored["lead_day"].between(1, 9)
        & scored["window_quality"].eq("exact")
        & scored["coverage_fraction"].ge(MINIMUM_COVERAGE)
        & scored["threshold_mm"].notna()
        & scored["p_bust"].notna()
    )
    scored.loc[~score_eligible, "p_bust"] = np.nan

    contribution_rows = scored.loc[score_eligible].copy()
    contributions_by_index: dict[int, np.ndarray] = {}
    if not contribution_rows.empty:
        categories = model.categorical_encoder.transform(contribution_rows)
        matrix = pd.DataFrame(index=contribution_rows.index)
        for feature in model.feature_columns:
            if feature in {"region_id", "season", "lead_bucket"}:
                matrix[feature] = categories[feature].astype(int)
            else:
                matrix[feature] = contribution_rows[feature].astype(float if feature == "f_control_mm" else int)
        values = model.booster.predict(matrix, pred_contrib=True)
        for row_index, value in zip(contribution_rows.index, values, strict=True):
            contributions_by_index[int(row_index)] = np.asarray(value, dtype=float)

    analog_columns = [
        "init_utc",
        "lead_day",
        "window_quality",
        "region_id",
        "season",
        "lead_bucket",
        "f_control_mm",
        "error_mm",
        "bust",
        "split",
    ]
    train_pool = pq.read_table(
        inputs.dataset_path,
        columns=analog_columns,
        filters=[("split", "==", "train")],
    ).to_pandas()
    train_pool = train_pool.loc[
        train_pool["lead_day"].between(1, 9)
        & train_pool["window_quality"].eq("exact")
        & train_pool["f_control_mm"].notna()
        & train_pool["bust"].notna()
    ].copy()
    pools = {
        key: group
        for key, group in train_pool.groupby(["region_id", "season", "lead_bucket"], sort=False)
    }

    provenance = _provenance(verified["manifest_id"], verified["booster_sha256"])
    replays: dict[str, dict[str, dict[str, Any]]] = {init: {} for init in selected_inits}
    region_details: dict[str, dict[str, Any]] = {}
    scored = scored.sort_values(["init_utc", "lead_day", "region_id"]).reset_index(drop=True)

    for init in selected_inits:
        init_rows = scored.loc[scored["init_utc"].eq(f"{init}T00:00:00Z")]
        for lead in range(1, 11):
            lead_rows = init_rows.loc[init_rows["lead_day"].eq(lead)]
            features: list[dict[str, Any]] = []
            for row_index, row in lead_rows.iterrows():
                reason = _no_data_reason(row)
                probability = _as_optional_float(row["p_bust"]) if reason is None else None
                props = {
                    "region_id": str(row["region_id"]),
                    "valid_start_utc": None if lead == 10 else row["valid_start_utc"],
                    "valid_end_utc": None if lead == 10 else row["valid_end_utc"],
                    "p_bust": probability,
                    "tier": tier_for_probability(probability),
                    "threshold_mm": None if lead == 10 else _as_optional_float(row["threshold_mm"]),
                    "f_control_mm": None if lead == 10 else _as_optional_float(row["f_control_mm"]),
                    "window_quality": str(row["window_quality"]),
                    "provenance": provenance,
                    "no_data_reason": reason,
                }
                feature = {"type": "Feature", "geometry": geometry[props["region_id"]], "properties": props}
                features.append(feature)

                query_pool = pools.get((row["region_id"], row["season"], row["lead_bucket"]), pd.DataFrame())
                analogs, analog_message = _analog_records(row, query_pool) if probability is not None else ([], "No scored exact replay row for analog retrieval.")
                reasons = (
                    _contribution_reasons(row, contributions_by_index.get(int(row["_row_id"])))
                    if probability is not None
                    else []
                )
                caveats = [
                    "Historical replay: observed rainfall is displayed only after the verification window and was not a model input.",
                    "This reduced c00-only candidate uses control rainfall, region, season, lead day, and lead bucket only.",
                    "Moisture, circulation, and ensemble-disagreement feature groups are deferred; no values were synthesized.",
                    "Model-score contributions are not proven meteorological causes.",
                ]
                if reason:
                    caveats.append(reason)
                elif analog_message:
                    caveats.append(analog_message)
                region_details[f"{init}:{lead}:{props['region_id']}"] = {
                    "region_id": props["region_id"],
                    "init_utc": str(row["init_utc"]),
                    "lead_day": lead,
                    "p_bust": probability,
                    "confidence_complement": None if probability is None else float(1.0 - probability),
                    "forecast_mm": None if lead == 10 else _as_optional_float(row["f_control_mm"]),
                    "observed_mm": None if lead == 10 else _as_optional_float(row["o_imd_mm"]),
                    "threshold_mm": props["threshold_mm"],
                    "window_quality": props["window_quality"],
                    "data_mode": "historical_replay",
                    "provenance": provenance,
                    "valid_start_utc": props["valid_start_utc"],
                    "valid_end_utc": props["valid_end_utc"],
                    "coverage_fraction": _as_optional_float(row["coverage_fraction"]),
                    "source_key": str(row["source_key"]),
                    "grib_steps": str(row["grib_steps"]),
                    "no_data_reason": reason,
                    "tier": props["tier"],
                    "reasons": reasons,
                    "analogs": analogs,
                    "caveats": caveats,
                }
            replays[init][str(lead)] = {
                "type": "FeatureCollection",
                "data_mode": "historical_replay",
                "model": MODEL_NAME,
                "truth_source": "IMD 0.25° daily gridded rainfall (historical verification)",
                "features": features,
            }

    evaluation_data = verified["evaluation"]["test_evaluation"]
    candidate_metrics = evaluation_data["candidate_metrics"]
    calibrated_brier = float(candidate_metrics["brier_score"])
    uncalibrated_brier = float(candidate_metrics["uncalibrated_brier_score"])
    evaluation = {
        "data_mode": "historical_replay",
        "status": verified["evaluation"]["status"],
        "message": (
            "Held-out evaluation of reduced_c00_only_candidate on the frozen 2018–2019 split. "
            "Calibration was fit only on 2016–2017 validation rows; calibrated Brier "
            f"{calibrated_brier:.6f} versus uncalibrated {uncalibrated_brier:.6f}."
        ),
        "metrics": {
            "candidate": candidate_metrics,
            "climatology": evaluation_data["climatology_metrics"],
            "brier_score_delta": evaluation_data["brier_score_delta"],
            "reliability": evaluation_data["reliability"],
            "calibration": verified["evaluation"]["calibration"],
            "deferred_feature_groups": list(DEFERRED_FEATURE_GROUPS),
        },
    }
    replay_payload = {
        "data_mode": "historical_replay",
        "model": MODEL_NAME,
        "truth_source": "IMD 0.25° daily gridded rainfall (historical verification)",
        "available_inits": selected_inits,
        "replays": replays,
        "regions": region_details,
        "evaluation": evaluation,
    }

    root = repo_root or Path(__file__).resolve().parents[3]
    try:
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=root, text=True).strip()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        commit = "uncommitted"
    metadata = {
        "schema_version": "1.0",
        "data_mode": "historical_replay",
        "model": MODEL_NAME,
        "selection_rule": "first, chronological-middle, and last available held-out initialization dates; availability only",
        "selected_inits": selected_inits,
        "row_count": len(scored),
        "feature_count": int(
            sum(len(payload["features"]) for leads in replays.values() for payload in leads.values())
        ),
        "manifest_id": verified["manifest_id"],
        "booster_sha256": verified["booster_sha256"],
        "git_commit": commit,
        "split": FROZEN_SPLIT_ID,
        "seed": seed,
        "calibration": "validation_only_sigmoid_platt",
        "deferred_feature_groups": list(DEFERRED_FEATURE_GROUPS),
        "replay_output": str(replay_output_path),
    }
    _atomic_write_json(replay_output_path, replay_payload)
    _atomic_write_json(metadata_output_path, metadata)
    return metadata
