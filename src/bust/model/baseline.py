"""Leakage-safe baseline utilities for the forecast-bust task.

These functions deliberately operate only on already-built, aligned rows.  They
do not create labels, infer observations, or turn incomplete data into results.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


BASELINE_GROUP_KEYS = ("region_id", "season", "lead_bucket")
REQUIRED_ROW_COLUMNS = ("split", "lead_day", "window_quality", "bust", *BASELINE_GROUP_KEYS)


class InsufficientBaselineDataError(ValueError):
    """Raised when no eligible train rows exist for a baseline fit."""


@dataclass(frozen=True)
class ClimatologyBaseline:
    """Train-only regional/season/lead-bucket bust-rate baseline."""

    global_train_rate: float
    group_rates: dict[tuple[str, str, str], float]


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
    return ClimatologyBaseline(global_train_rate=global_rate, group_rates=group_rates)


def apply_climatology_baseline(rows: pd.DataFrame, model: ClimatologyBaseline) -> pd.DataFrame:
    """Attach a train-only climatology probability while preserving input order.

    Exact Day 1-9 rows use their regional/season/lead-bucket rate when one was
    observed in train.  A missing group falls back only to the global *train*
    rate.  Day 10 and unavailable rows receive null predictions.
    """
    _require_columns(rows, ("lead_day", "window_quality", *BASELINE_GROUP_KEYS))
    result = rows.copy()
    probabilities: list[float] = []
    status: list[str] = []

    for _, row in result.iterrows():
        if int(row["lead_day"]) == 10 or row["window_quality"] == "unavailable":
            probabilities.append(np.nan)
            status.append("unavailable_window")
            continue
        if row["window_quality"] != "exact":
            probabilities.append(np.nan)
            status.append("non_exact_window")
            continue

        key = tuple(str(row[column]) for column in BASELINE_GROUP_KEYS)
        if key in model.group_rates:
            probabilities.append(model.group_rates[key])
            status.append("group_train_climatology")
        else:
            probabilities.append(model.global_train_rate)
            status.append("global_train_fallback")

    result["p_climatology"] = probabilities
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
