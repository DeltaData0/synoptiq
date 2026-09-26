# Data audit

**Status: ✅ D1-04 signed — labels may be built only for exact Day 1–9 windows.** The IMD and GEFS source-file pilots are complete; the IMD daily-window mapping below is source-grounded and signed by the project decision owner. Day 10 is deliberately `unavailable` and must render gray; it is not an approximate empirical label. This sign-off permits no performance claim by itself.

## Required sign-off

| Gate | Evidence required | Owner | Status |
| --- | --- | --- | --- |
| GEFS pilot | Actual S3 key, checksum/size, decoded GRIB metadata, members and steps | Data lead | ✅ Complete — `gefs-20180801-*` entries in `DATA_MANIFEST.csv` |
| IMD pilot | Two annual source URLs, decoded variable/grid/time axis/units | Verification lead | ✅ Complete — `imd-2017-pilot` and `imd-2018-pilot` in `DATA_MANIFEST.csv` |
| UTC mapping | Audited IMD day ↔ `[start, end)` UTC table | Project decision owner | ✅ Complete — documented below; source-grounded mapping signed 2026-09-27 |
| Day 10 | +240/+246-hour step analysis and exact/approximate/unavailable decision | Project decision owner | ✅ Complete — `unavailable`; documented below |

No training, verification metric, or replay asset may be described as empirical until its own required source coverage, split, leakage, and end-to-end gates are also complete and logged. D1-04 only authorizes exact Day 1–9 label construction.

## D1-04 daily-window and Day-10 audit — 2026-09-27 UTC

**✅ Complete — signed by Kanishka Pandey, project decision owner.** The decision is limited to the selected IMD daily gridded rainfall product and the inventoried 00 UTC GEFSv12 reforecast layout. It does not validate any model or metric.

### Source evidence and mapping

The IMD-hosted Mitra et al. technical paper states that IMD rain-gauge daily values are 24-hour accumulations **valid at 0300 UTC**, and that observatories report rainfall that occurred in the prior 24 hours ending at 0300 UTC. It also states that the land-only IMDNCC gridded daily product is independently analysed from those IMD records. The selected official IMD 0.25° NetCDF archive exposes only date labels, not an explicit bounds variable. Therefore the mapping below is a documented, source-grounded inference from the product's daily labels and the IMD observing convention—not an invented timestamp.

Primary source: A. K. Mitra et al. (2009), *Daily Indian Precipitation Analysis Formed from a Merge of Rain-Gauge Data with the TRMM TMPA Satellite-Derived Rainfall Estimates*, pp. 267–268, IMD-hosted PDF: <https://imdpune.gov.in/cmpg/Realtimedata/gpm/mitra_etal_2009.pdf>. The relevant text says IMD gauge daily values are valid at 0300 UTC and covers rainfall in the past 24 hours ending then. This is corroborated by the subsequent IMD-dataset literature: [JHM-D-22-0160.1](https://journals.ametsoc.org/view/journals/hydr/24/6/JHM-D-22-0160.1.xml) describes IMD daily reporting from 0830 IST (0300 UTC) to the following 0830 IST as the next day's rainfall.

| IMD NetCDF date label `D` | Audited observation interval | GEFS 00 UTC issue-time target | `window_quality` |
| --- | --- | --- | --- |
| `D` | `[D - 1 day 03:00Z, D 03:00Z)` | For lead `L` (`D = init date + L`): `[init + (24L-21)h, init + (24L+3)h)` | `exact` for L=1…9 only |
| `init date + 10 days` | `[init +219h, init +243h)` | Requires the +240–+243 three-hour amount | `unavailable` |

The start-inclusive/end-exclusive notation is adopted for code joins. It prevents an endpoint from being counted twice; the source establishes the 03:00 UTC observation ending convention.

### Real GRIB hand calculation and code check

The actual retained GEFSv12 reforecast file `gefs-20180801-p01-apcp` was inspected at the common grid point 20.00°N, 78.00°E. Its unit is `kg m**-2` (numerically mm of water accumulation). For the label `2018-08-02`, the audited interval is 2018-08-01 03:00Z through 2018-08-02 03:00Z. The source GRIB messages yield the following non-overlapping three-hour amounts after subtracting the documented overlapping six-hour accumulations:

| UTC offset from 2018-08-01 00Z | GRIB source values | Derived amount (mm) |
| --- | --- | ---: |
| 03–06 | `0–6 = 0.70` minus `0–3 = 0.56` | 0.14 |
| 06–09 | `6–9 = 0.40` | 0.40 |
| 09–12 | `6–12 = 2.80` minus `6–9 = 0.40` | 2.40 |
| 12–15 | `12–15 = 3.40` | 3.40 |
| 15–18 | `12–18 = 4.90` minus `12–15 = 3.40` | 1.50 |
| 18–21 | `18–21 = 0.30` | 0.30 |
| 21–24 | `18–24 = 0.30` minus `18–21 = 0.30` | 0.00 |
| 24–27 | `24–27 = 0.10` | 0.10 |
| **Total** | `0.14 + 0.40 + 2.40 + 3.40 + 1.50 + 0.30 + 0.00 + 0.10` | **8.24** |

