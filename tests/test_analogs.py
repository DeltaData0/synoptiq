"""Regression tests for leakage-safe analog chronology selection."""

from datetime import UTC, datetime, timedelta, timezone

import pandas as pd
import pytest

from bust.features.analogs import (
    assert_earlier_analog,
    select_earlier_analogs,
    validate_analog_rank_features,
)

QUERY_INIT = datetime(2018, 8, 10, tzinfo=UTC)


def test_selection_rejects_same_and_future_candidates_preserving_prior_rank_order() -> None:
    candidates = pd.DataFrame(
        {
            "init_utc": [
                QUERY_INIT,
                QUERY_INIT + timedelta(days=1),
                QUERY_INIT - timedelta(days=2),
                QUERY_INIT - timedelta(days=3),
                QUERY_INIT - timedelta(days=5),
            ],
            # Past outcomes may be shown after retrieval, but selection does not read them.
            "error_mm": [999.0, 999.0, 3.0, 7.0, 11.0],
        }
    )

    selection = select_earlier_analogs(QUERY_INIT, candidates, limit=3)

    assert selection.status == "complete"
    assert selection.rejected_not_earlier == 2
    assert selection.analogs.index.tolist() == [2, 3, 4]
    assert selection.analogs["error_mm"].tolist() == [3.0, 7.0, 11.0]
    assert (pd.to_datetime(selection.analogs["init_utc"], utc=True) < QUERY_INIT).all()


def test_selection_returns_explicit_fallback_without_padding() -> None:
    candidates = pd.DataFrame(
        {
            "init_utc": [QUERY_INIT, QUERY_INIT - timedelta(days=1)],
            "similarity_rank": [1, 2],
        }
    )

    selection = select_earlier_analogs(QUERY_INIT, candidates, limit=5)

    assert selection.status == "insufficient_earlier_analogs"
    assert selection.requested_count == 5
    assert len(selection.analogs) == 1
    assert "do not pad" in selection.message


def test_selection_rejects_naive_or_non_utc_timestamps() -> None:
    with pytest.raises(ValueError, match="zero UTC offset"):
        assert_earlier_analog(
            QUERY_INIT,
            datetime(2018, 8, 9, tzinfo=timezone(timedelta(hours=5, minutes=30))),
        )

    candidates = pd.DataFrame({"init_utc": [datetime(2018, 8, 9, tzinfo=UTC)]})
    with pytest.raises(ValueError, match="zero UTC offset"):
        select_earlier_analogs(
            datetime(2018, 8, 10, tzinfo=timezone(timedelta(hours=5, minutes=30))),
            candidates,
        )


def test_rank_feature_validation_rejects_observation_and_label_columns() -> None:
    assert validate_analog_rank_features(["control_rain_mm", "pwat_mean"]) == (
        "control_rain_mm",
        "pwat_mean",
    )
    with pytest.raises(ValueError, match="issue-time features only"):
        validate_analog_rank_features(["control_rain_mm", "error_mm", "bust", "o_imd_mm"])
