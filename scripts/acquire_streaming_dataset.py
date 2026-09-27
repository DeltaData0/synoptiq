"""Disk-safe, resumable GEFSv12 and IMD streaming acquisition and processing entry point."""

from __future__ import annotations

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Add scripts directory to path for _run_context
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _run_context import ROOT, emit

from bust.data.acquisition import (
    DEFAULT_CONCURRENCY,
    MAX_RAW_BUFFER_COUNT,
    MAX_WORKING_BYTES,
    DiskLimitExceededError,
    count_raw_c00_files,
    derive_expected_gefs_dates,
    download_gefs_c00_file,
    finalize_streaming_dataset,
    format_progress_report,
    get_configured_pipeline_roots,
    inventory_noaa_s3,
    measure_pipeline_footprint,
    process_gefs_c00_file,
    sync_manifest_with_streaming_corpus,
    validate_shard_for_recovery,
    verify_or_fetch_imd_years,
)
from bust.data.acquisition_state import AcquisitionState, AcquisitionStatus
from bust.data.dataset import get_manifest_fingerprint, load_splits_config
from bust.data.regions import load_regions_geojson


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Disk-safe, resumable GEFSv12/IMD streaming acquisition and processing pipeline."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform source inventory and disk budget audit without downloading raw files.",
    )
    parser.add_argument(
        "--imd-only",
        action="store_true",
        help="Acquire and verify official IMD annual files (2010–2020) only, without any GEFS retrieval.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=DEFAULT_CONCURRENCY,
        help=f"Number of concurrent download workers (default: {DEFAULT_CONCURRENCY}).",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=ROOT / "data/interim/acquisition",
        help="Working directory for state database and temporary files.",
    )
    parser.add_argument(
        "--raw-gefs-dir",
        type=Path,
        default=ROOT / "data/interim/acquisition/raw",
        help="Directory for temporary raw GEFS c00 downloads.",
    )
    parser.add_argument(
        "--shards-dir",
        type=Path,
        default=ROOT / "data/interim/acquisition/shards",
        help="Directory for validated interim row shards.",
    )
    parser.add_argument(
        "--raw-imd-dir",
        type=Path,
        default=ROOT / "data/raw/imd",
        help="Directory containing official IMD annual NetCDFs (2010–2020).",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=ROOT / "data/processed/rows.parquet",
        help="Final destination for atomic rows.parquet output.",
    )
    parser.add_argument(
        "--summary-path",
        type=Path,
        default=ROOT / "artifacts/metrics/dataset_summary.json",
        help="Final destination for dataset_summary.json.",
    )
    parser.add_argument(
        "--replace-final",
        action="store_true",
        help="Allow replacing existing final rows.parquet output.",
    )
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Requeue and process failed items with verified retained raw files without new downloads.",
    )

    args = parser.parse_args()

    work_dir = args.work_dir
    raw_gefs_dir = args.raw_gefs_dir
    shards_dir = args.shards_dir
    raw_imd_dir = args.raw_imd_dir
    output_path = args.output_path
    summary_path = args.summary_path
    concurrency = args.concurrency

    work_dir.mkdir(parents=True, exist_ok=True)
    raw_gefs_dir.mkdir(parents=True, exist_ok=True)
    shards_dir.mkdir(parents=True, exist_ok=True)
    raw_imd_dir.mkdir(parents=True, exist_ok=True)

    manifest_id = get_manifest_fingerprint(ROOT / "DATA_MANIFEST.csv")
    try:
        out_rel = str(output_path.relative_to(ROOT))
    except ValueError:
        out_rel = str(output_path)
    emit("streaming-acquisition", out_rel, manifest_id=manifest_id, split="2010-2015/2016-2017/2018-2019")

    state_db_path = work_dir / "acquisition_state.db"
    state = AcquisitionState(state_db_path)

    # Dedicated IMD-only workflow: acquire/verify IMD 2010-2020 without touching GEFS
    if args.imd_only:
        print("=== IMD Annual Files Acquisition & Verification (2010–2020) ===")
        imd_complete, imd_errors = verify_or_fetch_imd_years(
            state=state,
            imd_dir=raw_imd_dir,
            manifest_path=ROOT / "DATA_MANIFEST.csv",
            required_years=list(range(2010, 2021)),
            allow_network_download=not args.dry_run,
        )

        print("\n--- Per-Year IMD Verification Status ---")
        imd_records = {r.year: r for r in state.list_imd_records()}
        for yr in range(2010, 2021):
            rec = imd_records.get(yr)
            st = rec.status if rec else "missing"
            b_str = f"{rec.local_bytes:,} bytes" if rec and rec.local_bytes else "no local file"
            sha_str = f"sha256:{rec.local_sha256[:8]}..." if rec and rec.local_sha256 else ""
            err_str = f" [error: {rec.error}]" if rec and rec.error and st != "verified" else ""
            print(f"  {yr}: status={st} ({b_str}) {sha_str}{err_str}")

        if not imd_complete:
            print(f"\n❌ IMD acquisition/verification incomplete ({len(imd_errors)} error(s)):")
            for err in imd_errors:
                print(f"  - {err}")
            sys.exit(1)
        else:
            print("\n✅ All IMD 2010–2020 annual files successfully verified.")
            sys.exit(0)

    expected_dates = derive_expected_gefs_dates()

    if args.dry_run:
        print("=== GEFSv12/IMD Streaming Acquisition Preflight & Dry Run ===")
        print(f"Expected initialization count (2010-01-01 to 2019-12-31): {len(expected_dates)}")

        # Audit S3 inventory without key guessing
        print("Auditing NOAA S3 retrospective archive inventory...")
        report = inventory_noaa_s3(
            state=state,
            expected_dates=expected_dates,
            max_workers=min(concurrency * 2, 32),
            shards_dir=shards_dir,
        )

        print(f"Actual listed count on NOAA S3: {report.actual_listed_count}")
        print(f"Missing GEFS dates: {len(report.missing_dates)}")
        if report.missing_dates:
            print(f"  Sample missing: {report.missing_dates[:5]}")
        print(f"Unexpected GEFS dates: {len(report.unexpected_dates)}")
        if report.unexpected_dates:
            print(f"  Sample unexpected: {report.unexpected_dates[:5]}")

        print("Sample observed keys from NOAA S3:")
        for k in report.sample_keys[:3]:
            print(f"  - {k['source_key']} ({k['remote_bytes']:,} bytes, ETag: {k['etag']})")

        proj_gib = report.projected_download_bytes / (1024**3)
        print(f"Projected download size using observed sizes: {report.projected_download_bytes:,} bytes (~{proj_gib:.2f} GiB)")
        pipeline_roots = get_configured_pipeline_roots(
            work_dir=work_dir,
            raw_gefs_dir=raw_gefs_dir,
            shards_dir=shards_dir,
            raw_imd_dir=raw_imd_dir,
            output_path=output_path,
            summary_path=summary_path,
        )
        current_footprint = measure_pipeline_footprint(pipeline_roots)
        print(f"Current measured footprint across all configured roots: {current_footprint:,} bytes ({current_footprint / (1024**2):.2f} MB)")

        existing_shards = list(shards_dir.glob("shard_*.parquet"))
        if existing_shards:
            avg_shard_bytes = sum(s.stat().st_size for s in existing_shards) / len(existing_shards)
            est_total_shard_bytes = int(avg_shard_bytes * len(expected_dates))
            print(
                f"Observed {len(existing_shards)} representative shard(s): avg {avg_shard_bytes:,.0f} bytes/shard; "
                f"projected {len(expected_dates):,} shards: ~{est_total_shard_bytes / (1024**2):.2f} MB"
            )
        else:
            print("Projected row shard footprint: unknown (no representative shards exist yet; runtime 8 GiB cap strictly enforced during streaming).")

        print(f"Active raw buffer limit: {MAX_RAW_BUFFER_COUNT} files (~{MAX_RAW_BUFFER_COUNT * 28:.1f} MB to ~{MAX_RAW_BUFFER_COUNT * 30 / 1024:.2f} GiB buffer).")
        print(f"Total pipeline footprint cap: {MAX_WORKING_BYTES:,} bytes (8.00 GiB). Runtime cap enforcement active: YES.")

        # Check IMD annual files status upfront
        print("\n--- IMD Annual Files Upfront Audit (2010–2020) ---")
        imd_complete, imd_errors = verify_or_fetch_imd_years(
            state=state,
            imd_dir=raw_imd_dir,
            manifest_path=ROOT / "DATA_MANIFEST.csv",
            required_years=list(range(2010, 2021)),
            allow_network_download=False,
        )
        imd_records = state.list_imd_records()
        present_years = [r.year for r in imd_records if r.status == "verified"]
        missing_years = [r.year for r in imd_records if r.status != "verified"]
        print(f"IMD verified present years: {present_years}")
        print(f"IMD missing / unverified years: {missing_years} (including 2020 verification-only)")

        if not imd_complete:
            print("\n⚠️ Blocked — D1-07: Real GEFS streaming requires all IMD 2010–2020 files before execution.")
            print(f"  Missing or invalid: {imd_errors[:3]}")
        else:
            print("\n✅ IMD upfront audit complete: All 2010–2020 annual files verified.")

        sys.exit(0)

    # Active acquisition and streaming pipeline execution:
    # 1. IMD Upfront verification gate
    print("Executing IMD upfront verification (2010–2020)...")
    imd_complete, imd_errors = verify_or_fetch_imd_years(
        state=state,
        imd_dir=raw_imd_dir,
        manifest_path=ROOT / "DATA_MANIFEST.csv",
        required_years=list(range(2010, 2021)),
        allow_network_download=True,
    )
    if not imd_complete:
        print("❌ Blocked — IMD upfront verification failed:")
        for err in imd_errors:
            print(f"  - {err}")
        print("Stopping before GEFS acquisition. D1-07 remains blocked.")
        sys.exit(1)

    # 2. Recover any in-flight states from prior interrupted run
    def _shard_validator(shard_path: Path, init_d: str) -> tuple[bool, str | None]:
        return validate_shard_for_recovery(shard_path, init_d, regions_path=ROOT / "config/regions_2deg.geojson")

    recovered = state.recover_in_flight_states(shard_validator=_shard_validator)
    if any(recovered.values()):
        print(f"State recovery complete: {recovered}")

    # 3. Ensure full inventory is listed (only if not in retry-failed mode)
    if not args.retry_failed:
        inv_report = inventory_noaa_s3(
            state=state,
            expected_dates=expected_dates,
            max_workers=concurrency * 2,
            shards_dir=shards_dir,
        )
        if inv_report.missing_dates:
            print(f"❌ Missing {len(inv_report.missing_dates)} GEFS dates in S3 inventory. Stopping.")
            sys.exit(1)

    if args.retry_failed:
        failed_items = state.list_gefs_items(status=AcquisitionStatus.FAILED)
        if not failed_items:
            print("No failed items found in state database to retry.")
        else:
            print(f"Verifying retained raw files for {len(failed_items)} failed item(s)...")
            requeued, errors = state.requeue_all_failed_items_for_retry(raw_gefs_dir=raw_gefs_dir)
            if errors:
                print("❌ Retained file validation failed:")
                for err in errors:
                    print(f"  - {err}")
                print("Stopping with failed state preserved. D1-07 remains blocked.")
                sys.exit(1)
            for r in requeued:
                print(
                    f"  ✅ Requeued {r.init_date} for retry (raw file verified: {r.local_bytes:,} bytes, "
                    f"sha256:{r.local_sha256[:8]}...)"
                )

    regions = load_regions_geojson(ROOT / "config/regions_2deg.geojson")
    splits_cfg = load_splits_config()
    open_imd_datasets = {}

    pipeline_roots = get_configured_pipeline_roots(
        work_dir=work_dir,
        raw_gefs_dir=raw_gefs_dir,
        shards_dir=shards_dir,
        raw_imd_dir=raw_imd_dir,
        output_path=output_path,
        summary_path=summary_path,
    )

    start_time = time.time()
    last_report_time = 0.0

    print(f"Starting disk-safe streaming acquisition (concurrency={concurrency}, max_buffer=150 raw files, max_footprint=8 GiB)...")

    # Producer-Consumer streaming loop
    while True:
        counts = state.count_gefs_by_status()
        completed = counts.get(AcquisitionStatus.COMPLETED, 0)
        failed = counts.get(AcquisitionStatus.FAILED, 0)
        if completed + failed >= len(expected_dates):
            break

        now = time.time()
        if now - last_report_time > 10.0:
            print(format_progress_report(state, pipeline_roots, raw_gefs_dir, start_time))
            last_report_time = now

        # Consumer step: process any verified raw files first to free disk space
        verified_items = state.list_gefs_items(status=AcquisitionStatus.VERIFIED)
        for v_item in verified_items[:concurrency]:
            try:
                process_gefs_c00_file(
                    item=v_item,
                    shards_dir=shards_dir,
                    imd_nc_dir=raw_imd_dir,
                    regions=regions,
                    splits_cfg=splits_cfg,
                    open_imd_datasets=open_imd_datasets,
                    state=state,
                    pipeline_roots=pipeline_roots,
                    max_working_bytes=MAX_WORKING_BYTES,
                    regions_path=ROOT / "config/regions_2deg.geojson",
                )
            except DiskLimitExceededError:
                # Working footprint limit reached; wait for producer/consumer to balance
                time.sleep(1.0)
            except Exception as e:  # noqa: BLE001
                print(f"Error processing {v_item.init_date}: {e}")

        # In retry-failed mode, do not download any files!
        if args.retry_failed:
            remaining_verified = state.list_gefs_items(status=AcquisitionStatus.VERIFIED)
            if not remaining_verified:
                break
            continue

        # Producer step: atomically reserve download slots within limits
        current_footprint = measure_pipeline_footprint(pipeline_roots)
        raw_count = count_raw_c00_files(raw_gefs_dir)

        reserved_batch = state.reserve_download_batch(
            ready_raw_count=raw_count,
            measured_footprint_bytes=current_footprint,
            batch_size=concurrency,
            max_working_bytes=MAX_WORKING_BYTES,
            max_raw_files=MAX_RAW_BUFFER_COUNT,
        )
        if not reserved_batch:
            # Buffer or footprint limit reached; wait for consumer to catch up
            time.sleep(1.0)
            continue

        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futs = {
                executor.submit(
                    download_gefs_c00_file,
                    item,
                    raw_gefs_dir,
                    work_dir,
                    state=state,
                ): item
                for item in reserved_batch
            }
            for fut in as_completed(futs):
                item = futs[fut]
                try:
                    fut.result()
                except Exception as e:  # noqa: BLE001
                    print(f"Download error for {item.init_date}: {e}")

    # Finalization
    counts = state.count_gefs_by_status()
    if counts.get(AcquisitionStatus.COMPLETED, 0) == len(expected_dates):
        print("All 3,652 dates completed! Finalizing dataset...")
        final_path = finalize_streaming_dataset(
            state=state,
            shards_dir=shards_dir,
            output_path=output_path,
            summary_path=summary_path,
            splits_cfg=splits_cfg,
            replace_final=args.replace_final,
            pipeline_roots=pipeline_roots,
            max_working_bytes=MAX_WORKING_BYTES,
        )
        print(f"Final dataset published atomically: {final_path}")

        # Synchronize DATA_MANIFEST.csv
        manifest_path = ROOT / "DATA_MANIFEST.csv"
        synced_count = sync_manifest_with_streaming_corpus(manifest_path, state)
        print(f"Synchronized {synced_count} GEFS records into {manifest_path}")
    else:
        print(f"Acquisition finished with {counts.get(AcquisitionStatus.FAILED, 0)} failed items. D1-07 remains blocked.")
        sys.exit(1)


if __name__ == "__main__":
    main()
