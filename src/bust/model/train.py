"""Deterministic CPU-only LightGBM candidate for the reduced c00-only workflow."""

from __future__ import annotations

import json
import os
import subprocess
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from bust.data.dataset import get_manifest_fingerprint
from bust.features.analogs import retrieve_c00_earlier_analogs
from bust.model.baseline import apply_climatology_baseline, fit_climatology_baseline
from bust.model.calibrate import apply_sigmoid_calibration, fit_validation_sigmoid_calibrator
from bust.model.evaluate import (
    FORBIDDEN_FEATURE_COLUMNS,
    FROZEN_SPLIT_ID,
    build_candidate_evaluation_artifact,
    build_candidate_frozen_run_metadata,
    evaluate_held_out_probabilities,
)

PERMITTED_CANDIDATE_FEATURES: tuple[str, ...] = (
    "f_control_mm",
    "region_id",
    "season",
    "lead_day",
    "lead_bucket",
)
CATEGORICAL_FEATURES: tuple[str, ...] = ("region_id", "season", "lead_bucket")
NUMERIC_FEATURES: tuple[str, ...] = ("f_control_mm", "lead_day")
DEFERRED_FEATURE_GROUPS: tuple[str, ...] = (
    "moisture",
    "circulation",
    "ensemble_disagreement",
)

ADDITIONAL_FORBIDDEN_COLUMNS: frozenset[str] = frozenset(
    {
        "init_utc",
        "coverage_fraction",
        "valid_start_utc",
        "valid_end_utc",
        "source_key",
        "grib_steps",
        "imd_year",
    }
)
ALL_FORBIDDEN_COLUMNS: frozenset[str] = FORBIDDEN_FEATURE_COLUMNS | ADDITIONAL_FORBIDDEN_COLUMNS

DEFAULT_LIGHTGBM_HYPERPARAMETERS: dict[str, Any] = {
    "objective": "binary",
    "boosting_type": "gbdt",
    "learning_rate": 0.05,
    "num_leaves": 31,
    "max_depth": -1,
    "min_child_samples": 50,
    "subsample": 1.0,
    "colsample_bytree": 1.0,
    "random_state": 42,
    "n_estimators": 100,
    "n_jobs": 4,
    "force_row_wise": True,
    "deterministic": True,
    "verbose": -1,
}


def validate_candidate_features(feature_columns: Sequence[str]) -> tuple[str, ...]:
    """Ensure feature set contains only approved issue-time predictors without leakage."""
    columns = tuple(feature_columns)
    if not columns or len(set(columns)) != len(columns):
        raise ValueError("Feature columns must be non-empty and unique.")

    forbidden = sorted(set(columns) & ALL_FORBIDDEN_COLUMNS)
    if forbidden:
        raise ValueError(f"Feature set contains forbidden observation/label/metadata columns: {forbidden}")

    unsupported = sorted(set(columns) - set(PERMITTED_CANDIDATE_FEATURES))
    if unsupported:
        raise ValueError(
            f"Reduced c00 candidate permits only {list(PERMITTED_CANDIDATE_FEATURES)}; "
            f"unsupported columns: {unsupported}"
        )

    return columns


@dataclass
class CategoricalEncoder:
    """Train-only categorical mapping with a deterministic unseen/missing fallback."""

    categories: dict[str, list[str]]
    fallback_code: int = -1

    @classmethod
    def fit(cls, df: pd.DataFrame, columns: Sequence[str]) -> CategoricalEncoder:
        categories: dict[str, list[str]] = {}
        for col in columns:
            if col not in df.columns:
                raise ValueError(f"Categorical column {col!r} not in DataFrame.")
            cats = sorted(str(v) for v in df[col].dropna().unique())
            categories[col] = cats
        return cls(categories=categories, fallback_code=-1)

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        transformed = pd.DataFrame(index=df.index)
        for col, cat_list in self.categories.items():
            if col not in df.columns:
                transformed[col] = self.fallback_code
                continue
            mapping = {cat: idx for idx, cat in enumerate(cat_list)}
            series = df[col]
            mapped = series.map(mapping)
            unseen_non_null = series.notna() & mapped.isna()
            mapped = mapped.mask(unseen_non_null, self.fallback_code)
            transformed[col] = mapped
        return transformed

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy": "train_only_sorted_ordinal_with_unseen_fallback",
            "fallback_code": self.fallback_code,
            "categories": self.categories,
        }


