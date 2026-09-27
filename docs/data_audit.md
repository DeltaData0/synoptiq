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

## D1-05 region lattice, coverage enforcement, and alignment audit — 2026-09-27 UTC

**⚠️ In review — pending verifier sign-off.** The 2° India-land region lattice, 80% coverage rule, and audited alignment helpers are implemented and tested against real decoded IMD and GEFS data.

### IMD grid coordinates and land mask audit

Inspection of official annual files `ind2017_rfp25.nc` and `ind2018_rfp25.nc`:
- Latitude: 129 points from 6.5°N to 38.5°N at regular 0.25° spacing.
- Longitude: 135 points from 66.5°E to 100.0°E at regular 0.25° spacing.
- Missing representation: float32 `NaN`. Exactly 12,451 points are unobserved/ocean NaNs on every single day (4,544,615 NaNs across all 365 days of 2017 and 2018).
- Land support: Exactly 4,964 grid points are valid land points. The mask is 100% static across all 365 days of 2018 and identical between 2017 and 2018.

### Proposed 2° India-land lattice and 80% coverage rule

- Lattice convention: Regular 2° cells with even-integer centers `(c_lat, c_lon)` where `c_lat` ∈ [8, 36] (step 2) and `c_lon` ∈ [68, 98] (step 2). `c_lat=38` candidates are excluded because the audited IMD grid terminates at 38.5°N, leaving incomplete 7×8 geometry; excluding 38°N ensures every included region in the frozen lattice has an exact, complete 8×8 = 64-point IMD geometry.
- Boundary definition: Half-open interval `[c_lat - 1.0, c_lat + 1.0) × [c_lon - 1.0, c_lon + 1.0)`.
- Points per nominal cell: Exactly 8 latitudes × 8 longitudes = 64 IMD grid points.
- Partition coverage: 240 candidate lattice cells (15 lat × 16 lon). Exactly 4,951 land points are captured across 112 intersecting cells. The 13 observed land points in the clipped northern source edge (`[37.0, 38.5]°N`) are excluded because no complete 2° source cell exists there; 100% partition coverage is not claimed after this change.
- Classification:
  - 128 cells: coverage = 0.0 (ocean / outside domain).
  - 112 cells: coverage > 0.0 (intersecting India land).
  - 65 cells: coverage ≥ 0.80 (≥ 52 / 64 valid land points). These 65 cells capture 4,033 land points (81.46% of captured land points) and form the supported regional forecast/evaluation grid.
  - 47 cells: 0 < coverage < 0.80 (coastal and border fringes). Preserved as explicit `no_data` outcomes with `no_data_reason = "coverage_fraction < 0.80"`; never silently dropped.
- Preserves all three existing fixture region IDs: `R20N-078E`, `R22N-080E`, `R24N-076E` (all have 64/64 = 1.00 coverage).

### Three hand-check cases with transparent arithmetic

1. **Hand-check Case 1 (Accepted coverage ≥ 0.80 on real IMD 2018 data):**
   - Region: `R20N-078E` (lat [19, 21), lon [77, 79)) on date `2018-08-02`.
   - Grid points: 64 out of 64 are valid land points (coverage = 1.0000 ≥ 0.80).
   - Sum of all 64 values: 171.810974 mm.
   - Expected mean: `171.810974 / 64 = 2.6845465 mm`.
   - Code verification: `aggregate_imd_daily_region` returns `has_sufficient_coverage = True`, `o_imd_mm = 2.6845465 mm`, `min_mm = 0.0 mm`, `max_mm = 18.546318 mm`. Matches exactly.

