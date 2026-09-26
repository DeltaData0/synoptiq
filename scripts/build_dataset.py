"""Guarded placeholder for aligned-row construction."""

from _run_context import emit

emit("dataset", "data/processed/rows.parquet", split="2010-2015/2016-2017/2018-2019")
raise SystemExit(
    "Dataset build blocked: complete and sign docs/data_audit.md before producing labels or rows."
)

