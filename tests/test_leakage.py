from datetime import UTC, datetime

import pandas as pd
import pytest

from bust.data.labels import fit_thresholds
from bust.features.analogs import assert_earlier_analog


def test_threshold_rejects_validation_rows() -> None:
    rows = pd.DataFrame(
        {
            "region_id": ["r"], "season": ["JJAS"], "lead_bucket": ["1-3"],
            "error_mm": [20.0], "split": ["validation"],
        }
    )
    with pytest.raises(ValueError, match="train"):
        fit_thresholds(rows)


def test_future_analog_is_rejected() -> None:
    with pytest.raises(ValueError, match="precede"):
        assert_earlier_analog(datetime(2018, 8, 1, tzinfo=UTC), datetime(2018, 8, 1, tzinfo=UTC))

