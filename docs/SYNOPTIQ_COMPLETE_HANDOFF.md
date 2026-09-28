# Synoptiq — complete project handoff for presentation and demo authors

**Prepared:** 28 September 2026. **Project:** SIH 26079. **Team:** HackTastic 6ix.
**Repository:** https://github.com/kan9667/synoptiq
**Inspected working checkout:** `feat/ui-demo-polish`, commit `decd176`.

This is a self-contained briefing for a teammate or AI agent making the idea PPT, speaker notes, demo script, or judge Q&A. It captures both the intended solution and the implemented research MVP. It is a dated snapshot, not an assertion that every planned capability is finished.

The facts below were checked against the local source, planning documents, saved dataset summary, model metadata, evaluation JSON, and replay JSON. The real replay smoke command passed during preparation. This session did not retrain the model, repeat the complete acquisition, independently review the recording, or visually retest every screen.

## 1. Read this first: the project in one minute

Synoptiq estimates the probability that a regional rainfall forecast will have an unusually large error. It uses information from the issued forecast, learns from historical forecast-versus-observation comparisons, and presents a risk map with model-score evidence and earlier comparable cases.

The forecast being assessed is the **NOAA GEFSv12 control member's regional 24-hour rainfall forecast**. The verification reference is **IMD 0.25° daily gridded rainfall**. The current trained model is a **reduced c00-only LightGBM candidate**, using five inputs. It has real historical data, held-out evaluation, a read-only API, and a working replay dashboard.

The broader design adds five-member ensemble information, moisture/circulation fields, and richer analog-error features. These remain future implementation work. The currently displayed examples for those atmospheric groups are labeled **Illustrative**.

The intended horizon is Days 1–10, subject to exact interval validation. The current release scores **Days 1–9**; **Day 10 is unavailable**. Of 112 fixed 2° regions, 65 meet the current IMD coverage rule and 47 remain explicit no-data.

**Short pitch:** “Synoptiq helps forecast reviewers identify which regional rainfall forecasts deserve closer inspection, with a bust probability, traceable evidence, and historical validation.”

**Original reference pitch:** “Given a GEFS forecast that was available at issue time, we estimate where its Day 1–10 rain forecast is unusually likely to fail, explain which measurable signals drove that estimate, and show whether those probabilities matched subsequent observations.”

**Required scope statement for empirical demos:** “GEFSv12 reforecast research prototype; not NCUM/NEPS operational validation.”

Sources: Canonical Reference §§1, 3–5; decisions D-005–D-009; current model and replay artifacts.

## 2. How to use this briefing

Use three explicit evidence levels:

| Level | Meaning | Suitable wording |
| --- | --- | --- |
| Implemented and evidenced | Present in current code and/or saved real artifacts | “The current prototype uses…”; “On the held-out cohort…” |
| Intended prototype capability | Part of the original architecture, not finished in the current candidate | “The proposed architecture combines…”; “The next model will be evaluated with…” |
| Longer-term extension | Requires new data, labels, validation, access, or operations | “A future extension would require…” |

For the **idea PPT**, explain the full proposed solution confidently in design language, while clearly labeling any actual results as results of the reduced candidate. For the **screen recording**, describe the software and data actually visible. Never narrate planned moisture or ensemble features as already contributing to today's displayed probability.

The existing deck should retain its slide count. The user explicitly requested **no additional slides**. Improve content within the existing template; use speaker notes for technical depth.

Repository evidence order for current claims:

1. Saved artifact values and the code that produces/serves them.
2. Dated sign-offs in `docs/RUN_LOG.md`, approved exceptions in `docs/DECISIONS.md`, and the signed source/window audit.
3. Current roadmap in `docs/AGENTS.md`.
4. The frozen Canonical Reference and Implementation Plan for intended scope.

Older blocked entries are historical records, not necessarily today's status. Do not take a checked ticket to mean that an approved deferred feature was implemented.

## 3. Problem, audience, and intended benefit

### The problem

A rainfall forecast gives an expected amount, but a reviewer also needs to assess how much confidence to place in that particular region and lead day. Large errors can result from rainfall placement, timing, or intensity differences. Synoptiq turns this review question into a defined, testable probability-estimation task.

It does not generate a new numerical weather forecast, repair a forecast automatically, predict flood depth, or decide whether an authority should issue a warning. Its output supports human forecast review.

### Intended users and value

| Audience | Intended benefit | Evidence boundary |
| --- | --- | --- |
| Meteorologists and forecast desks | Prioritize region/lead combinations for closer scrutiny and inspect supporting evidence | Direct product workflow demonstrated by historical replay; time savings not measured |
| Disaster management authorities | Bring forecast-reliability context into scenario planning and preparedness discussions | Operational use needs independent validation and meteorologist oversight |
| Rainfall-sensitive planning teams | Consider forecast reliability in agriculture, aviation, and flood-preparedness planning | No sector deployment, economic benefit, or avoided-loss result has been measured |
| Research and integration teams | Reproduce the forecast/observation comparison and inspect the API and provenance | Current code and saved artifacts provide a research integration surface |

**Impact wording:** “Make forecast review more targeted, evidence-based, and transparent.”

Do not invent adoption numbers, customers, partnerships, lives saved, financial savings, reduced false-alarm percentages, or a business model. No measured operational-impact study or pricing plan is established in the source documents.

## 4. What makes the approach distinctive

These are defensible design strengths, not claims that no other team or prior research has used them.

| Differentiator | Why it matters | Current vs intended |
| --- | --- | --- |
| Forecast-error risk as the target | Answers which issued forecasts merit review, rather than presenting another rainfall map alone | Implemented for the defined c00 rainfall error |
| Region × season × lead-aware bust definition | A material error is judged against the relevant historical error distribution | Implemented, train-only thresholds with a 10 mm floor |
| Audited daily time alignment | Prevents a timing mismatch from being mistaken for a weather-model failure | Implemented exact Day 1–9 windows; Day 10 withheld |
| Probability plus inspectable evidence | Lets reviewers inspect feature contributions and earlier forecast cases | Implemented for five c00 candidate features and simple rainfall analogs |
| Transparent missing-data behavior | Makes unsupported regions and lead windows visible rather than implying certainty | Implemented gray/null states |
| Evaluation tied to a baseline and frozen years | Makes claims testable instead of relying on a visually impressive case | Implemented Brier/reliability comparison against climatology |
| Disk-bounded, resumable data processing | Makes a large archive usable on a machine without storing the entire raw corpus | Implemented acquisition, validation, shard persistence, and raw-file deletion |
| Rich physical + ensemble + analog-error model | Intended to combine multiple issue-time signals and test whether they add value | Full version deferred; not responsible for current reported performance |