2. **Hand-check Case 2 (Rejected low-coverage / explicit no-data on real IMD 2018 data):**
   - Region A (Kerala coast): `R10N-076E` (lat [9, 11), lon [75, 77)) on date `2018-08-02`.
     - Valid points: 28 out of 64 (coverage = 28 / 64 = 0.4375 < 0.80). 36 ocean points are `NaN`.
     - Valid land mean: 6.0870004 mm.
     - Code verification: Returns `has_sufficient_coverage = False`, `o_imd_mm = None`, `no_data_reason = "coverage_fraction 0.4375 is below minimum 0.80"`.
     - Ocean NaNs are confirmed NOT filled with 0.0 mm (which would have yielded an erroneous 2.663 mm).
   - Region B (Gujarat coast near boundary): `R22N-070E` (lat [21, 23), lon [69, 71)) on `2018-08-02`.
     - Valid points: 51 out of 64 (coverage = 51 / 64 = 0.796875 < 0.80).
3. **Hand-check Case 3 (Audited interval tied to D1-04 mapping):**
   - For GEFS 00 UTC init `2018-08-01 00:00Z` and lead day 1:
     - Target window: `[2018-08-01 03:00Z, 2018-08-02 03:00Z)`.
     - IMD date label: `2018-08-02`.
     - GRIB 3-hour non-overlapping derived steps at 20.00°N, 78.00°E: 0.14 + 0.40 + 2.40 + 3.40 + 1.50 + 0.30 + 0.00 + 0.10 = 8.24 mm.
     - `exact_24h_total` returns 8.24 mm.
   - For lead day 9: maps to `[2018-08-09 03:00Z, 2018-08-10 03:00Z)` with IMD label `2018-08-10`.
   - For lead day 10: `get_lead_window` returns `window_quality = "unavailable"`; `get_exact_lead_window` raises `ValueError` citing the unevidenced +240–+243h accumulation.

### Reproducible region generation script

Deterministic region generation is implemented in `scripts/build_regions.py` using only the audited local Git-ignored IMD pilot files `data/raw/imd/ind2017_rfp25.nc` and `data/raw/imd/ind2018_rfp25.nc`.
- Verifies exact 0.25° coordinate resolution on both files (129 lats, 135 lons).
- Verifies static land mask across all days of both years (4,964 land points).
- Generates `config/regions_2deg.geojson` as the canonical source-of-truth artifact (112 regions; 65 supported, 47 peripheral; captures 4,951 land points; 13 northern-edge points excluded).
- Generates `web/src/regions_grid.json` identically from the source-of-truth.
- Uses explicit exception raises (`ValueError`, `RuntimeError`) rather than Python assertions so validation cannot disappear under `python -O`.
- Unit test `test_regions_grid_json_matches_config_geojson` proves both artifacts are semantically identical.
- Grid shape guard: `validate_grid_geometry` strictly rejects every non-8×8 intersecting region (no edge-clipped bypass); any region with truncated geometry (such as center_lat=38 at the 38.5°N edge) raises `ValueError`.

### Asset provenance and strict offline compliance

- **Strict offline operation**: All remote tile layers (CartoDB Dark tiles, remote URLs, and `L.tileLayer`) have been completely removed. Automated regression test `test_strict_offline_frontend_has_no_remote_tiles_or_cdns` ensures no remote tile or CDN URLs can be introduced under `web/src/`.
- **Forecast view honesty**: In fixture mode, forecast rainfall totals are visibly marked "Forecast total unavailable in fixture". No inferred rainfall colours, no `F_control` values, and no legend language claiming predicted/accumulated GEFS rainfall are presented.
- **Coverage split policy label**: Cell tooltip displays future-tense "Eligible for future rows.parquet build" because `rows.parquet` does not yet exist.
- **Bundled visual assets**: Visual orientation outline derived from the audited IMD grid mask; not an official or political boundary. Recorded as provenance/license pending for visual orientation.
- **Client-side visual rendering**: The particle streamline animation and radial heatfield smoothing are purely decorative client-side canvas rendering effects (`Flow (FX)` and `Glow (FX)`); they are explicitly NOT decoded GEFS wind fields, radar observations, or gridded rainfall observations.