@dataclass
class LightGBMCandidateModel:
    """Trained LightGBM candidate with associated encoders and metadata."""

    booster: lgb.Booster
    feature_columns: tuple[str, ...]
    categorical_encoder: CategoricalEncoder
    hyperparameters: dict[str, Any]
    lightgbm_version: str
    train_sample_count: int
    train_excluded_missing_features_count: int


def fit_reduced_c00_candidate(
    df: pd.DataFrame,
    *,
    feature_columns: Sequence[str] = PERMITTED_CANDIDATE_FEATURES,
    hyperparameters: Mapping[str, Any] | None = None,
    seed: int = 42,
) -> LightGBMCandidateModel:
    """Fit a deterministic CPU-only LightGBM candidate on eligible train rows."""
    valid_features = validate_candidate_features(feature_columns)

    required_cols = {"split", "lead_day", "window_quality", "bust", *valid_features}
    missing = sorted(required_cols - set(df.columns))
    if missing:
        raise ValueError(f"Training DataFrame is missing required columns: {missing}")

    train_mask = (
        df["split"].eq("train")
        & df["lead_day"].between(1, 9)
        & df["window_quality"].eq("exact")
        & df["bust"].notna()
    )
    has_all_features = df[list(valid_features)].notna().all(axis=1)
    missing_features_count = int((train_mask & ~has_all_features).sum())

    train_rows = df[train_mask & has_all_features].copy()
    if train_rows.empty:
        raise ValueError("No eligible exact Day 1-9 train rows available for fitting.")

    encoder = CategoricalEncoder.fit(train_rows, CATEGORICAL_FEATURES)
    cat_transformed = encoder.transform(train_rows)

    X_train = pd.DataFrame(index=train_rows.index)
    for col in valid_features:
        if col in CATEGORICAL_FEATURES:
            X_train[col] = cat_transformed[col].astype(int)
        else:
            X_train[col] = train_rows[col].astype(float if col == "f_control_mm" else int)

    y_train = train_rows["bust"].astype(int).to_numpy()

    params = dict(DEFAULT_LIGHTGBM_HYPERPARAMETERS)
    if hyperparameters:
        params.update(hyperparameters)
    params["seed"] = seed
    params["random_state"] = seed
    params["device_type"] = "cpu"
    params["deterministic"] = True
    params["force_row_wise"] = True

    n_estimators = int(params.pop("n_estimators", 100))
    n_jobs = int(params.pop("n_jobs", 4))
    params["num_threads"] = n_jobs

    ds_train = lgb.Dataset(
        X_train,
        label=y_train,
        categorical_feature=[c for c in valid_features if c in CATEGORICAL_FEATURES],
        free_raw_data=False,
    )

    booster = lgb.train(params, ds_train, num_boost_round=n_estimators)

    all_params = dict(params)
    all_params["n_estimators"] = n_estimators
    all_params["n_jobs"] = n_jobs

    return LightGBMCandidateModel(
        booster=booster,
        feature_columns=valid_features,
        categorical_encoder=encoder,
        hyperparameters=all_params,
        lightgbm_version=lgb.__version__,
        train_sample_count=len(train_rows),
        train_excluded_missing_features_count=missing_features_count,
    )


