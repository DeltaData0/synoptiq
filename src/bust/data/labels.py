"""Leakage-safe label helpers and classification policies."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from bust.data.align import validate_utc_datetime


def get_season(valid_end_utc: datetime) -> str:
    """Return the season label ('JJAS' or 'other') for a given valid_end_utc timestamp.

    Per config/label_policy.yaml: months 6, 7, 8, 9 are 'JJAS'; all others are 'other'.
    """
    validate_utc_datetime(valid_end_utc, "valid_end_utc")
    if valid_end_utc.month in (6, 7, 8, 9):
        return "JJAS"
    return "other"


def get_lead_bucket(lead_day: int) -> str:
    """Return the lead bucket ('1-3', '4-7', or '8-10') for a lead day between 1 and 10."""
    if not isinstance(lead_day, int) or not (1 <= lead_day <= 10):
        raise ValueError(f"lead_day must be an integer between 1 and 10; got {lead_day!r}")
    if 1 <= lead_day <= 3:
        return "1-3"
    if 4 <= lead_day <= 7:
        return "4-7"
    return "8-10"


def compute_error_mm(f_control_mm: float | None, o_imd_mm: float | None) -> float | None:
    """Compute absolute forecast error abs(F - O), returning None if either input is missing."""
    if f_control_mm is None or o_imd_mm is None:
        return None
    return float(abs(f_control_mm - o_imd_mm))


def compute_bust(error_mm: float | None, threshold_mm: float | None) -> bool | None:
    """Return True if error_mm strictly exceeds threshold_mm, or None if either is missing."""
    if error_mm is None or threshold_mm is None:
        return None
    return bool(error_mm > threshold_mm)


def fit_thresholds(train_rows: pd.DataFrame, floor_mm: float = 10.0) -> pd.Series:
    """Fit regional x season x lead-bucket q90 error thresholds with a minimum floor on train rows only."""
    required = {"region_id", "season", "lead_bucket", "error_mm", "split"}
    if missing := required - set(train_rows.columns):
        raise ValueError(f"Missing label fields: {sorted(missing)}")
    if set(train_rows["split"].dropna().unique()) - {"train"}:
        raise ValueError("Thresholds may be fit only on train rows")
    keys = ["region_id", "season", "lead_bucket"]
    return train_rows.groupby(keys)["error_mm"].quantile(0.90).clip(lower=floor_mm)
