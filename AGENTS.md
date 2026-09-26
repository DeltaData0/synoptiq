# Synoptiq agent contract

## Project identity

Synoptiq is a CPU-first, local research prototype that replays historical GEFSv12 issue-time forecasts against IMD daily gridded rainfall to estimate the probability that a fixed Indian 2° land region's Day 1–10, 24-hour rainfall forecast will have an unusually large error. It is **not** a live public-warning service and is **not** NCUM/NEPS operational validation; every empirical demo must visibly state “GEFSv12 reforecast research prototype; not NCUM/NEPS operational validation.” (Reference §1; Plan §5). **Pitch:** “Given a GEFS forecast that was available at issue time, we estimate where its Day 1–10 rain forecast is unusually likely to fail, explain which measurable signals drove that estimate, and show whether those probabilities matched subsequent observations.” (Reference §1)

## Non-negotiable rules

- **Never invent evidence.** Do not invent metadata, GRIB step values, decoded output, object keys, URLs, checksums, file contents, or command output that a real tool call in the current session did not produce. Record only observed GEFS archive keys and IMD selector URLs; never guess key templates. (Plan §2, acquisition gates)
- **Never fabricate coverage or performance.** Do not fill missing dates with invented forecasts, use a rolling recent feed as historical reforecast data, or present fixture/pilot output as validated-model output. If the corpus or audit is incomplete, label the result `fixture`, `pilot_only`, `insufficient_test_data`, or blocked as applicable. (Plan introduction, §§2–3, §6; Reference §§3–4)
- **Preserve frozen decisions.** A dataset/source swap, threshold change, split change, time-window change, region-grid change, or feature-policy change requires a dated entry in `DECISIONS.md`; never make a silent edit. (Plan §§1–3, §10; Reference §3)
- **Keep restricted material out of Git.** Never commit raw data, credentials, local absolute paths, or large binaries. Check `.gitignore` before staging; stop and call out a potential violation. Commit only fixtures and small, permitted release artifacts with provenance. (Plan §1, §10)
- **Protect M0 invariants.** Once M0 is signed off, do not silently modify the 2010–15 train / 2016–17 validation / 2018–19 test split or `config/label_policy.yaml`. Flag the conflict and update `DECISIONS.md` before any approved change. Thresholds are train-only regional × season × lead-bucket q90 with a 10 mm/day floor; no random row split. (Plan §3 M0; Reference §3)
- **Treat verification time as first-class data.** `init_utc + lead_day` is not a verification interval. Preserve exact UTC start/end, GRIB accumulation intervals, and `window_quality`; never silently compare 00–00 forecast totals with an unaudited IMD daily window. Day 10 remains gray/unavailable unless the +240/+246-hour gate passes or an explicitly documented approximation is approved. (Plan §§1–2, §5; Reference §3)
- **Do not overstate explanations.** SHAP is model-score evidence, not a proven meteorological cause. Explanations must name the feature, direction, and evidence layer; analogs must be earlier than the query initialization. (Plan §4; Reference §5)

## Repo map and ownership

The paths below are the project layout frozen in Plan §1. “Owner” uses the accountable roles and tracker tickets in Plan §§8–9.

