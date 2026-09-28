"""Regression tests for D2-04 candidate evaluation and validation calibration contracts."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from bust.model.calibrate import (
    apply_sigmoid_calibration,
    fit_validation_sigmoid_calibrator,
)
from bust.model.evaluate import (
    CandidateFrozenRunMetadata,
    ProbabilityEvaluation,
    build_candidate_evaluation_artifact,
)
from bust.model.train import (
    PERMITTED_CANDIDATE_FEATURES,
    apply_reduced_c00_candidate,
    fit_reduced_c00_candidate,
    run_reduced_c00_evaluation_pipeline,
    run_reduced_c00_pipeline,
)


def _make_dataset_with_test() -> pd.DataFrame:
    """Generate minimal synthetic rows covering train, validation, and test splits."""
    rows = []
    # Train rows (2015)
    for idx in range(10):
        rows.append(
            {
                "init_utc": f"2015-06-{idx+1:02d}T00:00:00Z",
                "split": "train",
                "lead_day": (idx % 3) + 1,
                "window_quality": "exact",
                "region_id": "R20N-078E",
                "season": "JJAS",
                "lead_bucket": "1-3",
                "f_control_mm": float(5.0 + idx * 2.0),
                "bust": int(idx % 2),
                "error_mm": float(idx * 3.0),
                "o_imd_mm": float(idx * 4.0),
                "threshold_mm": 12.0,
            }
        )
    # Validation rows (2016) - both bust and non-bust for valid calibration
    for idx in range(10):
        rows.append(
            {
                "init_utc": f"2016-06-{idx+1:02d}T00:00:00Z",
                "split": "validation",
                "lead_day": (idx % 3) + 1,
                "window_quality": "exact",
                "region_id": "R20N-078E",
                "season": "JJAS",
                "lead_bucket": "1-3",
                "f_control_mm": float(6.0 + idx * 1.5),
                "bust": int((idx + 1) % 2),
                "error_mm": float(idx * 2.5),
                "o_imd_mm": float(idx * 3.5),
                "threshold_mm": 12.0,
            }
        )
    # Test rows (2018)
    for idx in range(10):
        rows.append(
            {
                "init_utc": f"2018-06-{idx+1:02d}T00:00:00Z",
                "split": "test",
                "lead_day": (idx % 3) + 1,
                "window_quality": "exact",
                "region_id": "R20N-078E",
                "season": "JJAS",
                "lead_bucket": "1-3",
                "f_control_mm": float(7.0 + idx * 1.8),
                "bust": int(idx % 2),
                "error_mm": float(idx * 2.0),
                "o_imd_mm": float(idx * 3.0),
                "threshold_mm": 12.0,
            }
        )
    # Unavailable Day 10 row in test
    rows.append(
        {
            "init_utc": "2018-06-20T00:00:00Z",
            "split": "test",
            "lead_day": 10,
            "window_quality": "unavailable",
            "region_id": "R20N-078E",
            "season": "JJAS",
            "lead_bucket": "8-10",
            "f_control_mm": 20.0,
            "bust": None,
            "error_mm": None,
            "o_imd_mm": None,
            "threshold_mm": None,
        }
    )
    return pd.DataFrame(rows)


def _setup_pipeline_environment(tmp_path: Path, df: pd.DataFrame) -> tuple[Path, Path, Path, Path, Path, Path]:
    """Helper to set up parquet dataset, manifest, and candidate model files."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    parquet_path = tmp_path / "rows.parquet"
    pq.write_table(pa.Table.from_pandas(df), parquet_path)

    manifest_path = tmp_path / "DATA_MANIFEST.csv"
    manifest_path.write_text("manifest_id,source,status\nmanifest-test-123,gefs,decoded\n", encoding="utf-8")

    model_path = tmp_path / "reduced_c00_candidate.json"
    val_metrics_path = tmp_path / "reduced_c00_validation.json"

    # Train candidate model using existing D2-03 pipeline
    run_reduced_c00_pipeline(
        dataset_path=parquet_path,
        model_output_path=model_path,
        metrics_output_path=val_metrics_path,
        manifest_path=manifest_path,
        seed=42,
        replace=True,
    )

    frozen_run_path = tmp_path / "reduced_c00_frozen_run.json"
    calibrator_path = tmp_path / "reduced_c00_calibrator.json"
    evaluation_path = tmp_path / "reduced_c00_evaluation.json"

    return parquet_path, model_path, frozen_run_path, calibrator_path, evaluation_path, manifest_path


