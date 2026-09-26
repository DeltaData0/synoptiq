from datetime import UTC, datetime, timedelta

import pytest

from bust.data.align import exact_24h_total


def test_exact_intervals_tile_a_24_hour_window() -> None:
    start = datetime(2018, 8, 2, 3, tzinfo=UTC)
    intervals = [(start + timedelta(hours=3 * i), start + timedelta(hours=3 * (i + 1)), 1.0) for i in range(8)]
    assert exact_24h_total(intervals, start, start + timedelta(hours=24)) == 8.0


def test_gap_is_rejected() -> None:
    start = datetime(2018, 8, 2, 3, tzinfo=UTC)
    intervals = [(start, start + timedelta(hours=3), 1.0), (start + timedelta(hours=6), start + timedelta(hours=24), 1.0)]
    with pytest.raises(ValueError, match="gap"):
        exact_24h_total(intervals, start, start + timedelta(hours=24))

