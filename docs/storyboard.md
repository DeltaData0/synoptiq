# Storyboard decision record

No recording may call the fixture replay a held-out prediction. Before recording
an empirical replay, record its preregistered selection criterion, issue date,
manifest ID, run ID, artifact hash, and reviewer here.

## Recording gate

- A fixture-only recording may demonstrate navigation, API contracts, explicit
  fixture labeling, provenance fields, no-data behavior, and the gray Day-10
  state. It must not claim a historical probability, forecast error, analog,
  SHAP explanation, calibration, or performance metric.
- A real replay recording requires the D2-05 evidence gate: an auditable
  `(init, region, lead)` trace from GRIB intervals through the IMD window,
  threshold, probability, explanation, API, and map; valid held-out artifacts;
  and an offline-refresh capture.
- Record the final three-minute cut only after every displayed number and
  caption is checked against the run log and frozen artifact. (Plan §§6, 9;
  `AGENTS.md`)