This independent arithmetic total is **8.24 mm**. The repository guard `bust.data.align.exact_24h_total` was then called with those eight contiguous intervals for the same `[03:00Z, 27:00Z)` window and returned **`8.24 mm`**. The IMD NetCDF value at the same grid coordinate with date label `2018-08-02` is **0.69903475 mm**. These values are a reproducible interval/accumulation check only; they are not a regional forecast, an error metric, or a bust label.

### Day-10 verdict

The real `gefs-20180801-c00-apcp-day10` object starts with the observed `240–246` hour accumulation. The audited Day-10 target ends at +243 hours, so it needs an exact +240–+243 amount. The inspected archive evidence does not provide that amount; using the 6-hour +240–+246 interval would overshoot the target by three hours. No approved sensitivity analysis exists. **Decision: Day 10 is `unavailable`, not approximate.** All Day-10 API/map values remain `null`/gray with a no-data reason until a new documented decision supplies valid exact or approved approximate evidence.

**Audit limitations:** this evidence does not supply an explicit time-bounds attribute inside the 2017/2018 NetCDF files. It is sufficient for the stated source-grounded product convention, but a contrary official product specification would require reopening D1-04, updating `DECISIONS.md`, and invalidating affected rows.

## IMD annual-file pilot — 2026-09-26 UTC

**✅ Complete — D1-03:** The official selector was retrieved from `https://imdpune.gov.in/cmpg/Griddata/Rainfall_25_NetCDF.html`. Its observed form route was `POST https://imdpune.gov.in/cmpg/Griddata/RF25.php` with `RF25=2017` and `RF25=2018`; the responses named `RF25/ind2017_rfp25.nc` and `RF25/ind2018_rfp25.nc` in `Content-Disposition`. Both files decoded with `xarray.open_dataset`.

| Year | Variable / units | Dimensions | Date axis | Missing cells | SHA-256 |
| --- | --- | --- | --- | ---: | --- |
| 2017 | `RAINFALL` / `mm` | `TIME=365`, `LATITUDE=129`, `LONGITUDE=135` | 2017-01-01 through 2017-12-31 | 4,544,615 | `49786e2d2b661c5d3bcfb3ffd90385c1133ec27a8a04bf272ff2df5029106a9c` |
| 2018 | `RAINFALL` / `mm` | `TIME=365`, `LATITUDE=129`, `LONGITUDE=135` | 2018-01-01 through 2018-12-31 | 4,544,615 | `26bd53aeb2d6f3f7d39516c41606db005dede474906b33462d1a0caef69cd6ec` |

The NetCDF date coordinate alone does **not** establish the IMD daily observation window. The D1-04 mapping is therefore supported separately by the IMD observing-convention evidence above and recorded as a source-grounded inference.

## GEFS control precipitation inspection — 2026-09-26 UTC

**✅ Complete — D1-02:** The official public bucket listing returned the observed key `GEFSv12/reforecast/2018/2018080100/c00/Days:1-10/apcp_sfc_2018080100_c00.grib2` (28,987,248 bytes; S3 ETag `ed0cae037f26554470a6321f071eed34`). The downloaded control object opened with `cfgrib` as `tp`, `GRIB_stepType=accum`, units `kg m**-2`, 0.25° regular latitude/longitude grid (`721 × 1440`), 80 messages, 00 UTC initialization, and valid steps +3 through +240 hours.

Direct `eccodes` inspection produced these actual control accumulated step ranges: `0-3`, `0-6`, `6-9`, `6-12`, `18-24`, `114-120`, and `234-240` hours. The four perturbed precipitation members decoded as `number=1` through `number=4`, all with `tp`, `accum`, `kg m**-2`, and steps through +240 hours. Control PWAT decoded as `pwat`, `instant`, `kg m**-2`, with steps +3 through +240 hours. Each object key, source ETag, byte count, and locally calculated SHA-256 where retained is in `DATA_MANIFEST.csv`.

The observed Day 10–35 control precipitation object has a distinct actual first message with `stepRange=240-246`, `startStep=240`, `endStep=246`, `tp`, `accum`, and units `kg m**-2`; it is on a `361 × 720` 0.5° grid. This proves the archive contains a +240–+246 accumulation interval. It does **not** itself establish the IMD observation window or authorize an exact Day-10 label.

The overlapping/cumulative convention must be normalized before summation. D1-04 now authorizes audited Day 1–9 windows only; Day 10 remains unavailable.
