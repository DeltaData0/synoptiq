"""Unit and hand-checked tests for verification time windows and accumulation intervals."""

from datetime import UTC, datetime, timedelta

import pytest

from bust.data.align import (
    exact_24h_total,
    get_exact_lead_window,
    get_imd_date_label,
    get_lead_window,
)


def test_exact_intervals_tile_a_24_hour_window() -> None:
    start = datetime(2018, 8, 2, 3, tzinfo=UTC)
    intervals = [(start + timedelta(hours=3 * i), start + timedelta(hours=3 * (i + 1)), 1.0) for i in range(8)]
    assert exact_24h_total(intervals, start, start + timedelta(hours=24)) == 8.0


def test_gap_is_rejected() -> None:
    start = datetime(2018, 8, 2, 3, tzinfo=UTC)
    intervals = [(start, start + timedelta(hours=3), 1.0), (start + timedelta(hours=6), start + timedelta(hours=24), 1.0)]
    with pytest.raises(ValueError, match="gap"):
        exact_24h_total(intervals, start, start + timedelta(hours=24))


def test_d1_exact_mapping_for_00z_init() -> None:
    """Lead Day 1 for 00 UTC init maps to [init + 3h, init + 27h) with window_quality='exact'."""
    init = datetime(2018, 8, 1, 0, 0, tzinfo=UTC)
    start, end, quality = get_lead_window(init, lead_day=1)

    assert start == datetime(2018, 8, 1, 3, 0, tzinfo=UTC)
    assert end == datetime(2018, 8, 2, 3, 0, tzinfo=UTC)
    assert quality == "exact"
    assert end - start == timedelta(hours=24)

    # Date label for Day 1 is init + 1 day = 2018-08-02
    assert get_imd_date_label(init, lead_day=1) == "2018-08-02"


def test_d9_exact_mapping_for_00z_init() -> None:
    """Lead Day 9 for 00 UTC init maps to [init + 195h, init + 219h) with window_quality='exact'."""
    init = datetime(2018, 8, 1, 0, 0, tzinfo=UTC)
    start, end, quality = get_lead_window(init, lead_day=9)

    assert start == datetime(2018, 8, 9, 3, 0, tzinfo=UTC)
    assert end == datetime(2018, 8, 10, 3, 0, tzinfo=UTC)
    assert quality == "exact"
    assert end - start == timedelta(hours=24)

    # Date label for Day 9 is init + 9 days = 2018-08-10
    assert get_imd_date_label(init, lead_day=9) == "2018-08-10"


def test_d10_returns_unavailable_not_invented_interval() -> None:
    """Lead Day 10 must return window_quality='unavailable' and reject exact alignment requests."""
    init = datetime(2018, 8, 1, 0, 0, tzinfo=UTC)
    start, end, quality = get_lead_window(init, lead_day=10)

    assert start == datetime(2018, 8, 10, 3, 0, tzinfo=UTC)
    assert end == datetime(2018, 8, 11, 3, 0, tzinfo=UTC)
    assert quality == "unavailable"

    with pytest.raises(ValueError, match="Day 10 is unavailable because the exact \\+240–\\+243-hour accumulation"):
        get_exact_lead_window(init, lead_day=10)


def test_utc_naive_timestamps_are_rejected() -> None:
    """Timezone-naive datetimes must raise ValueError across alignment and accumulation functions."""
    naive_dt = datetime(2018, 8, 1, 0, 0)
    aware_dt = datetime(2018, 8, 1, 0, 0, tzinfo=UTC)

    with pytest.raises(ValueError, match="timezone-aware UTC"):
        get_lead_window(naive_dt, lead_day=1)

    with pytest.raises(ValueError, match="timezone-aware UTC"):
        get_imd_date_label(naive_dt, lead_day=1)

    intervals = [(naive_dt, naive_dt + timedelta(hours=24), 5.0)]
    with pytest.raises(ValueError, match="timezone-aware UTC"):
        exact_24h_total(intervals, naive_dt, naive_dt + timedelta(hours=24))

    # Mixed aware target with naive intervals
    with pytest.raises(ValueError, match="timezone-aware UTC"):
        exact_24h_total(intervals, aware_dt, aware_dt + timedelta(hours=24))


