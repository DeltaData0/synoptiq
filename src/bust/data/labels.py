"""Leakage-safe label helpers."""

import pandas as pd


def fit_thresholds(train_rows: pd.DataFrame, floor_mm: float = 10.0) -> pd.Series:
    required = {"region_id", "season", "lead_bucket", "error_mm", "split"}
    if missing := required - set(train_rows.columns):
        raise ValueError(f"Missing label fields: {sorted(missing)}")
    if set(train_rows["split"].dropna().unique()) - {"train"}:
        raise ValueError("Thresholds may be fit only on train rows")
    keys = ["region_id", "season", "lead_bucket"]
    return train_rows.groupby(keys)["error_mm"].quantile(0.90).clip(lower=floor_mm)

