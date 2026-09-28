"""Guarded entry point for reduced c00-only candidate held-out evaluation and validation calibration."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from bust.data.dataset import get_manifest_fingerprint
from bust.model.evaluate import FROZEN_SPLIT_ID
from bust.model.train import run_reduced_c00_evaluation_pipeline

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run reproducible validation calibration and held-out test evaluation for reduced c00 candidate."
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=ROOT / "data" / "processed" / "rows.parquet",
        help="Path to aligned rows Parquet file (default: data/processed/rows.parquet)",
    )
    parser.add_argument(
        "--model-path",
        type=Path,
        default=ROOT / "artifacts" / "model" / "reduced_c00_candidate.json",
        help="Path to candidate model JSON artifact (default: artifacts/model/reduced_c00_candidate.json)",
    )
    parser.add_argument(
        "--frozen-run-output",
        type=Path,
        default=ROOT / "artifacts" / "model" / "reduced_c00_frozen_run.json",
        help="Path for frozen run metadata artifact (default: artifacts/model/reduced_c00_frozen_run.json)",
    )
    parser.add_argument(
        "--calibrator-output",
        type=Path,
        default=ROOT / "artifacts" / "model" / "reduced_c00_calibrator.json",
        help="Path for calibrator model artifact (default: artifacts/model/reduced_c00_calibrator.json)",
    )
    parser.add_argument(
        "--metrics-output",
        type=Path,
        default=ROOT / "artifacts" / "metrics" / "reduced_c00_evaluation.json",
        help="Path for held-out evaluation artifact (default: artifacts/metrics/reduced_c00_evaluation.json)",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "DATA_MANIFEST.csv",
        help="Path to DATA_MANIFEST.csv (default: DATA_MANIFEST.csv)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed (default: 42)",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Overwrite existing output artifacts if they exist",
    )

    args = parser.parse_args()

    # Preflight check: dataset must exist
    if not args.dataset.exists():
        manifest_id = get_manifest_fingerprint(args.manifest)
        print("command=evaluate-candidate")
        print("model_name=reduced_c00_only_candidate")
        print(f"manifest_id={manifest_id}")
        print(f"split={FROZEN_SPLIT_ID}")
        print(f"seed={args.seed}")
        print(f"input_path={args.dataset}")
        print("status=blocked_missing_dataset")
        sys.stderr.write(f"Candidate evaluation blocked: processed dataset not found at {args.dataset}\n")
        sys.exit(1)

    # Preflight check: candidate model must exist
    if not args.model_path.exists():
        manifest_id = get_manifest_fingerprint(args.manifest)
        print("command=evaluate-candidate")
        print("model_name=reduced_c00_only_candidate")
        print(f"manifest_id={manifest_id}")
        print(f"split={FROZEN_SPLIT_ID}")
        print(f"seed={args.seed}")
        print(f"model_path={args.model_path}")
        print("status=blocked_missing_candidate_model")
        sys.stderr.write(f"Candidate evaluation blocked: candidate model not found at {args.model_path}\n")
        sys.exit(1)

    try:
        summary = run_reduced_c00_evaluation_pipeline(
            dataset_path=args.dataset,
            candidate_model_path=args.model_path,
            frozen_run_output_path=args.frozen_run_output,
            calibrator_output_path=args.calibrator_output,
            metrics_output_path=args.metrics_output,
            manifest_path=args.manifest,
            seed=args.seed,
            replace=args.replace,
            repo_root=ROOT,
        )
    except FileExistsError as err:
        sys.stderr.write(f"Error: {err}\n")
        sys.exit(1)
    except (ValueError, RuntimeError, OSError, KeyError) as err:
        sys.stderr.write(f"Candidate evaluation failed: {err}\n")
        sys.exit(1)

    print("command=evaluate-candidate")
    print("model_name=reduced_c00_only_candidate")
    print(f"manifest_id={summary['manifest_id']}")
    print(f"git_commit={summary['git_commit']}")
    print(f"split={FROZEN_SPLIT_ID}")
    print(f"seed={args.seed}")
    print(f"input_path={args.dataset}")
    print(f"frozen_run_artifact={summary['frozen_run_artifact']}")
    print(f"calibrator_artifact={summary['calibrator_artifact']}")
    print(f"metrics_artifact={summary['metrics_artifact']}")
    print(f"calibration_status={summary['calibration_status']}")
    print(f"calibration_sample_count={summary['calibration_sample_count']}")
    print(f"status={summary.get('status', 'eligible_test_metrics')}")
    print(f"test_samples={summary['test_sample_count']}")
    if summary["candidate_test_brier_score"] is not None:
        print(f"candidate_test_brier_score={summary['candidate_test_brier_score']:.6f}")
    if summary.get("candidate_uncalibrated_brier_score") is not None:
        print(f"candidate_uncalibrated_brier_score={summary['candidate_uncalibrated_brier_score']:.6f}")
    if summary["candidate_test_bust_prevalence"] is not None:
        print(f"candidate_test_bust_prevalence={summary['candidate_test_bust_prevalence']:.6f}")
    if summary["climatology_test_brier_score"] is not None:
        print(f"climatology_test_brier_score={summary['climatology_test_brier_score']:.6f}")
    if summary["brier_score_delta"] is not None:
        print(f"brier_score_delta={summary['brier_score_delta']:.6f}")
    print(f"deferred_feature_groups={','.join(summary['deferred_feature_groups'])}")


if __name__ == "__main__":
    main()
