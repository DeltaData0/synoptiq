# Data audit

**Status: BLOCKED — fixture integration only.** No GEFSv12 or IMD source file has yet been retrieved or decoded in this repository.

## Required sign-off

| Gate | Evidence required | Owner | Status |
| --- | --- | --- | --- |
| GEFS pilot | Actual S3 key, checksum/size, decoded GRIB metadata, members and steps | Data lead | Pending |
| IMD pilot | Two annual source URLs, decoded variable/grid/time axis/units | Verification lead | Pending |
| UTC mapping | Audited IMD day ↔ `[start, end)` UTC table | A + B | Pending |
| Day 10 | +240/+246-hour step analysis and exact/approximate/unavailable decision | A + B | Pending |

No training, verification metric, or replay asset may be described as empirical until all applicable gates are signed here and logged in `DATA_MANIFEST.csv`.

