"""Regression tests for leakage-safe analog chronology selection."""

from datetime import UTC, datetime, timedelta, timezone

import pandas as pd
import pytest

from bust.features.analogs import (
    assert_earlier_analog,
    retrieve_c00_earlier_analogs,
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


def test_retrieve_c00_earlier_analogs_chronology_and_same_init_rejection() -> None:
    query = {
        "init_utc": "2018-08-10T00:00:00Z",
        "region_id": "R20N-078E",
        "season": "JJAS",
        "lead_bucket": "1-3",
        "lead_day": 2,
        "window_quality": "exact",
        "f_control_mm": 25.0,
    }
    pool = pd.DataFrame(
        {
            "init_utc": [
                "2018-08-11T00:00:00Z",  # future -> rejected
                "2018-08-10T00:00:00Z",  # same-init -> rejected
                "2018-08-09T00:00:00Z",  # earlier -> eligible
                "2017-08-10T00:00:00Z",  # earlier -> eligible
            ],
            "region_id": ["R20N-078E"] * 4,
            "season": ["JJAS"] * 4,
            "lead_bucket": ["1-3"] * 4,
            "lead_day": [2] * 4,
            "window_quality": ["exact"] * 4,
            "f_control_mm": [25.0, 25.0, 24.0, 26.0],
            "error_mm": [0.0, 0.0, 5.0, 3.0],
            "bust": [0, 0, 0, 1],
        }
    )

    selection = retrieve_c00_earlier_analogs(query, pool, limit=5)
    assert selection.status == "insufficient_earlier_analogs"
    assert selection.rejected_not_earlier == 2
    assert len(selection.analogs) == 2
    assert (pd.to_datetime(selection.analogs["init_utc"], utc=True) < pd.Timestamp(query["init_utc"])).all()
    # Post-hoc evidence fields preserved without influencing ranking
    assert "error_mm" in selection.analogs.columns
    assert "bust" in selection.analogs.columns


def test_retrieve_c00_earlier_analogs_deterministic_ranking_and_five_cap() -> None:
    query = {
        "init_utc": "2018-08-10T00:00:00Z",
        "region_id": "R20N-078E",
        "season": "JJAS",
        "lead_bucket": "1-3",
        "lead_day": 1,
        "window_quality": "exact",
        "f_control_mm": 20.0,
    }
    # 7 candidates with varying rain and dates
    inits = [
        "2016-08-01T00:00:00Z",
        "2016-08-02T00:00:00Z",
        "2016-08-03T00:00:00Z",
        "2017-08-01T00:00:00Z",
        "2017-08-02T00:00:00Z",
        "2017-08-03T00:00:00Z",
        "2017-08-04T00:00:00Z",
    ]
    rains = [20.0, 21.0, 19.5, 20.0, 22.0, 18.0, 30.0]
    pool = pd.DataFrame(
        {
            "init_utc": inits,
            "region_id": ["R20N-078E"] * 7,
            "season": ["JJAS"] * 7,
            "lead_bucket": ["1-3"] * 7,
            "lead_day": [1] * 7,
            "window_quality": ["exact"] * 7,
            "f_control_mm": rains,
        }
    )

    selection = retrieve_c00_earlier_analogs(query, pool, limit=5)
    assert selection.status == "complete"
    assert len(selection.analogs) == 5
    # Tied forecast_diff (0.0): 2017-08-01 should precede 2016-08-01 due to desc init_utc tie-breaking
    assert selection.analogs.iloc[0]["init_utc"] == "2017-08-01T00:00:00Z"
    assert selection.analogs.iloc[1]["init_utc"] == "2016-08-01T00:00:00Z"
    # Next closest diff (0.5): 19.5 on 2016-08-03
    assert selection.analogs.iloc[2]["f_control_mm"] == 19.5
    # Next closest diff (1.0): 21.0 on 2016-08-02
    assert selection.analogs.iloc[3]["f_control_mm"] == 21.0
    # Next closest diff (2.0): ties 22.0 (2017-08-02) and 18.0 (2017-08-03), 2017-08-03 has later init
    assert selection.analogs.iloc[4]["init_utc"] == "2017-08-03T00:00:00Z"


def test_retrieve_c00_earlier_analogs_day10_and_non_exact_unavailable() -> None:
    pool = pd.DataFrame(
        {
            "init_utc": ["2016-08-01T00:00:00Z"],
            "region_id": ["R20N-078E"],
            "season": ["JJAS"],
            "lead_bucket": ["8-10"],
            "lead_day": [9],
            "window_quality": ["exact"],
            "f_control_mm": [10.0],
        }
    )
    # Day 10 query
    query_day10 = {
        "init_utc": "2018-08-10T00:00:00Z",
        "region_id": "R20N-078E",
        "season": "JJAS",
        "lead_bucket": "8-10",
        "lead_day": 10,
        "window_quality": "unavailable",
        "f_control_mm": 10.0,
    }
    sel_day10 = retrieve_c00_earlier_analogs(query_day10, pool)
    assert sel_day10.status == "unavailable"
    assert len(sel_day10.analogs) == 0

    # Non-exact query
    query_approx = {
        "init_utc": "2018-08-10T00:00:00Z",
        "region_id": "R20N-078E",
        "season": "JJAS",
        "lead_bucket": "1-3",
        "lead_day": 2,
        "window_quality": "approximate",
        "f_control_mm": 10.0,
    }
    sel_approx = retrieve_c00_earlier_analogs(query_approx, pool)
    assert sel_approx.status == "unavailable"
    assert len(sel_approx.analogs) == 0