### Test suite status

- `tests/test_regions.py`: Exactly 10 tests covering lattice generation (240 candidate cells), 38°N candidate absence and geometry rejection, 80% coverage partition, non-8x8 grid rejection, strict GeoJSON schema validation, artifact parity, and 3 hand-checked arithmetic rows.
- `tests/test_time_windows.py`: Exactly 9 tests covering exact 24h interval tiling, 00 UTC GEFS init enforcement, Day 1–9 exact mapping, Day 10 unavailable state, and rejection of timezone-naive as well as non-zero UTC offset datetimes (e.g. IST +05:30).
- `tests/test_labels.py`: Exactly 4 tests covering train-only quantile thresholds, approved seasons (`JJAS`, `other`), approved lead buckets (`1-3`, `4-7`, `8-10`), absolute error, and `compute_bust(error_mm, threshold_mm)`.
- `tests/test_api.py`: Exactly 3 tests covering fixture replay contract, invalid date handling, and automated regression test for strict offline frontend.
- `tests/test_accumulation.py`: Exactly 1 test.
- `tests/test_leakage.py`: Exactly 2 tests.
- `tests/test_dataset.py`: Exactly 27 tests covering chronological split assignment (train 2010–2015, validation 2016–2017, test 2018–2019), detection of incomplete local corpus, rejection of duplicate or out-of-range dates, failure on out-of-range dates when all expected are present (both local files and otherwise-valid manifest entries), strict GEFS manifest acceptance criteria (source=gefs, status=decoded, variable=apcp_sfc, member=c00, non-empty key, units, numeric finite non-negative forward step range `0 <= step_start_h < step_end_h` rejecting empty, NaN, inf, reversed, zero-length intervals, and explicit UTC timezone `Z` or `+00:00` in `init_utc` rejecting naive datetimes), rejection of p01-only files substituting for required c00 control coverage, train-only threshold fitting and anti-leakage with Day-10 exclusion, schema-valid input deduplication (safely removes pre-existing threshold_mm and bust before many_to_one merge, returning exactly one column each and preserving row order), rejection of empty train rows, frozen shared row schema enforcement with strict Day 10 unavailable rules (including null imd_year), unit tests for accumulation-step interval validation, GRIB lead total extraction on pilot data, single-date 10-lead row construction across all 112 regions, build_dataset guard rejection, verification-only requirement for IMD 2020 on late-December 2019 inits, rejection of 2020 GEFS initializations, Day-10 regional coverage preservation for peripheral and supported regions, manifest fingerprint derivation, GRIB metadata cross-checking with duplicate interval rejection, missing perturbationNumber and invalid units rejection, strict GEFS manifest/local resolver contract (rejecting ambiguous records and mismatched SHA-256/bytes), atomic Parquet build cleanup on error, and bounded-memory numeric threshold fitting equivalence.
- Full pytest suite: Exactly **56 tests collected and passing** in ~8s.
- D1-05 status: ✅ Complete — signed off by verifier (29 passed pytest suite including 3 real-data hand-checks and zero-offset UTC validator, deterministic 240-candidate / 112-region / 65-supported / 47-peripheral lattice build with non-8×8 rejection, clean `make web` and `make smoke`, strict offline URL enforcement, and honest fixture forecast view). Preserves all fixture-only and Day-10-unavailable caveats; no empirical `rows.parquet`, model training, or metrics produced.

### D1-07: Real dataset corpus preflight audit and blocked status

