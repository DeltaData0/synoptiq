"""Leakage-safe chronology utilities for previously ranked forecast analogs.

This module intentionally does *not* define an analog similarity metric. The
future model pipeline must provide candidates already ranked from issue-time
features only. Here we enforce the non-negotiable temporal boundary: an analog
can only come from an initialization strictly earlier than the queried one.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

import pandas as pd

FORBIDDEN_ANALOG_RANK_COLUMNS = frozenset(
    {
        "bust",
        "error_mm",
        "o_imd_mm",
        "observed_mm",
        "p_bust",
        "target",
        "threshold_mm",
    }
)


@dataclass(frozen=True)
class AnalogSelection:
    """A chronology-filtered analog result with an explicit fallback state."""

    analogs: pd.DataFrame
    status: str
    requested_count: int
    rejected_not_earlier: int
    message: str


def _require_utc(value: datetime | str | pd.Timestamp, *, name: str) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None or timestamp.utcoffset() != timedelta(0):
        raise ValueError(f"{name} must have an explicit zero UTC offset.")
    return timestamp.tz_convert("UTC")


def assert_earlier_analog(query_init: datetime, analog_init: datetime) -> None:
    """Reject same-init and future analogs under the project's UTC contract."""
    query_timestamp = _require_utc(query_init, name="query_init")
    analog_timestamp = _require_utc(analog_init, name="analog_init")
    if analog_timestamp >= query_timestamp:
        raise ValueError("Analog initialization must precede the query initialization")


def validate_analog_rank_features(feature_columns: Sequence[str]) -> tuple[str, ...]:
    """Reject observation/label-derived inputs to an analog similarity ranking.

    Returned analog rows may display a past analog's observed error as evidence,
    but those fields must never determine which candidates are retrieved.
    """
    columns = tuple(feature_columns)
    forbidden = sorted(set(columns) & FORBIDDEN_ANALOG_RANK_COLUMNS)
    if forbidden:
        raise ValueError(
            "Analog ranking may use issue-time features only; forbidden columns: "
            f"{forbidden}"
        )
    return columns


def select_earlier_analogs(
    query_init: datetime | str | pd.Timestamp,
    ranked_candidates: pd.DataFrame,
    *,
    limit: int = 5,
    init_column: str = "init_utc",
) -> AnalogSelection:
    """Keep the first ``limit`` strictly earlier candidates from an input ranking.

    The caller owns the similarity metric and supplies its ranking in order.
    This function never reads, sorts on, or derives an outcome/error/label field.
    Same-init and future candidates are rejected from the returned result. If
    fewer than ``limit`` eligible candidates remain, the explicit fallback is
    ``insufficient_earlier_analogs``; rows are never invented or duplicated.
    """
    if limit < 1:
        raise ValueError("Analog selection limit must be at least 1.")
    if init_column not in ranked_candidates.columns:
        raise ValueError(f"Ranked analog candidates are missing {init_column!r}.")

    query_timestamp = _require_utc(query_init, name="query_init")
    accepted_positions: list[int] = []
    rejected_not_earlier = 0
    for position, candidate_init in enumerate(ranked_candidates[init_column].tolist()):
        candidate_timestamp = _require_utc(candidate_init, name=f"candidate[{position}].{init_column}")
        if candidate_timestamp >= query_timestamp:
            rejected_not_earlier += 1
            continue
        accepted_positions.append(position)
        if len(accepted_positions) == limit:
            break

    analogs = ranked_candidates.iloc[accepted_positions].copy()
    if len(analogs) == limit:
        return AnalogSelection(
            analogs=analogs,
            status="complete",
            requested_count=limit,
            rejected_not_earlier=rejected_not_earlier,
            message=f"Selected {limit} strictly earlier analogs from the supplied issue-time ranking.",
        )
    return AnalogSelection(
        analogs=analogs,
        status="insufficient_earlier_analogs",
        requested_count=limit,
        rejected_not_earlier=rejected_not_earlier,
        message=(
            f"Only {len(analogs)} strictly earlier analogs are available; "
            "do not pad or fabricate analog evidence."
        ),
    )
