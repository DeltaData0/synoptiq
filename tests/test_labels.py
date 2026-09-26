import pandas as pd

from bust.data.labels import fit_thresholds


def test_threshold_has_material_error_floor() -> None:
    rows = pd.DataFrame(
        {
            "region_id": ["r"] * 3,
            "season": ["JJAS"] * 3,
            "lead_bucket": ["1-3"] * 3,
            "error_mm": [1.0, 2.0, 3.0],
            "split": ["train"] * 3,
        }
    )
    assert fit_thresholds(rows).iloc[0] == 10.0

