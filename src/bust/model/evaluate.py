"""Held-out, no-data-safe probability evaluation utilities."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

import numpy as np
import pandas as pd

FROZEN_SPLIT_ID = "2010-2015/2016-2017/2018-2019"
FORBIDDEN_FEATURE_COLUMNS = frozenset(
    {
        "bust",
        "error_mm",
        "o_imd_mm",
        "observed_mm",
        "p_bust",
        "target",
        "threshold_mm",
    }
)


@dataclass(frozen=True)
class FrozenRunMetadata:
    """Immutable context required beside every generated model/evaluation artifact."""

    manifest_id: str
    git_commit: str
    split_id: str
    seed: int
    feature_columns: tuple[str, ...]
    feature_set_sha256: str
    hyperparameters: dict[str, Any]


def build_frozen_run_metadata(
    *,
    manifest_id: str,
    git_commit: str,
    seed: int,
    feature_columns: tuple[str, ...] | list[str],
    hyperparameters: Mapping[str, Any],
    split_id: str = FROZEN_SPLIT_ID,
) -> FrozenRunMetadata:
    """Validate and freeze context before candidate fitting or test evaluation."""
    if not manifest_id.strip() or not git_commit.strip():
        raise ValueError("Run metadata requires a non-empty manifest_id and git_commit.")
    if split_id != FROZEN_SPLIT_ID:
        raise ValueError(f"Frozen split must remain {FROZEN_SPLIT_ID}.")
    columns = tuple(feature_columns)
    if not columns or len(set(columns)) != len(columns):
        raise ValueError("Feature columns must be non-empty and unique in their frozen order.")
    forbidden = sorted(set(columns) & FORBIDDEN_FEATURE_COLUMNS)
    if forbidden:
        raise ValueError(f"Feature set contains forbidden observation/label columns: {forbidden}")

    try:
        canonical_hyperparameters = json.loads(json.dumps(dict(hyperparameters), sort_keys=True))
    except (TypeError, ValueError) as exc:
        raise ValueError("Hyperparameters must be JSON-serializable.") from exc
    feature_hash = sha256(
        json.dumps(list(columns), separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()
    return FrozenRunMetadata(
        manifest_id=manifest_id,
        git_commit=git_commit,
        split_id=split_id,
        seed=seed,
        feature_columns=columns,
        feature_set_sha256=feature_hash,
        hyperparameters=canonical_hyperparameters,
    )


@dataclass(frozen=True)
class ProbabilityEvaluation:
    """Evaluation result that is explicit when held-out data is absent."""

    status: str
    sample_count: int
    metrics: dict[str, float] | None
    reliability: list[dict[str, float | int]]
    message: str


def build_evaluation_artifact(
    run: FrozenRunMetadata,
    evaluation: ProbabilityEvaluation,
    *,
    calibration_status: str,
    calibration_sample_count: int,
) -> dict[str, Any]:
    """Build a serializable, evidence-bound evaluation artifact.

    A populated held-out metric is accepted only when validation-only
    calibration was ready. Missing test evidence remains an explicit artifact
    with null metrics and no reliability bins.
    """
    if calibration_sample_count < 0:
        raise ValueError("Calibration sample count cannot be negative.")
    if evaluation.status == "eligible_test_metrics" and calibration_status != "ready":
        raise ValueError("Held-out calibrated metrics require a ready validation-only calibrator.")
    if evaluation.status == "insufficient_test_data" and (
        evaluation.metrics is not None or evaluation.reliability
    ):
        raise ValueError("Insufficient-test-data artifacts must not contain metrics or reliability bins.")

    return {
        "schema_version": "1.0",
        "status": evaluation.status,
        "message": evaluation.message,
        "metrics": evaluation.metrics,
        "reliability": evaluation.reliability,
        "calibration": {
            "status": calibration_status,
            "sample_count": calibration_sample_count,
        },
        "run": {
            "manifest_id": run.manifest_id,
            "git_commit": run.git_commit,
            "split_id": run.split_id,
            "seed": run.seed,
            "feature_columns": list(run.feature_columns),
            "feature_set_sha256": run.feature_set_sha256,
            "hyperparameters": run.hyperparameters,
        },
    }


def evaluate_held_out_probabilities(
    rows: pd.DataFrame,
    probability_column: str,
    *,
    split: str = "test",
    bins: int = 10,
) -> ProbabilityEvaluation:
    """Evaluate probabilities only on eligible, labeled rows in the requested split.

    The caller must supply probabilities produced without test labels.  This
    function refuses to convert unavailable rows into negatives and returns an
    explicit insufficient-data result rather than a fabricated metric.
    """
    required = {"split", "lead_day", "window_quality", "bust", probability_column}
    missing = sorted(required - set(rows.columns))
    if missing:
        raise ValueError(f"Evaluation rows are missing required columns: {missing}")
    if bins < 2:
        raise ValueError("Reliability evaluation requires at least two bins.")

    eligible = rows.loc[
        rows["split"].eq(split)
        & rows["lead_day"].between(1, 9)
        & rows["window_quality"].eq("exact")
        & rows["bust"].notna()
        & rows[probability_column].notna()
    ].copy()

    if eligible.empty:
        return ProbabilityEvaluation(
            status="insufficient_test_data",
            sample_count=0,
            metrics=None,
            reliability=[],
            message=f"No eligible exact Day 1-9 labeled {split} rows with probabilities are available.",
        )

    probabilities = eligible[probability_column].astype(float).to_numpy()
    if np.any(~np.isfinite(probabilities)) or np.any((probabilities < 0.0) | (probabilities > 1.0)):
        raise ValueError(f"{probability_column} must contain finite probabilities in [0, 1].")

    outcomes = eligible["bust"].astype(float).to_numpy()
    brier_score = float(np.mean((probabilities - outcomes) ** 2))
    prevalence = float(np.mean(outcomes))

    bin_edges = np.linspace(0.0, 1.0, bins + 1)
    reliability: list[dict[str, float | int]] = []
    for index in range(bins):
        low, high = float(bin_edges[index]), float(bin_edges[index + 1])
        # Include p=1.0 only in the final bin.
        mask = (probabilities >= low) & (
            probabilities <= high if index == bins - 1 else probabilities < high
        )
        if not mask.any():
            continue
        reliability.append(
            {
                "bin_start": low,
                "bin_end": high,
                "count": int(mask.sum()),
                "mean_prediction": float(np.mean(probabilities[mask])),
                "observed_frequency": float(np.mean(outcomes[mask])),
            }
        )

    return ProbabilityEvaluation(
        status="eligible_test_metrics",
        sample_count=len(eligible),
        metrics={"brier_score": brier_score, "bust_prevalence": prevalence},
        reliability=reliability,
        message=f"Metrics computed on {len(eligible)} eligible exact Day 1-9 {split} rows.",
    )


@dataclass(frozen=True)
class CandidateFrozenRunMetadata:
    """Immutable candidate run context frozen before any test data access."""

    manifest_id: str
    git_commit: str
    is_dirty: bool
    split_id: str
    seed: int
    feature_columns: tuple[str, ...]
    feature_set_sha256: str
    model_file_sha256: str
    lightgbm_version: str
    categorical_encoding: dict[str, Any]
    hyperparameters: dict[str, Any]
    frozen_before_test_access: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "model_type": "reduced_c00_only_candidate",
            "model_name": "reduced_c00_only_candidate",
            "manifest_id": self.manifest_id,
            "git_commit": self.git_commit,
            "is_dirty": self.is_dirty,
            "split_id": self.split_id,
            "seed": self.seed,
            "feature_columns": list(self.feature_columns),
            "feature_set_sha256": self.feature_set_sha256,
            "model_file_sha256": self.model_file_sha256,
            "lightgbm_version": self.lightgbm_version,
            "categorical_encoding": self.categorical_encoding,
            "hyperparameters": self.hyperparameters,
            "frozen_before_test_access": self.frozen_before_test_access,
        }


def build_candidate_frozen_run_metadata(
    *,
    manifest_id: str,
    git_commit: str,
    is_dirty: bool,
    seed: int,
    feature_columns: tuple[str, ...] | list[str],
    model_file_sha256: str,
    lightgbm_version: str,
    categorical_encoding: Mapping[str, Any],
    hyperparameters: Mapping[str, Any],
    split_id: str = FROZEN_SPLIT_ID,
    frozen_before_test_access: bool = True,
) -> CandidateFrozenRunMetadata:
    """Validate and build candidate frozen-run context before reading test data."""
    if not manifest_id.strip() or not git_commit.strip():
        raise ValueError("Run metadata requires non-empty manifest_id and git_commit.")
    if split_id != FROZEN_SPLIT_ID:
        raise ValueError(f"Frozen split must remain {FROZEN_SPLIT_ID}.")
    if not model_file_sha256.strip() or len(model_file_sha256) != 64:
        raise ValueError("Candidate model_file_sha256 must be a 64-character SHA-256 hex string.")
    if not frozen_before_test_access:
        raise ValueError("frozen_before_test_access must be True.")

    columns = tuple(feature_columns)
    if not columns or len(set(columns)) != len(columns):
        raise ValueError("Feature columns must be non-empty and unique in their frozen order.")
    forbidden = sorted(set(columns) & FORBIDDEN_FEATURE_COLUMNS)
    if forbidden:
        raise ValueError(f"Feature set contains forbidden observation/label columns: {forbidden}")

    try:
        canonical_hyperparameters = json.loads(json.dumps(dict(hyperparameters), sort_keys=True))
    except (TypeError, ValueError) as exc:
        raise ValueError("Hyperparameters must be JSON-serializable.") from exc

    try:
        canonical_encoding = json.loads(json.dumps(dict(categorical_encoding), sort_keys=True))
    except (TypeError, ValueError) as exc:
        raise ValueError("Categorical encoding must be JSON-serializable.") from exc

    feature_hash = sha256(
        json.dumps(list(columns), separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()

    return CandidateFrozenRunMetadata(
        manifest_id=manifest_id,
        git_commit=git_commit,
        is_dirty=is_dirty,
        split_id=split_id,
        seed=seed,
        feature_columns=columns,
        feature_set_sha256=feature_hash,
        model_file_sha256=model_file_sha256,
        lightgbm_version=lightgbm_version,
        categorical_encoding=canonical_encoding,
        hyperparameters=canonical_hyperparameters,
        frozen_before_test_access=frozen_before_test_access,
    )


def build_candidate_evaluation_artifact(
    run: CandidateFrozenRunMetadata,
    *,
    candidate_evaluation: ProbabilityEvaluation,
    climatology_evaluation: ProbabilityEvaluation,
    uncalibrated_evaluation: ProbabilityEvaluation | None,
    calibration_status: str,
    calibration_sample_count: int,
    calibration_parameters: dict[str, Any] | None,
    sample_counts: Mapping[str, Any],
    deferred_feature_groups: tuple[str, ...] | list[str],
) -> dict[str, Any]:
    """Build honest, held-out evaluation artifact comparing candidate to climatology on same cohort."""
    if calibration_sample_count < 0:
        raise ValueError("Calibration sample count cannot be negative.")
    if candidate_evaluation.status == "eligible_test_metrics" and calibration_status != "ready":
        raise ValueError("Held-out calibrated metrics require a ready validation-only calibrator.")
    if candidate_evaluation.sample_count != climatology_evaluation.sample_count:
        raise ValueError(
            f"Candidate ({candidate_evaluation.sample_count}) and climatology "
            f"({climatology_evaluation.sample_count}) must evaluate on identical sample counts."
        )

    brier_delta: float | None = None
    if (
        candidate_evaluation.metrics is not None
        and climatology_evaluation.metrics is not None
    ):
        brier_delta = (
            candidate_evaluation.metrics["brier_score"]
            - climatology_evaluation.metrics["brier_score"]
        )

    candidate_metrics: dict[str, float] | None = None
    if candidate_evaluation.metrics is not None:
        candidate_metrics = dict(candidate_evaluation.metrics)
        if uncalibrated_evaluation and uncalibrated_evaluation.metrics:
            candidate_metrics["uncalibrated_brier_score"] = (
                uncalibrated_evaluation.metrics["brier_score"]
            )

    return {
        "schema_version": "1.0",
        "model_type": "reduced_c00_only_candidate",
        "model_name": "reduced_c00_only_candidate",
        "data_mode": "held_out_test",
        "status": candidate_evaluation.status,
        "message": candidate_evaluation.message,
        "sample_counts": dict(sample_counts),
        "cohort_definition": {
            "split": "test",
            "lead_days": "1-9",
            "window_quality": "exact",
            "label_required": "bust.notna()",
            "required_features": list(run.feature_columns),
            "same_cohort_evaluated": True,
        },
        "test_evaluation": {
            "sample_count": candidate_evaluation.sample_count,
            "candidate_metrics": candidate_metrics,
            "climatology_metrics": climatology_evaluation.metrics,
            "brier_score_delta": brier_delta,
            "reliability": candidate_evaluation.reliability,
        },
        "calibration": {
            "status": calibration_status,
            "sample_count": calibration_sample_count,
            "method": "sigmoid_platt",
            "parameters": calibration_parameters,
        },
        "deferred_feature_groups": list(deferred_feature_groups),
        "run": run.to_dict(),
    }
