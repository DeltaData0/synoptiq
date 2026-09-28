"""Guarded entry point for reduced c00-only candidate training and validation comparison."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from bust.data.dataset import get_manifest_fingerprint
from bust.model.evaluate import FROZEN_SPLIT_ID
from bust.model.train import run_reduced_c00_pipeline

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run reproducible training and validation evaluation for reduced c00 candidate."
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=ROOT / "data" / "processed" / "rows.parquet",
        help="Path to aligned rows Parquet file (default: data/processed/rows.parquet)",
    )
    parser.add_argument(
        "--model-output",
        type=Path,
        default=ROOT / "artifacts" / "model" / "reduced_c00_candidate.json",
        help="Path for model artifact JSON (default: artifacts/model/reduced_c00_candidate.json)",
    )
    parser.add_argument(
        "--metrics-output",
        type=Path,
        default=ROOT / "artifacts" / "metrics" / "reduced_c00_validation.json",
        help="Path for validation artifact JSON (default: artifacts/metrics/reduced_c00_validation.json)",
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
        print("command=candidate")
        print("model_name=reduced_c00_only_candidate")
        print(f"manifest_id={manifest_id}")
        print(f"split={FROZEN_SPLIT_ID}")
        print(f"seed={args.seed}")
        print(f"input_path={args.dataset}")
        print(f"model_artifact={args.model_output}")
        print(f"metrics_artifact={args.metrics_output}")
        print("status=blocked_missing_dataset")
        sys.stderr.write(f"Candidate training blocked: processed dataset not found at {args.dataset}\n")
        sys.exit(1)

    try:
        summary = run_reduced_c00_pipeline(
            dataset_path=args.dataset,
            model_output_path=args.model_output,
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
        sys.stderr.write(f"Candidate training failed: {err}\n")
        sys.exit(1)

    print("command=candidate")
    print("model_name=reduced_c00_only_candidate")
    print(f"manifest_id={summary['manifest_id']}")
    print(f"git_commit={summary['git_commit']}")
    print(f"split={FROZEN_SPLIT_ID}")
    print(f"seed={args.seed}")
    print(f"input_path={args.dataset}")
    print(f"model_artifact={args.model_output}")
    print(f"metrics_artifact={args.metrics_output}")
    print("status=validation_only")
    print(f"train_samples={summary['train_samples']}")
    print(f"validation_samples={summary['validation_samples']}")
    print(f"candidate_validation_brier_score={summary['candidate_validation_brier_score']:.6f}")
    print(f"candidate_validation_bust_prevalence={summary['candidate_validation_bust_prevalence']:.6f}")
    print(f"climatology_validation_brier_score={summary['climatology_validation_brier_score']:.6f}")
    print(f"deferred_feature_groups={','.join(summary['deferred_feature_groups'])}")


if __name__ == "__main__":
    main()