def apply_reduced_c00_candidate(
    df: pd.DataFrame,
    model: LightGBMCandidateModel,
    *,
    probability_column: str = "p_candidate",
) -> pd.DataFrame:
    """Predict probabilities for eligible exact Day 1-9 rows; non-exact/Day 10/missing features stay strictly null."""
    result = df.copy()
    result[probability_column] = np.nan

    required = {"lead_day", "window_quality", *model.feature_columns}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"DataFrame missing columns required for prediction: {missing}")

    eligible_mask = (
        result["lead_day"].between(1, 9)
        & result["window_quality"].eq("exact")
        & result[list(model.feature_columns)].notna().all(axis=1)
    )
    if not eligible_mask.any():
        return result

    eligible_rows = result[eligible_mask]
    cat_transformed = model.categorical_encoder.transform(eligible_rows)

    X_eval = pd.DataFrame(index=eligible_rows.index)
    for col in model.feature_columns:
        if col in CATEGORICAL_FEATURES:
            X_eval[col] = cat_transformed[col].astype(int)
        else:
            X_eval[col] = eligible_rows[col].astype(float if col == "f_control_mm" else int)

    preds = model.booster.predict(X_eval)
    result.loc[eligible_mask, probability_column] = preds
    return result



def run_reduced_c00_pipeline(
    dataset_path: Path | str,
    model_output_path: Path | str,
    metrics_output_path: Path | str,
    manifest_path: Path | str | None = None,
    seed: int = 42,
    replace: bool = False,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Execute the reduced c00 candidate workflow and produce validation-only comparison artifacts."""
    dataset_p = Path(dataset_path)
    model_out_p = Path(model_output_path)
    metrics_out_p = Path(metrics_output_path)

    if not dataset_p.exists():
        raise FileNotFoundError(f"Processed dataset not found: {dataset_p}")

    model_txt_p = model_out_p.with_suffix(".txt")

    if not replace:
        if model_out_p.exists():
            raise FileExistsError(
                f"Refusing to overwrite existing model artifact: {model_out_p}. Use --replace to allow."
            )
        if model_txt_p.exists():
            raise FileExistsError(
                f"Refusing to overwrite existing model booster file: {model_txt_p}. Use --replace to allow."
            )
        if metrics_out_p.exists():
            raise FileExistsError(
                f"Refusing to overwrite existing metrics artifact: {metrics_out_p}. Use --replace to allow."
            )

    root = repo_root or Path(__file__).resolve().parents[3]
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=root, text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        commit = "uncommitted"

    manifest_id = get_manifest_fingerprint(manifest_path)

    schema = pq.read_schema(dataset_p)
    cols = [
        "split",
        "lead_day",
        "window_quality",
        "bust",
        *PERMITTED_CANDIDATE_FEATURES,
    ]
    if "init_utc" in schema.names:
        cols.append("init_utc")
    if "error_mm" in schema.names:
        cols.append("error_mm")
    columns_to_read = list(dict.fromkeys(cols))

    # Invariant: Never load, score, or inspect held-out test rows
    table = pq.read_table(
        dataset_p,
        columns=columns_to_read,
        filters=[("split", "in", ["train", "validation"])],
    )
    df = table.to_pandas()

    # Fit candidate model strictly on train split
    candidate_model = fit_reduced_c00_candidate(
        df,
        feature_columns=PERMITTED_CANDIDATE_FEATURES,
        seed=seed,
    )

    # Fit D2-01 climatology baseline strictly on train split
    train_df = df[df["split"].eq("train")].copy()
    climatology_model = fit_climatology_baseline(train_df)

    # Apply both models to validation rows
    val_df = df[df["split"].eq("validation")].copy()
    val_df = apply_reduced_c00_candidate(val_df, candidate_model, probability_column="p_candidate")
    val_df = apply_climatology_baseline(val_df, climatology_model)

    # Evaluate validation metrics
    candidate_val_eval = evaluate_held_out_probabilities(
        val_df, "p_candidate", split="validation"
    )
    climatology_val_eval = evaluate_held_out_probabilities(
        val_df, "p_climatology", split="validation"
    )

    if candidate_val_eval.metrics is None or climatology_val_eval.metrics is None:
        raise RuntimeError("Validation evaluation returned empty metrics for candidate or baseline.")

    cand_brier = candidate_val_eval.metrics["brier_score"]
    clim_brier = climatology_val_eval.metrics["brier_score"]
    bust_prev = candidate_val_eval.metrics["bust_prevalence"]
    brier_delta = cand_brier - clim_brier

    # Produce validation-only analog evidence from eligible train rows
    analog_evidence: dict[str, Any] | None = None
    if "init_utc" in df.columns:
        eligible_val_mask = (
            val_df["lead_day"].between(1, 9)
            & val_df["window_quality"].eq("exact")
            & val_df["bust"].notna()
            & val_df[list(PERMITTED_CANDIDATE_FEATURES)].notna().all(axis=1)
        )
        eligible_train_mask = (
            train_df["lead_day"].between(1, 9)
            & train_df["window_quality"].eq("exact")
            & train_df["bust"].notna()
            & train_df[list(PERMITTED_CANDIDATE_FEATURES)].notna().all(axis=1)
        )
        eligible_val = val_df[eligible_val_mask]
        eligible_train_pool = train_df[eligible_train_mask]

        if not eligible_val.empty:
            sorted_val = eligible_val.sort_values(
                by=["init_utc", "region_id", "lead_day"], ascending=[True, True, True]
            )
            query_row = sorted_val.iloc[0]
            analog_selection = retrieve_c00_earlier_analogs(query_row, eligible_train_pool, limit=5)

            analog_records: list[dict[str, Any]] = []
            for _, row in analog_selection.analogs.iterrows():
                analog_records.append(
                    {
                        "init_utc": str(row["init_utc"]),
                        "lead_day": int(row["lead_day"]),
                        "f_control_mm": float(row["f_control_mm"]),
                        "forecast_diff_mm": float(row["forecast_diff"]),
                        "error_mm": float(row["error_mm"]) if pd.notna(row.get("error_mm")) else None,
                        "bust": int(row["bust"]) if pd.notna(row.get("bust")) else None,
                    }
                )

            analog_evidence = {
                "query": {
                    "init_utc": str(query_row["init_utc"]),
                    "region_id": str(query_row["region_id"]),
                    "season": str(query_row["season"]),
                    "lead_day": int(query_row["lead_day"]),
                    "lead_bucket": str(query_row["lead_bucket"]),
                    "f_control_mm": float(query_row["f_control_mm"]),
                },
                "status": analog_selection.status,
                "requested_count": analog_selection.requested_count,
                "returned_count": len(analog_records),
                "rejected_not_earlier": analog_selection.rejected_not_earlier,
                "analogs": analog_records,
                "post_hoc_disclosure": (
                    "Observed analog outcomes (error_mm, bust) are post-hoc evidence only "
                    "and are never used as model features or similarity ranking inputs."
                ),
            }

    feature_hash = sha256(
        json.dumps(list(PERMITTED_CANDIDATE_FEATURES), separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()

    model_artifact: dict[str, Any] = {
        "schema_version": "1.0",
        "model_type": "reduced_c00_only_candidate",
        "model_name": "reduced_c00_only_candidate",
        "status": "trained",
        "train_sample_count": candidate_model.train_sample_count,
        "train_excluded_missing_features_count": candidate_model.train_excluded_missing_features_count,
        "lightgbm_version": candidate_model.lightgbm_version,
        "feature_columns": list(candidate_model.feature_columns),
        "feature_set_sha256": feature_hash,
        "categorical_encoding": candidate_model.categorical_encoder.to_dict(),
        "hyperparameters": candidate_model.hyperparameters,
        "deferred_feature_groups": list(DEFERRED_FEATURE_GROUPS),
        "booster_file": model_txt_p.name,
        "run": {
            "manifest_id": manifest_id,
            "git_commit": commit,
            "split_id": FROZEN_SPLIT_ID,
            "seed": seed,
        },
    }

    metrics_artifact: dict[str, Any] = {
        "schema_version": "1.0",
        "model_type": "reduced_c00_only_candidate",
        "model_name": "reduced_c00_only_candidate",
        "data_mode": "validation_only",
        "status": "validation_comparison_only",
        "message": (
            "Validation-only comparison against D2-01 climatology baseline. "
            "Held-out test rows (2018-2019) were not loaded, scored, or inspected."
        ),
        "sample_counts": {
            "train_eligible": candidate_model.train_sample_count,
            "train_excluded_missing_features": candidate_model.train_excluded_missing_features_count,
            "validation_eligible": candidate_val_eval.sample_count,
            "test_eligible": None,
        },
        "validation_evaluation": {
            "sample_count": candidate_val_eval.sample_count,
            "candidate_metrics": {
                "brier_score": cand_brier,
                "bust_prevalence": bust_prev,
            },
            "climatology_metrics": {
                "brier_score": clim_brier,
                "bust_prevalence": bust_prev,
            },
            "brier_score_delta": brier_delta,
            "reliability": candidate_val_eval.reliability,
        },
        "analog_evidence": analog_evidence,
        "deferred_feature_groups": list(DEFERRED_FEATURE_GROUPS),
        "run": {
            "manifest_id": manifest_id,
            "git_commit": commit,
            "split_id": FROZEN_SPLIT_ID,
            "seed": seed,
            "feature_columns": list(candidate_model.feature_columns),
            "feature_set_sha256": feature_hash,
            "hyperparameters": candidate_model.hyperparameters,
            "lightgbm_version": candidate_model.lightgbm_version,
        },
    }

    def _write_json_atomic(target_path: Path, data: dict[str, Any]) -> None:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = target_path.with_suffix(f".tmp_{os.getpid()}_{uuid.uuid4().hex[:8]}.json")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        tmp.replace(target_path)

    _write_json_atomic(model_out_p, model_artifact)
    _write_json_atomic(metrics_out_p, metrics_artifact)

    # Save serialized booster file
    tmp_txt = model_txt_p.with_suffix(f".tmp_{os.getpid()}_{uuid.uuid4().hex[:8]}.txt")
    candidate_model.booster.save_model(str(tmp_txt))
    tmp_txt.replace(model_txt_p)

    return {
        "manifest_id": manifest_id,
        "git_commit": commit,
        "model_output": str(model_out_p),
        "model_txt_output": str(model_txt_p),
        "metrics_output": str(metrics_out_p),
        "train_samples": candidate_model.train_sample_count,
        "validation_samples": candidate_val_eval.sample_count,
        "candidate_validation_brier_score": cand_brier,
        "candidate_validation_bust_prevalence": bust_prev,
        "climatology_validation_brier_score": clim_brier,
        "brier_score_delta": brier_delta,
        "deferred_feature_groups": list(DEFERRED_FEATURE_GROUPS),
        "analog_evidence": analog_evidence,
    }


def load_reduced_c00_candidate(
    model_json_path: Path | str,
    booster_txt_path: Path | str | None = None,
) -> LightGBMCandidateModel:
    """Load a saved candidate model metadata and serialized Booster."""
    json_p = Path(model_json_path)
    if not json_p.exists():
        raise FileNotFoundError(f"Candidate model JSON not found: {json_p}")

    txt_p = Path(booster_txt_path) if booster_txt_path else json_p.with_suffix(".txt")
    if not txt_p.exists():
        raise FileNotFoundError(f"Candidate model booster file not found: {txt_p}")

    data = json.loads(json_p.read_text(encoding="utf-8"))
    booster = lgb.Booster(model_file=str(txt_p))

    encoder = CategoricalEncoder(
        categories=data["categorical_encoding"]["categories"],
        fallback_code=data["categorical_encoding"]["fallback_code"],
    )

    return LightGBMCandidateModel(
        booster=booster,
        feature_columns=tuple(data["feature_columns"]),
        categorical_encoder=encoder,
        hyperparameters=data["hyperparameters"],
        lightgbm_version=data["lightgbm_version"],
        train_sample_count=data["train_sample_count"],
        train_excluded_missing_features_count=data["train_excluded_missing_features_count"],
    )


def run_reduced_c00_evaluation_pipeline(
    dataset_path: Path | str,
    candidate_model_path: Path | str,
    frozen_run_output_path: Path | str,
    calibrator_output_path: Path | str,
    metrics_output_path: Path | str,
    manifest_path: Path | str | None = None,
    seed: int = 42,
    replace: bool = False,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Execute validation-only sigmoid calibration and held-out test evaluation."""
    dataset_p = Path(dataset_path)
    model_json_p = Path(candidate_model_path)
    frozen_run_p = Path(frozen_run_output_path)
    calibrator_p = Path(calibrator_output_path)
    metrics_p = Path(metrics_output_path)

    if not dataset_p.exists():
        raise FileNotFoundError(f"Processed dataset not found: {dataset_p}")
    if not model_json_p.exists():
        raise FileNotFoundError(f"Candidate model JSON not found: {model_json_p}")

    model_txt_p = model_json_p.with_suffix(".txt")
    if not model_txt_p.exists():
        raise FileNotFoundError(f"Candidate model booster file not found: {model_txt_p}")

    if not replace:
        if frozen_run_p.exists():
            raise FileExistsError(
                f"Refusing to overwrite existing frozen run artifact: {frozen_run_p}. Use --replace to allow."
            )
        if calibrator_p.exists():
            raise FileExistsError(
                f"Refusing to overwrite existing calibrator artifact: {calibrator_p}. Use --replace to allow."
            )
        if metrics_p.exists():
            raise FileExistsError(
                f"Refusing to overwrite existing evaluation artifact: {metrics_p}. Use --replace to allow."
            )

    root = repo_root or Path(__file__).resolve().parents[3]
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=root, text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        commit = "uncommitted"

    try:
        status_out = subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=root, text=True
        ).strip()
        is_dirty = bool(status_out)
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        is_dirty = False

    manifest_id = get_manifest_fingerprint(manifest_path)

    # Load candidate model metadata and compute model booster sha256
    model_raw = json.loads(model_json_p.read_text(encoding="utf-8"))
    model_file_sha256 = sha256(model_txt_p.read_bytes()).hexdigest()

    frozen_run_meta = build_candidate_frozen_run_metadata(
        manifest_id=manifest_id,
        git_commit=commit,
        is_dirty=is_dirty,
        seed=seed,
        feature_columns=PERMITTED_CANDIDATE_FEATURES,
        model_file_sha256=model_file_sha256,
        lightgbm_version=model_raw.get("lightgbm_version", lgb.__version__),
        categorical_encoding=model_raw["categorical_encoding"],
        hyperparameters=model_raw["hyperparameters"],
        split_id=FROZEN_SPLIT_ID,
        frozen_before_test_access=True,
    )

    def _write_json_atomic(target_path: Path, data: dict[str, Any]) -> None:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = target_path.with_suffix(f".tmp_{os.getpid()}_{uuid.uuid4().hex[:8]}.json")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        tmp.replace(target_path)

    # STAGE 1: Freeze before reading any test data
    _write_json_atomic(frozen_run_p, frozen_run_meta.to_dict())

    # Load candidate model booster and categorical encoder
    candidate_model = load_reduced_c00_candidate(model_json_p, model_txt_p)

    # STAGE 2: Calibration (load ONLY train/validation rows)
    columns_to_read = list(dict.fromkeys(["split", "lead_day", "window_quality", "bust", *PERMITTED_CANDIDATE_FEATURES]))
    train_val_table = pq.read_table(
        dataset_p,
        columns=columns_to_read,
        filters=[("split", "in", ["train", "validation"])],
    )
    train_val_df = train_val_table.to_pandas()

    val_df = train_val_df[train_val_df["split"].eq("validation")].copy()
    val_df = apply_reduced_c00_candidate(val_df, candidate_model, probability_column="p_candidate")

    calibrator = fit_validation_sigmoid_calibrator(val_df, "p_candidate", seed=seed)

    calibration_parameters: dict[str, Any] | None = None
    if calibrator.estimator is not None:
        calibration_parameters = {
            "coef": calibrator.estimator.coef_.tolist(),
            "intercept": calibrator.estimator.intercept_.tolist(),
        }

    calibrator_artifact: dict[str, Any] = {
        "schema_version": "1.0",
        "model_type": "reduced_c00_only_candidate",
        "model_name": "reduced_c00_only_candidate",
        "status": calibrator.status,
        "sample_count": calibrator.sample_count,
        "message": calibrator.message,
        "method": "sigmoid_platt",
        "parameters": calibration_parameters,
        "run": frozen_run_meta.to_dict(),
    }
    _write_json_atomic(calibrator_p, calibrator_artifact)

    # Fit climatology baseline on train split
    train_df = train_val_df[train_val_df["split"].eq("train")].copy()
    climatology_model = fit_climatology_baseline(train_df)

    # Check calibration readiness
    if calibrator.status != "ready":
        sample_counts = {
            "train_eligible": candidate_model.train_sample_count,
            "train_excluded_missing_features": candidate_model.train_excluded_missing_features_count,
            "validation_eligible": calibrator.sample_count,
            "test_total": 0,
            "test_eligible": 0,
            "test_excluded_missing_features": 0,
            "test_unavailable_day10": 0,
            "test_non_exact": 0,
            "test_unlabeled_or_insufficient_coverage": 0,
        }
        metrics_artifact = {
            "schema_version": "1.0",
            "model_type": "reduced_c00_only_candidate",
            "model_name": "reduced_c00_only_candidate",
            "data_mode": "held_out_test",
            "status": "calibration_not_ready",
            "message": "Held-out evaluation refused because validation-only calibrator was not ready.",
            "sample_counts": sample_counts,
            "cohort_definition": {
                "split": "test",
                "lead_days": "1-9",
                "window_quality": "exact",
                "label_required": "bust.notna()",
                "required_features": list(PERMITTED_CANDIDATE_FEATURES),
                "same_cohort_evaluated": True,
            },
            "test_evaluation": {
                "sample_count": 0,
                "candidate_metrics": None,
                "climatology_metrics": None,
                "brier_score_delta": None,
                "reliability": [],
            },
            "calibration": {
                "status": calibrator.status,
                "sample_count": calibrator.sample_count,
                "method": "sigmoid_platt",
                "parameters": None,
            },
            "deferred_feature_groups": list(DEFERRED_FEATURE_GROUPS),
            "run": frozen_run_meta.to_dict(),
        }
        _write_json_atomic(metrics_p, metrics_artifact)
        return {
            "status": "calibration_not_ready",
            "manifest_id": manifest_id,
            "git_commit": commit,
            "frozen_run_artifact": str(frozen_run_p),
            "calibrator_artifact": str(calibrator_p),
            "metrics_artifact": str(metrics_p),
            "calibration_status": calibrator.status,
            "calibration_sample_count": calibrator.sample_count,
            "test_sample_count": 0,
            "candidate_test_brier_score": None,
            "candidate_uncalibrated_brier_score": None,
            "candidate_test_bust_prevalence": None,
            "climatology_test_brier_score": None,
            "brier_score_delta": None,
            "sample_counts": sample_counts,
            "deferred_feature_groups": list(DEFERRED_FEATURE_GROUPS),
        }

    # STAGE 3: Held-out test evaluation (load test rows ONLY AFTER Stage 1 and Stage 2 are written)
    test_table = pq.read_table(
        dataset_p,
        columns=columns_to_read,
        filters=[("split", "==", "test")],
    )
    test_df = test_table.to_pandas()

    test_df = apply_reduced_c00_candidate(test_df, candidate_model, probability_column="p_candidate")
    test_df = apply_sigmoid_calibration(test_df, calibrator, "p_candidate", output_column="p_calibrated")
    test_df = apply_climatology_baseline(test_df, climatology_model)

    # Identical eligible cohort filtering
    is_exact_lead = test_df["lead_day"].between(1, 9) & test_df["window_quality"].eq("exact")
    has_bust = test_df["bust"].notna()
    has_all_features = test_df[list(PERMITTED_CANDIDATE_FEATURES)].notna().all(axis=1)

    eligible_cohort_mask = is_exact_lead & has_bust & has_all_features
    test_cohort = test_df[eligible_cohort_mask].copy()

    test_total_count = len(test_df)
    test_eligible_count = int(eligible_cohort_mask.sum())
    test_excluded_missing_features = int((is_exact_lead & has_bust & ~has_all_features).sum())
    test_unavailable_day10 = int(
        (test_df["lead_day"].eq(10) | test_df["window_quality"].eq("unavailable")).sum()
    )
    test_non_exact = int(
        (
            test_df["lead_day"].between(1, 9)
            & test_df["window_quality"].ne("exact")
            & test_df["window_quality"].ne("unavailable")
        ).sum()
    )
    test_unlabeled_or_insufficient = int((is_exact_lead & test_df["bust"].isna()).sum())

    sample_counts = {
        "train_eligible": candidate_model.train_sample_count,
        "train_excluded_missing_features": candidate_model.train_excluded_missing_features_count,
        "validation_eligible": calibrator.sample_count,
        "test_total": test_total_count,
        "test_eligible": test_eligible_count,
        "test_excluded_missing_features": test_excluded_missing_features,
        "test_unavailable_day10": test_unavailable_day10,
        "test_non_exact": test_non_exact,
        "test_unlabeled_or_insufficient_coverage": test_unlabeled_or_insufficient,
    }

    cand_eval = evaluate_held_out_probabilities(test_cohort, "p_calibrated", split="test")
    uncal_eval = evaluate_held_out_probabilities(test_cohort, "p_candidate", split="test")
    clim_eval = evaluate_held_out_probabilities(test_cohort, "p_climatology", split="test")

    metrics_artifact = build_candidate_evaluation_artifact(
        frozen_run_meta,
        candidate_evaluation=cand_eval,
        climatology_evaluation=clim_eval,
        uncalibrated_evaluation=uncal_eval,
        calibration_status=calibrator.status,
        calibration_sample_count=calibrator.sample_count,
        calibration_parameters=calibration_parameters,
        sample_counts=sample_counts,
        deferred_feature_groups=DEFERRED_FEATURE_GROUPS,
    )
    _write_json_atomic(metrics_p, metrics_artifact)

    cand_brier = cand_eval.metrics["brier_score"] if cand_eval.metrics else None
    cand_uncal_brier = uncal_eval.metrics["brier_score"] if uncal_eval.metrics else None
    cand_prev = cand_eval.metrics["bust_prevalence"] if cand_eval.metrics else None
    clim_brier = clim_eval.metrics["brier_score"] if clim_eval.metrics else None
    brier_delta = (cand_brier - clim_brier) if (cand_brier is not None and clim_brier is not None) else None

    return {
        "manifest_id": manifest_id,
        "git_commit": commit,
        "frozen_run_artifact": str(frozen_run_p),
        "calibrator_artifact": str(calibrator_p),
        "metrics_artifact": str(metrics_p),
        "calibration_status": calibrator.status,
        "calibration_sample_count": calibrator.sample_count,
        "test_sample_count": test_eligible_count,
        "candidate_test_brier_score": cand_brier,
        "candidate_uncalibrated_brier_score": cand_uncal_brier,
        "candidate_test_bust_prevalence": cand_prev,
        "climatology_test_brier_score": clim_brier,
        "brier_score_delta": brier_delta,
        "sample_counts": sample_counts,
        "deferred_feature_groups": list(DEFERRED_FEATURE_GROUPS),
    }