- **Decision D-007 — IMD 2020 verification-only requirement**:
  - The project decision owner approved IMD 2020 annual gridded rainfall NetCDF as verification-only coverage for late-2019 Day 1–9 forecast windows.
  - Audited Day 1–9 24h verification windows for GEFS 00 UTC initializations on 2019-12-23 through 2019-12-31 end between 2020-01-01 03:00Z and 2020-01-10 03:00Z, corresponding to IMD date labels `2020-01-01` through `2020-01-10` in calendar year 2020.
  - IMD 2020 is strictly required only to verify those late-2019 forecast windows.
  - GEFS initialization dates remain strictly 2010-01-01 through 2019-12-31 (3,652 runs).
  - Chronological splits (2010–2015 train, 2016–2017 validation, 2018–2019 test), train-only threshold fitting, and test reporting are completely unaltered.
  - No 2020 GEFS initialization is permitted or counted toward the corpus. Any 2020 GEFS initialization raises an unexpected-date coverage failure.
- **Canonical GEFS c00 pilot provenance resolved**:
  - Downloaded the observed NOAA S3 c00 object (`GEFSv12/reforecast/2018/2018080100/c00/Days:1-10/apcp_sfc_2018080100_c00.grib2`) once to canonical local path `data/raw/gefs/apcp_sfc_2018080100_c00.grib2`.
  - Byte count: exactly `28,987,248` bytes.
  - Local SHA-256: `11ad16be864bef08eed6a038e888b0b0d9013ce17a95a2cea3684ee8f137be44`.
  - S3 ETag: `"ed0cae037f26554470a6321f071eed34"`.
  - Decoded metadata: shortName `tp`, stepType `accum`, perturbationNumber 0 (c00 control), regular 0.25° grid (`721 × 1440`), 80 messages, dataTime 0 (00 UTC init), valid steps +3 through +240 hours.
  - The older ambiguous local file `data/raw/gefs/apcp_sfc_2018080100_c00_days1-10.grib2` (36,773,744 bytes) is preserved untouched but marked unverified; pilot tests and documentation use only the verified canonical file.
  - `DATA_MANIFEST.csv` row 5 (`gefs-20180801-c00-apcp`) updated with real observed SHA-256 and retrieval timestamp.
- **Derived IMD coverage semantics**:
  - Required IMD annual years are derived dynamically from actual audited Day 1–9 verification labels of the expected GEFS 00 UTC initializations (2010-01-01 through 2019-12-31).
  - This requires 11 IMD annual years: `[2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020]`.
  - Year 2020 is explicitly marked verification-only.
- **Strict GEFS manifest and local file resolver**:
  - Implemented `resolve_gefs_init_file` in `src/bust/data/dataset.py`:
    - Requires exactly one decoded `c00` APCP `Days:1-10` manifest record for each daily 00 UTC initialization.
    - Requires observed object key and canonical filename to agree (`apcp_sfc_YYYYMMDD00_c00.grib2`).
    - Verifies local file exists and that local byte size and SHA-256 match manifest values exactly.
    - Eliminates guessed source-key fallbacks, broad exception swallowing, and `*_c00*.grib2` first-match globbing.
- **Strengthened GRIB decoding validation**:
  - In `extract_gefs_c00_lead_totals`:
    - Missing `perturbationNumber` fails; perturbationNumber must equal 0.
    - Missing or invalid `units` fails; units must match `kg m**-2`.
    - ShortName (`tp`/`apcp`), `stepType=accum`, 00 UTC date/time, 721×1440 geometry, duplicate step interval rejection, and all required intervals for leads 1..9 strictly verified.
- **Atomic Parquet output**:
  - `build_dataset` writes Parquet chunks to a unique temporary file (`rows.parquet.tmp_<hex>`).
  - Atomically renames to `rows.parquet` only after all chunks, schema validation, and summary writes succeed.
  - Cleans up temporary output on any failure; tested with simulated mid-build error proving no `rows.parquet` is created.
- **Bounded-memory numeric threshold fitting**:
  - Training errors are accumulated exclusively into compact `array.array('d')` numeric storage keyed by `(region_id, season, lead_bucket)` (672 keys, ~10 MB RAM for 1.28M doubles across 6 train years).
  - Computes exact train-only q90 error thresholds with 10.0 mm floor without holding date-row dictionaries globally.
  - Passes 1 and 2 discard single-date rows immediately after processing.
