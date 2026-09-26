from datetime import UTC, datetime, timedelta

import pytest

from bust.data.align import exact_24h_total


def test_overlap_is_rejected() -> None:
    start = datetime(2018, 8, 2, 3, tzinfo=UTC)
    intervals = [
        (start, start + timedelta(hours=12), 3.0),
        (start + timedelta(hours=9), start + timedelta(hours=24), 4.0),
    ]
    with pytest.raises(ValueError, match="gap, overlap"):
        exact_24h_total(intervals, start, start + timedelta(hours=24))