| Path | Contents / contract | Owner / ticket |
| --- | --- | --- |
| `README.md`, `DECISIONS.md`, `RUN_LOG.md`, `DATA_MANIFEST.csv`, `.env.example` | Scope, decision log, reproducibility log, source manifest, and local configuration contract. | A + F / D1-01 |
| `pyproject.toml`, `requirements.lock`, `Makefile`, `.gitignore` | Python environment, resolved lock, named run targets, and Git safety boundary. | A + E / D1-01 |
| `config/regions_2deg.geojson` | Fixed 2° India-land region definition; freeze IDs before training. | B / D1-05 |
| `config/label_policy.yaml`, `config/splits.yaml` | Frozen label policy and chronological split policy. | B + C / D1-05, D1-07, M0 |
| `config/reason_groups.yaml` | Grouped explanation policy: moisture, circulation, ensemble disagreement, analog-error memory, lead/season. | D + C / Plan §4 |
| `data/raw/`, `data/interim/`, `data/processed/` | Local raw, intermediate, and processed data; Git-ignored. `rows.parquet` belongs in processed only after the audit gate. | A + B / D1-02–D1-07 |
| `data/fixtures/` | Versioned API fixtures only; they must visibly remain fixtures and make no model claim. | E + F / D1-06 |
| `artifacts/model/`, `artifacts/metrics/`, `artifacts/replay/` | Generated model, metric, and frozen replay assets; only small permitted release files may be committed. | C / M3; D + E / M4 |
| `src/bust/data/{inventory,fetch_gefs,fetch_imd,decode_grib,align,regions,labels}.py` | Provenance inventory, real source retrieval/decoding, interval alignment, fixed regions, and leakage-safe labels. | A + B / D1-02–D1-05 |
| `src/bust/features/{forecast,analogs}.py` | Issue-time physical/spread features and strictly earlier analog retrieval. | D + C / D2-03 |
| `src/bust/model/{baseline,train,calibrate,evaluate,explain}.py` | Baselines, model fitting, validation-only calibration, held-out evaluation, and grouped score evidence. | C + D / D2-01, D2-03, D2-04 |
| `src/bust/api/{main,schemas,store}.py` | Read-only FastAPI replay, region, evaluation, schema, and artifact store. | E / D1-06, D2-02, D3-01 |
| `scripts/{pilot,build_dataset,train_all,export_replay,smoke}.py` | Named, reproducible pipeline entry points; every run prints manifest ID, commit, split, seed, and output path. | A–F / Plan §1, D1-06, D2-05 |
| `web/{package.json,index.html,src/{main,api,map,region,trust,styles}.js}` | Vite + local Leaflet + plain JS/CSS dashboard; it must work offline without map tiles/CDN. | E + F / D1-06, D2-02, D3-01 |
| `tests/{test_time_windows,test_accumulation,test_labels,test_leakage,test_api}.py` | Tests for high-risk joins and response contracts, not duplicate implementation tests. | F with A–E review / Plan §6 |
| `docs/{data_audit,method,results,storyboard,judge_qa}.md` | Data-audit sign-off, method, honest results, recording criterion, and judge answers. | A/B/F / D1-04, D3-02–D3-03 |
| `slides/`, `demo/` | Submission presentation and recorded-demo assets; all values must match frozen artifacts. | F / D3-02–D3-05 |

## Row and API contracts

### Shared row schema

Use these field names exactly in aligned rows and downstream code:

```text
init_utc, lead_day, valid_start_utc, valid_end_utc, region_id, season,
lead_bucket, f_control_mm, o_imd_mm, coverage_fraction, error_mm,
threshold_mm, bust, source_key, grib_steps, imd_year, window_quality
```

`window_quality` is exactly `exact`, `approximate`, or `unavailable`. All timestamps are UTC. Include a named feature-column set separately; do not use observations, later analysis, error, bust, or test-wide statistics as predictors. Missing data is not “no bust.” (Plan §§1–3; Reference §§3–4)

### `GET /v1/replay` contract

`GET /v1/replay?init=YYYY-MM-DD&lead=1…10` returns a GeoJSON `FeatureCollection`. Preserve these response field names exactly: `data_mode`, `model`, `truth_source`, `valid_start_utc`, `valid_end_utc`, `threshold_mm`, `window_quality`, `provenance`, `p_bust`, `tier`, and `no_data_reason`; features also identify `region_id`. `data_mode` is `historical_replay` only for a real frozen replay. Unknown dates return 404 with available dates. An unavailable Day 10 returns `null`/gray, never a zero probability. Do not change fixture keys when generated assets replace them. (Plan §5; Reference §4)

The related endpoints are fixed as `GET /health`, `GET /v1/region/{region_id}?init=...&lead=...`, and `GET /v1/evaluation`; retain Pydantic validation and `/docs`. (Plan §5)

## Ticket-state protocol

### Startup read order

Before changing code or data, read these in order:

1. `RUN_LOG.md`: identify the latest dated run, its exact command, commit, manifest/hash, split/seed, output, outcome, and remaining caveat.
2. `DATA_MANIFEST.csv`: distinguish actual inventoried/downloaded source objects from fixtures; treat an absent field or row as **not attempted**, not as evidence of failure or success.
3. `docs/data_audit.md`: this is the authoritative status for GEFS decoding, IMD decoding, the IMD-day UTC mapping, coverage, and the Day-10 verdict. A pending audit blocks empirical labels and metrics. (Plan §2; D1-04)
4. `DECISIONS.md`: check frozen choices and any approved exception before altering source, window, region, threshold, split, or model policy. (Plan §§1–4)
5. The relevant Plan §9 ticket and its dependencies: tracker status begins `Todo`; use `Blocked` with a link to the blocking audit, and update the next owner at the prescribed check-in. (Plan §9)

### Status and end-of-turn updates

Use a dated status line in the artifact you update:

- `✅ Complete — <ticket/gate>: <evidence and path>` only when the stated acceptance evidence exists.
- `⚠️ Blocked — <ticket/gate>: <specific missing evidence>; <next safe action>` when a dependency, access route, or audit is unresolved.
- `❌ Failed — <ticket/gate>: <real command/output or failing assertion>; <preserved fallback>` when a real attempt fails.