def test_changing_test_labels_does_not_alter_candidate_or_validation_calibrator(tmp_path: Path) -> None:
    """Changing test labels cannot alter the frozen candidate model or the validation calibrator."""
    df1 = _make_dataset_with_test()
    df2 = _make_dataset_with_test()
    # In df2, invert all test bust labels completely
    df2.loc[df2["split"].eq("test") & df2["bust"].notna(), "bust"] = (
        1 - df2.loc[df2["split"].eq("test") & df2["bust"].notna(), "bust"]
    )

    p1, m1, fr1, c1, e1, man1 = _setup_pipeline_environment(tmp_path / "run1", df1)
    p2, m2, fr2, c2, e2, man2 = _setup_pipeline_environment(tmp_path / "run2", df2)

    # Candidate booster file must be bitwise identical
    assert (tmp_path / "run1" / "reduced_c00_candidate.txt").read_bytes() == (
        tmp_path / "run2" / "reduced_c00_candidate.txt"
    ).read_bytes()

    run_reduced_c00_evaluation_pipeline(
        dataset_path=p1,
        candidate_model_path=m1,
        frozen_run_output_path=fr1,
        calibrator_output_path=c1,
        metrics_output_path=e1,
        manifest_path=man1,
        seed=42,
        replace=True,
    )
    run_reduced_c00_evaluation_pipeline(
        dataset_path=p2,
        candidate_model_path=m2,
        frozen_run_output_path=fr2,
        calibrator_output_path=c2,
        metrics_output_path=e2,
        manifest_path=man2,
        seed=42,
        replace=True,
    )

    cal1 = json.loads(c1.read_text(encoding="utf-8"))
    cal2 = json.loads(c2.read_text(encoding="utf-8"))

    # Calibrator parameters must match exactly between runs despite opposite test labels
    assert cal1["status"] == "ready"
    assert cal2["status"] == "ready"
    assert cal1["sample_count"] == cal2["sample_count"]
    np.testing.assert_allclose(
        cal1["parameters"]["coef"],
        cal2["parameters"]["coef"],
        rtol=1e-10,
    )
    np.testing.assert_allclose(
        cal1["parameters"]["intercept"],
        cal2["parameters"]["intercept"],
        rtol=1e-10,
    )


