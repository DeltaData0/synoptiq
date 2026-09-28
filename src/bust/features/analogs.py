"""Leakage-safe chronology utilities for previously ranked forecast analogs.

This module intentionally does *not* define an analog similarity metric. The
future model pipeline must provide candidates already ranked from issue-time
features only. Here we enforce the non-negotiable temporal boundary: an analog
can only come from an initialization strictly earlier than the queried one.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

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


def retrieve_c00_earlier_analogs(
    query_row: Mapping[str, Any] | pd.Series,
    candidate_pool: pd.DataFrame,
    *,
    limit: int = 5,
) -> AnalogSelection:
    """Retrieve strictly earlier c00 forecast analogs for a query forecast.

    Matches same region_id, season, and lead_bucket.
    Filters candidate analogs to strictly earlier issue time (init_utc < query.init_utc).
    Ranks using only issue-time c00 forecast similarity:
        abs(candidate.f_control_mm - query.f_control_mm)
    with deterministic tie-breaking (init_utc desc, lead_day asc).

    Day 10 or non-exact queries return an explicit 'unavailable' result without analogs.
    Returns at most `limit` analogs. If fewer than `limit` eligible candidates exist,
    returns status 'insufficient_earlier_analogs'.
    """
    if limit < 1:
        raise ValueError("Analog selection limit must be at least 1.")

    # Guard: Day 10 remains unavailable and must never receive an analog result
    query_lead = query_row.get("lead_day") if hasattr(query_row, "get") else query_row["lead_day"]
    query_window = (
        query_row.get("window_quality", "exact")
        if hasattr(query_row, "get")
        else query_row["window_quality"]
    )
    if query_lead == 10 or query_window != "exact":
        return AnalogSelection(
            analogs=pd.DataFrame(),
            status="unavailable",
            requested_count=limit,
            rejected_not_earlier=0,
            message="Day 10 or non-exact forecast cannot receive analog retrieval.",
        )

    # Validate ranking feature
    validate_analog_rank_features(["f_control_mm"])

    # Required query fields
    query_init = query_row["init_utc"]
    query_timestamp = _require_utc(query_init, name="query.init_utc")
    query_region = query_row["region_id"]
    query_season = query_row["season"]
    query_lead_bucket = query_row["lead_bucket"]
    query_rain = float(query_row["f_control_mm"])

    if candidate_pool.empty:
        return AnalogSelection(
            analogs=pd.DataFrame(),
            status="insufficient_earlier_analogs",
            requested_count=limit,
            rejected_not_earlier=0,
            message="Only 0 strictly earlier analogs are available; do not pad or fabricate analog evidence.",
        )

    required_pool_cols = {"init_utc", "region_id", "season", "lead_bucket", "f_control_mm"}
    missing = sorted(required_pool_cols - set(candidate_pool.columns))
    if missing:
        raise ValueError(f"Candidate pool is missing required columns: {missing}")

    # Filter to matching region, season, lead_bucket, non-null f_control_mm
    mask = (
        candidate_pool["region_id"].eq(query_region)
        & candidate_pool["season"].eq(query_season)
        & candidate_pool["lead_bucket"].eq(query_lead_bucket)
        & candidate_pool["f_control_mm"].notna()
    )
    if "lead_day" in candidate_pool.columns:
        mask = mask & candidate_pool["lead_day"].between(1, 9)
    if "window_quality" in candidate_pool.columns:
        mask = mask & candidate_pool["window_quality"].eq("exact")

    matched_candidates = candidate_pool[mask].copy()
    if matched_candidates.empty:
        return AnalogSelection(
            analogs=pd.DataFrame(),
            status="insufficient_earlier_analogs",
            requested_count=limit,
            rejected_not_earlier=0,
            message="Only 0 strictly earlier analogs are available; do not pad or fabricate analog evidence.",
        )

    # Temporal filtering: candidate.init_utc < query.init_utc
    candidate_ts = pd.to_datetime(matched_candidates["init_utc"], utc=True)
    earlier_mask = candidate_ts < query_timestamp
    rejected_not_earlier = int((~earlier_mask).sum())

    eligible = matched_candidates[earlier_mask].copy()
    if eligible.empty:
        return AnalogSelection(
            analogs=pd.DataFrame(),
            status="insufficient_earlier_analogs",
            requested_count=limit,
            rejected_not_earlier=rejected_not_earlier,
            message="Only 0 strictly earlier analogs are available; do not pad or fabricate analog evidence.",
        )

    # Compute issue-time forecast similarity
    eligible["forecast_diff"] = (eligible["f_control_mm"].astype(float) - query_rain).abs()
    eligible["_parsed_init_utc"] = candidate_ts[earlier_mask]

    # Deterministic sorting: forecast_diff asc, init_utc desc, lead_day asc
    sort_cols = ["forecast_diff", "_parsed_init_utc"]
    sort_asc = [True, False]
    if "lead_day" in eligible.columns:
        sort_cols.append("lead_day")
        sort_asc.append(True)

    sorted_eligible = eligible.sort_values(by=sort_cols, ascending=sort_asc)
    selected = sorted_eligible.head(limit).drop(columns=["_parsed_init_utc"])

    if len(selected) == limit:
        return AnalogSelection(
            analogs=selected,
            status="complete",
            requested_count=limit,
            rejected_not_earlier=rejected_not_earlier,
            message=f"Selected {limit} strictly earlier analogs from c00 forecast similarity.",
        )
    return AnalogSelection(
        analogs=selected,
        status="insufficient_earlier_analogs",
        requested_count=limit,
        rejected_not_earlier=rejected_not_earlier,
        message=(
            f"Only {len(selected)} strictly earlier analogs are available; "
            "do not pad or fabricate analog evidence."
        ),
    )