**Slide-ready innovation points:**

- **Forecast reliability:** flag regional forecasts that deserve closer review.
- **Audited timing:** compare the same 24-hour forecast and observation windows.
- **Inspectable evidence:** pair scores with contributions, prior cases, and provenance.
- **Measured credibility:** evaluate on later years against a climatology baseline.

**Prior-art boundary:** boosted trees, calibration, SHAP, ensemble spread, and analog methods are established techniques. The project contribution is their proposed integration around an auditable Indian regional rainfall-bust workflow. “World first,” “unique AI invention,” and “no other team has this” are unsupported. (Reference §§1, 7–9.)

## 5. Exact scientific target and terminology

### One row / prediction unit

One sample is `(00 UTC initialization date, lead day, fixed 2° region)`.

Let:

- `F` = GEFSv12 c00 regional rainfall accumulated over the audited 24-hour window.
- `O` = IMD regional rainfall over the matching window.
- `error_mm = abs(F - O)`.
- `threshold_mm = max(training q90 of error for region × season × lead bucket, 10 mm)`.
- `bust = error_mm > threshold_mm` — strict greater-than, not greater-than-or-equal.

The model estimates `P(bust)` using permitted issue-time predictors. Both overprediction and underprediction can create a bust. Low bust probability does not mean low rainfall; high bust probability does not mean a flood is likely.

The 10 mm floor is a declared research policy, not an official IMD warning criterion. A regional threshold can be above 10 mm. Missing observations do not imply “no bust.”

Seasons: `JJAS` (June–September) and `other`. Lead buckets: `1–3`, `4–7`, `8–10`; unavailable Day 10 is excluded from threshold fitting and scoring.

`1 - P(bust)` is only the complement for this particular event definition. It is not a general forecast-accuracy or safety score.

### Time-window rule and Day 10

For IMD date label `D`, the adopted mapping is `[D - 1 day 03:00 UTC, D 03:00 UTC)`. The convention was grounded in source evidence and hand-checked arithmetic; it is not an explicit time-bounds attribute discovered in the NetCDF files.

For GEFS 00 UTC initialization `init` and lead `L`:

```text
start = init + (24L - 21) hours
end   = init + (24L + 3) hours
```

| Lead | Required interval after initialization |
| --- | --- |
| Day 1 | [+3h, +27h) |
| Day 6 | [+123h, +147h) |
| Day 9 | [+195h, +219h) |
| Day 10 | [+219h, +243h) |

Day 10 needs the final **+240h to +243h** amount. An inspected **+240h to +246h** six-hour accumulation cannot establish how much fell in its first three hours. Halving it would impose an unvalidated rainfall-distribution assumption. The current policy returns no-data.

**Idea-PPT wording:** “Day 10 is release-gated: score it only after an exact matching 24-hour interval is validated; otherwise return explicit no-data.”

**Current-demo wording:** “Days 1–9 are available; Day 10 is withheld because the required exact interval is not evidenced.”

### Regional coverage

The fixed 2° grid has 112 intersecting regions: 65 supported and 47 peripheral. Each full 2° cell contains an 8×8 arrangement of the IMD 0.25° grid. The current eligibility rule requires coverage of at least 0.80. This is a defined grid-support/valid-data rule, not a claim of complete gauge coverage everywhere in India.

Peripheral no-data cells are intentional. Lowering the threshold to color them in would change the evaluation policy. Region IDs encode cell centers; do not call every cell a district or city. `R28N-094E` is centered at 28°N, 94°E; the cell is approximately 27–29°N, 93–95°E. Avoid the earlier script's unsupported “near Guwahati” label.

Sources: `config/label_policy.yaml`; `docs/data_audit.md`; decisions D-005–D-007; data alignment/region/label code.

## 6. Data and completed acquisition

| Item | Current evidence |
| --- | --- |
| Forecast corpus | 3,652 daily 00 UTC GEFSv12 c00 precipitation initializations, 2010-01-01 through 2019-12-31 |
| Variable | Control accumulated precipitation, `apcp_sfc` |
| Observation corpus | 11 IMD annual NetCDFs, 2010–2020 |
| Why 2020 exists | Verification-only observations for late-December 2019 Day 1–9 windows; no 2020 forecast initialization enters training/test |
| Observed remote GEFS payload | 98,387,769,232 bytes, approximately 98.39 GB / 91.63 GiB |
| IMD file payload | 279,959,156 bytes across 11 years |
| Aligned dataset | 4,090,240 rows = 3,652 dates × 112 regions × 10 leads |
| Day-10 unavailable rows | 409,024 |
| Dataset Parquet size inspected | 60,625,386 bytes; compression/derived rows explain why this is far smaller than the raw archive |

The manifest has additional pilot/method/fixture records. Its total line count is not the number of training initialization dates. Some p01–p04 pilot evidence exists, but that does not establish a complete ensemble corpus for training.

### Disk-safe acquisition design actually implemented

- Producer discovers actual archive objects and retrieves them with bounded concurrency.
- Current defaults: **12 download workers**, **150 raw-file buffer limit**, **8 GiB working-footprint cap**. Earlier discussions mentioned 200 files; 150 is the inspected implementation.
- Byte reservations and filesystem checks regulate capacity independently of download concurrency.
- Consumer verifies downloaded metadata/size/checksum evidence, decodes and aligns a date, writes a shard, and validates it before deleting its raw GEFS file.
- SQLite acquisition state tracks completion and retry state; restart logic reconciles persisted work.
- Failures remain explicit. A corpus is complete only with the intended date coverage and validated shards.
- The final Parquet is published after completion checks; train-only thresholds are applied without requiring the entire raw archive to remain on disk.

The audit's completion sign-off records 3,652 completed items, zero failed items, and 3,652 valid reopened shards. This is historical sign-off evidence; the entire download was not repeated for this handoff.

**Feasibility claim:** “A resumable pipeline processes roughly 98 GB of raw archive data within a configured 8 GiB working budget.” Do not claim that total internet transfer was only 8 GB, or that 8 GiB is the complete machine's total storage/RAM requirement.

## 7. Model, explanations, and analogs

### Current trained candidate

Model identifier: `reduced_c00_only_candidate`.

| Input | Meaning |
| --- | --- |
| `f_control_mm` | Issue-time control forecast rainfall for the region/window |
| `region_id` | Fixed region identity |
| `season` | JJAS or other |
| `lead_day` | Lead number |
| `lead_bucket` | 1–3 / 4–7 / 8–10 bucket |

