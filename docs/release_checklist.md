# Release and second-machine checklist

This is a preparation checklist for D3-03 through D3-05. It does not certify a
release by itself. Check an item only against the final release candidate and
record the command output, commit, manifest ID, split, seed, and artifact path
in `RUN_LOG.md`. (Plan §§6, 9; `AGENTS.md`)

## Evidence and claims

- [ ] The release candidate identifies its commit, input manifest fingerprint,
  frozen split, seed, and every generated artifact.
- [ ] `DATA_MANIFEST.csv` contains observed source keys/URLs, checksums/sizes,
  retrieval metadata, and decoded fields for all data used by the release.
- [ ] `docs/data_audit.md` records the applicable signed interval and coverage
  evidence; Day 10 remains `unavailable` unless a new audited decision exists.
- [ ] `docs/results.md`, slides, dashboard copy, and video captions use only
  values from the final frozen artifacts and run log. Fixture/pilot output is
  visibly labeled and never called held-out validation.
- [ ] Any source, split, threshold, time-window, grid, or feature-policy
  change has a dated approval in `DECISIONS.md`.

## Provenance and licensing

- [ ] Release notes acknowledge the NOAA GEFSv12 reforecast archive and the
  official IMD 0.25° daily rainfall catalogue, using the source URLs in
  `README.md` and `docs/data_audit.md`.
- [ ] Before public release, record the then-current data-use/attribution terms
  from the official NOAA and IMD source pages. Do not infer or claim a data
  license that has not been checked.
- [ ] List all bundled non-project assets and their source/license. Remove or
  replace any asset lacking a permitted license or documented provenance.
- [ ] Confirm the visual India outline is described only as an orientation
  outline derived from the audited IMD grid mask, not an official or political
  boundary.
- [ ] Confirm `LICENSE` applies to Synoptiq source code only; it does not grant
  rights to external datasets or dependencies.

## Fresh-clone offline demonstration

- [ ] On a second machine, clone the intended commit without copying raw data,
  credentials, local absolute paths, or untracked artifacts.
- [ ] Create the documented Python 3.11 environment and install the locked
  dependencies. Use the documented conda-forge fallback if GRIB bindings fail.
- [ ] Build the local dashboard with `make web`; verify it has no required
  remote tiles or CDN assets.
- [ ] Run `make smoke` and the full test suite. Record actual output and any
  warnings in `RUN_LOG.md`.
- [ ] Start `make api`, open `/`, `/docs`, `/health`, `/v1/replay`,
  `/v1/region/{region_id}`, and `/v1/evaluation`; verify the response mode,
  no-data behavior, and provenance match the frozen replay artifacts.
- [ ] Record a screen capture of the offline refresh and one complete replay
  interaction. For a real release, trace one `(init, region, lead)` from GRIB
  steps to the IMD interval, threshold, probability, explanation, API, and map
  as required by D2-05.

## Submission package

- [ ] Slides, video, README, and release assets display the scope statement:
  “GEFSv12 reforecast research prototype; not NCUM/NEPS operational
  validation.”
- [ ] Every number and caption in the three-minute video matches a run-log
  entry and frozen artifact; do not record a fixture as a held-out case.
- [ ] A second team member opens the final package on a second device and
  verifies the PPT/video links before upload.
- [ ] Save the submission receipt and record it in `RUN_LOG.md`.
