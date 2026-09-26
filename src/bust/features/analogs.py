"""Chronology guard for analog retrieval."""

from datetime import datetime


def assert_earlier_analog(query_init: datetime, analog_init: datetime) -> None:
    if analog_init >= query_init:
        raise ValueError("Analog initialization must precede the query initialization")