These are the five actual model inputs. IMD observed rainfall, realized error, bust labels, and post-hoc analog outcomes are not predictors.

The saved model uses LightGBM binary gradient boosting on CPU: 100 estimators, 31 leaves, learning rate 0.05, minimum child samples 50, four threads, deterministic settings, seed 42. Saved category mappings come from training data with an explicit unseen-category fallback. The saved LightGBM version is 4.7.0.

The current feature simplicity is an approved deadline decision (D-008). Do not call it a five-member trained system just because there are five input columns.

### Splits and calibration

| Partition | Initialization years | Eligible labeled rows | Role |
| --- | --- | ---: | --- |
| Train | 2010–2015 | 1,281,735 | Fit thresholds, baseline, candidate, and training-era analog pool |
| Validation | 2016–2017 | 427,635 | Candidate comparison and sigmoid/Platt calibration |
| Test | 2018–2019 | 427,050 | Held-out comparison after candidate freeze |

Counts refer to eligible exact Day 1–9 region/lead samples. Rows are correlated across dates, regions, and leads; they are not 427,050 independent storms.

The evaluation pipeline records frozen-run metadata before reading test rows. The saved run records a dirty worktree at training/evaluation commit `356f599`; exact Booster and feature hashes provide additional artifact identity. Do not describe it as a pristine tagged release at training time.

### Score evidence / SHAP terminology

The exporter uses the saved LightGBM Booster's `pred_contrib=True` contributions. They describe contributions to the underlying tree score, not percentage-point changes in the final calibrated probability. The UI groups them as control rain, regional context, and lead/season.

SHAP-style score attribution is legitimate evidence about the fitted model. It does not prove a moisture mechanism, monsoon depression, atmospheric cause, or a real-world causal explanation. Near-zero values can round to `0.0000`; that does not imply the model failed.

### Current analog retrieval

The current implementation:

1. Uses the training-era pool for held-out replay.
2. Matches the same region, season, and lead bucket.
3. Requires initialization strictly earlier than the query and eligible exact Day 1–9 data.
4. Ranks by absolute difference in c00 forecast rainfall, with deterministic tie-breaking.
5. Returns up to five cases, then displays their saved error and bust outcomes as post-hoc context.

It is a simple forecast-rain similarity retrieval, not a completed multivariable weather-pattern search. Those five cases do not determine the current classifier probability. Their bust fraction need not equal the model's probability.

### Broader intended feature/model design

The original design calls for roughly 15–25 named issue-time quantities: control/ensemble rainfall summaries, rain spread, wet-member fraction, precipitable water, humidity/winds, sea-level pressure, geopotential height, lead/season context, and analog-error summaries. Five-member design means **c00 plus p01–p04**.

Before using those features, acquire and decode their real full-date fields, establish variable units and grids, audit chronology, freeze the changed feature policy, and validate the new model. UI q850 examples do not establish that q850 was acquired; current `reason_groups.yaml` also names relative humidity (`rh850_mean`). Specific versus relative humidity and 10 m versus 850 hPa wind must be resolved from actual source variables before implementation or precise architecture claims.

The project uses ML, but no integrated generative-LLM reasoning layer is established in the current source. Do not describe it as an autonomous AI meteorologist, chatbot, RAG platform, or agentic warning system.

## 8. Verified results and how to describe them

Source: `artifacts/metrics/reduced_c00_evaluation.json`, read during preparation.

| Metric on the same eligible 2018–2019 cohort | Value |
| --- | ---: |
| Test samples | 427,050 |
| Observed bust prevalence | 0.0474300433 (4.7430%) |
| Train-only climatology Brier score | 0.0435859087 |
| Reduced candidate, uncalibrated Brier score | 0.0294928722 |
| Reduced candidate, calibrated Brier score | 0.0304852794 |
| Calibrated minus climatology Brier | −0.0131006292 |
| Derived Brier skill against climatology | 0.3005702907 |
| Derived relative Brier-score reduction | 30.0570%, approximately 30.1% |

Calculation: `1 - 0.030485279439155667 / 0.04358590868166439`.

**Safe result sentence:** “On 427,050 eligible Day 1–9 verifications from held-out 2018–19 initializations, the calibrated reduced candidate achieved a Brier score of 0.03049 versus 0.04359 for climatology, a 30.1% relative reduction.”

**Required accompanying qualification:** “The uncalibrated candidate scored 0.02949, so validation-only calibration did not improve held-out Brier in this run.”

Brier is mean squared error of binary-event probabilities; lower is better. The 30.1% figure is not accuracy, rainfall-error reduction, recall, or damage avoided. No confidence interval or significance claim follows from this calculation alone.

The reliability plot is **not perfectly calibrated**. For example, the 10–20% bin has mean prediction about 14.50% and observed bust frequency about 28.31%; the 80–90% bin has mean prediction about 85.19% and observed frequency about 72.59%. Lower-mid bins underestimate risk and several high bins overestimate it. Do not say “whenever we say 60%, exactly 60% bust.”

Validation-only result: Brier **0.027952** for the candidate versus approximately **0.041111** for climatology. Keep it labeled validation, separate from the held-out result.

The current saved candidate evaluation provides Brier, prevalence, calibration metadata, sample counts, and reliability bins. **Spread-only results, reported PR-AUC, alert-budget recall, block-bootstrap intervals, full ablations, and physical-feature gains are not established by that artifact.** They remain evaluation work in the intended plan.

Artifact identifiers:

```text
manifest_id: manifest-fp-12803f75af61
split: 2010-2015/2016-2017/2018-2019
seed: 42
Booster SHA-256:
7428cfb384986c82ac09d1d0edd72762289bcdda597935b5c45d54f4b8f9170b
feature-set SHA-256:
8565c522cabe8226c01a5ba94d83e75ea47f83f196beca8962feca8baf32267e
```

## 9. Current product: what is real, illustrative, or absent

| Capability | Current status |
| --- | --- |
| Historical c00 rainfall corpus and aligned labels | Real, completed and signed off |
| LightGBM probability and validation-only calibrator | Real saved artifacts |
| Climatology comparison and reliability plot | Real held-out evaluation |
| Map, region click, per-lead probability curve | Implemented with saved replay responses |
| Forecast-vs-observation and threshold | Real for supported exact replay rows |
| Model-score contributions | Real saved LightGBM contributions |
| Earlier analog cases | Real c00 similarity cases with post-hoc outcomes |
| Ensemble/moisture/circulation preview numbers | Illustrative examples; not retrieved observations or model inputs |
| Flow/glow effects | Presentation effects; do not narrate as measured winds or a physical simulation |
| Arbitrary historical-date browsing | Not in the current exported slice; three dates available |
| Day 10 probability | Unavailable |
| 47 low-coverage regions | Explicit no-data; not a UI defect |
| Spread-only baseline | Unavailable without full perturbed-member data |
| Live forecast feed/public warning service | Not implemented |
| NCUM/NEPS validation | Not performed |
| Heat-wave/cyclone models | Future, separate tasks |
| Final submission and second-machine acceptance | Not established as complete by current roadmap |