Before ending a turn, add a dated `RUN_LOG.md` row stating the exact command(s), real output/artifact path, manifest ID/hash, commit, split, seed, what was verified, what remains TODO, and each Plan §9 ID touched. Add actual source URLs/keys, retrieval time, checksum/size, run/member/variable/step/units, and notes to `DATA_MANIFEST.csv`; never add placeholders as if they were records. Update `docs/data_audit.md` with decoded-source and hand-check evidence; update `DECISIONS.md` for any approved decision change. (Plan §§1–2, §6, §9)

GPT plans/verifies; execution agents implement. A verifier may report a gate status, but no agent may turn a pending, blocked, or fixture-only gate into `✅ Complete` without the Plan-required artifact and real output.

## Environment

Use **Python 3.11**. The primary setup is:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

The Python project declares `numpy`, `pandas`, `xarray`, `cfgrib`, `eccodes`, `pyarrow`, `scipy`, `scikit-learn`, `lightgbm`, `shap`, `fastapi`, `uvicorn`, `pydantic`, `requests`, `matplotlib`, `pytest`, and `httpx`. Resolve and commit `requirements.lock` on the first working machine, then test a second laptop. For macOS GRIB friction, use the tested conda-forge/micromamba fallback with `eccodes` and `cfgrib`. No GPU is required. (Plan §1)

The frontend is **Vite + Leaflet + plain JavaScript/CSS**. Run `npm install` and `npm run dev` in `web/`; Leaflet must be bundled locally, with no CDN or required map tiles. FastAPI serves built `web/dist` and generated GeoJSON/JSON. Keep storage paths configurable with `DATA_DIR`; never commit an absolute laptop path. (Plan §1; Reference §4)

Use the named targets rather than ad-hoc pipeline entry points:

```sh
make pilot
make dataset
make train
make replay
make api
make web
make smoke
make demo
```

Each target must invoke its named script and print the input manifest ID, git commit, split, seed, and output path. (Plan §1)

## Handoff etiquette

- Work from `main` on `feat/<task-id>-<short-name>`, make a small vertical slice, and request review. Review schema, date/lead convention, provenance, and the smoke command before merge. No unreviewed dataset swap. (Plan §1)
- Leave a dated `RUN_LOG.md` note before ending every session. State exactly what ran, what the terminal/tool actually proved, which files were changed, what remains TODO/blocked, and the Plan §9 ticket(s) touched. Do not convert an assumption into a run result. (Plan §§1, 6, 9)
- Refuse to mark an acceptance gate `✅` without its evidence. For example, D1-04 requires decoded GEFS and IMD source evidence, a signed concrete `IMD day ↔ [UTC start,end)` table, inspected +240/+246 GRIB steps, and real hand-computed 24-hour totals compared with script output—not an assumed 03–03 convention. (Plan §2; D1-04)
- If data acquisition fails, retain the selected GEFSv12/IMD scope, document the failure, and continue only with visibly labeled fixture integration. Do not substitute recent GFS/ECMWF, IMERG, merged products, TIGGE, IMDAA, or NCUM data without an approved decision change and fresh validation. (Plan §§2, 10; Reference §3)
- If leakage is found, halt evaluation, rebuild permitted artifacts, rerun checks, and invalidate affected scores/screenshots. If performance is negative or the test is inadequate, report that honestly. (Plan §10; Reference §§1, 3–4)

## Testing and acceptance gates quick reference

Run `pytest` for accumulation gaps/overlaps, timezone convention, region coverage, train-only thresholds, analog chronology, immutable split, API response schema, and fixture smoke behavior. These tests protect high-risk joins. (Plan §6)

### D1-04 — blocking time-window gate

Do not build empirical labels, train, or report model skill until `docs/data_audit.md` is signed with: an actual GEFS object decoded by `cfgrib` (metadata, units, members, steps), two actual IMD annual files decoded (grid, units, time axis/date labels), a concrete IMD day-to-UTC interval mapping, hand-calculated 24-hour totals checked against code, and an explicit Day-10 `exact` / documented `approximate` / `unavailable` verdict based on +240/+246 steps. If it fails, empirical claims are blocked and Day 10 is gray. (Plan §2; D1-04; Reference §3)

### D2-05 — real-data end-to-end gate

Run `make pilot`, `make dataset`, `make train`, `make replay`, and `make smoke`. A real-data `✅` requires all of the following:

1. One `(init, region, lead)` traces from inventoried GRIB steps through the audited IMD day, frozen threshold, probability, explanation, API, and map.
2. An independent hand calculation matches `abs(F−O)` and `bust`; every region has coverage ≥0.80 or explicit no-data.
3. Tests prove no future analog and no threshold/calibrator leakage; exact and approximate windows remain distinct.
4. Replay is valid GeoJSON with `data_mode=historical_replay`; region and evaluation endpoints match the same frozen artifacts; invalid inputs and unavailable Day 10 behave correctly.
5. An offline refresh reproduces the bundled map, with a captured screen recording.

