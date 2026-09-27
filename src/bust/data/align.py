"""Verification-window guards for accumulated rainfall and audited lead-window mapping."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta


def validate_utc_datetime(
    dt: datetime,
    param_name: str = "datetime",
    require_00_utc: bool = False,
) -> datetime:
    """Validate that dt is a timezone-aware datetime with exact 00:00 UTC offset.

    Rejects:
    - Non-datetime instances.
    - Naive datetimes (dt.tzinfo is None or dt.utcoffset() is None).
    - Timezone-aware datetimes with non-zero UTC offset (e.g. IST +05:30, EST -05:00).
    - Non-00:00:00 UTC times when require_00_utc is True.
    """
    if not isinstance(dt, datetime):
        raise TypeError(f"{param_name} must be a datetime instance; got {type(dt)!r}")

    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"{param_name} must be a timezone-aware UTC datetime; got naive datetime")

    if dt.utcoffset() != timedelta(0):
        raise ValueError(
            f"{param_name} must have a UTC offset of exactly zero (+00:00); "
            f"got offset {dt.utcoffset()} ({dt.tzinfo})"
        )

    if require_00_utc and (dt.hour != 0 or dt.minute != 0 or dt.second != 0 or dt.microsecond != 0):
        raise ValueError(
            f"Only 00 UTC GEFS initializations are supported; got {dt.strftime('%H:%M:%S')}"
        )

    return dt


def exact_24h_total(
    intervals: Iterable[tuple[datetime, datetime, float]],
    start: datetime,
    end: datetime,
) -> float:
    """Sum non-overlapping interval amounts only when they exactly tile a 24-hour target window.

    Guards:
    - start and end must be timezone-aware UTC datetimes with offset 0.
    - All interval endpoints must be timezone-aware UTC datetimes with offset 0.
    - end - start must be exactly 24 hours.
    - Intervals must be contiguous and non-overlapping, with no gaps or inversions.
    """
    validate_utc_datetime(start, "start")
    validate_utc_datetime(end, "end")

    if end - start != timedelta(hours=24):
        raise ValueError("Accumulations do not exactly cover the requested verification window")

    ordered = sorted(intervals, key=lambda item: item[0])
    if not ordered:
        raise ValueError("Accumulations do not exactly cover the requested verification window")

    for int_start, int_end, _ in ordered:
        validate_utc_datetime(int_start, "interval start")
        validate_utc_datetime(int_end, "interval end")

    if ordered[0][0] != start or ordered[-1][1] != end:
        raise ValueError("Accumulations do not exactly cover the requested verification window")

    cursor = start
    total = 0.0
    for interval_start, interval_end, amount_mm in ordered:
        if interval_start != cursor or interval_end <= interval_start:
            raise ValueError("Accumulations contain a gap, overlap, or invalid interval")
        total += amount_mm
        cursor = interval_end

    return total


def get_lead_window(init_utc: datetime, lead_day: int) -> tuple[datetime, datetime, str]:
    """Map a GEFS 00 UTC initialization datetime and lead day to the audited verification window.

    Signed D1-04 Policy:
    - IMD NetCDF date label D maps to [D - 1 day 03:00Z, D 03:00Z).
    - For 00 UTC GEFS initialization and lead L (1..9):
      Target window is [init + (24L-21)h, init + (24L+3)h).
      Window duration is exactly 24 hours, window_quality is 'exact'.
    - For lead L = 10:
      Target window is [init + 219h, init + 243h).
      Because the +240–+243-hour accumulation is unevidenced in the GEFS archive,
      window_quality is 'unavailable'. Never create an empirical Day-10 label.
    """
    validate_utc_datetime(init_utc, "init_utc", require_00_utc=True)

    if not isinstance(lead_day, int) or not (1 <= lead_day <= 10):
        raise ValueError(f"lead_day must be an integer between 1 and 10; got {lead_day!r}")

    if 1 <= lead_day <= 9:
        start = init_utc + timedelta(hours=24 * lead_day - 21)
        end = init_utc + timedelta(hours=24 * lead_day + 3)
        return start, end, "exact"

    start = init_utc + timedelta(hours=219)
    end = init_utc + timedelta(hours=243)
    return start, end, "unavailable"


def get_exact_lead_window(init_utc: datetime, lead_day: int) -> tuple[datetime, datetime]:
    """Return (start_utc, end_utc) for exact lead days 1..9, or raise ValueError for Day 10."""
    start, end, quality = get_lead_window(init_utc, lead_day)
    if quality != "exact":
        raise ValueError(
            f"Lead Day {lead_day} is unavailable: Day 10 is unavailable because the "
            "exact +240–+243-hour accumulation is not evidenced; no empirical label may be created."
        )
    return start, end


def get_imd_date_label(init_utc: datetime, lead_day: int) -> str:
    """Return the corresponding IMD daily NetCDF date label 'YYYY-MM-DD' for a 00 UTC init and lead day.

    Reuses get_lead_window to validate init_utc (timezone-aware, zero offset, 00:00 UTC)
    and lead_day (1..10).

    For Day 1–9, the window end is init + (24L+3)h at 03:00Z on calendar date D,
    which corresponds to IMD date label D.
    For Day 10, window_quality is 'unavailable' per D1-04 policy; raises ValueError
    because no empirical Day 10 label may be created.
    """
    _start_utc, end_utc, quality = get_lead_window(init_utc, lead_day)
    if quality != "exact":
        raise ValueError(
            f"Lead Day {lead_day} is unavailable: Day 10 is unavailable because the "
            "exact +240–+243-hour accumulation is not evidenced; no empirical label may be created."
        )
    return end_utc.date().isoformat()