The illustrative cards currently contain fixed examples such as rain range 12.4–29.8 mm, spread 6.3 mm, q850 11.8 g/kg, precipitable water 42 mm, wind 9.6 m/s SE, and pressure 1002 hPa. These are examples of how the future interface will present fields. **They must never enter the results slide, be linked to R28N-094E as observations, or be described as the reason for its 65.44% probability.** Keep the Illustrative badge visible when showing them.

### UI risk-tier discrepancy to know before recording

The inspected exporter and legend use **low <30%, watch 30–<50%, high ≥50%**. The Canonical Reference proposed **low <20%, watch 20–<50%, high ≥50%**. This is an unresolved design-to-implementation discrepancy; this handoff does not approve a policy change.

For current recordings, use the numeric API probability and the visible server tier. In particular, **28.83% currently appears low**, not watch. Before declaring a final tier policy, reconcile it through the decision/release process. Tiers are presentation thresholds, not official warnings or validated calibration bins.

## 10. Architecture and technical feasibility

### Actual pipeline

```text
Observed NOAA object inventory + IMD annual files
    -> bounded acquisition / checksum and decode checks
    -> exact UTC-window alignment + fixed 2° regional aggregation
    -> train-only error thresholds and labels
    -> rows.parquet + dataset summary
    -> c00 LightGBM + validation-only sigmoid calibrator
    -> held-out evaluation against climatology
    -> frozen replay export + score contributions + earlier analogs
    -> read-only FastAPI -> offline Vite/Leaflet dashboard
```

During prediction, only issue-time inputs go into the model. IMD observations create historical labels and later verification displays. A presentation diagram must not draw a prediction-time arrow from observed IMD rain or realized bust labels into the feature extractor/model.

The current analog branch enriches replay explanations after prediction; the richer analog-error-as-predictor branch belongs to the intended future model.

### Stack

| Layer | Technologies / purpose |
| --- | --- |
| Runtime | Python 3.11; CPU-first local execution |
| Retrieval | Requests, observed public archive inventory, persistent acquisition state |
| Data decoding | ecCodes/cfgrib for GRIB2; xarray for labeled arrays and NetCDF |
| Tables/numerics | NumPy, pandas, PyArrow/Parquet; scientific Python dependencies |
| Model | LightGBM; scikit-learn calibration/evaluation utilities |
| Explanations | Saved Booster feature contributions; SHAP ecosystem in intended stack |
| API | FastAPI, Pydantic, Uvicorn, OpenAPI `/docs` |
| Web | Vite, Leaflet, plain JavaScript/CSS; bundled local assets |
| State/storage | SQLite for acquisition progress; Parquet for rows; JSON for current replay/model metadata/metrics; Booster text model |
| Quality/reproducibility | pytest, Ruff, Make targets, Git, manifests, checksums, frozen config |

**SQLite correction:** the actual replay API loads a JSON asset into a cached store. Do not label the current replay backend a SQLite database; SQLite currently belongs to acquisition state.

### Feasibility and limits

- Real archive acquisition and aligned rows demonstrate data feasibility for the reduced candidate.
- CPU model training and local serving avoid a GPU requirement for this implementation.
- Precomputed replay supports stable offline playback after dependencies, web assets, and replay are prepared.
- Network access is still needed for initial data/dependency acquisition and sharing; “offline” describes prepared replay operation.
- The current replay asset inspected is about 15.5 MB; raw source data are not necessary just to serve that asset.
- No measured training-time SLA, latency percentile, deployment cost, nationwide operational scale result, or runtime hardware benchmark is supplied here. Do not invent one.
- Implementing new data adapters does not demonstrate statistical transfer to a different forecast model. NCUM/NEPS needs historical issue-time inputs, matching verification, retraining/recalibration, and independent testing.

## 11. Repository map and commands

Paths are relative to the repository root. The latest inspected checkout places the agent contract in `docs/AGENTS.md`; older logs still mention root `AGENTS.md`.

```text
synoptiq/
├── README.md                         Human entry point
├── DATA_MANIFEST.csv                 Observed source provenance
├── Makefile / pyproject.toml         Commands and Python package
├── requirements.lock / environment.yml
├── config/                          Split, label, region, explanation policies
├── src/bust/
│   ├── data/                        Acquisition, decoding, alignment, labels
│   ├── features/                    Forecast features and analog retrieval
│   ├── model/                       Baseline, training, calibration, evaluation
│   └── api/                         Replay export, schema, store, endpoints
├── scripts/                         Reproducible command entry points
├── tests/                           Contract, leakage, data and model tests
├── web/                             Vite/Leaflet dashboard source and local assets
├── data/
│   ├── fixtures/                    Committed integration fixture
│   └── raw/, interim/, processed/   Local, Git-ignored data
├── artifacts/model/, metrics/, replay/
│                                    Local, Git-ignored generated evidence
├── docs/                            Plans, decisions, audit, results, run log,
│                                    agent contract and this handoff
├── assets/screenshots/              Small reviewed screen captures
├── submission/                      Submission-facing material/link metadata
├── slides/                          Slide assets
└── demo/                            Demo material; raw videos are ignored
```

Generated artifacts are not included simply by cloning GitHub. Empty tracked folders are places for deliverables, not evidence that final PPT/video files exist.

Setup from a clone:

```sh
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
make web
make smoke
```

The conda-forge environment is an alternative for GRIB dependency difficulties. Use the repo's locked/declared dependencies; do not rebuild the project in a different framework merely for the presentation.

To serve an already supplied real replay asset from the repository root:

```sh
source .venv/bin/activate
unset SYNOPTIQ_DEMO_MODE
REPLAY_ASSET_PATH=artifacts/replay/reduced_c00_replay.json API_PORT=8001 make api
```

Open `http://127.0.0.1:8001/`. The port number itself does not determine whether the server is real or fixture. Check `/health` for `data_mode=historical_replay` and confirm the expected three dates and model identity.

Default `make api` without a real replay path serves the checked-in fixture. **`make demo` explicitly enables the illustrative fixture store**; it is not the command for recording real model results.

