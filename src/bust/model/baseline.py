"""Leakage-safe baseline utilities for the forecast-bust task.

These functions deliberately operate only on already-built, aligned rows.  They
do not create labels, infer observations, or turn incomplete data into results.
"""

from __future__ import annotations

import json
import os
import subprocess
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from bust.data.dataset import get_manifest_fingerprint
from bust.model.evaluate import (
    FROZEN_SPLIT_ID,
    ProbabilityEvaluation,
    evaluate_held_out_probabilities,
)

BASELINE_GROUP_KEYS = ("region_id", "season", "lead_bucket")
REQUIRED_ROW_COLUMNS = ("split", "lead_day", "window_quality", "bust", *BASELINE_GROUP_KEYS)


class InsufficientBaselineDataError(ValueError):
    """Raised when no eligible train rows exist for a baseline fit."""


@dataclass(frozen=True)
class ClimatologyBaseline:
    """Train-only regional/season/lead-bucket bust-rate baseline."""

    global_train_rate: float
    group_rates: dict[tuple[str, str, str], float]
    train_sample_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_type": "climatology_baseline",
            "global_train_rate": self.global_train_rate,
            "train_sample_count": self.train_sample_count,
            "num_groups": len(self.group_rates),
            "group_keys": list(BASELINE_GROUP_KEYS),
            "group_rates": {
                f"{k[0]}|{k[1]}|{k[2]}": rate
                for k, rate in sorted(self.group_rates.items())
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ClimatologyBaseline:
        raw_rates = data.get("group_rates", {})
        group_rates: dict[tuple[str, str, str], float] = {}
        for key_str, rate in raw_rates.items():
            parts = tuple(key_str.split("|"))
            if len(parts) == 3:
                group_rates[(parts[0], parts[1], parts[2])] = float(rate)
        return cls(
            global_train_rate=float(data["global_train_rate"]),
            group_rates=group_rates,
            train_sample_count=int(data.get("train_sample_count", 0)),
        )


@dataclass(frozen=True)
class BaselineReadiness:
    """Explicit readiness state for a baseline that may be data-blocked."""

    status: str
    missing_columns: tuple[str, ...] = ()
    message: str = ""


def _require_columns(rows: pd.DataFrame, columns: tuple[str, ...]) -> None:
    missing = sorted(set(columns) - set(rows.columns))
    if missing:
        raise ValueError(f"Baseline rows are missing required columns: {missing}")


def eligible_labeled_rows(rows: pd.DataFrame) -> pd.DataFrame:
    """Return only exact, Day 1-9 rows with an observed bust label.

    Missing/unavailable rows remain missing; they are never coerced to a negative
    label or a zero probability.
    """
    _require_columns(rows, REQUIRED_ROW_COLUMNS)
    mask = (
        rows["lead_day"].between(1, 9)
        & rows["window_quality"].eq("exact")
        & rows["bust"].notna()
    )
    return rows.loc[mask].copy()


def fit_climatology_baseline(rows: pd.DataFrame) -> ClimatologyBaseline:
    """Fit the frozen grouped climatology using **train rows only**."""
    train_rows = eligible_labeled_rows(rows)
    train_rows = train_rows.loc[train_rows["split"].eq("train")].copy()
    if train_rows.empty:
        raise InsufficientBaselineDataError(
            "Cannot fit climatology baseline: zero eligible exact Day 1-9 train rows."
        )

    train_rows["_bust_numeric"] = train_rows["bust"].astype(float)
    global_rate = float(train_rows["_bust_numeric"].mean())
    grouped = train_rows.groupby(list(BASELINE_GROUP_KEYS), dropna=False)["_bust_numeric"].mean()
    group_rates = {
        tuple(str(value) for value in key): float(rate)
        for key, rate in grouped.items()
    }
    return ClimatologyBaseline(
        global_train_rate=global_rate,
        group_rates=group_rates,
        train_sample_count=len(train_rows),
    )


def apply_climatology_baseline(rows: pd.DataFrame, model: ClimatologyBaseline) -> pd.DataFrame:
    """Attach a train-only climatology probability while preserving input order.

    Exact Day 1-9 rows use their regional/season/lead-bucket rate when one was
    observed in train.  A missing group falls back only to the global *train*
    rate.  Day 10 and unavailable rows receive null predictions.
    """
    _require_columns(rows, ("lead_day", "window_quality", *BASELINE_GROUP_KEYS))
    result = rows.copy()

    lead_day = result["lead_day"].astype(int).to_numpy()
    wq = result["window_quality"].astype(str).to_numpy()

    unavailable_mask = (lead_day == 10) | (wq == "unavailable")
    non_exact_mask = ~unavailable_mask & (wq != "exact")
    exact_mask = ~unavailable_mask & ~non_exact_mask

    rates_df = pd.DataFrame(
        [
            {
                "region_id": str(k[0]),
                "season": str(k[1]),
                "lead_bucket": str(k[2]),
                "_rate": float(v),
                "_in_group": 1,
            }
            for k, v in model.group_rates.items()
        ]
    )
    for col in BASELINE_GROUP_KEYS:
        if rates_df.empty:
            rates_df[col] = pd.Series(dtype=str)
        else:
            rates_df[col] = rates_df[col].astype(str)

    temp_df = result[list(BASELINE_GROUP_KEYS)].copy()
    for col in BASELINE_GROUP_KEYS:
        temp_df[col] = temp_df[col].astype(str)
    temp_df["_orig_idx"] = np.arange(len(result))

    merged = temp_df.merge(rates_df, on=list(BASELINE_GROUP_KEYS), how="left").sort_values("_orig_idx")

    p = np.full(len(result), np.nan, dtype=float)
    status = np.full(len(result), "", dtype=object)

    status[unavailable_mask] = "unavailable_window"
    status[non_exact_mask] = "non_exact_window"

    in_group = merged["_in_group"].fillna(0).astype(bool).to_numpy()
    rate_vals = merged["_rate"].to_numpy(dtype=float)

    is_group_train = exact_mask & in_group
    is_fallback = exact_mask & (~in_group)

    p[is_group_train] = rate_vals[is_group_train]
    status[is_group_train] = "group_train_climatology"

    p[is_fallback] = model.global_train_rate
    status[is_fallback] = "global_train_fallback"

    result["p_climatology"] = p
    result["climatology_status"] = status
    return result


def assess_spread_only_readiness(rows: pd.DataFrame) -> BaselineReadiness:
    """Report whether the real ensemble-spread input exists; never synthesize it."""
    required = ("rain_member_std",)
    missing = tuple(column for column in required if column not in rows.columns)
    if missing:
        return BaselineReadiness(
            status="blocked_missing_features",
            missing_columns=missing,
            message="Spread-only baseline requires measured ensemble spread from real member data.",
        )

    usable = rows.loc[
        rows["lead_day"].between(1, 9)
        & rows["window_quality"].eq("exact")
        & rows["rain_member_std"].notna()
    ]
    if usable.empty:
        return BaselineReadiness(
            status="insufficient_data",
            message="Spread-only baseline has no eligible measured ensemble-spread rows.",
        )
    return BaselineReadiness(status="ready", message="Measured ensemble spread is available.")


def build_climatology_evaluation_artifact(
    *,
    manifest_id: str,
    git_commit: str,
    seed: int,
    train_count: int,
    validation_count: int,
    test_count: int,
    test_evaluation: ProbabilityEvaluation,
    spread_readiness: BaselineReadiness,
    validation_evaluation: ProbabilityEvaluation | None = None,
    split_id: str = FROZEN_SPLIT_ID,
    group_keys: tuple[str, ...] = BASELINE_GROUP_KEYS,
    hyperparameters: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a serializable, evidence-bound evaluation artifact for the climatology baseline."""
    group_hash = sha256(
        json.dumps(list(group_keys), separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()

    params = dict(hyperparameters or {})
    params.setdefault("policy", "regional_x_season_x_lead_bucket_train_only")
    params.setdefault("floor_mm", 10.0)
    params.setdefault("fallback", "global_train_rate")

    artifact: dict[str, Any] = {
        "schema_version": "1.0",
        "model_type": "climatology_baseline",
        "status": test_evaluation.status,
        "message": test_evaluation.message,
        "sample_counts": {
            "train_eligible": train_count,
            "validation_eligible": validation_count,
            "test_eligible": test_count,
        },
        "test_evaluation": {
            "status": test_evaluation.status,
            "sample_count": test_evaluation.sample_count,
            "metrics": test_evaluation.metrics,
            "reliability": test_evaluation.reliability,
            "message": test_evaluation.message,
        },
        "spread_only_baseline": {
            "status": spread_readiness.status,
            "missing_columns": list(spread_readiness.missing_columns),
            "message": spread_readiness.message,
        },
        "run": {
            "manifest_id": manifest_id,
            "git_commit": git_commit,
            "split_id": split_id,
            "seed": seed,
            "group_keys": list(group_keys),
            "group_keys_sha256": group_hash,
            "hyperparameters": params,
        },
    }
    if validation_evaluation is not None:
        artifact["validation_evaluation"] = {
            "status": validation_evaluation.status,
            "sample_count": validation_evaluation.sample_count,
            "metrics": validation_evaluation.metrics,
            "reliability": validation_evaluation.reliability,
            "message": validation_evaluation.message,
        }
    return artifact


def run_climatology_baseline_pipeline(
    dataset_path: Path | str,
    model_output_path: Path | str,
    metrics_output_path: Path | str,
    manifest_path: Path | str | None = None,
    seed: int = 42,
    replace: bool = False,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Execute the train-only climatology baseline workflow and produce honest local artifacts."""
    dataset_p = Path(dataset_path)
    model_out_p = Path(model_output_path)
    metrics_out_p = Path(metrics_output_path)

    if not dataset_p.exists():
        raise FileNotFoundError(f"Processed dataset not found: {dataset_p}")

    if not replace:
        if model_out_p.exists():
            raise FileExistsError(
                f"Refusing to overwrite existing model artifact: {model_out_p}. Use --replace to allow."
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
    columns_to_read = ["split", "lead_day", "window_quality", "bust", *BASELINE_GROUP_KEYS]
    if "rain_member_std" in schema.names:
        columns_to_read.append("rain_member_std")
    table = pq.read_table(dataset_p, columns=columns_to_read)
    df = table.to_pandas()

    spread_readiness = assess_spread_only_readiness(df)

    model = fit_climatology_baseline(df)

    df = apply_climatology_baseline(df, model)

    test_eval = evaluate_held_out_probabilities(df, "p_climatology", split="test")

    val_eval = evaluate_held_out_probabilities(df, "p_climatology", split="validation")

    eligible_train = int(
        (
            df["split"].eq("train")
            & df["lead_day"].between(1, 9)
            & df["window_quality"].eq("exact")
            & df["bust"].notna()
        ).sum()
    )
    eligible_val = int(
        (
            df["split"].eq("validation")
            & df["lead_day"].between(1, 9)
            & df["window_quality"].eq("exact")
            & df["bust"].notna()
        ).sum()
    )
    eligible_test = int(
        (
            df["split"].eq("test")
            & df["lead_day"].between(1, 9)
            & df["window_quality"].eq("exact")
            & df["bust"].notna()
        ).sum()
    )

    group_hash = sha256(
        json.dumps(list(BASELINE_GROUP_KEYS), separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()

    model_artifact = {
        "schema_version": "1.0",
        "model_type": "climatology_baseline",
        "status": "ready",
        "train_sample_count": eligible_train,
        "num_groups": len(model.group_rates),
        "global_train_rate": model.global_train_rate,
        "group_keys": list(BASELINE_GROUP_KEYS),
        "group_rates": {
            f"{k[0]}|{k[1]}|{k[2]}": rate
            for k, rate in sorted(model.group_rates.items())
        },
        "spread_only_baseline": {
            "status": spread_readiness.status,
            "missing_columns": list(spread_readiness.missing_columns),
            "message": spread_readiness.message,
        },
        "run": {
            "manifest_id": manifest_id,
            "git_commit": commit,
            "split_id": FROZEN_SPLIT_ID,
            "seed": seed,
            "group_keys": list(BASELINE_GROUP_KEYS),
            "group_keys_sha256": group_hash,
            "hyperparameters": {
                "policy": "regional_x_season_x_lead_bucket_train_only",
                "floor_mm": 10.0,
                "fallback": "global_train_rate",
            },
        },
    }

    eval_artifact = build_climatology_evaluation_artifact(
        manifest_id=manifest_id,
        git_commit=commit,
        split_id=FROZEN_SPLIT_ID,
        seed=seed,
        train_count=eligible_train,
        validation_count=eligible_val,
        test_count=eligible_test,
        test_evaluation=test_eval,
        spread_readiness=spread_readiness,
        validation_evaluation=val_eval,
    )

    def _write_json_atomic(target_path: Path, data: dict[str, Any]) -> None:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = target_path.with_suffix(f".tmp_{os.getpid()}_{uuid.uuid4().hex[:8]}.json")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        tmp.replace(target_path)

    _write_json_atomic(model_out_p, model_artifact)
    _write_json_atomic(metrics_out_p, eval_artifact)

    return {
        "manifest_id": manifest_id,
        "git_commit": commit,
        "model_output": str(model_out_p),
        "metrics_output": str(metrics_out_p),
        "sample_counts": {
            "train_eligible": eligible_train,
            "validation_eligible": eligible_val,
            "test_eligible": eligible_test,
        },
        "test_evaluation": {
            "status": test_eval.status,
            "sample_count": test_eval.sample_count,
            "metrics": test_eval.metrics,
            "reliability": test_eval.reliability,
        },
        "spread_only_status": spread_readiness.status,
    }
