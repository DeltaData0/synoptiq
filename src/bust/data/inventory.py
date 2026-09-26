"""Typed source-manifest helpers. Remote object paths must be observed, never guessed."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceRecord:
    source_key: str
    provider: str
    variable: str
    init_utc: str
    status: str = "inventoried"