| Command | Purpose / caution |
| --- | --- |
| `make pilot`, `make dataset` | Inventory and dataset workflow; not needed to read this briefing |
| `make train` | Baseline entry point; currently passes `--replace` |
| `make candidate` | Reduced c00 training; default overwrite protection |
| `make evaluate-candidate` | Frozen candidate evaluation; do not rerun/retune for prettier results |
| `make replay` | Regenerates replay and passes `--replace`; not a serving command |
| `make web` | Build local frontend |
| `make smoke` | Default fixture smoke unless real environment supplied |
| `make replay-smoke` | Check the real replay asset |
| `make test`, `make lint` | Tests and source lint |

## 12. API and schema contract

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Check served data mode |
| `GET /v1/replay?init=2019-12-31&lead=6` | Region map as GeoJSON FeatureCollection |
| `GET /v1/region/R28N-094E?init=2019-12-31&lead=6` | Probability, forecast/verification, reasons, analogs, provenance |
| `GET /v1/evaluation` | Saved held-out evaluation |
| `/docs` | Interactive OpenAPI documentation |

Unsupported dates return 404 with available initialization dates. Lead numbers are constrained to 1–10. Day 10 returns an unavailable record, not a fabricated zero risk.

Shared row names:

```text
init_utc, lead_day, valid_start_utc, valid_end_utc, region_id, season,
lead_bucket, f_control_mm, o_imd_mm, coverage_fraction, error_mm,
threshold_mm, bust, source_key, grib_steps, imd_year, window_quality
```

The completed dataset also carries `split`. API map contracts preserve `data_mode`, `model`, `truth_source`, UTC bounds, threshold, window quality, provenance, `p_bust`, `tier`, `no_data_reason`, and `region_id`. The region endpoint uses `forecast_mm` and `observed_mm` for its displayed amounts.

## 13. Verified demo case: R28N-094E

**Initialization:** 2019-12-31 00:00 UTC. **Region:** R28N-094E. Use the featured-case control or select the cell manually. The date is one of the exported first/middle/last available test dates; the featured region/lead is a walkthrough illustration, not a preregistered representative event or proof of general performance.

The replay dates are **2018-01-01, 2019-01-01, 2019-12-31**. The export has 3,360 region/lead records. The underlying dataset spans all 3,652 initializations; the browser does not expose every one.

### Read these numbers exactly, with sensible display rounding

| Value | Day 1 | Day 5 | Day 6 |
| --- | ---: | ---: | ---: |
| Bust probability | 1.53918% → **1.54%** | 28.82659% → **28.83%** | 65.43746% → **65.44%** |
| Control forecast rainfall | 0.02344 mm | 13.03219 mm | **20.16000 mm** |
| IMD observed rainfall | 0 mm | 12.27437 mm | **5.07229 mm** |
| Absolute error, calculated from stored F/O | 0.02344 mm | 0.75781 mm | **15.08771 mm** |
| Threshold | 10 mm | 10 mm | **10 mm** |
| Outcome under strict label policy | No bust | No bust | **Bust** |

Day 6 verifies **2020-01-05 03:00 UTC to 2020-01-06 03:00 UTC**. Coverage is `0.984375`, or **98.4375%**. The 2020 observation is correct for a forecast initialized in 2019 and does not change its test partition.

Observed provenance for this case:

```text
source_key:
GEFSv12/reforecast/2019/2019123100/c00/Days:1-10/apcp_sfc_2019123100_c00.grib2

Day-6 accumulation arithmetic:
(120-126)-(120-123)+(126-132)+(132-138)+(138-144)+(144-147)
```

The first difference isolates +123 to +126 hours; the remaining intervals complete the exact +123 to +147 hour window.

**Narration:** “For this region, the estimated bust probability rises from 1.54% on Day 1 to 65.44% on Day 6. The Day 6 control forecast was 20.16 mm; the subsequent IMD value was 5.07 mm. Their 15.09 mm difference exceeds this row's frozen 10 mm threshold.”

Do not claim a displaced storm, a cyclone, a flood, a monsoon depression, a 300-km rain shift, or nearly double observed intensity. None of those follows from this regional case; here the forecast overpredicts rainfall.

### Day-6 score contributions

| Feature | Saved underlying-model score contribution |
| --- | ---: |
| Control rainfall | +4.2087 |
| Region | −0.3067 |
| Season | +1.0251 |
| Lead day | +0.1425 |
| Lead bucket | +0.0000 at displayed precision |

These are not calibrated probability points. “Forecast rainfall makes the largest positive contribution to the model score in this case” is supported; a physical-cause claim is not.

### Day-6 earlier analog cases

| Earlier initialization | Lead | Forecast mm | Absolute error mm | Bust |
| --- | ---: | ---: | ---: | --- |
| 2015-04-14 | 4 | 20.15328 | 9.62031 | No |
| 2012-04-11 | 5 | 20.18563 | 7.94757 | No |
| 2010-05-22 | 5 | 20.12625 | 17.55087 | Yes |
| 2013-05-18 | 5 | 20.20141 | 9.99181 | No |
| 2012-05-11 | 6 | 20.11375 | 8.40764 | No |

Exactly **one of these five Day-6 analogs** busted. Do not substitute the Day-5 analog count or say “three of five.” Five analog examples are not a calibration sample and need not match the classifier's 65.44% probability.

## 14. Every product surface to cover or capture

This inventory comes from the current source. Rehearse the live UI before recording, because labels/layout can change with later polish.

