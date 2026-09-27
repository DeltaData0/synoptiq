"""Durable SQLite state tracking for resumable GEFSv12 and IMD streaming acquisition."""

from __future__ import annotations

import hashlib
import sqlite3
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class AcquisitionStatus:
    LISTED = "listed"
    DOWNLOADING = "downloading"
    DOWNLOADED = "downloaded"
    VERIFIED = "verified"
    PROCESSING = "processing"
    VALIDATED_STAGED = "validated_staged"
    DELETION_PENDING = "deletion_pending"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class GEFSRecord:
    init_date: str  # YYYY-MM-DD
    member: str = "c00"
    source_key: str = ""
    remote_bytes: int | None = None
    etag: str | None = None
    provider_checksum: str | None = None
    local_path: str | None = None
    local_bytes: int | None = None
    local_sha256: str | None = None
    part_path: str | None = None
    status: str = AcquisitionStatus.LISTED
    attempt_count: int = 0
    processing_attempts: int = 0
    last_error: str | None = None
    listed_at: str | None = None
    downloaded_at: str | None = None
    verified_at: str | None = None
    decoded_at: str | None = None
    row_shard_written_at: str | None = None
    raw_deleted_at: str | None = None
    completed_at: str | None = None
    shard_path: str | None = None
    shard_rows: int | None = None
    validation_result: str | None = None


@dataclass
class IMDRecord:
    year: int
    status: str  # 'verified', 'missing', 'failed'
    local_path: str | None = None
    local_bytes: int | None = None
    local_sha256: str | None = None
    time_dim: int | None = None
    lat_dim: int | None = None
    lon_dim: int | None = None
    retrieved_at: str | None = None
    error: str | None = None


