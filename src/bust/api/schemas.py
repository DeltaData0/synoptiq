"""Pydantic models for the stable replay API contract."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    data_mode: Literal["fixture", "historical_replay"]


class FeatureProperties(BaseModel):
    region_id: str
    valid_start_utc: str | None
    valid_end_utc: str | None
    p_bust: float | None = Field(default=None, ge=0, le=1)
    tier: Literal["low", "watch", "high", "no_data"]
    threshold_mm: float | None = Field(default=None, ge=0)
    window_quality: Literal["exact", "approximate", "unavailable"]
    provenance: str
    no_data_reason: str | None = None


class ReplayFeature(BaseModel):
    type: Literal["Feature"]
    geometry: dict[str, Any]
    properties: FeatureProperties


class ReplayResponse(BaseModel):
    type: Literal["FeatureCollection"]
    data_mode: Literal["fixture", "historical_replay"]
    model: str
    truth_source: str
    features: list[ReplayFeature]


class Reason(BaseModel):
    group: str
    direction: str
    feature: str
    value: float | None
    train_range: list[float] | None
    caption: str
    evidence_layer: str


class RegionResponse(BaseModel):
    region_id: str
    init_utc: str
    lead_day: int = Field(ge=1, le=10)
    p_bust: float | None = Field(default=None, ge=0, le=1)
    confidence_complement: float | None = Field(default=None, ge=0, le=1)
    forecast_mm: float | None
    observed_mm: float | None
    threshold_mm: float | None
    window_quality: Literal["exact", "approximate", "unavailable"]
    data_mode: Literal["fixture", "historical_replay"]
    provenance: str
    reasons: list[Reason]
    analogs: list[dict[str, Any]]
    caveats: list[str]


class EvaluationResponse(BaseModel):
    data_mode: Literal["fixture", "historical_replay"]
    status: str
    message: str
    metrics: dict[str, Any] | None