| Surface | What to show | What it establishes |
| --- | --- | --- |
| Operational Scope modal | Prototype boundary and acknowledgement | Historical GEFS replay and intended user context |
| Header/status chips | Issue context, model/scope status, replay identity | Current data mode and scope |
| Issue initialization selector | Three available dates; choose 2019-12-31 | Frozen replay selection |
| 10-Year Corpus Info modal | 2010–15 / 2016–17 / 2018–19 | Data split; three replay dates are not the training corpus |
| Day selector | Days 1, 5, 6, then briefly 10 | Lead-specific probabilities and explicit unavailable state |
| Featured Held-Out Case button | R28N-094E, Day 6 | A reproducible recording starting point |
| Bust Risk map + legend/counts | Selected cell and risk tier | Review prioritization; counts depend on date/lead |
| Forecast Rain layer | Control rainfall with its own legend | Rainfall amount is a different quantity from bust probability |
| 2° Land Grid layer | Supported/peripheral cells | Coverage gate and spatial resolution |
| Selected-region inspector | ID, probability with decimals, threshold, valid window, coverage | Row-specific interpretation |
| WHY FLAGGED? summary | Selected case summary and prominent evidence | Quick reading, not causal diagnosis |
| Lead trajectory | Supplied probability per lead | Real API values, no client interpolation |
| Forecast/observation amounts | Day-6 F, O, threshold | Post-hoc verification; not observed model input |
| Diagnostic Evidence | Active contributions and direction | Underlying saved-model attribution |
| Comparable Earlier Cases | Dates and actual error/bust fields | Earlier-only analog context |
| Illustrative atmospheric cards | Badge and example values visible together | Future UI design only |
| Model Feature Architecture / Roadmap modal | Active vs deferred capabilities | Separates reduced candidate from full design |
| Contract & Caveats / provenance | Source key, GRIB steps, UTC interval | Traceability |
| Trust / Reliability Diagram modal | Brier values, curve, sample counts, calibration scope | Aggregate evaluation and its limitations |
| Spread-only unavailable notice | Missing perturbed-member comparison | An explicitly uncompleted baseline |
| Live-mode status/scope dialog | Inactive/current research status | No operational live feed |
| API Specs `/docs` | Execute replay/region request | Integration contract |
| Footer | Scope sentence | Correct interpretation of the demo |

Flow/glow can be shown briefly as visual treatment, without a scientific claim. Cover secondary screens using short B-roll or the recording appendix; do not race through every modal at the expense of the main case and results.

## 15. Suggested three-minute narration and shot order

This is a draft grounded in the checked artifacts. Match screen values again immediately before recording. Do not conceal the historical-replay identity or illustrative labels.

**0:00–0:20 — Opening and scope**

Screen: Scope modal, then dashboard.

“Which rainfall forecasts deserve a closer look? Synoptiq estimates the risk of a large regional forecast error using information available when the forecast was issued. Our prototype replays NOAA GEFSv12 forecasts against IMD rainfall and gives reviewers a probability, supporting evidence, and a verification trail.”

**0:20–0:40 — Date, horizon, map**

Screen: 2019-12-31; corpus split briefly; Day selector and map.

“The research corpus spans 2010 to 2019. This interface replays three selected test dates. We score exact Days 1 to 9; Day 10 remains unavailable because its final three-hour amount cannot be established. Gray regions do not meet our observation-coverage rule.”

**0:40–1:15 — R28N-094E case**

Screen: Day 1, lead trajectory, Day 6, forecast and observed values; brief forecast-rain layer.

“Consider R28N-094E. Its bust probability is 1.54 percent on Day 1 and 65.44 percent on Day 6. For Day 6, GEFS forecast 20.16 millimeters. The subsequent IMD value was 5.07. That is an error of 15.09 millimeters, above the frozen 10-millimeter threshold. This is one illustration; aggregate evaluation tells us whether the method is useful more broadly.”

**1:15–1:45 — Evidence and future design**

Screen: Contributions, analogs, then one brief active/deferred overview.

“These contributions explain the fitted model's score, not a proven weather cause. Five earlier training-era forecasts provide context, with their actual errors shown afterward. Today's candidate uses control rainfall, region, season, and lead information. Ensemble spread, moisture, and circulation belong to the next model; their preview cards are illustrative.”

**1:45–2:20 — Trust panel**

Screen: Reliability modal and metrics, including the uncalibrated result.

“On 427,050 eligible held-out verifications, the calibrated candidate's Brier score is 0.03049, against 0.04359 for climatology: about a 30 percent reduction in probability error. Calibration did not improve on the uncalibrated candidate in this run, and the reliability curve still shows gaps. We report those limits alongside the result. The spread-only comparison awaits ensemble data.”

**2:20–2:45 — Provenance and API**

Screen: UTC interval/source key; `/docs` replay request with `init=2019-12-31`, `lead=6`.

“Every replay ties the score to its forecast source and exact verification window. A read-only API serves the same map, regional evidence, and evaluation. The prepared dashboard runs offline with its saved replay asset.”

**2:45–3:00 — Benefit and close**

Screen: Full map, selected region, scope footer.

“Synoptiq helps forecast reviewers decide where closer inspection is warranted. Operational transfer needs the target model's historical data and fresh validation. Synoptiq, by HackTastic 6ix: forecast reliability made inspectable.”

For an expanded recording, add the coverage layer, Day-10 empty inspector, corpus modal, and detailed analog/provenance screens as separate clips. Do not claim the three-minute edit covers every field in depth.

## 16. PPT content plan within the existing slide count

The known deck is an idea presentation. Preserve its existing pages and headings; the structure below maps to the title plus five content slides discussed with the project owner. Confirm the actual template before editing.

| Existing slide | Main message | Content priorities |
| --- | --- | --- |
| Title / team | Synoptiq — Forecast Bust Detection; SIH 26079 | Team identity and one-sentence pitch; use official PS wording only if supplied |
| Proposed Solution | A risk/evidence layer for regional forecast review | Target, output, beneficiaries, four differentiators; five-member input design clearly marked proposed |
| Technical Approach & Architecture | Train with historical verification, score from issue-time inputs | Pipeline; five active c00 features versus proposed atmospheric/ensemble inputs; no observation leakage arrows |
| Feasibility & Viability | Real data and local execution support the prototype | Completed corpus, disk-bounded processing, CPU model, time-window/coverage risks and mitigations; compact reduced-candidate result |
| Impacts & Benefits | More targeted review and informed scenario planning | Direct forecast-review benefit; downstream potential; one concise operational boundary |
| Research / References | Sources supporting data, verification, and methods | Primary dataset sources, forecast-bust prior art, method attribution; do not use citations to imply measured Synoptiq results |

If the supplied deck uses a different arrangement, adapt within its existing count. Do not silently add a results or appendix slide; place a compact result on an existing appropriate slide and use speaker notes.

Suggested idea headline: **“Flag the forecast that deserves a second look.”**

Suggested architecture caption: **“Issue-time forecast signals → bust probability → evidence-led human review.”**

Suggested success criterion: **“Evaluate on held-out years against climatology, and against spread-only predictions when ensemble data are available; report reliability and probability error.”** This is an evaluation objective, not a guarantee that every future model improves every metric.

Presentation treatment: one argument per slide, short labels, readable numbers, a simple pipeline, and a large authentic dashboard screenshot. Move equations, file paths, model hashes, and long caveats into notes. Keep one clear scope line and concise illustrative labels rather than overwhelming the pitch with repetitive warnings.

## 17. Ticket progress and what remains

This table reflects the current roadmap and dated evidence, not a new sign-off by this document.

