"""Validation-only sigmoid calibration with explicit no-data behavior."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression


@dataclass(frozen=True)
class SigmoidCalibrator:
    """A calibrator fit exclusively on eligible validation rows."""

    status: str
    sample_count: int
    estimator: LogisticRegression | None
    message: str


def _eligible_validation_rows(rows: pd.DataFrame, score_column: str) -> pd.DataFrame:
    required = {"split", "lead_day", "window_quality", "bust", score_column}
    missing = sorted(required - set(rows.columns))
    if missing:
        raise ValueError(f"Calibration rows are missing required columns: {missing}")
    return rows.loc[
        rows["split"].eq("validation")
        & rows["lead_day"].between(1, 9)
        & rows["window_quality"].eq("exact")
        & rows["bust"].notna()
        & rows[score_column].notna()
    ].copy()


def fit_validation_sigmoid_calibrator(
    rows: pd.DataFrame,
    score_column: str,
    *,
    seed: int = 42,
) -> SigmoidCalibrator:
    """Fit Platt-style calibration from validation rows and labels only.

    This deliberately filters the input by ``split == 'validation'`` before it
    reads either score or outcome. Train and test labels cannot affect the
    fitted estimator. A missing/single-class validation sample produces an
    explicit status rather than a fabricated calibrated probability.
    """
    eligible = _eligible_validation_rows(rows, score_column)
    if eligible.empty:
        return SigmoidCalibrator(
            status="insufficient_validation_data",
            sample_count=0,
            estimator=None,
            message="No eligible exact Day 1-9 validation rows are available for calibration.",
        )

    scores = eligible[score_column].astype(float).to_numpy()
    outcomes = eligible["bust"].astype(int).to_numpy()
    if np.any(~np.isfinite(scores)):
        raise ValueError(f"{score_column} must contain finite values for calibration.")
    if not np.isin(outcomes, (0, 1)).all():
        raise ValueError("Calibration bust labels must be boolean/0/1 values.")
    if np.unique(outcomes).size < 2:
        return SigmoidCalibrator(
            status="insufficient_validation_data",
            sample_count=len(eligible),
            estimator=None,
            message="Validation calibration requires both bust and non-bust rows.",
        )

    estimator = LogisticRegression(random_state=seed, solver="lbfgs")
    estimator.fit(scores.reshape(-1, 1), outcomes)
    return SigmoidCalibrator(
        status="ready",
        sample_count=len(eligible),
        estimator=estimator,
        message=f"Sigmoid calibrator fit on {len(eligible)} eligible validation rows only.",
    )


def apply_sigmoid_calibration(
    rows: pd.DataFrame,
    calibrator: SigmoidCalibrator,
    score_column: str,
    *,
    output_column: str = "p_calibrated",
) -> pd.DataFrame:
    """Apply a fitted calibrator without reading labels or changing unavailable rows."""
    required = {"lead_day", "window_quality", score_column}
    missing = sorted(required - set(rows.columns))
    if missing:
        raise ValueError(f"Calibration rows are missing required columns: {missing}")

    result = rows.copy()
    result[output_column] = np.nan
    if calibrator.status != "ready" or calibrator.estimator is None:
        return result

    eligible = (
        result["lead_day"].between(1, 9)
        & result["window_quality"].eq("exact")
        & result[score_column].notna()
    )
    scores = result.loc[eligible, score_column].astype(float).to_numpy()
    if np.any(~np.isfinite(scores)):
        raise ValueError(f"{score_column} must contain finite values for calibration.")
    result.loc[eligible, output_column] = calibrator.estimator.predict_proba(scores.reshape(-1, 1))[:, 1]
    return result