def test_test_rows_not_loaded_until_freeze_and_calibration_complete(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test rows are not read from disk until frozen-run metadata and calibrator artifacts are written."""
    df = _make_dataset_with_test()
    p, m, fr, c, e, man = _setup_pipeline_environment(tmp_path, df)

    real_read_table = pq.read_table
    test_read_checked = False

    def spy_read_table(*args, **kwargs):
        filters = kwargs.get("filters")
        if filters:
            # Check if this read is for the test split
            is_test_read = any(
                isinstance(f, (tuple, list)) and len(f) == 3 and f[0] == "split" and f[1] == "==" and f[2] == "test"
                for f in filters
            )
            if is_test_read:
                nonlocal test_read_checked
                test_read_checked = True
                # Assert that both frozen_run and calibrator already exist on disk!
                assert fr.exists(), "frozen_run_output must be written BEFORE test data is read!"
                assert c.exists(), "calibrator_output must be written BEFORE test data is read!"
        return real_read_table(*args, **kwargs)

    monkeypatch.setattr("bust.model.train.pq.read_table", spy_read_table)

    run_reduced_c00_evaluation_pipeline(
        dataset_path=p,
        candidate_model_path=m,
        frozen_run_output_path=fr,
        calibrator_output_path=c,
        metrics_output_path=e,
        manifest_path=man,
        seed=42,
        replace=True,
    )

    assert test_read_checked, "Expected a pq.read_table call for the test split to be intercepted and verified."


def test_missing_permitted_features_non_exact_rows_and_day10_remain_null() -> None:
    """Missing permitted features, non-exact rows, and Day 10 remain strictly null in predictions and calibration."""
    df = _make_dataset_with_test()
    model = fit_reduced_c00_candidate(df, seed=42)
    val_scored = apply_reduced_c00_candidate(df, model)
    calibrator = fit_validation_sigmoid_calibrator(val_scored, "p_candidate", seed=42)

    test_cases = pd.DataFrame(
        {
            "split": ["test"] * 7,
            "lead_day": [1, 1, 1, 1, 10, 2, 1],
            "window_quality": ["exact", "exact", "exact", "exact", "unavailable", "approximate", "exact"],
            "region_id": ["R20N-078E", None, "R20N-078E", "R20N-078E", "R20N-078E", "R20N-078E", "R20N-078E"],
            "season": ["JJAS", "JJAS", None, "JJAS", "JJAS", "JJAS", "JJAS"],
            "lead_bucket": ["1-3", "1-3", "1-3", None, "8-10", "1-3", "1-3"],
            "f_control_mm": [None, 10.0, 10.0, 10.0, 20.0, 10.0, 10.0],
        }
    )

    scored = apply_reduced_c00_candidate(test_cases, model, probability_column="p_candidate")
    calibrated = apply_sigmoid_calibration(scored, calibrator, "p_candidate", output_column="p_calibrated")

    # Cases 0-5 must be strictly NaN for both candidate and calibrated probabilities
    for idx in range(6):
        assert pd.isna(scored.iloc[idx]["p_candidate"]), f"Case {idx} p_candidate should be NaN"
        assert pd.isna(calibrated.iloc[idx]["p_calibrated"]), f"Case {idx} p_calibrated should be NaN"

    # Case 6 is fully valid exact Day 1 row
    assert pd.notna(scored.iloc[6]["p_candidate"])
    assert 0.0 <= scored.iloc[6]["p_candidate"] <= 1.0
    assert pd.notna(calibrated.iloc[6]["p_calibrated"])
    assert 0.0 <= calibrated.iloc[6]["p_calibrated"] <= 1.0


def test_candidate_and_climatology_use_same_test_comparison_cohort(tmp_path: Path) -> None:
    """Candidate and climatology baseline must evaluate on the exact same eligible cohort; missing features are excluded and recorded."""
    df = _make_dataset_with_test()

    # Modify test rows to create specific exclusion scenarios:
    # Set row with index 20 (first test row) to have missing f_control_mm
    test_indices = df[df["split"].eq("test")].index.tolist()
    missing_feat_idx = test_indices[0]
    df.loc[missing_feat_idx, "f_control_mm"] = None

    p, m, fr, c, e, man = _setup_pipeline_environment(tmp_path, df)

    summary = run_reduced_c00_evaluation_pipeline(
        dataset_path=p,
        candidate_model_path=m,
        frozen_run_output_path=fr,
        calibrator_output_path=c,
        metrics_output_path=e,
        manifest_path=man,
        seed=42,
        replace=True,
    )

    eval_data = json.loads(e.read_text(encoding="utf-8"))
    counts = eval_data["sample_counts"]

    # 10 test rows total (Day 1-9) + 1 Day 10 row = 11 rows in test
    assert counts["test_total"] == 11
    # 1 row had missing f_control_mm
    assert counts["test_excluded_missing_features"] == 1
    # 1 row was Day 10 unavailable
    assert counts["test_unavailable_day10"] == 1
    # Eligible cohort is 10 - 1 = 9
    assert counts["test_eligible"] == 9

    # Both candidate and climatology must evaluate on exactly 9 rows
    assert eval_data["test_evaluation"]["sample_count"] == 9
    assert eval_data["cohort_definition"]["same_cohort_evaluated"] is True
    assert summary["test_sample_count"] == 9


def test_evaluation_artifact_refuses_held_out_metrics_if_calibration_not_ready(tmp_path: Path) -> None:
    """Evaluation artifact refuses to report held-out metrics if validation calibration is not ready."""
    df = _make_dataset_with_test()
    # Make all validation rows have bust = 0 (single class -> calibrator cannot fit)
    df.loc[df["split"].eq("validation"), "bust"] = 0

    p, m, fr, c, e, man = _setup_pipeline_environment(tmp_path, df)

    summary = run_reduced_c00_evaluation_pipeline(
        dataset_path=p,
        candidate_model_path=m,
        frozen_run_output_path=fr,
        calibrator_output_path=c,
        metrics_output_path=e,
        manifest_path=man,
        seed=42,
        replace=True,
    )

    assert summary["status"] == "calibration_not_ready"
    assert summary["calibration_status"] == "insufficient_validation_data"
    assert summary["candidate_test_brier_score"] is None
    assert summary["climatology_test_brier_score"] is None

    eval_data = json.loads(e.read_text(encoding="utf-8"))
    assert eval_data["status"] == "calibration_not_ready"
    assert eval_data["test_evaluation"]["candidate_metrics"] is None
    assert eval_data["test_evaluation"]["sample_count"] == 0

    # Also verify build_candidate_evaluation_artifact raises ValueError if attempted directly
    meta = CandidateFrozenRunMetadata(
        manifest_id="test",
        git_commit="deadbeef",
        is_dirty=False,
        split_id="2010-2015/2016-2017/2018-2019",
        seed=42,
        feature_columns=("f_control_mm",),
        feature_set_sha256="a" * 64,
        model_file_sha256="b" * 64,
        lightgbm_version="4.7.0",
        categorical_encoding={},
        hyperparameters={},
    )
    bogus_eval = ProbabilityEvaluation(
        status="eligible_test_metrics",
        sample_count=10,
        metrics={"brier_score": 0.05, "bust_prevalence": 0.05},
        reliability=[],
        message="Bogus",
    )
    with pytest.raises(ValueError, match="ready validation-only calibrator"):
        build_candidate_evaluation_artifact(
            meta,
            candidate_evaluation=bogus_eval,
            climatology_evaluation=bogus_eval,
            uncalibrated_evaluation=None,
            calibration_status="insufficient_validation_data",
            calibration_sample_count=0,
            calibration_parameters=None,
            sample_counts={},
            deferred_feature_groups=(),
        )


def test_artifact_includes_every_required_freeze_and_provenance_field(tmp_path: Path) -> None:
    """Artifacts include every required field: manifest, git commit, is_dirty, seed, hashes, params, etc."""
    df = _make_dataset_with_test()
    p, m, fr, c, e, man = _setup_pipeline_environment(tmp_path, df)

    run_reduced_c00_evaluation_pipeline(
        dataset_path=p,
        candidate_model_path=m,
        frozen_run_output_path=fr,
        calibrator_output_path=c,
        metrics_output_path=e,
        manifest_path=man,
        seed=42,
        replace=True,
    )

    # 1. Check frozen run metadata artifact
    fr_data = json.loads(fr.read_text(encoding="utf-8"))
    assert fr_data["model_type"] == "reduced_c00_only_candidate"
    assert fr_data["manifest_id"].startswith("manifest-")
    assert "git_commit" in fr_data
    assert "is_dirty" in fr_data
    assert fr_data["seed"] == 42
    assert fr_data["split_id"] == "2010-2015/2016-2017/2018-2019"
    assert fr_data["feature_columns"] == list(PERMITTED_CANDIDATE_FEATURES)
    assert len(fr_data["feature_set_sha256"]) == 64
    assert len(fr_data["model_file_sha256"]) == 64
    assert "lightgbm_version" in fr_data
    assert "categorical_encoding" in fr_data
    assert "hyperparameters" in fr_data
    assert fr_data["frozen_before_test_access"] is True

    # 2. Check calibrator artifact
    c_data = json.loads(c.read_text(encoding="utf-8"))
    assert c_data["model_type"] == "reduced_c00_only_candidate"
    assert c_data["status"] == "ready"
    assert c_data["method"] == "sigmoid_platt"
    assert c_data["sample_count"] == 10
    assert "coef" in c_data["parameters"]
    assert "intercept" in c_data["parameters"]
    assert c_data["run"]["seed"] == 42
    assert c_data["run"]["model_file_sha256"] == fr_data["model_file_sha256"]

    # 3. Check evaluation artifact
    e_data = json.loads(e.read_text(encoding="utf-8"))
    assert e_data["model_type"] == "reduced_c00_only_candidate"
    assert e_data["data_mode"] == "held_out_test"
    assert e_data["status"] == "eligible_test_metrics"
    assert "sample_counts" in e_data
    assert "cohort_definition" in e_data
    assert "test_evaluation" in e_data
    assert "candidate_metrics" in e_data["test_evaluation"]
    assert "climatology_metrics" in e_data["test_evaluation"]
    assert "brier_score_delta" in e_data["test_evaluation"]
    assert "reliability" in e_data["test_evaluation"]
    assert e_data["calibration"]["status"] == "ready"
    assert e_data["run"]["model_file_sha256"] == fr_data["model_file_sha256"]
    assert e_data["run"]["feature_set_sha256"] == fr_data["feature_set_sha256"]
    assert e_data["deferred_feature_groups"] == ["moisture", "circulation", "ensemble_disagreement"]


def test_evaluation_pipeline_refuses_overwrite_without_replace(tmp_path: Path) -> None:
    """Evaluation pipeline refuses to overwrite artifacts unless replace=True is explicitly given."""
    df = _make_dataset_with_test()
    p, m, fr, c, e, man = _setup_pipeline_environment(tmp_path, df)

    # First run succeeds
    run_reduced_c00_evaluation_pipeline(
        dataset_path=p,
        candidate_model_path=m,
        frozen_run_output_path=fr,
        calibrator_output_path=c,
        metrics_output_path=e,
        manifest_path=man,
        seed=42,
        replace=False,
    )

    # Second run without replace must raise FileExistsError
    with pytest.raises(FileExistsError, match="Refusing to overwrite existing frozen run artifact"):
        run_reduced_c00_evaluation_pipeline(
            dataset_path=p,
            candidate_model_path=m,
            frozen_run_output_path=fr,
            calibrator_output_path=c,
            metrics_output_path=e,
            manifest_path=man,
            seed=42,
            replace=False,
        )

    # With replace=True it succeeds
    summary = run_reduced_c00_evaluation_pipeline(
        dataset_path=p,
        candidate_model_path=m,
        frozen_run_output_path=fr,
        calibrator_output_path=c,
        metrics_output_path=e,
        manifest_path=man,
        seed=42,
        replace=True,
    )
    assert summary["test_sample_count"] == 10