- **Day-10 row and schema semantics**:
  - Day-10 rows enforce `imd_year = None` (null).
  - `validate_row_schema` strictly rejects non-null `imd_year` on Day 10.
- **Full summary dimensions**:
  - Successful builds print all required dimensions: initialization year, lead, season, split, coverage/no-data outcome, and missingness; and write `dataset_summary.json`.
- **Calendar-date set comparison**: Constructed exact expected 00 UTC calendar-date set for 2010-01-01 through 2019-12-31 (3,652 dates). Compares sets of valid in-scope dates rather than count, rejecting duplicate filenames on the same date and failing coverage if any unexpected out-of-range dates exist.
- **Local control files requirement**: Local control-date collection requires the expected `c00` control filename/object convention (`apcp_sfc_YYYYMMDD00_c00...`). `p01`–`p04` files cannot substitute for `c00`; when all 3,652 expected dates have only `p01` files, `is_complete` is `False` and all 3,652 control dates are reported missing.
- **Explicit UTC timezone enforcement**: Manifest `init_utc` requires explicit UTC (`Z` or `+00:00`). Timezone-naive datetimes (`2015-06-01T00:00:00`) are rejected and block coverage.
- **Unexpected manifest dates**: An otherwise-valid out-of-range manifest record sets `is_complete=False` and names the unexpected date in `unexpected_gefs_dates` and `blocking_reason`.
- **Hardened accumulation steps**: `validate_accumulation_steps()` rejects empty, NaN, infinite, negative, reversed, or zero-length APCP intervals, requiring finite numeric hours with `0 <= step_start_h < step_end_h`.
- **Manifest evidence requirement**: Preflight strictly audits `DATA_MANIFEST.csv` decoded records alongside local files; GEFS records count only with `source=gefs`, `status=decoded`, `variable=apcp_sfc`, `member=c00`, non-empty key/URL, units, numeric step range (`step_start_h`, `step_end_h`), and valid 00 UTC initialization date. Coverage cannot pass on raw filenames alone without observed source metadata records.
- **Observed source capacity audit**:
  - Available disk capacity: `df -h .` proves 25 GiB available on `/System/Volumes/Data` (228 GiB total, 177 GiB used, 88% capacity).
  - Observed GEFSv12 `c00` APCP payload: Full real NOAA S3 retrospective inventory discovered all 3,652 daily 00 UTC c00 Days:1-10 objects for 2010-01-01 through 2019-12-31, totaling exactly 98,387,769,232 bytes (~98.39 GB / ~91.63 GiB) observed remote payload (replacing the earlier single-pilot extrapolation of 98.59 GiB / 105.86 GB).
  - Observed IMD 0.25° annual NetCDF payload: All 11 IMD annual files (2010–2020) are now verified locally. Total payload across all 11 files is exactly 279,959,156 bytes (8 non-leap years of 365 days at 25,431,832 bytes each: 2010, 2011, 2013, 2014, 2015, 2017, 2018, 2019; and 3 leap years of 366 days at 25,501,500 bytes each: 2012, 2016, 2020).
  - Total projected GEFS raw download size: 98,387,769,232 bytes (~91.63 GiB).
  - Capacity constraint: Full raw archive exceeds host available disk space (25 GiB) by ~66.6 GiB (~3.7x storage deficit). The streaming acquisition pipeline enforces an 8 GiB runtime working footprint and 150-file buffer cap to process raw files into interim row shards and delete raw data safely.
