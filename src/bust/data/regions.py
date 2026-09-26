"""Region coverage checks."""


def has_sufficient_coverage(coverage_fraction: float | None, minimum: float = 0.80) -> bool:
    return coverage_fraction is not None and coverage_fraction >= minimum