def test_non_zero_utc_offsets_are_rejected() -> None:
    """Timezone-aware datetimes with non-zero offsets (e.g. IST UTC+05:30) must be rejected."""
    from datetime import timezone

    ist = timezone(timedelta(hours=5, minutes=30))
    ist_dt = datetime(2018, 8, 1, 5, 30, tzinfo=ist)  # Equal in instant to 00:00 UTC, but non-zero offset
    utc_dt = datetime(2018, 8, 1, 0, 0, tzinfo=UTC)

    with pytest.raises(ValueError, match="UTC offset of exactly zero"):
        get_lead_window(ist_dt, lead_day=1)

    with pytest.raises(ValueError, match="UTC offset of exactly zero"):
        get_imd_date_label(ist_dt, lead_day=1)

    # exact_24h_total rejects IST start/end
    with pytest.raises(ValueError, match="UTC offset of exactly zero"):
        exact_24h_total([], ist_dt, utc_dt + timedelta(hours=24))

    with pytest.raises(ValueError, match="UTC offset of exactly zero"):
        exact_24h_total([], utc_dt, ist_dt + timedelta(hours=24))

    # exact_24h_total rejects IST interval timestamps
    ist_intervals = [(ist_dt, ist_dt + timedelta(hours=24), 10.0)]
    with pytest.raises(ValueError, match="UTC offset of exactly zero"):
        exact_24h_total(ist_intervals, utc_dt, utc_dt + timedelta(hours=24))


def test_unsupported_leads_and_inits_are_rejected() -> None:
    """Leads outside 1..10 and non-00 UTC initializations must raise ValueError."""
    init_00z = datetime(2018, 8, 1, 0, 0, tzinfo=UTC)
    init_12z = datetime(2018, 8, 1, 12, 0, tzinfo=UTC)

    with pytest.raises(ValueError, match="lead_day must be an integer between 1 and 10"):
        get_lead_window(init_00z, lead_day=0)

    with pytest.raises(ValueError, match="lead_day must be an integer between 1 and 10"):
        get_lead_window(init_00z, lead_day=11)

    with pytest.raises(ValueError, match="Only 00 UTC GEFS initializations are supported"):
        get_lead_window(init_12z, lead_day=1)

    # get_imd_date_label reuses same validation
    with pytest.raises(ValueError, match="Only 00 UTC GEFS initializations are supported"):
        get_imd_date_label(init_12z, lead_day=1)

    # Day 10 is unavailable and prohibits creating an empirical label
    with pytest.raises(ValueError, match="Day 10 is unavailable"):
        get_imd_date_label(init_00z, lead_day=10)


def test_hand_check_case_3_d1_audited_interval_accumulation() -> None:
    """Hand-check Case 3: Recheck the D1-04 signed GRIB accumulation arithmetic.

    At 20.00°N, 78.00°E on 2018-08-01 00Z for Day 1 [2018-08-01 03:00Z, 2018-08-02 03:00Z):
    GRIB non-overlapping 3-hour derived amounts from gefs-20180801-p01-apcp:
    - 03–06h: 0.14 mm
    - 06–09h: 0.40 mm
    - 09–12h: 2.40 mm
    - 12–15h: 3.40 mm
    - 15–18h: 1.50 mm
    - 18–21h: 0.30 mm
    - 21–24h: 0.00 mm
    - 24–27h: 0.10 mm

    Transparent expected arithmetic:
    Total = 0.14 + 0.40 + 2.40 + 3.40 + 1.50 + 0.30 + 0.00 + 0.10 = 8.24 mm.
    """
    init = datetime(2018, 8, 1, 0, 0, tzinfo=UTC)
    target_start, target_end, quality = get_lead_window(init, lead_day=1)
    assert quality == "exact"
    assert target_start == datetime(2018, 8, 1, 3, 0, tzinfo=UTC)
    assert target_end == datetime(2018, 8, 2, 3, 0, tzinfo=UTC)

    amounts = [0.14, 0.40, 2.40, 3.40, 1.50, 0.30, 0.00, 0.10]
    expected_sum = sum(amounts)
    assert expected_sum == pytest.approx(8.24)

    intervals = [
        (
            init + timedelta(hours=3 + 3 * i),
            init + timedelta(hours=3 + 3 * (i + 1)),
            amounts[i],
        )
        for i in range(8)
    ]

    total_accum = exact_24h_total(intervals, target_start, target_end)
    assert total_accum == pytest.approx(8.24)
