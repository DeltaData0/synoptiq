"""Unit tests for leakage-safe label and feature policies."""

from datetime import UTC, datetime

import pandas as pd
import pytest

from bust.data.labels import (
    compute_bust,
    compute_error_mm,
    fit_thresholds,
    get_lead_bucket,
    get_season,
)


def test_threshold_has_material_error_floor() -> None:
    rows = pd.DataFrame(
        {
            "region_id": ["r"] * 3,
            "season": ["JJAS"] * 3,
            "lead_bucket": ["1-3"] * 3,
            "error_mm": [1.0, 2.0, 3.0],
            "split": ["train"] * 3,
        }
    )
    assert fit_thresholds(rows).iloc[0] == 10.0


def test_season_mapping() -> None:
    """Months 6, 7, 8, 9 are JJAS; all other months are other."""
    assert get_season(datetime(2018, 6, 15, tzinfo=UTC)) == "JJAS"
    assert get_season(datetime(2018, 7, 1, tzinfo=UTC)) == "JJAS"
    assert get_season(datetime(2018, 8, 2, tzinfo=UTC)) == "JJAS"
    assert get_season(datetime(2018, 9, 30, tzinfo=UTC)) == "JJAS"
    assert get_season(datetime(2018, 1, 1, tzinfo=UTC)) == "other"
    assert get_season(datetime(2018, 5, 31, tzinfo=UTC)) == "other"
    assert get_season(datetime(2018, 10, 1, tzinfo=UTC)) == "other"

    # Must reject naive datetime
    with pytest.raises(ValueError, match="timezone-aware UTC"):
        get_season(datetime(2018, 7, 1, 3, 0))  # noqa: DTZ001

    # Must reject non-zero offset timezone
    from datetime import timedelta, timezone

    ist = timezone(timedelta(hours=5, minutes=30))
    with pytest.raises(ValueError, match="UTC offset of exactly zero"):
        get_season(datetime(2018, 7, 1, 8, 30, tzinfo=ist))


def test_lead_bucket_mapping() -> None:
    """Leads 1-3 -> '1-3', 4-7 -> '4-7', 8-10 -> '8-10'."""
    assert get_lead_bucket(1) == "1-3"
    assert get_lead_bucket(3) == "1-3"
    assert get_lead_bucket(4) == "4-7"
    assert get_lead_bucket(7) == "4-7"
    assert get_lead_bucket(8) == "8-10"
    assert get_lead_bucket(10) == "8-10"

    with pytest.raises(ValueError, match="lead_day must be an integer between 1 and 10"):
        get_lead_bucket(0)
    with pytest.raises(ValueError, match="lead_day must be an integer between 1 and 10"):
        get_lead_bucket(11)


def test_error_and_bust_computation() -> None:
    """Error is abs(F - O); bust is error > threshold; missing values return None."""
    assert compute_error_mm(10.0, 5.0) == 5.0
    assert compute_error_mm(5.0, 10.0) == 5.0
    assert compute_error_mm(None, 5.0) is None
    assert compute_error_mm(10.0, None) is None

    assert compute_bust(15.0, 10.0) is True
    assert compute_bust(10.0, 10.0) is False  # Strictly exceeds
    assert compute_bust(8.0, 10.0) is False
    assert compute_bust(None, 10.0) is None
    assert compute_bust(15.0, None) is None