| Ticket | Status | Meaning / remaining work |
| --- | --- | --- |
| D1-01 | Complete in tracker | Repository, roster, schema and change-control setup |
| D1-02 | Complete in tracker | Real GEFS pilot decoded with provenance |
| D1-03 | Complete in tracker | Real IMD pilot files decoded |
| D1-04 | Complete in tracker | Audited daily convention and explicit Day-10 verdict |
| D1-05 | Complete in tracker | Fixed grid, coverage and label/alignment tests |
| D1-06 | Complete in tracker | Offline fixture integration |
| D1-07 | Complete in tracker | Full c00 aligned dataset and threshold summary |
| D2-01 | Complete under explicit-status acceptance | Climatology evaluated; spread-only explicitly unavailable |
| D2-02 | Complete in tracker | Real drill-down and lead data wired |
| D2-03 | Complete for D-008 reduced candidate | c00 model and earlier analogs; original full physical model deferred |
| D2-04 | Complete in tracker | Frozen candidate and validation-only calibration/test artifacts |
| D2-05 | Complete in tracker | Real vertical slice; owner confirmed offline recording; `e2e-v1` sign-off recorded |
| D3-01 | Open | UI/trust/API exist; finish five-explanation audit and full acceptance reconciliation |
| D3-02 | Open | Final three-minute cut and result-caption audit |
| D3-03 | Open | Licensing/provenance package and fresh-clone/second-machine acceptance |
| D3-04 | Open | Final release commit/assets and `submission-freeze` process |
| D3-05 | Open | Rehearsal, exported deck/video links, second-device check and submission receipt |

Phases 1–3 are checked in the current tracker; Phase 4 remains open. The original plan's dates/cutoff were planning assumptions, not verified official submission deadlines.

### Immediate submission work

1. Reconcile captions, tier policy, current feature scope, and saved metrics.
2. Finish the explanation audit, actual demo recording, and slide/script consistency check.
3. Prepare permitted derived release assets and test the real replay on another machine.
4. Review provider/asset attribution, freeze the submission version, verify links, and save the receipt.

### Next scientific/product iteration

1. Acquire real full-date p01–p04 rainfall and the named atmospheric fields using the bounded pipeline.
2. Build/audit physical and spread features; implement spread-only comparison and richer analog patterns/error features.
3. Perform appropriate model/feature comparisons, reliability analysis, lead/season slices, uncertainty estimates, and alert-budget evaluation.
4. Investigate the current calibration gap using permitted development data. The existing 2018–2019 test has now been inspected: do not repeatedly tune against it and still describe it as a fresh untouched test. New iteration claims need an explicit evaluation protocol and suitable independent assessment.
5. Reopen Day 10 only with new exact evidence or an explicitly approved, separately evaluated approximation. Review low-coverage treatment only through a documented new policy/reference study.
6. Consider NCUM/NEPS transfer only after access, model-specific alignment/training/calibration, and new validation.
7. Treat heat-wave, cyclone-track/intensity, ocean-reference, and live-operation work as separately validated extensions.

The frontend sometimes calls deferred atmospheric work “Phase 4 multi-level ingestion.” The formal Phase 4 in `docs/AGENTS.md` is **trust, demo production, and submission freeze**. Avoid conflating those labels in the deck; say “next feature expansion.” No completion date or new owner is promised here.

## 18. Risks, mitigations, and judge answers

| Question or risk | Concise answer |
| --- | --- |
| Why GEFS rather than NCUM? | GEFSv12 provides the selected historical source used for this prototype. NCUM/NEPS validation requires its own historical issue-time corpus and fresh evaluation. |
| What counts as a bust? | Absolute regional daily error above a train-only region/season/lead q90 threshold, floored at 10 mm. |
| Is high risk the same as heavy rain? | No. It estimates a large forecast error, which can be an overforecast or underforecast. |
| Why not use ensemble spread alone? | That is an intended baseline. The current full-date corpus is c00-only, so no superiority to spread-only is claimed. |
| Is the model calibrated? | A validation-only sigmoid calibrator is applied; held-out reliability remains imperfect and calibrated Brier is worse than the uncalibrated candidate here. |
| Why is Day 10 gray? | The exact +240–+243h final component of its daily window is not evidenced. |
| Why are 47 regions blank? | They do not meet the current IMD coverage rule. The product exposes missing support rather than treating it as zero risk. |
| Are explanations meteorological causes? | No. They are saved model-score contributions and earlier examples. |
| Can a friend run the real demo from GitHub alone? | The clone provides code and a fixture; real replay requires separately shared permitted generated assets. |
| Does the system have to store 98 GB at once? | No. The acquisition pipeline validates shards before deleting raw GEFS files and uses a configured 8 GiB working budget. |
| Is it live? | The current product is historical replay. Live operation requires a matched data/model pipeline and independent operational validation. |
| Is IMD perfect truth? | It is the chosen gauge-based gridded verification reference and has coverage/measurement/interpolation limitations. |
| Is this innovation a new ML algorithm? | No such claim is made. The contribution is the integrated, traceable forecast-review workflow and its evaluated reduced prototype. |
| Does 65.44% mean this forecast must fail? | No. It is a probability estimate for a defined error event; single cases do not validate calibration. |
| Can you guarantee selection or lives saved? | No. Neither selection nor operational benefits have been established by these model metrics. |

## 19. Team and handoff responsibilities

| Plan label | Member | GitHub |
| --- | --- | --- |
| A | Kanishka Pandey | https://github.com/kan9667 |
| B | Aanya Varshney | https://github.com/aanyavarshneyav |
| C | Rudraksh Saini | https://github.com/Rudrakssh |
| D | Dhruv Makkar | https://github.com/dhruvsded1 |
| E | Aadi Jain | https://github.com/DeltaData0 |
| F | Triman Singh Chadha | https://github.com/Triman01 |

The roster is for team identification and plan accountability. The project owner clarified that Kanishka is doing the implementation/orchestration work. Do not invent completed contributions for the other members or copy their old project's Flutter, artisan, pricing, speech, or image-pipeline responsibilities into this project.

A friend can use her own AI account to prepare the deck/script. She does not need the owner's Google account or ChatGPT login. Share the material/files or appropriate document access, not credentials.

## 20. What to send your friend

For PPT and script generation, send this file, the current PPT/template or accessible deck link, and the screenshots/recording clips to use. This briefing contains the main verified numbers even if her agent cannot access local generated artifacts.

Known working presentation link supplied by the owner:
https://docs.google.com/presentation/d/1Q67WpiAVBQIJFHVkx0ieGoigGOeNd8uUv9JwkkDcS9s/edit?usp=sharing

