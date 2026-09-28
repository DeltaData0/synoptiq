"""Report factual source-pilot status without downloading or inventing evidence."""

from __future__ import annotations

import csv

from _run_context import ROOT, emit
from bust.data.dataset import get_manifest_fingerprint


def main() -> None:
    manifest = ROOT / "DATA_MANIFEST.csv"
    manifest_id = get_manifest_fingerprint(manifest)
    emit("pilot", "docs/data_audit.md", manifest_id=manifest_id)
    with manifest.open(encoding="utf-8", newline="") as handle:
        records = list(csv.DictReader(handle))
    gefs_c00 = [
        row
        for row in records
        if row.get("source") == "gefs"
        and row.get("status") == "decoded"
        and row.get("variable") == "apcp_sfc"
        and row.get("member") == "c00"
    ]
    imd = [row for row in records if row.get("source") == "imd" and row.get("status") == "decoded"]
    if len(gefs_c00) >= 3652 and len(imd) >= 11:
        print("status=real_source_pilots_verified")
        print(f"decoded_gefs_c00_records={len(gefs_c00)}")
        print(f"decoded_imd_records={len(imd)}")
        print("note=Real source provenance is recorded in DATA_MANIFEST.csv and docs/data_audit.md.")
        return
    print("status=blocked")
    print(f"decoded_gefs_c00_records={len(gefs_c00)}")
    print(f"decoded_imd_records={len(imd)}")
    print("reason=Required real GEFSv12/IMD pilot evidence is incomplete; fixture mode remains active.")


if __name__ == "__main__":
    main()