- **Verified IMD coverage**: All 11 required IMD annual NetCDF files (2010–2020) are verified and present in `data/raw/imd/` (total 279,959,156 bytes). Each file passes strict `validate_imd_netcdf` verification (exact calendar-date time coordinate matching the full expected year without duplicates, gaps, or replacements; 129×135 grid; RAINFALL variable with required unit `mm`). All 11 records in `DATA_MANIFEST.csv` are decoded and documented with factual provenance without unproven `Content-Disposition` claims. IMD 2020 is verified as verification-only for late-2019 Day 1–9 windows per D-007.
- **Missing GEFS coverage**: GEFS reforecast archive and manifest records are missing 3,651 of 3,652 daily 00 UTC runs across 2010–2019 (only pilot run `2018-08-01` exists).
- **Day-10 anti-leakage**: Excluded all Day-10 and unavailable rows from threshold fitting. `fit_and_apply_thresholds()` safely removes pre-existing `threshold_mm`/`bust` columns, merges with `validate="many_to_one"`, preserves row order, and ensures Day 10 retains null `f_control_mm`, `o_imd_mm`, `error_mm`, `threshold_mm`, `bust`, and `imd_year`. In `validate_row_schema()`, Day-10 rows must have `window_quality == "unavailable"` and null metrics.
- **D1-07 status**: ⚠️ Blocked — D1-07: All 11 IMD annual files (2010–2020) are now verified locally (total 279,959,156 bytes) with decoded manifest records in `DATA_MANIFEST.csv`. D1-07 remains blocked solely on the missing 3,651 GEFS c00 runs and their decoded manifest records (only 2018-08-01 present). Next safe action: Acquire and process the remaining 3,651 GEFS c00 initializations via the disk-safe streaming pipeline. Real build pipeline is implemented and tested behind the preflight guard, but no dataset (`data/processed/rows.parquet`), thresholds, metrics, or model results are claimed until the full corpus is accommodated and built.

## D1-07 streaming completion and verifier sign-off — 2026-09-27 UTC

**✅ Complete — D1-07:** The immediately preceding missing-corpus status is a
historical preflight record and has been superseded by the completed disk-safe
streaming run. The source scope, frozen split, label policy, and Day-10 verdict
did not change.

- SQLite acquisition state records exactly **3,652 completed**, **0 failed**
  GEFS c00 Days:1–10 initializations from 2010-01-01 through 2019-12-31.
- Independent readback validation reopened every one of the 3,652 interim
  shards: **3,652 valid**, **0 invalid**. All raw GEFS downloads were deleted
  only after shard validation; the raw working directory is empty.
- The one retained retry (`2013-11-09`) was revalidated for byte size and
  SHA-256, decoded through the identical-duplicate GRIB guard, published as a
  validated shard, and then deleted normally. Retry state hardening now rejects
  missing retained metadata and performs multi-item retry preparation
  atomically.
- `data/processed/rows.parquet` was atomically published from validated shards:
  **4,090,240 rows**, 3,652 row groups, and the shared schema plus `split`.
  Counts by initialization year, lead, season, split, coverage outcome, and
  missingness are recorded in `artifacts/metrics/dataset_summary.json`.
- Independent contract scan found Day 1–9 rows exact and all **409,024** Day-10
  rows unavailable with null forecast, observation, error, threshold, bust,
  and IMD year. A train-only q90 threshold spot check matched the stored value;
  held-out sampled rows matched both `abs(F−O)` and strict `error > threshold`
  bust semantics.
- `DATA_MANIFEST.csv` now has **3,652** unique full-corpus c00 APCP records
  with actual source key, retrieval time, byte count, SHA-256, UTC init,
  `0..240` span, units, decoded status, and shard/deletion note. Its final
  post-synchronization fingerprint is `manifest-fp-12803f75af61`.
- Verification after hardening: 115 pytest tests passed, one local-data test
  skipped; Ruff, `git diff --check`, `make web`, and `make smoke` passed. The
  Starlette `TestClient` deprecation warning remains non-blocking.

This sign-off authorizes D1-07 and Phase 2 only. It does **not** establish a
trained candidate, calibrated probability, analog result, feature-complete
model, held-out skill metric, or historical-replay frontend; those remain
separate D2/D3 gates.
