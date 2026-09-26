"""GRIB decoding contracts."""


def require_step_metadata(record: dict) -> None:
    required = {"shortName", "stepType", "startStep", "endStep", "units"}
    missing = required - record.keys()
    if missing:
        raise ValueError(f"GRIB record missing required metadata: {sorted(missing)}")