That link is a project reference; this session did not inspect its latest edits or verify the friend's access. Use the owner's latest export if sharing is restricted.

For **running the real replay only**, additionally supply the permitted `artifacts/replay/reduced_c00_replay.json` and its metadata file. Preserve checksums/provenance and remove machine-specific absolute-path metadata from a shareable copy where appropriate. The dashboard service reads the replay JSON; it does not need to train or download the raw corpus to show it.

For **independent model/result verification**, supply the relevant model, calibrator, frozen-run, evaluation and dataset-summary artifacts; the aligned dataset is needed for full recomputation. This is a different, larger handoff. A copied briefing alone cannot substitute for independent numerical verification.

Do not put raw datasets, secrets, virtual environments, `node_modules`, or large recording files in Git to make sharing easier. Keep source attribution and check redistribution terms for any real derived asset package. No new license permission is inferred here.

## 21. Instructions to paste into her AI agent

> Use this document as the Synoptiq project briefing. Create polished content for the existing idea PPT and a demo script centered on R28N-094E, initialization 2019-12-31. Preserve the supplied deck's slide count and existing template; do not add slides. Present the full architecture as intended design, and label all measured results as those of the reduced c00-only candidate. Use only the numerical results in this briefing or newer verified artifacts. Keep the main story focused on forecast-review value, with readable visuals and concise scope labels. Put detail in speaker notes. For the recording, describe only current screens and real fields; keep illustrative labels visible and distinguish them from real evidence. Explain the calibrated-versus-uncalibrated result honestly. Do not claim live NCUM/NEPS operation, complete ensemble/atmospheric features, a new foundational ML algorithm, or measured social/economic benefits. Keep technical terminology precise and avoid unsupported buzzwords. Deliver slide-by-slide copy, speaker notes, a timed script, a screen-action list, and a list of any unresolved factual questions. Do not edit the repository, train models, change thresholds, or push code as part of this presentation task.

## 22. Final authoring checklist and claims to avoid

- Distinguish **forecast-error probability** from probability of rain, flood, or a forecast being completely correct.
- Distinguish **five input features** from **five ensemble members**.
- Say **ten years of initialization dates**, **six years of training**, and **two held-out test years**; never “trained on fifteen years.”
- Say **4.09 million total schema rows**, not 4.09 million eligible training examples.
- Say **30.1% relative Brier reduction versus climatology**, not “30% more accurate.”
- Say **historical issue-time replay**, not a live warning or an actual forecast issued by this system in 2019. Reforecasts are retrospective model runs; replay tests the issue-time information boundary.
- Show Day 10 and low-coverage cells as unavailable, not 0% risk.
- Do not describe the reliability curve as perfect or calibration as an improvement in this run.
- Do not imply the original atmospheric architecture is the source of current reduced-candidate skill.
- Do not imply a 2° region is district-level or that a decorative outline is an official national boundary.
- Do not identify rainfall legend categories as official warning classifications.
- Do not use unsupported phrases such as “revolutionary,” “world-first,” “zero-error,” “guaranteed trust,” “autonomous meteorologist,” or “real-time nationwide early warning.”
- Keep benefits strong and concrete: review prioritization, traceability, reproducibility, and clearer evidence.

## 23. Sources and evidence pointers

### Project source of truth

- [Canonical Reference](SIH-26079-Forecast-Bust-Detection-Canonical-Reference.md): original dataset, architecture, impact, prior-art and risk rationale; especially §§1, 3–7 and bibliography §9.
- [72-Hour Implementation Plan](SIH-26079-72-Hour-Implementation-Plan.md): repository, schema, gates and D1/D2/D3 tickets; original schedule assumptions are not official deadlines.
- [Decisions](DECISIONS.md): approved alignment, grid, 2020 observation boundary, and reduced-candidate exceptions.
- [Data audit](data_audit.md): signed interval evidence and later completed-corpus sign-off.
- [Run log](RUN_LOG.md): chronological execution and acceptance history.
- [Results](results.md): recorded model/evaluation summary.
- [Agent contract and roadmap](AGENTS.md): current scope and checkbox status.
- [Release checklist](release_checklist.md): remaining second-machine and submission checks.
- `artifacts/metrics/dataset_summary.json`, `artifacts/metrics/reduced_c00_evaluation.json`, `artifacts/model/reduced_c00_candidate.json`, and `artifacts/replay/reduced_c00_replay.json`: local artifacts inspected for this handoff.

### Primary references carried forward from the canonical bibliography

These citations support data/method background; they do not establish Synoptiq's measured performance. Provider pages were not freshly re-audited for licensing or current product updates during this writing session.

- NOAA/AWS [GEFSv12 reforecast archive](https://registry.opendata.aws/noaa-gefs-reforecast/).
- NOAA [reforecast data description](https://noaa-gefs-retrospective.s3.amazonaws.com/Description_of_reforecast_data.pdf).
- Guan et al. (2022), [GEFSv12 reforecast dataset paper](https://repository.library.noaa.gov/view/noaa/53301).
- IMD Pune [0.25° rainfall NetCDF catalogue](https://imdpune.gov.in/cmpg/Griddata/Rainfall_25_NetCDF.html).
- Pai et al. (2014), [IMD gridded rainfall method](https://mausamjournal.imd.gov.in/index.php/MAUSAM/article/view/851?articlesBySameAuthorPage=2).
- Rodwell et al. (2013), [Characteristics of Occasional Poor Medium-Range Weather Forecasts for Europe](https://journals.ametsoc.org/view/journals/bams/94/9/bams-d-12-00099.1.xml).
- SHAP [TreeExplainer documentation](https://shap.readthedocs.io/en/latest/generated/shap.TreeExplainer.html).

### Known documentation inconsistencies to resolve before final release

The inspected `README.md` still has older blocked/progress wording; `docs/results.md` still mentions the recording as pending, while the later run-log entry and roadmap record owner confirmation and D2-05 completion. D-002 retains an old pending status, whereas later artifacts apply the frozen split. D-010 and some checklist paths mention root `AGENTS.md`, but the current checkout moved it into `docs/`. The former `judge_qa.md` and `storyboard.md` were removed in the inspected latest commit; this document supplies new handoff guidance rather than pretending those files still exist.

Treat these as documentation cleanup items, alongside the risk-tier and “Phase 4” wording discrepancies described above. They do not authorize changing scientific policy or silently overwriting historical records. This handoff leaves existing files and acceptance checkboxes unchanged apart from adding its own preparation entry to the run log.