If any evidence is absent, D2-05 is only `⚠️ Blocked` or fixture integration; results and slides must say so. (Plan §6; D2-05)

## Submission Roadmap

**Non-negotiable ordering:** A real measured classifier claim requires the intended 2010–2019 issue-time and verification samples, a frozen 2018–2019 test, and metrics generated by that run. Never fill missing dates with invented forecasts or present fixture metrics as validation. If a gate fails, mark it `⚠️ Blocked — needs human` with a link to the blocking audit and use the explicit fixture/pilot fallback; do not silently skip it. (Plan introduction, §9, §10; Reference §§3–4)

Check a task's box only after producing real, verifiable output for it in this session — never check a box based on a plan description alone.

### Phase 1: Repository contract and data-feasibility gate — [ ] Phase complete

- [ ] D1-01 — Repo, roles, `DECISIONS.md`, issue board, schema contract (Owner: A+F) — done when: Six names, branch rules, sources/manifest template and issue ownership posted.
- [x] D1-02 — GEFS real-object pilot per §3 S1–S2 (Owner: A) — done when: GRIB decodes; actual key, member/step/unit/grid/bytes logged. Evidence: `docs/data_audit.md` GEFS control precipitation inspection and `DATA_MANIFEST.csv` IDs `gefs-20180801-*`.
- [x] D1-03 — IMD 2017/18 pilot per §3 S3 (Owner: B) — done when: Both annual files decode; date axis and mask logged. Evidence: `docs/data_audit.md` IMD annual-file pilot and `DATA_MANIFEST.csv` IDs `imd-2017-pilot` / `imd-2018-pilot`.
- [ ] D1-04 — 03–03/day label and +240/+246 Day-10 audit (Owner: A+B+F) — done when: Signed `data_audit.md`; exact/approximate/unavailable policy frozen. Otherwise empirical-model claim blocked.

### Phase 2: Audited labels and fixture vertical slice — [ ] Phase complete

- [ ] D1-05 — Region GeoJSON, 80% coverage, alignment/label unit tests (Owner: B) — done when: Three hand-checked rows and no-data cases pass.
- [ ] D1-06 — Fixture API/map + provenance (Owner: E+F) — done when: `make smoke` launches and renders a fixture replay offline with visible fixture ribbon. Tag `pilot-gate`.
- [ ] D1-07 — First split-aware real `rows.parquet`/threshold summary (Owner: A+B+C) — done when: Counts by year/lead/season and missingness printed; train-only threshold test passes.

### Phase 3: Model, calibration, and real-data integration gate — [ ] Phase complete

- [ ] D2-01 — Climatology and spread-only baseline (Owner: C) — done when: Reproducible predictions and eligible test metrics or explicit insufficient-data status.
- [ ] D2-02 — Drill-down wired to schema (Owner: E) — done when: Region click and lead curve show threshold, interval, data provenance.
- [ ] D2-03 — Named fields, earlier analog retrieval, LightGBM candidate (Owner: D+C) — done when: Feature leakage audit, 5 analogs or fallback, validation comparison.
- [ ] D2-04 — Sigmoid calibrator, score evidence, frozen candidate (Owner: C+D) — done when: Run log locks feature set/hyperparameters before test, metrics generated honestly.
- [ ] D2-05 — Full real-data vertical slice (Owner: A–F; F accountable) — done when: Dataset → prediction → API → map → explanation → test-panel smoke succeeds, or explicitly labeled fixture/pilot mode. Tag `e2e-v1`.

### Phase 4: Trust, demo production, and submission freeze — [ ] Phase complete

- [ ] D3-01 — Evidence layers, trust panel, API docs (Owner: D+E) — done when: Five explanations audited; test values match `evaluation.json` or pending notice.
- [ ] D3-02 — Video first cut and results slides (Owner: F+C) — done when: 3-minute cut; all numbers and captions checked against run log.
- [ ] D3-03 — Judge Q&A, licensing/provenance, offline second-machine smoke (Owner: F+A+B) — done when: Demo runs from fresh clone + generated release assets; links and caveats visible.
- [ ] D3-04 — Freeze release commit and assets (Owner: A–F; F accountable) — done when: PRs merged, tagged `submission-freeze`; no unverified new feature or metric.
- [ ] D3-05 — Buffer: render/export/rehearse, fix only blockers, upload before assumed cutoff (Owner: F; all review) — done when: PPT/video link verified, one team member opens the submission package on a second device; submission receipt saved.