def iso_now() -> str:
    """Return current UTC time in ISO format."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class AcquisitionState:
    """Thread-safe transactional SQLite database for streaming acquisition state."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 30000;")
        return conn

    def init_schema(self) -> None:
        with self._lock, self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS gefs_items (
                    init_date TEXT PRIMARY KEY,
                    member TEXT NOT NULL DEFAULT 'c00',
                    source_key TEXT NOT NULL,
                    remote_bytes INTEGER,
                    etag TEXT,
                    provider_checksum TEXT,
                    local_path TEXT,
                    local_bytes INTEGER,
                    local_sha256 TEXT,
                    part_path TEXT,
                    status TEXT NOT NULL,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    processing_attempts INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT,
                    listed_at TEXT,
                    downloaded_at TEXT,
                    verified_at TEXT,
                    decoded_at TEXT,
                    row_shard_written_at TEXT,
                    raw_deleted_at TEXT,
                    completed_at TEXT,
                    shard_path TEXT,
                    shard_rows INTEGER,
                    validation_result TEXT
                );
                """
            )
            try:
                conn.execute("ALTER TABLE gefs_items ADD COLUMN processing_attempts INTEGER NOT NULL DEFAULT 0;")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE gefs_items ADD COLUMN part_path TEXT;")
            except sqlite3.OperationalError:
                pass
            conn.execute("CREATE INDEX IF NOT EXISTS idx_gefs_items_status ON gefs_items(status);")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS imd_items (
                    year INTEGER PRIMARY KEY,
                    status TEXT NOT NULL,
                    local_path TEXT,
                    local_bytes INTEGER,
                    local_sha256 TEXT,
                    time_dim INTEGER,
                    lat_dim INTEGER,
                    lon_dim INTEGER,
                    retrieved_at TEXT,
                    error TEXT
                );
                """
            )

    def upsert_gefs_inventory(
        self,
        init_date: str,
        source_key: str,
        remote_bytes: int | None = None,
        etag: str | None = None,
        provider_checksum: str | None = None,
        member: str = "c00",
    ) -> None:
        """Insert a listed GEFS object if not already present; preserve progress if present."""
        now = iso_now()
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM gefs_items WHERE init_date = ?", (init_date,))
            row = cursor.fetchone()
            if row is None:
                cursor.execute(
                    """
                    INSERT INTO gefs_items (
                        init_date, member, source_key, remote_bytes, etag, provider_checksum,
                        status, listed_at, attempt_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                    """,
                    (
                        init_date,
                        member,
                        source_key,
                        remote_bytes,
                        etag,
                        provider_checksum,
                        AcquisitionStatus.LISTED,
                        now,
                    ),
                )
            else:
                cursor.execute(
                    """
                    UPDATE gefs_items SET
                        source_key = ?,
                        remote_bytes = COALESCE(?, remote_bytes),
                        etag = COALESCE(?, etag),
                        provider_checksum = COALESCE(?, provider_checksum)
                    WHERE init_date = ?
                    """,
                    (source_key, remote_bytes, etag, provider_checksum, init_date),
                )

    def get_gefs_item(self, init_date: str) -> GEFSRecord | None:
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM gefs_items WHERE init_date = ?", (init_date,))
            row = cursor.fetchone()
            if row is None:
                return None
            return GEFSRecord(**dict(row))

    def list_gefs_items(self, status: str | None = None) -> list[GEFSRecord]:
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            if status is None:
                cursor.execute("SELECT * FROM gefs_items ORDER BY init_date ASC")
            else:
                cursor.execute("SELECT * FROM gefs_items WHERE status = ? ORDER BY init_date ASC", (status,))
            return [GEFSRecord(**dict(r)) for r in cursor.fetchall()]

    def count_gefs_by_status(self) -> dict[str, int]:
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status, COUNT(*) as cnt FROM gefs_items GROUP BY status")
            counts = {row["status"]: row["cnt"] for row in cursor.fetchall()}
            cursor.execute("SELECT COUNT(*) as total FROM gefs_items")
            counts["total"] = cursor.fetchone()["total"]
            return counts

    def update_gefs_status(
        self,
        init_date: str,
        status: str,
        **kwargs: Any,
    ) -> None:
        """Update status and optional fields on a GEFS item."""
        set_clauses = ["status = ?"]
        values: list[Any] = [status]
        for key, val in kwargs.items():
            set_clauses.append(f"{key} = ?")
            values.append(val)
        values.append(init_date)

        sql = f"UPDATE gefs_items SET {', '.join(set_clauses)} WHERE init_date = ?"
        with self._lock, self._get_connection() as conn:
            conn.execute(sql, values)

    def record_gefs_download_success(
        self,
        init_date: str,
        local_path: str | Path,
        local_bytes: int,
        local_sha256: str,
    ) -> None:
        now = iso_now()
        self.update_gefs_status(
            init_date,
            status=AcquisitionStatus.VERIFIED,
            local_path=str(local_path),
            local_bytes=local_bytes,
            local_sha256=local_sha256,
            downloaded_at=now,
            verified_at=now,
            last_error=None,
        )

    def record_gefs_failure(
        self,
        init_date: str,
        error_msg: str,
        max_retries: int = 3,
    ) -> None:
        """Increment attempt_count; mark failed if attempts >= max_retries, else reset to listed."""
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT attempt_count FROM gefs_items WHERE init_date = ?", (init_date,))
            row = cursor.fetchone()
            current_attempts = row["attempt_count"] if row else 0
            new_attempts = current_attempts + 1
            new_status = AcquisitionStatus.FAILED if new_attempts >= max_retries else AcquisitionStatus.LISTED
            cursor.execute(
                """
                UPDATE gefs_items SET
                    status = ?,
                    attempt_count = ?,
                    last_error = ?
                WHERE init_date = ?
                """,
                (new_status, new_attempts, error_msg, init_date),
            )

    def record_gefs_shard_success(
        self,
        init_date: str,
        shard_path: str | Path,
        shard_rows: int,
    ) -> None:
        now = iso_now()
        self.update_gefs_status(
            init_date,
            status=AcquisitionStatus.DELETION_PENDING,
            shard_path=str(shard_path),
            shard_rows=shard_rows,
            decoded_at=now,
            row_shard_written_at=now,
            validation_result="passed",
            last_error=None,
        )

    def record_gefs_completed(
        self,
        init_date: str,
    ) -> None:
        now = iso_now()
        self.update_gefs_status(
            init_date,
            status=AcquisitionStatus.COMPLETED,
            raw_deleted_at=now,
            completed_at=now,
        )

    def reserve_download_batch(
        self,
        ready_raw_count: int,
        measured_footprint_bytes: int,
        batch_size: int = 12,
        max_working_bytes: int = 8 * 1024 * 1024 * 1024,
        max_raw_files: int = 150,
    ) -> list[GEFSRecord]:
        """Atomically reserve up to batch_size download slots in SQLite.

        Guarantees:
        - ready_raw_count + current_in_flight + newly_reserved <= max_raw_files (150)
        - measured_footprint_bytes + current_reserved_bytes + newly_reserved_bytes <= max_working_bytes (8 GiB)
        - Updates reserved items to status='downloading' within an exclusive transaction.
        """
        reserved_items: list[GEFSRecord] = []
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) as cnt, COALESCE(SUM(remote_bytes), 0) as total_bytes FROM gefs_items WHERE status = ?",
                (AcquisitionStatus.DOWNLOADING,),
            )
            row = cursor.fetchone()
            current_in_flight = row["cnt"] if row else 0
            current_reserved_bytes = row["total_bytes"] if row else 0

            cursor.execute(
                "SELECT * FROM gefs_items WHERE status = ? ORDER BY init_date ASC",
                (AcquisitionStatus.LISTED,),
            )
            candidates = [GEFSRecord(**dict(r)) for r in cursor.fetchall()]

            in_flight_count = current_in_flight
            in_flight_bytes = current_reserved_bytes

            for item in candidates:
                if len(reserved_items) >= batch_size:
                    break
                if ready_raw_count + in_flight_count >= max_raw_files:
                    break
                item_bytes = item.remote_bytes if (item.remote_bytes and item.remote_bytes > 0) else 30_000_000
                if measured_footprint_bytes + in_flight_bytes + item_bytes > max_working_bytes:
                    break

                cursor.execute(
                    "UPDATE gefs_items SET status = ? WHERE init_date = ? AND status = ?",
                    (AcquisitionStatus.DOWNLOADING, item.init_date, AcquisitionStatus.LISTED),
                )
                if cursor.rowcount == 1:
                    item.status = AcquisitionStatus.DOWNLOADING
                    reserved_items.append(item)
                    in_flight_count += 1
                    in_flight_bytes += item_bytes

        return reserved_items

    def release_download_reservation(self, init_date: str, error_msg: str | None = None) -> None:
        """Release a download reservation back to listed status."""
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE gefs_items SET status = ?, last_error = COALESCE(?, last_error) WHERE init_date = ? AND status = ?",
                (AcquisitionStatus.LISTED, error_msg, init_date, AcquisitionStatus.DOWNLOADING),
            )

    def record_gefs_processing_failure(
        self,
        init_date: str,
        error_msg: str,
        max_retries: int = 3,
    ) -> None:
        """Record a processing/decode/schema failure with bounded retries.

        Retains the raw file, increments processing_attempts, resets to VERIFIED if attempts < max_retries,
        or marks FAILED if exhausted.
        """
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT processing_attempts FROM gefs_items WHERE init_date = ?",
                (init_date,),
            )
            row = cursor.fetchone()
            current_attempts = row["processing_attempts"] if row and row["processing_attempts"] is not None else 0
            new_attempts = current_attempts + 1
            new_status = AcquisitionStatus.FAILED if new_attempts >= max_retries else AcquisitionStatus.VERIFIED
            cursor.execute(
                """
                UPDATE gefs_items SET
                    status = ?,
                    processing_attempts = ?,
                    last_error = ?
                WHERE init_date = ?
                """,
                (
                    new_status,
                    new_attempts,
                    f"Processing failure (attempt {new_attempts}/{max_retries}): {error_msg}",
                    init_date,
                ),
            )

    def recover_in_flight_states(
        self,
        shard_validator: Any = None,
    ) -> dict[str, int]:
        """Recover from crashes / restarts safely.

        Rules:
        - completed: strictly preserved (never reset).
        - deletion_pending or validated_staged: verify shard exists, is non-empty, and satisfies shard_validator;
          if valid, delete retained raw file and transition to completed.
          if invalid, retain raw file and reset to retriable status with error recorded!
        - downloading: reset to listed (remove any orphan .part file).
        - processing: if local raw file exists and is verified, reset to verified; else reset to listed.
        """
        recovered_counts = {
            "deletion_pending_completed": 0,
            "deletion_pending_rejected": 0,
            "deletion_pending_failed": 0,
            "reset_to_listed": 0,
            "reset_to_verified": 0,
        }
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            # 1. Recover deletion_pending
            cursor.execute(
                "SELECT * FROM gefs_items WHERE status IN (?, ?)",
                (AcquisitionStatus.DELETION_PENDING, AcquisitionStatus.VALIDATED_STAGED),
            )
            for row in cursor.fetchall():
                item = GEFSRecord(**dict(row))
                shard_p = Path(item.shard_path) if item.shard_path else None
                raw_p = Path(item.local_path) if item.local_path else None

                shard_valid = False
                validation_err = None

                if shard_p and shard_p.exists() and shard_p.stat().st_size > 0:
                    if shard_validator is not None:
                        try:
                            shard_valid, validation_err = shard_validator(shard_p, item.init_date)
                        except Exception as e:  # noqa: BLE001
                            shard_valid = False
                            validation_err = f"Shard validator exception: {e}"
                    else:
                        shard_valid = False
                        validation_err = "No shard validator provided; recovery blocked to protect raw data"

                if shard_valid:
                    deletion_failed = False
                    deletion_err = None
                    if raw_p and raw_p.exists():
                        try:
                            raw_p.unlink()
                        except OSError as e:
                            deletion_failed = True
                            deletion_err = str(e)

                    # Mark completed only if the raw file is absent after attempted deletion
                    if raw_p and raw_p.exists():
                        deletion_failed = True
                        if not deletion_err:
                            deletion_err = f"Raw file {raw_p} still exists after attempted deletion"

                    if deletion_failed:
                        # Retain deletion_pending, retain raw path, store real deletion error in last_error,
                        # and do not set raw_deleted_at or completed_at
                        cursor.execute(
                            "UPDATE gefs_items SET last_error = ? WHERE init_date = ?",
                            (f"Raw deletion failed: {deletion_err}", item.init_date),
                        )
                        recovered_counts["deletion_pending_failed"] += 1
                    else:
                        now = iso_now()
                        cursor.execute(
                            """
                            UPDATE gefs_items SET
                                status = ?,
                                raw_deleted_at = ?,
                                completed_at = ?
                            WHERE init_date = ?
                            """,
                            (AcquisitionStatus.COMPLETED, now, now, item.init_date),
                        )
                        recovered_counts["deletion_pending_completed"] += 1
                else:
                    # Shard missing or invalid: DO NOT delete raw file! Retain raw file and reset to retriable status
                    err_msg = validation_err or "Shard file missing or empty"
                    if raw_p and raw_p.exists():
                        cursor.execute(
                            "UPDATE gefs_items SET status = ?, last_error = ? WHERE init_date = ?",
                            (AcquisitionStatus.VERIFIED, f"Recovery rejected: {err_msg}", item.init_date),
                        )
                        recovered_counts["reset_to_verified"] += 1
                    else:
                        cursor.execute(
                            "UPDATE gefs_items SET status = ?, last_error = ? WHERE init_date = ?",
                            (AcquisitionStatus.LISTED, f"Recovery rejected: {err_msg}", item.init_date),
                        )
                        recovered_counts["reset_to_listed"] += 1
                    recovered_counts["deletion_pending_rejected"] += 1

            # 2. Reset in-flight downloading to listed and clean up their specific .part files
            cursor.execute(
                "SELECT * FROM gefs_items WHERE status = ?",
                (AcquisitionStatus.DOWNLOADING,),
            )
            for row in cursor.fetchall():
                item = GEFSRecord(**dict(row))
                cleaned_part = False
                if item.part_path:
                    p_part = Path(item.part_path)
                    if p_part.exists() and p_part.is_file() and ".part" in p_part.name:
                        try:
                            p_part.unlink()
                            cleaned_part = True
                        except OSError:
                            pass
                cursor.execute(
                    """
                    UPDATE gefs_items SET
                        status = ?,
                        part_path = NULL,
                        last_error = ?
                    WHERE init_date = ?
                    """,
                    (
                        AcquisitionStatus.LISTED,
                        f"Interrupted download recovered; cleaned_part={cleaned_part}",
                        item.init_date,
                    ),
                )
                recovered_counts["reset_to_listed"] += 1

            # 3. Reset in-flight processing to verified (if raw file exists) or listed
            cursor.execute(
                "SELECT * FROM gefs_items WHERE status = ?",
                (AcquisitionStatus.PROCESSING,),
            )
            for row in cursor.fetchall():
                item = GEFSRecord(**dict(row))
                raw_p = Path(item.local_path) if item.local_path else None
                if raw_p and raw_p.exists():
                    cursor.execute(
                        "UPDATE gefs_items SET status = ? WHERE init_date = ?",
                        (AcquisitionStatus.VERIFIED, item.init_date),
                    )
                    recovered_counts["reset_to_verified"] += 1
                else:
                    cursor.execute(
                        "UPDATE gefs_items SET status = ? WHERE init_date = ?",
                        (AcquisitionStatus.LISTED, item.init_date),
                    )
                    recovered_counts["reset_to_listed"] += 1

        return recovered_counts

    def _validate_failed_item_retained_file(
        self,
        item: GEFSRecord,
        raw_gefs_dir: Path | str | None = None,
    ) -> tuple[bool, Path | None, int | None, str | None, str | None]:
        """Validate that a failed item has all required metadata in SQLite and a matching retained raw file.

        Requires:
        - item.status == FAILED (completed items are immutable)
        - non-empty local_path in SQLite
        - positive local_bytes in SQLite
        - non-empty local_sha256 in SQLite
        - raw file exists on disk and is a normal file
        - exact byte-size match between disk file and SQLite record
        - exact SHA-256 match between disk file and SQLite record

        Returns:
            (valid, raw_path, actual_size, actual_sha, error_message)
        """
        init_date = item.init_date

        if item.status != AcquisitionStatus.FAILED:
            return (
                False,
                None,
                None,
                None,
                (
                    f"Item {init_date} has status '{item.status}' (expected '{AcquisitionStatus.FAILED}'); "
                    f"completed items are immutable and cannot be requeued"
                ),
            )

        if not item.local_path or not str(item.local_path).strip():
            return False, None, None, None, f"Failed item {init_date} lacks a recorded local_path in state database"

        if item.local_bytes is None or item.local_bytes <= 0:
            return (
                False,
                None,
                None,
                None,
                f"Failed item {init_date} lacks positive local_bytes in state database (found {item.local_bytes})",
            )

        if not item.local_sha256 or not str(item.local_sha256).strip():
            return False, None, None, None, f"Failed item {init_date} lacks a recorded local_sha256 in state database"

        raw_path = Path(item.local_path)
        if not raw_path.exists() and raw_gefs_dir:
            candidate = Path(raw_gefs_dir) / f"apcp_sfc_{init_date.replace('-', '')}00_c00.grib2"
            if candidate.exists():
                raw_path = candidate

        if not raw_path.exists() or not raw_path.is_file():
            return False, None, None, None, f"Retained raw file not found for failed item {init_date}: {raw_path}"

        actual_size = raw_path.stat().st_size
        if actual_size != item.local_bytes:
            return (
                False,
                None,
                None,
                None,
                f"Retained raw file size mismatch for {init_date}: expected {item.local_bytes} bytes, found {actual_size} bytes",
            )

        h = hashlib.sha256()
        with open(raw_path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        actual_sha = h.hexdigest().lower()

        if actual_sha != item.local_sha256.lower().strip():
            return (
                False,
                None,
                None,
                None,
                f"Retained raw file SHA-256 mismatch for {init_date}: expected {item.local_sha256.lower().strip()}, found {actual_sha}",
            )

        return True, raw_path, actual_size, actual_sha, None

    def requeue_failed_item_for_retry(
        self,
        init_date: str,
        raw_gefs_dir: Path | str | None = None,
    ) -> tuple[bool, GEFSRecord | None, str | None]:
        """Verify retained raw file integrity and requeue a failed item to VERIFIED status for retry.

        Requirements:
        - It may requeue only items currently in 'failed' status.
        - Completed items must remain immutable and cannot be requeued.
        - Retained raw file must exist and its byte size + SHA-256 must match the state record.
        - Rejects missing local_path, non-positive local_bytes, and missing local_sha256.
        - Preserves prior failure audit trail in last_error with a factual retry note.
        - Transitions item to VERIFIED and resets processing_attempts to 0 for the consumer path.
        """
        item = self.get_gefs_item(init_date)
        if item is None:
            return False, None, f"Item {init_date} not found in state database"

        valid, raw_path, actual_size, actual_sha, err = self._validate_failed_item_retained_file(
            item, raw_gefs_dir=raw_gefs_dir
        )
        if not valid or raw_path is None or actual_size is None or actual_sha is None:
            return False, None, err

        now = iso_now()
        prior_error = item.last_error or "Prior failure recorded"
        retry_note = (
            f"{prior_error} | Requeued for retry after verifying retained raw file "
            f"({actual_size} bytes, sha256:{actual_sha[:8]}...) at {now}"
        )

        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT status FROM gefs_items WHERE init_date = ?", (init_date,))
                    row = cursor.fetchone()
                    if not row:
                        return False, None, f"Item {init_date} not found in state database"
                    if row[0] != AcquisitionStatus.FAILED:
                        return (
                            False,
                            None,
                            (
                                f"Item {init_date} has status '{row[0]}' (expected '{AcquisitionStatus.FAILED}'); "
                                f"completed items are immutable and cannot be requeued"
                            ),
                        )
                    cursor.execute(
                        """
                        UPDATE gefs_items SET
                            status = ?,
                            processing_attempts = 0,
                            last_error = ?,
                            local_path = ?,
                            local_bytes = ?,
                            local_sha256 = ?,
                            verified_at = ?
                        WHERE init_date = ? AND status = ?
                        """,
                        (
                            AcquisitionStatus.VERIFIED,
                            retry_note,
                            str(raw_path.resolve()),
                            actual_size,
                            actual_sha,
                            now,
                            init_date,
                            AcquisitionStatus.FAILED,
                        ),
                    )
            finally:
                conn.close()

        updated = self.get_gefs_item(init_date)
        return True, updated, None

    def requeue_all_failed_items_for_retry(
        self,
        raw_gefs_dir: Path | str | None = None,
    ) -> tuple[list[GEFSRecord], list[str]]:
        """Atomically requeue all failed items with verified retained raw files.

        All-or-nothing:
        - First validates every failed item's retained raw file and metadata without changing SQLite.
        - If any one item fails validation, returns errors and leaves every failed item unchanged.
        - Only when every failed item validates, transitions all of them from failed to verified
          inside a single SQLite transaction.
        - Preserves the prior error text in each item's retry note.
        - Resets processing_attempts to 0 only for items actually requeued after full validation succeeds.
        - Rechecks that each target is still 'failed' inside the transaction; if not, rolls back and returns an error.
        - Completed items remain strictly immutable.
        """
        failed_items = self.list_gefs_items(status=AcquisitionStatus.FAILED)
        if not failed_items:
            return [], []

        validated_items: list[tuple[GEFSRecord, Path, int, str]] = []
        errors: list[str] = []

        # Step 1: Pre-validate every failed item without changing SQLite
        for item in failed_items:
            valid, raw_path, actual_size, actual_sha, err = self._validate_failed_item_retained_file(
                item, raw_gefs_dir=raw_gefs_dir
            )
            if not valid or raw_path is None or actual_size is None or actual_sha is None:
                errors.append(err or f"Validation failed for {item.init_date}")
            else:
                validated_items.append((item, raw_path, actual_size, actual_sha))

        # If any item fails validation, abort without modifying SQLite
        if errors:
            return [], errors

        # Step 2: All items passed pre-validation; atomically transition all in one SQLite transaction
        now = iso_now()
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    cursor = conn.cursor()
                    # Recheck that each target is still failed inside the transaction
                    for item, _, _, _ in validated_items:
                        cursor.execute("SELECT status FROM gefs_items WHERE init_date = ?", (item.init_date,))
                        row = cursor.fetchone()
                        if not row:
                            raise RuntimeError(f"Item {item.init_date} not found during atomic transition")
                        if row[0] != AcquisitionStatus.FAILED:
                            raise RuntimeError(
                                f"Item {item.init_date} has status '{row[0]}' (expected '{AcquisitionStatus.FAILED}'); "
                                f"completed items are immutable; atomic transition rolled back"
                            )

                    # Update all validated items to VERIFIED
                    for item, raw_path, actual_size, actual_sha in validated_items:
                        prior_error = item.last_error or "Prior failure recorded"
                        retry_note = (
                            f"{prior_error} | Requeued for retry after verifying retained raw file "
                            f"({actual_size} bytes, sha256:{actual_sha[:8]}...) at {now}"
                        )
                        cursor.execute(
                            """
                            UPDATE gefs_items SET
                                status = ?,
                                processing_attempts = 0,
                                last_error = ?,
                                local_path = ?,
                                local_bytes = ?,
                                local_sha256 = ?,
                                verified_at = ?
                            WHERE init_date = ? AND status = ?
                            """,
                            (
                                AcquisitionStatus.VERIFIED,
                                retry_note,
                                str(raw_path.resolve()),
                                actual_size,
                                actual_sha,
                                now,
                                item.init_date,
                                AcquisitionStatus.FAILED,
                            ),
                        )
            except (sqlite3.Error, RuntimeError, OSError) as exc:
                return [], [f"Atomic retry transaction failed: {exc}"]
            finally:
                conn.close()

        # Step 3: Fetch updated records
        requeued: list[GEFSRecord] = []
        for item, _, _, _ in validated_items:
            rec = self.get_gefs_item(item.init_date)
            if rec:
                requeued.append(rec)
        return requeued, []

    def upsert_imd_record(self, record: IMDRecord) -> None:
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO imd_items (
                    year, status, local_path, local_bytes, local_sha256,
                    time_dim, lat_dim, lon_dim, retrieved_at, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(year) DO UPDATE SET
                    status = excluded.status,
                    local_path = excluded.local_path,
                    local_bytes = excluded.local_bytes,
                    local_sha256 = excluded.local_sha256,
                    time_dim = excluded.time_dim,
                    lat_dim = excluded.lat_dim,
                    lon_dim = excluded.lon_dim,
                    retrieved_at = excluded.retrieved_at,
                    error = excluded.error
                """,
                (
                    record.year,
                    record.status,
                    record.local_path,
                    record.local_bytes,
                    record.local_sha256,
                    record.time_dim,
                    record.lat_dim,
                    record.lon_dim,
                    record.retrieved_at,
                    record.error,
                ),
            )

    def get_imd_record(self, year: int) -> IMDRecord | None:
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM imd_items WHERE year = ?", (year,))
            row = cursor.fetchone()
            if row is None:
                return None
            return IMDRecord(**dict(row))

    def list_imd_records(self) -> list[IMDRecord]:
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM imd_items ORDER BY year ASC")
            return [IMDRecord(**dict(r)) for r in cursor.fetchall()]
