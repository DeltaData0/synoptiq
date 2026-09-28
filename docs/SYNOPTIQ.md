# Synoptiq — Project Reference

**Forecast reliability made inspectable.**

Synoptiq is a research prototype that estimates whether an issued regional rainfall forecast is unusually likely to have a large error. It combines a defined forecast-error event, historical verification, a probability model, and an interface for inspecting the evidence behind each score. The aim is to help forecast reviewers decide **where a second look is warranted**, not to replace numerical weather prediction.

**Project:** SIH 26079 · **Team:** HackTastic 6ix · **Repository:** [kan9667/synoptiq](https://github.com/kan9667/synoptiq)

**Project-state snapshot: 28 September 2026.** This reference brings together the project's research, design decisions, implementation history, results, and future direction. It distinguishes the implemented reduced prototype from the broader intended system. Reported results come from the existing project records and saved-artifact summaries; compiling this document did not constitute a new experimental run.

## Contents

1. [Purpose and scope](#1-purpose-and-scope)
2. [Value and differentiation](#2-value-and-differentiation)
3. [Current implementation](#3-current-implementation)
4. [Scientific definition](#4-scientific-definition)
5. [Time alignment and spatial coverage](#5-time-alignment-and-spatial-coverage)
6. [Data sources and acquisition](#6-data-sources-and-acquisition)
7. [Architecture and technology](#7-architecture-and-technology)
8. [Model, calibration, and evidence](#8-model-calibration-and-evidence)
9. [Recorded evaluation](#9-recorded-evaluation)
10. [A worked historical example](#10-a-worked-historical-example)
11. [Dashboard and API](#11-dashboard-and-api)
12. [Repository and local operation](#12-repository-and-local-operation)
13. [Development history and completion status](#13-development-history-and-completion-status)
14. [Quality, reproducibility, and release](#14-quality-reproducibility-and-release)
15. [Future development](#15-future-development)
16. [Limitations and open questions](#16-limitations-and-open-questions)
17. [Team](#17-team)
18. [Research and project records](#18-research-and-project-records)

## 1. Purpose and scope

A rainfall forecast provides an expected amount, but not necessarily an accessible answer to: *How likely is this particular region-and-lead forecast to be substantially wrong?* Synoptiq treats that question as a separate, measurable prediction problem.

Its forecast target is the **NOAA GEFSv12 control member's regional 24-hour rainfall total**. Its verification reference is **IMD 0.25° daily gridded rainfall**. Historical forecasts supply the inputs; their subsequent differences from IMD rainfall supply labels for learning and evaluation.

The intended workflow is:

> Issued forecast → estimated error risk → inspectable evidence → human forecast review.

The original vision covers Days 1–10, subject to exact time-window evidence. The implemented version scores **Days 1–9**, with explicit no-data for unsupported lead windows and regions. Its broad design includes ensemble disagreement, atmospheric fields, and analog-error memory. The first real-data model is a narrower, approved **reduced c00-only candidate**.

Synoptiq is not a new rainfall-generating model, a flood-probability model, a multi-hazard warning system, or a validated live service. GEFS-based results do not establish performance on NCUM or NEPS. The scope statement is:

> GEFSv12 reforecast research prototype; not NCUM/NEPS operational validation.

This boundary is also the foundation for future expansion: each new forecast system or hazard needs its own data, target, and validation.

## 2. Value and differentiation

The immediate audience is meteorologists and forecast desks reviewing regional forecasts. Synoptiq brings the estimated risk, historical comparison, and provenance into one view. Disaster management and rainfall-sensitive sectors could use validated reliability evidence in scenario planning, but operational adoption and resulting social or economic benefits have not been measured.

| Design strength | Practical value |
| --- | --- |
| Forecast-error risk rather than another rainfall map | Separates how much rain is forecast from how likely that forecast is to be substantially wrong. |
| Region-, season-, and lead-aware event definition | Judges an error against the relevant historical distribution while retaining a material-error floor. |
| Exact forecast/observation alignment | Avoids labeling a time-window mismatch as a weather-model failure. |
| Probability accompanied by evidence | Lets a reviewer inspect model contributions, earlier cases, and the underlying forecast/reference values. |
| Visible unsupported states | Distinguishes missing evidence from low risk. |
| Out-of-time baseline comparison | Tests usefulness beyond an attractive map or selected successful example. |
| Disk-bounded acquisition | Makes a large raw archive manageable on a local development machine. |

The innovation is the integrated, auditable regional forecast-review workflow. Boosted trees, probability calibration, SHAP, ensemble spread, and analog retrieval are established methods; the project does not claim to have invented them or to be the first forecast-bust detector.

The proposed full system asks a further research question: **do ensemble, physical, and earlier-error signals improve useful forecast-risk estimates beyond simple climatology and ensemble spread?** The reduced model has answered only part of that question.

## 3. Current implementation

| Area | State recorded at this snapshot |
| --- | --- |
| Forecast corpus | 3,652 daily GEFSv12 c00 precipitation initializations, 2010–2019. |
| Observation corpus | 11 IMD annual files, 2010–2020; 2020 supplies trailing verification only. |
| Aligned dataset | 4,090,240 rows, including unavailable rows retained for explicit accounting. |
| Spatial support | 112 intersecting 2° regions: 65 supported, 47 peripheral/no-data under the current rule. |
| Trained candidate | LightGBM using five c00/context inputs, with validation-only sigmoid calibration. |
| Evaluation | Real held-out Brier and reliability results against train-only climatology. |
| Evidence | Saved model-score contributions and earlier training-era c00 analog cases. |
| Product | Read-only API and offline-capable dashboard serving three frozen test initializations. |
| Integration | D2-05 real-data vertical-slice completion is recorded, including owner-confirmed offline recording. |
| Remaining release work | Final explanation audit, presentation/video reconciliation, second-machine release check, asset freeze, and submission acceptance remain open in the tracker. |

The complete p01–p04 and atmospheric training corpus is **not** implemented. Ensemble, moisture, and circulation preview cards contain labeled illustrative examples; they are not inputs to the current model. A completed integration milestone does not mean every feature in the original research design has been delivered.

## 4. Scientific definition

### Prediction unit and label

One sample is a **00 UTC initialization date × lead day × fixed 2° region**.

```text
F = control-member regional rainfall over the audited 24-hour interval
O = IMD regional rainfall over the same interval

error_mm     = abs(F - O)
threshold_mm = max(train-only q90(error | region, season, lead bucket), 10 mm)
bust         = error_mm > threshold_mm
```

The comparison is strictly greater-than. A forecast error exactly equal to the threshold is not a bust. Both overprediction and underprediction count. The 10 mm daily-total floor is a declared research policy, not an official IMD warning threshold; regional thresholds can be higher.

The season categories are `JJAS` and `other`. Lead buckets are Days `1–3`, `4–7`, and `8–10`; unavailable Day 10 does not enter threshold fitting or scored evaluation.

The probability is for **this defined rainfall-error event**. It is not probability of rain, probability of flooding, or the chance that every aspect of a forecast is correct. Its complement, `1 - P(bust)`, has the same narrow interpretation.

### Chronological design

| Partition | Initialization years | Eligible labeled rows | Permitted role |
| --- | --- | ---: | --- |
| Training | 2010–2015 | 1,281,735 | Thresholds, climatology, model fitting, training-derived encodings, and analog pool. |
| Validation | 2016–2017 | 427,635 | Model development/comparison and probability calibration. |
| Held-out test | 2018–2019 | 427,050 | Evaluation of the frozen candidate. |

Rows are not randomly split. Forecasts at nearby dates, locations, and leads are correlated; these counts are not independent weather events. Observations, realized errors, labels, and later analyses are excluded from current predictors.

The 2018–2019 test was reserved for the recorded evaluation, but its results have now been examined. Future development cannot repeatedly tune against those results and continue calling the same test an untouched assessment.

*Basis: Canonical Reference §3; Implementation Plan §3; decisions D-002, D-005, D-008; recorded results.*

## 5. Time alignment and spatial coverage

### Why the 03 UTC boundary matters

The selected GEFS forecasts initialize at 00 UTC. The adopted IMD daily-date interpretation is:

```text
IMD label D → [D minus one day at 03:00 UTC, D at 03:00 UTC)
```

This convention is supported by the source literature and documented observing convention. It is not an explicit time-bounds attribute found in the downloaded NetCDF files. Decision D-005 retains that distinction and allows reopening the mapping if an authoritative product-specific specification contradicts it.

For initialization `init` and lead `L`, the selected daily interval is:

```text
[init + (24L - 21) hours, init + (24L + 3) hours)
```

| Lead | Exact interval relative to initialization |
| --- | --- |
| Day 1 | +3 to +27 hours |
| Day 6 | +123 to +147 hours |
| Day 9 | +195 to +219 hours |
| Day 10 | +219 to +243 hours |

GRIB accumulations must tile that interval without gaps or double-counting. Where messages describe overlapping accumulations, appropriate differences isolate the needed subintervals. Stored provenance preserves the **actual GRIB arithmetic**, not just the nominal target window.

The pilot audit independently summed a real eight-part 03–27 UTC point total to **8.24 mm**, matching the code. That validates an accumulation calculation, not regional model skill.

### Day 10

The inspected archive supplies a +240–+246-hour accumulation, while the end of the required Day-10 window needs +240–+243 hours. A six-hour amount does not establish its first three-hour amount. Dividing it by two would introduce an unvalidated assumption.

Consequently, Day 10 is unavailable in the current release and excluded from numerical skill claims. It has null forecast, observation, threshold, label, and probability fields. Coverage is real computed support or null where unavailable, never an invented full-coverage value. A future exact source could reopen this limit; approximation would be a separately approved and evaluated policy, not the present implementation.

### Regions and observation support

The fixed lattice uses even-integer centers from 8–36°N and 68–98°E. Each full 2° cell has 8×8 IMD grid positions. Of 240 candidate cells, 112 intersect the selected land mask; 65 meet the ≥80% coverage rule and 47 remain visible as peripheral no-data regions.

The current rule measures valid grid support against the nominal 64-position region. It does **not** mean that 80% of a region has independent rain gauges. Thirteen northern-edge land points are excluded because the source grid does not support a complete cell there; 4,951 of 4,964 land points are captured by the intersecting lattice.

Regional hand checks include a full 64/64 cell and rejected 28/64 and 51/64 examples. A 51/64 fraction is approximately 79.69%, below the rule. Missing support is never treated as zero rainfall or zero bust probability.

Region names encode centers, not administrative districts. The dashboard's orientation outline comes from the IMD grid mask and is not an official political boundary.

*Basis: data audit; decisions D-005–D-007. The later fixed-grid decision makes the implemented coverage denominator more specific than the original plan's generic area-coverage description.*

## 6. Data sources and acquisition

### Chosen sources

**GEFSv12 reforecast** was selected because it provides the historical forecast family needed for retrospective learning. The broader archive description covers 2000–2019; this project selects 2010–2019 daily 00 UTC initializations. The completed bulk acquisition is c00 `apcp_sfc`, not all five members and atmospheric fields. Successful perturbed-member pilots do not imply a full ensemble training corpus.

Reforecasts are retrospective model runs for historical initialization dates, not proof that the same model output was operationally issued on those dates. Replay tests the issue-time information boundary; it does not mean Synoptiq actually issued a warning in 2019.

**IMD 0.25° daily rainfall** supplies the gauge-based gridded verification reference. It is a spatially processed observation product with uncertainty, not perfect truth. The decoded annual files use `RAINFALL`, units mm, and a 129-latitude × 135-longitude grid.

IMD 2020 is included **only to verify late-December 2019 forecasts whose valid windows cross into January**. No 2020 GEFS initialization enters the dataset or changes its splits.

### Volume and processing strategy

The recorded GEFS inventory totals **98,387,769,232 bytes**—approximately 98.39 GB or 91.63 GiB. The 11 IMD annual files total 279,959,156 bytes. The pipeline avoids retaining the entire raw GEFS corpus at once:

1. Discover actual source object keys and metadata; record provenance.
2. Download within independent concurrency and disk limits.
3. Verify, decode, and build each date's aligned regional shard.
4. Validate and read back the shard before deleting its raw GEFS file.
5. Persist progress and reconcile incomplete work after interruption.
6. Publish the final dataset only after corpus-completeness and shard checks pass.

The recorded implementation uses **12 download workers**, a **150-file raw buffer cap**, and an **8 GiB working-footprint budget**. File count and worker count are separate controls; byte reservations also account for in-flight and derived work. This is a configured pipeline storage budget, not total download traffic, total machine storage, or a RAM guarantee.

SQLite persists acquisition state. Failed items remain explicit and retryable; a raw deletion failure is not silently converted into completed cleanup. Raw files are retained until validated derived data exist.

The final acquisition sign-off records **3,652 completed items, zero failed items, and 3,652 reopened valid shards**. The resulting Parquet contains **4,090,240 rows = 3,652 dates × 112 regions × 10 leads**, of which 409,024 are unavailable Day-10 rows. Its recorded size is 60,625,386 bytes. The smaller derived file does not imply the original download was similarly small.

### Lessons retained from the build

The acquisition and audit history produced concrete safeguards: a mismatched pilot was re-downloaded and verified rather than trusted by filename; source keys retain actual remote identities; stored steps reflect real accumulation arithmetic; January observations cover the year boundary; unavailable rows do not acquire fabricated coverage or labels. One source object with duplicate GRIB messages was accepted only after identical interval/shape/value duplicates were distinguished from conflicting data.

These are part of the reproducibility design, not incidental download details. A rolling recent forecast feed is not a substitute for this historical corpus.

## 7. Architecture and technology

```text
Observed GEFS inventory + IMD annual files
                  │
        Bounded acquisition and decode
                  │
     Exact UTC alignment + fixed regions
                  │
     Train-only thresholds and real labels
                  │
              rows.parquet
                  │
     c00 LightGBM + validation calibrator
                  │
     Held-out evaluation vs climatology
                  │
     Frozen replay export + contributions
                  │
     Earlier analogs added as context
                  │
      Read-only API → replay dashboard
```

Historical observations are necessary for labels and evaluation, but there is no observation-to-predictor path at issue time. The current analog branch adds post-hoc context to replay; the full proposed architecture would also investigate earlier analog-error summaries as model features under stricter chronology controls.

| Layer | Implementation |
| --- | --- |
| Runtime and data | Python 3.11; xarray, cfgrib/ecCodes, NumPy, pandas, PyArrow/Parquet. |
| Learning | LightGBM; scikit-learn calibration/evaluation utilities; saved model contributions. |
| API | FastAPI, Pydantic, Uvicorn, OpenAPI. |
| Frontend | Vite, locally bundled Leaflet, plain JavaScript/CSS. |
| Persistence | SQLite acquisition state; Parquet rows; JSON replay, metadata, and metrics; saved Booster. |
| Quality | pytest, Ruff, Make commands, manifests, checksums, frozen configuration, Git history. |

The actual replay service loads a cached JSON asset; SQLite is used for acquisition state, not the current replay database. Local map geometry and bundled web dependencies allow prepared replay without external map tiles or a CDN. Initial dependency and data acquisition still require network access.

Boosted trees were preferred to the proposed U-Net approach because the initial task is a regional tabular problem that can be trained and examined on CPU. A dense-looking map alone does not justify a high-volume pixel model. No GPU or managed cloud service is required for the present candidate; no measured runtime SLA or deployment-cost claim is established.

## 8. Model, calibration, and evidence

### Implemented model

Decision D-008 approved a deadline-limited reduced candidate, identified as `reduced_c00_only_candidate`. It uses exactly:

| Input | Meaning |
| --- | --- |
| `f_control_mm` | Issued regional control-member rainfall. |
| `region_id` | Fixed region identity. |
| `season` | JJAS or other. |
| `lead_day` | Forecast lead. |
| `lead_bucket` | Grouped lead context. |

Five inputs are **not five ensemble members**. IMD rain, realized error, bust, and analog outcomes are not current predictors.

The saved configuration uses binary LightGBM gradient boosting, 100 estimators, 31 leaves, learning rate 0.05, minimum child samples 50, four threads, and seed 42. Category mappings are derived from training data with an explicit unseen-category fallback. The candidate is frozen before test evaluation; the sigmoid/Platt calibrator is fitted on validation only.

The climatology comparator estimates training-era bust frequency by region, season, and lead bucket, with an explicit broader fallback. The recorded baseline covers 390 training groups. The full proposed shrinkage and spread-only comparison should not be inferred from that basic comparator.

### Interpreting explanations

Saved LightGBM `pred_contrib=True` outputs describe contributions to the raw tree score. They are **not percentage-point effects on the calibrated probability**, nor proof of meteorological causation. The current display groups control rainfall, regional context, and lead/season evidence under decision D-009.

There is no integrated generative-LLM reasoning layer. The evidence is numerical attribution and historical retrieval, not an autonomous meteorologist or generated causal diagnosis.

### Earlier comparable cases

Current analog retrieval filters to the same region, season, and lead bucket; requires a strictly earlier initialization and eligible exact data; and ranks candidates by absolute difference in forecast c00 rainfall. Held-out replay uses the training-era pool. Deterministic tie-breaking makes the result reproducible.

Up to five actual cases are shown with their subsequent errors and labels. Retrieval does not use those outcomes to select the neighbors, and missing neighbors are not padded. This is a simple rain-similarity method, not a completed multivariable atmospheric-pattern search. Its observed bust fraction need not match the classifier's probability.

### Intended richer model

The full design calls for roughly 15–25 named quantities from c00+p01–p04 rain, member spread and wet-member fraction, moisture, wind, pressure, geopotential height, and earlier analog-error summaries. These require complete source acquisition, unit/grid auditing, training-only transformations, and a new feature/model evaluation. Preview numbers do not supply those missing data.

## 9. Recorded evaluation

The following results describe the **same 427,050 eligible exact Day 1–9 verifications from 2018–2019 initializations**. They are results for the reduced candidate, not the future full ensemble/physical model.

| Held-out quantity | Recorded value |
| --- | ---: |
| Bust prevalence | 4.7430% |
| Train-only climatology Brier score | 0.0435859087 |
| Uncalibrated candidate Brier score | 0.0294928722 |
| Calibrated candidate Brier score | 0.0304852794 |
| Calibrated minus climatology Brier | −0.0131006292 |
| Derived Brier skill against climatology | 0.3005702907 |

Brier score is the mean squared error of a binary-event probability; lower is better. The calibrated result represents a **30.1% relative Brier-score reduction versus climatology**, calculated as `1 - 0.0304852794 / 0.0435859087`. It is not 30.1% more rainfall accuracy, a recall figure, or avoided disaster loss.

**Calibration did not improve held-out Brier in this run.** The uncalibrated candidate scored better than the calibrated candidate. Applying a validation-only calibrator does not guarantee calibration quality or test improvement.

Reliability also remains imperfect. In the saved 10–20% bin, mean prediction is approximately 14.50% against 28.31% observed frequency; in the 80–90% bin, it is approximately 85.19% against 72.59%. These examples show underestimation at some lower probabilities and overestimation at some higher probabilities, not a perfectly diagonal reliability curve.

The separate validation comparison was 0.027952 Brier for the candidate versus approximately 0.041111 for climatology on 427,635 validation rows. It is not an additional independent test result.

The recorded evaluation does not establish spread-only skill, PR-AUC, alert-budget recall, block-bootstrap uncertainty, physical-feature gains, or complete ablations. Those remain part of the planned assessment. No statistical-significance claim follows from row count alone.

### Result identity

```text
Manifest: manifest-fp-12803f75af61
Split:    2010-2015 / 2016-2017 / 2018-2019
Seed:     42

Booster SHA-256:
7428cfb384986c82ac09d1d0edd72762289bcdda597935b5c45d54f4b8f9170b

Feature-set SHA-256:
8565c522cabe8226c01a5ba94d83e75ea47f83f196beca8962feca8baf32267e
```

The underlying records are `artifacts/metrics/reduced_c00_evaluation.json`, `artifacts/model/reduced_c00_frozen_run.json`, and the saved calibrator/model metadata. These generated artifacts are local and Git-ignored. The recorded run includes a dirty worktree at commit `356f599`; it should not be described as training from a pristine tagged release.

## 10. A worked historical example

**R28N-094E**, initialized **31 December 2019 at 00 UTC**, illustrates the complete path from forecast to score to later verification. The region is centered at 28°N, 94°E, approximately covering 27–29°N and 93–95°E; it is not a city-specific prediction.

| Quantity | Day 1 | Day 5 | Day 6 |
| --- | ---: | ---: | ---: |
| Bust probability | 1.54% | 28.83% | 65.44% |
| Forecast rainfall | 0.02344 mm | 13.03219 mm | 20.16000 mm |
| Subsequent IMD rainfall | 0 mm | 12.27437 mm | 5.07229 mm |
| Absolute error | 0.02344 mm | 0.75781 mm | 15.08771 mm |
| Frozen threshold | 10 mm | 10 mm | 10 mm |
| Label | No bust | No bust | Bust |

Day 6 verifies **5 January 2020 03 UTC to 6 January 2020 03 UTC**, with coverage 98.4375%. The 2020 observation does not change the initialization's 2019 test membership.

```text
Source key:
GEFSv12/reforecast/2019/2019123100/c00/Days:1-10/apcp_sfc_2019123100_c00.grib2

Day-6 accumulation arithmetic:
(120-126)-(120-123)+(126-132)+(132-138)+(138-144)+(144-147)
```

The leading difference isolates +123–+126 hours; the remaining intervals complete +123–+147 hours. The largest positive saved score contribution in this case is forecast rainfall. One of the five displayed earlier analogs is a bust; their fraction is not the source of the 65.44% classifier probability.

This is a reproducible illustration, not a preregistered representative event or proof of overall skill. The regional totals do not establish a storm track, displacement distance, flood impact, or physical cause.

## 11. Dashboard and API

### What the interface exposes

The dashboard starts with a research-scope acknowledgement and identifies the replay initialization and model. Users choose a date and lead, inspect the bust-risk map, switch to forecast rainfall or coverage geometry, and open a region's evidence.

The inspector brings together decimal probability, threshold, exact UTC interval, coverage, forecast-versus-observation values, per-lead trajectory, score contributions, earlier cases, and provenance. The trust panel displays aggregate Brier/reliability evidence and the unavailable spread-only baseline. Corpus, roadmap, scope, and API documentation surfaces provide supporting context.

The exported slice contains **2018-01-01, 2019-01-01, and 2019-12-31**: the first, chronological-middle, and last available held-out initialization. Its **3,360 records** equal three dates × 112 regions × ten leads. This small replay is not an arbitrary-date browser over the entire decade.

Unavailable windows and regions remain null/gray, not low-risk. Illustrative ensemble/moisture/circulation cards preview future interface behavior and do not contribute to probabilities. Decorative flow/glow effects are not wind measurements or atmospheric simulations.

### API contract

| Route | Purpose |
| --- | --- |
| `GET /health` | Service and served-mode information. |
| `GET /v1/replay?init=YYYY-MM-DD&lead=1…10` | Regional GeoJSON FeatureCollection. |
| `GET /v1/region/{region_id}?init=...&lead=...` | Selected-region values, explanations, analogs, and provenance. |
| `GET /v1/evaluation` | Saved evaluation evidence. |
| `/docs` | Interactive OpenAPI specification. |

Replay responses retain `data_mode`, `model`, `truth_source`, `valid_start_utc`, `valid_end_utc`, `threshold_mm`, `window_quality`, `provenance`, `p_bust`, `tier`, `no_data_reason`, and region identity. The region response exposes rainfall amounts as `forecast_mm` and `observed_mm`. Unknown dates return 404 with available dates; lead validation is bounded to 1–10.

The shared data-row fields are:

```text
init_utc, lead_day, valid_start_utc, valid_end_utc, region_id, season,
lead_bucket, f_control_mm, o_imd_mm, coverage_fraction, error_mm,
threshold_mm, bust, source_key, grib_steps, imd_year, window_quality
```

The completed dataset additionally carries `split`. UTC timestamps and `window_quality` distinguish exact, approximate, and unavailable records; the present scored candidate uses exact Day 1–9 only.

## 12. Repository and local operation

| Location | Purpose |
| --- | --- |
| `README.md` | Entry point and quick start. |
| `docs/` | This project reference and underlying research, decisions, audit, results, and release records. |
| `DATA_MANIFEST.csv` | Observed source identities, decoded metadata, and provenance. |
| `config/` | Region geometry, label/split policies, and explanation groups. |
| `src/bust/data/` | Inventory, acquisition, decoding, alignment, regions, labels, dataset construction. |
| `src/bust/features/` | Candidate features and analog retrieval. |
| `src/bust/model/` | Baseline, fitting, calibration, and evaluation. |
| `src/bust/api/` | Export, schemas, artifact store, and read-only routes. |
| `scripts/` | Reproducible command entry points. |
| `tests/` | Data, leakage, model, and API contract tests. |
| `web/` | Vite/Leaflet frontend and local assets. |
| `data/fixtures/` | Committed illustrative integration data. |
| `data/raw/`, `data/interim/`, `data/processed/` | Local, ignored source/intermediate/derived data. |
| `artifacts/model/`, `artifacts/metrics/`, `artifacts/replay/` | Local, ignored generated model and evidence assets. |
| `assets/screenshots/`, `submission/`, `slides/`, `demo/` | Homes for reviewed presentation and submission material; folder existence is not release completion. |

### Setup

Python 3.11 and Node 20+ are the documented starting environment:

```sh
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
make web
make smoke
```

The repository supplies dependency declarations/lock information and `environment.yml`. Where GRIB bindings are difficult to install, the conda-forge alternative is `conda env create -f environment.yml`, followed by `conda activate synoptiq`.

A clone contains code and fixtures, **not the real generated replay or raw training corpus**. With the permitted real replay asset supplied separately, serve it using:

```sh
source .venv/bin/activate
unset SYNOPTIQ_DEMO_MODE
REPLAY_ASSET_PATH=artifacts/replay/reduced_c00_replay.json API_PORT=8001 make api
```

The dashboard is then at `http://127.0.0.1:8001/`. The mode comes from configuration and the asset, not the port. Without a real replay path, the default service serves the fixture; current `make demo` explicitly enables fixture demonstration mode. This differs from the original plan's intended use of that command.

| Command | Current purpose |
| --- | --- |
| `make pilot`, `make dataset` | Inventory/data-building workflow. |
| `make train` | Climatology baseline workflow; currently permits replacement. |
| `make candidate` | Reduced c00 candidate training with overwrite protection. |
| `make evaluate-candidate` | Frozen-candidate calibration/evaluation workflow. |
| `make replay` | Generate replay artifacts; currently permits replacement. |
| `make api`, `make web` | Serve the selected replay and build the frontend. |
| `make smoke`, `make replay-smoke` | Fixture/API smoke and real replay smoke respectively. |
| `make test`, `make lint` | Tests and source linting. |

Serving an existing replay does not require downloading the corpus or retraining. Recomputing results does require the relevant aligned data, model/calibrator identities, and evaluation configuration. Source-code licensing does not itself authorize redistribution of external data.

## 13. Development history and completion status

The original 72-hour plan established two critical boundaries: **D1-04**, proving the forecast/observation time match before empirical labels; and **D2-05**, proving the complete real-data path before an empirical demonstration. Frontend integration could proceed earlier using explicit fixtures.

The project then evolved through these decisions:

| Decision group | Lasting consequence |
| --- | --- |
| D-001–D-003 | Rainfall-only GEFSv12/IMD research scope, chronological splits, and a visible distinction between fixtures and real evidence. |
| D-004–D-005 | Audited 03–03 UTC mapping; exact Days 1–9; Day 10 withheld. |
| D-006 | Fixed region geometry and the explicit 80% support rule. |
| D-007 | IMD 2020 added only for late-2019 verification. |
| D-008 | Reduced c00-only model approved for the deadline without abandoning the full long-term feature design. |
| D-009 | Current control-rain and regional-context score evidence displayed without claiming physical causes. |
| Documentation/layout work | Reader documentation collected under `docs/`, with separate screenshot/submission homes and stable pipeline paths. |

### Recorded milestones

| Tickets | Completion recorded | Scope and remaining distinction |
| --- | --- | --- |
| D1-01–D1-04 | Complete | Setup, source pilots, and signed time-window/Day-10 gate. |
| D1-05–D1-07 | Complete | Regions/labels, offline fixture slice, and full real c00 dataset. |
| D2-01 | Complete under explicit-status acceptance | Real climatology; spread-only remains unavailable. |
| D2-02 | Complete | Real drill-down, lead values, intervals, and provenance. |
| D2-03–D2-04 | Complete for D-008 | Reduced candidate, earlier analogs, frozen configuration, calibration, and honest test artifacts; not the full physical model. |
| D2-05 | Complete in later log/roadmap | Real dataset → model → API → map → evidence/test-panel integration and recorded offline verification; `e2e-v1` sign-off recorded. |
| D3-01 | Open | Complete the five-explanation audit and trust/API acceptance reconciliation. |
| D3-02 | Open | Final video cut and results/caption check. |
| D3-03 | Open | Provenance/licensing package and fresh-clone, second-machine acceptance. |
| D3-04 | Open | Final merged release and assets, `submission-freeze`. |
| D3-05 | Open | Export/rehearsal, working shared links, second-device check, submission receipt. |

The formal first three phases are recorded as complete; the trust/demo/submission phase remains open. The plan's 27–29 September timetable was a planning assumption, not verified evidence of an official portal deadline. Its role placeholders are historical accountability assignments, not proof that each named person performed every task.

Older “blocked” or “recording pending” paragraphs remain in the chronological records. This overview uses later completion entries where available rather than treating all historical status statements as simultaneous.

## 14. Quality, reproducibility, and release

Scientific credibility depends on the joins between sources, not just a passing training command. The test and acceptance design covers accumulation gaps/overlaps, daily-date mapping, regional support, strict labels, training-only thresholds, earlier-only analogs, validation-only calibration, fixed splits, API schemas, and explicit no-data handling.

A release needs a traceable row linking a real source key and GRIB steps to its IMD interval, forecast/reference amounts, threshold, probability, explanation, API response, and rendered region. Fixture smoke verifies integration; it does not establish model skill.

The lasting release requirements are:

- **Identity:** a known code state, manifest fingerprint, split, seed, feature schema, model identity, and matching generated artifacts.
- **Consistency:** one set of frozen values across metrics, dashboard, documentation, slides, and video; failed or unavailable comparisons remain visible.
- **Reproduction:** fresh-clone setup plus the permitted generated release assets, real replay smoke, and a second-machine offline refresh.
- **Interpretability:** five inspected explanations tied to actual inputs and earlier cases; model attribution distinguished from physical causation.
- **Distribution:** current provider terms and third-party asset attribution checked; no raw archives, credentials, virtual environments, or large recordings committed.
- **Acceptance:** final release/assets frozen, presentation/video links opened on another device, and submission receipt retained when applicable.

The source manifest and dated run log preserve what was actually attempted and produced. Source, threshold, time-window, split, grid, or feature changes are recorded as decisions rather than silently changing the meaning of existing results. Missing dates are not filled with fabricated forecasts; an incomplete gate remains blocked with a labeled fixture/pilot fallback.

These principles remain relevant beyond the hackathon. They support comparing future versions without losing the meaning of the first result.

## 15. Future development

The roadmap is dependency-driven, not a promise that adding a data field will improve skill.

### Complete the present release

Finish D3-01–D3-05 against the current reduced model: reconcile score/tier captions, audit explanations, finalize recordings and result text, verify asset terms, reproduce the real replay on another machine, and freeze the package. UI polish must not blur the distinction between active evidence and illustrative future panels.

### Expand the scientific candidate

1. **Acquire the missing corpus:** complete p01–p04 rainfall and selected atmospheric fields through the resumable pipeline, preserving source identities, units, grids, and exact intervals.
2. **Resolve feature definitions:** choose actual available humidity/wind/pressure/height quantities and build the intended named physical and ensemble summaries. The present documents differ on specific versus relative humidity and on wind level; these are unresolved design details, not acquired predictors.
3. **Strengthen the analog model:** move beyond scalar rainfall similarity to audited multivariable forecast patterns; investigate earlier analog-error summaries as predictors using training-only transformations and query-safe chronology.
4. **Compare justified alternatives:** implement spread-only predictions, evaluate proposed weighting choices, and ablate physical and analog features against simpler models.
5. **Broaden evaluation:** report PR-AUC, recall at the planned top-10% regional-alert budget, lead/season slices, reliability counts, and week/episode-block uncertainty where supported. Investigate 5/10/20 mm floor and spatial-displacement sensitivity without silently replacing the main target.
6. **Address calibration:** investigate the observed reliability gap using permitted development data and an explicit independent assessment protocol for new claims.

### Extend supported windows and coverage carefully

Day 10 needs exact interval evidence or a separately approved approximation with sensitivity analysis and explicit display/evaluation treatment. Peripheral-region support needs a justified coverage/reference study, not a lower threshold merely to fill the map. Neither is solved by frontend changes.

### Transfer to institutional and current forecast systems

NCUM/NEPS transfer requires access to historical issue-time fields, a model-specific variable/time mapping, matched verification, retraining/recalibration, and new held-out testing. TIGGE may offer a constrained research route, but catalogue membership does not prove continuous coverage or unrestricted redistribution.

A live service additionally needs a verified current-model bridge, data-availability and latency handling, version/drift monitoring, and human operational validation. Historical replay demonstrates the interface and research method; it does not establish safe live use.

### Separate research extensions

| Extension | Required distinction |
| --- | --- |
| Heat-wave/temperature errors | New temperature forecast target, event/label policy, reference, and evaluation. |
| Cyclone track/intensity errors | Forecast tracks/intensity, storm identifiers, appropriate best-track verification, and separate metrics. |
| ERA5 or IMDAA context | Reanalysis is model-informed context, not error-free truth or automatically available issue-time input. |
| IMERG/reference sensitivity | Different product, grid, timing, and measurement characteristics; not an interchangeable replacement for IMD land rainfall. |
| Multi-centre forecasts | Separate source distributions, archive completeness, licences, and validation. |
| Dense spatial/deep models | Additional data, compute, leakage checks, and demonstrable value beyond the regional baseline. |

Monsoon depressions, western disturbances, active/break regimes, and rainfall displacement motivate potential features. They remain physical hypotheses unless supported by actual fields and analysis; current score contributions do not establish those mechanisms.

## 16. Limitations and open questions

The present model establishes a narrow but real historical result. Important limits are the c00-only feature set, incomplete reliability, lack of the full planned evaluation suite, fixed 2° spatial scale, gridded-reference uncertainty, three-date replay slice, and no operational or sector-impact validation.

Two presentation/design inconsistencies remain explicit:

- **Risk tiers:** the recorded exporter/legend uses low below 30%, watch 30–<50%, and high ≥50%; the original reference proposed a 20% low/watch boundary. This document reports the discrepancy without approving a policy change. Numeric probability is the underlying output; tiers are not official warnings.
- **Phase naming:** some UI wording calls atmospheric expansion “Phase 4,” while the formal fourth phase is trust, demonstration, and submission. “Future feature expansion” is the unambiguous description of deferred atmospheric work.

Older records also retain stale pending statuses, root-document paths, and an overextended January endpoint in D-007. The adopted interval formula and exact per-row UTC bounds determine verification dates; inclusion of IMD 2020 does not expand the initialization years. These historical wording inconsistencies should not become new scientific assumptions.

If a future version fails to improve on a simpler baseline, the result remains worth reporting as a diagnostic finding. A working interface, an appealing explanation, or one successful example is not a substitute for aggregate validation.

## 17. Team

**HackTastic 6ix**

| Member | GitHub |
| --- | --- |
| Kanishka Pandey | [kan9667](https://github.com/kan9667) |
| Aanya Varshney | [aanyavarshneyav](https://github.com/aanyavarshneyav) |
| Rudraksh Saini | [Rudrakssh](https://github.com/Rudrakssh) |
| Dhruv Makkar | [dhruvsded1](https://github.com/dhruvsded1) |
| Aadi Jain | [DeltaData0](https://github.com/DeltaData0) |
| Triman Singh Chadha | [Triman01](https://github.com/Triman01) |

This identifies the team without attributing unverified individual implementation contributions. The original A–F assignments are retained in the implementation history.

## 18. Research and project records

### Primary research and data references

These sources support the data and methodological background, not Synoptiq's measured performance. Links and source interpretations are carried forward from the research/audit documents; they were not newly checked for current product or licensing changes during this consolidation.

- NOAA/AWS: [GEFSv12 reforecast archive](https://registry.opendata.aws/noaa-gefs-reforecast/) and [data description](https://noaa-gefs-retrospective.s3.amazonaws.com/Description_of_reforecast_data.pdf).
- Guan et al.: [GEFSv12 reforecast dataset paper](https://repository.library.noaa.gov/view/noaa/53301).
- IMD Pune: [0.25° daily rainfall NetCDF catalogue](https://imdpune.gov.in/cmpg/Griddata/Rainfall_25_NetCDF.html).
- Pai et al.: [IMD gridded rainfall methodology](https://mausamjournal.imd.gov.in/index.php/MAUSAM/article/view/851?articlesBySameAuthorPage=2).
- Daily-window background: [IMD evaluation/reporting-convention paper](https://journals.ametsoc.org/view/journals/hydr/24/6/JHM-D-22-0160.1.xml) and [IMD-hosted Mitra et al. study](https://imdpune.gov.in/cmpg/Realtimedata/gpm/mitra_etal_2009.pdf); product-specific interpretation is retained in the signed audit.
- Rodwell et al.: [Characteristics of Occasional Poor Medium-Range Weather Forecasts for Europe](https://journals.ametsoc.org/view/journals/bams/94/9/bams-d-12-00099.1.xml). Its event definition is not adopted as an Indian rainfall standard.
- SHAP: [TreeExplainer documentation](https://shap.readthedocs.io/en/latest/generated/shap.TreeExplainer.html).
- Transfer context: [NCMRWF system descriptions](https://nwp.ncmrwf.gov.in/HomePage/index.php) and [TIGGE archive overview](https://ecds.ecmwf.int/datasets/tigge-forecasts?tab=overview).

### Underlying project history

This is the single reader-facing synthesis. Original files remain available for detailed evidence and historical traceability, not as additional required reading:

| Record | Contribution to this reference |
| --- | --- |
| [Canonical research reference](SIH-26079-Forecast-Bust-Detection-Canonical-Reference.md) | Problem, source selection, alternatives, full architecture, prior literature, risks, and future scope. |
| [72-hour implementation plan](SIH-26079-72-Hour-Implementation-Plan.md) | Original dependencies, schema, milestones, acceptance gates, and submission design. |
| [Decisions](DECISIONS.md) | Approved time, grid, observation-boundary, reduced-candidate, and display choices. |
| [Data audit](data_audit.md) | Real decoding, accumulation/region hand checks, provenance corrections, and completed-corpus sign-off. |
| [Method](method.md) and [results](results.md) | Statistical protocol and recorded baseline/candidate/replay evidence. |
| [Run log](RUN_LOG.md) | Dated commands, outcomes, later verifications, and progress history. |
| [Historical agent contract and roadmap](AGENTS.md) | Original collaboration safeguards and recorded ticket status. |
| [Release checklist](release_checklist.md) | Packaging, attribution, second-machine, and submission requirements. |
| [Earlier complete handoff](SYNOPTIQ_COMPLETE_HANDOFF.md) | Detailed saved-artifact summary, worked example, product inventory, and communication context. |

As Synoptiq develops, this reference can evolve with it: retain dated result identities, explain material design changes, and keep implemented capabilities distinct from research proposals. The project's durable core is not a particular dashboard or model version—it is a reproducible answer to a clearly defined forecast-reliability question.
