"""Tests for train-only baselines and held-out probability evaluation."""

import pandas as pd
import pytest

from bust.model.baseline import (
    InsufficientBaselineDataError,
    apply_climatology_baseline,
    assess_spread_only_readiness,
    fit_climatology_baseline,
)
from bust.model.evaluate import evaluate_held_out_probabilities


def _rows() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"split": "train", "lead_day": 1, "window_quality": "exact", "bust": False, "region_id": "R20", "season": "JJAS", "lead_bucket": "1-3"},
            {"split": "train", "lead_day": 1, "window_quality": "exact", "bust": True, "region_id": "R20", "season": "JJAS", "lead_bucket": "1-3"},
            {"split": "train", "lead_day": 4, "window_quality": "exact", "bust": True, "region_id": "R22", "season": "other", "lead_bucket": "4-7"},
            {"split": "validation", "lead_day": 1, "window_quality": "exact", "bust": True, "region_id": "R20", "season": "JJAS", "lead_bucket": "1-3"},
            {"split": "test", "lead_day": 1, "window_quality": "exact", "bust": False, "region_id": "R20", "season": "JJAS", "lead_bucket": "1-3"},
            {"split": "test", "lead_day": 2, "window_quality": "exact", "bust": True, "region_id": "UNSEEN", "season": "JJAS", "lead_bucket": "1-3"},
            {"split": "test", "lead_day": 10, "window_quality": "unavailable", "bust": None, "region_id": "R20", "season": "JJAS", "lead_bucket": "8-10"},
        ]
    )


def test_climatology_is_train_only_preserves_order_and_keeps_day10_null() -> None:
    rows = _rows()
    model = fit_climatology_baseline(rows)
    result = apply_climatology_baseline(rows, model)

    assert result.index.tolist() == rows.index.tolist()
    assert model.global_train_rate == pytest.approx(2 / 3)
    assert model.group_rates[("R20", "JJAS", "1-3")] == pytest.approx(0.5)
    assert result.loc[4, "p_climatology"] == pytest.approx(0.5)
    # The unseen group must use only global *train* prevalence, not test labels.
    assert result.loc[5, "p_climatology"] == pytest.approx(2 / 3)
    assert result.loc[5, "climatology_status"] == "global_train_fallback"
    assert pd.isna(result.loc[6, "p_climatology"])
    assert result.loc[6, "climatology_status"] == "unavailable_window"


def test_climatology_requires_eligible_train_rows() -> None:
    rows = _rows().query("split != 'train'")
    with pytest.raises(InsufficientBaselineDataError, match="zero eligible"):
        fit_climatology_baseline(rows)


def test_spread_baseline_is_explicitly_blocked_without_measured_spread() -> None:
    readiness = assess_spread_only_readiness(_rows())
    assert readiness.status == "blocked_missing_features"
    assert readiness.missing_columns == ("rain_member_std",)


def test_held_out_evaluation_uses_only_eligible_test_rows() -> None:
    rows = _rows()
    rows["p_climatology"] = [0.5, 0.5, 1.0, 0.5, 0.5, 2 / 3, None]
    result = evaluate_held_out_probabilities(rows, "p_climatology")

    assert result.status == "eligible_test_metrics"
    assert result.sample_count == 2
    assert result.metrics is not None
    assert result.metrics["brier_score"] == pytest.approx(((0.5 - 0) ** 2 + (2 / 3 - 1) ** 2) / 2)
    assert sum(item["count"] for item in result.reliability) == 2


def test_held_out_evaluation_reports_insufficient_data_without_inventing_metrics() -> None:
    rows = _rows().query("split != 'test'").copy()
    rows["p_climatology"] = 0.5
    result = evaluate_held_out_probabilities(rows, "p_climatology")

    assert result.status == "insufficient_test_data"
    assert result.sample_count == 0
    assert result.metrics is None
    assert result.reliability == []
