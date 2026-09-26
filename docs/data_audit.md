# Data audit

**Status: ⚠️ BLOCKED — fixture integration only.** The IMD annual-file pilot is complete; the GEFS member/pattern pilot and UTC-window sign-off remain incomplete. No empirical model claim is permitted.

## Required sign-off

| Gate | Evidence required | Owner | Status |
| --- | --- | --- | --- |
| GEFS pilot | Actual S3 key, checksum/size, decoded GRIB metadata, members and steps | Data lead | In progress — 2018-08-01 00 UTC control APCP decoded; all five members and PWAT still required |
| IMD pilot | Two annual source URLs, decoded variable/grid/time axis/units | Verification lead | ✅ Complete — `imd-2017-pilot` and `imd-2018-pilot` in `DATA_MANIFEST.csv` |
| UTC mapping | Audited IMD day ↔ `[start, end)` UTC table | A + B | Pending |
| Day 10 | +240/+246-hour step analysis and exact/approximate/unavailable decision | A + B | Pending |

No training, verification metric, or replay asset may be described as empirical until all applicable gates are signed here and logged in `DATA_MANIFEST.csv`.

## IMD annual-file pilot — 2026-09-26 UTC

**✅ Complete — D1-03:** The official selector was retrieved from `https://imdpune.gov.in/cmpg/Griddata/Rainfall_25_NetCDF.html`. Its observed form route was `POST https://imdpune.gov.in/cmpg/Griddata/RF25.php` with `RF25=2017` and `RF25=2018`; the responses named `RF25/ind2017_rfp25.nc` and `RF25/ind2018_rfp25.nc` in `Content-Disposition`. Both files decoded with `xarray.open_dataset`.

| Year | Variable / units | Dimensions | Date axis | Missing cells | SHA-256 |
| --- | --- | --- | --- | ---: | --- |
| 2017 | `RAINFALL` / `mm` | `TIME=365`, `LATITUDE=129`, `LONGITUDE=135` | 2017-01-01 through 2017-12-31 | 4,544,615 | `49786e2d2b661c5d3bcfb3ffd90385c1133ec27a8a04bf272ff2df5029106a9c` |
| 2018 | `RAINFALL` / `mm` | `TIME=365`, `LATITUDE=129`, `LONGITUDE=135` | 2018-01-01 through 2018-12-31 | 4,544,615 | `26bd53aeb2d6f3f7d39516c41606db005dede474906b33462d1a0caef69cd6ec` |

The NetCDF date coordinate alone does **not** establish the IMD daily observation window. It is not evidence for a 03–03 UTC mapping; that remains a D1-04 human/audit requirement.

## GEFS control precipitation inspection — 2026-09-26 UTC

**⚠️ In progress — D1-02:** The official public bucket listing returned the observed key `GEFSv12/reforecast/2018/2018080100/c00/Days:1-10/apcp_sfc_2018080100_c00.grib2` (28,987,248 bytes; S3 ETag `ed0cae037f26554470a6321f071eed34`). The downloaded control object opened with `cfgrib` as `tp`, `GRIB_stepType=accum`, units `kg m**-2`, 0.25° regular latitude/longitude grid (`721 × 1440`), 80 messages, 00 UTC initialization, and valid steps +3 through +240 hours.

Direct `eccodes` inspection produced these actual accumulated step ranges: `0-3`, `0-6`, `6-9`, `6-12`, `18-24`, `114-120`, and `234-240` hours. The overlapping/cumulative convention must be normalized before summation. This single decoded control file is insufficient for D1-02: complete all five precipitation members and the selected pressure/moisture field, then log their metadata and checksums.
