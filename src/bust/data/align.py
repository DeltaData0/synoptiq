"""Verification-window guards for accumulated rainfall."""

from collections.abc import Iterable
from datetime import datetime


def exact_24h_total(intervals: Iterable[tuple[datetime, datetime, float]], start: datetime, end: datetime) -> float:
    """Sum non-overlapping interval amounts only when they exactly tile a target window."""
    ordered = sorted(intervals, key=lambda item: item[0])
    if not ordered or ordered[0][0] != start or ordered[-1][1] != end:
        raise ValueError("Accumulations do not exactly cover the requested verification window")
    cursor = start
    total = 0.0
    for interval_start, interval_end, amount_mm in ordered:
        if interval_start != cursor or interval_end <= interval_start:
            raise ValueError("Accumulations contain a gap, overlap, or invalid interval")
        total += amount_mm
        cursor = interval_end
    return total

