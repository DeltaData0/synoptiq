# Judge Q&A

Use these answers only with the evidence that exists in the release being
demonstrated. A fixture response is an integration demonstration, not a model
result. (Plan §§5–6; `AGENTS.md`)

## Purpose and scope

**What does Synoptiq do?** Given a historical GEFS forecast available at its
00 UTC issue time, Synoptiq is designed to estimate where a fixed 2° Indian
land region's 24-hour rain forecast is unusually likely to have a large error,
then expose the interval, provenance, and score evidence behind that estimate.
It is a research replay prototype, not another rainfall-prediction model.

**Is it live?** No. Synoptiq is a historical issue-time replay prototype. It
does not issue public warnings or provide operational decisions.

**Does it validate NCUM/NEPS?** No. The selected source scope is GEFSv12
reforecasts and IMD daily gridded rainfall. NCUM/NEPS would require matched
historical fields, a separate training/calibration run, and independent
out-of-time validation.

**What is a “bust”?** It is a regional 24-hour absolute rain error `|F − O|`
that is strictly greater than the frozen train-only regional × season ×
lead-bucket 90th-percentile threshold, with a 10 mm/day floor. It is not an
IMD alert threshold and is not a claim that rain itself is extreme.

## Data integrity and leakage controls

**Why is the time window important?** An initialization date plus a lead day
is not enough to define a verification target. For Day 1–9, Synoptiq uses the
audited IMD mapping `[D−1 03:00Z, D 03:00Z)` and preserves the exact GRIB
accumulation intervals used to form its forecast total. The source-grounded
audit and a real 8.24 mm GRIB hand check are documented in
[`docs/data_audit.md`](data_audit.md).

**Why is Day 10 gray/unavailable?** The audited Day-10 observation target ends
at +243 hours, while the inspected source supplies a +240–+246-hour
accumulation. Treating that six-hour value as a 24-hour target would add three
unevidenced hours. Synoptiq therefore returns no Day-10 probability, label,
or metric unless an exact or explicitly approved approximation is evidenced.

**How do you prevent leakage?** The temporal split is frozen: 2010–2015 train,
2016–2017 validation, and 2018–2019 held-out test. Thresholds are fit on train
rows only; calibration is validation-only; test labels do not enter any fitting
decision. Analog retrieval, when available, is restricted to initializations
earlier than the query. Observations, later analysis, error, and bust labels
are never predictors.

**Why are some regions unavailable?** A 2° region must contain at least 80%
valid IMD land-grid coverage. Coastal or border cells below that threshold are
explicit `no_data`; ocean/missing values are never filled with zero rainfall.

**What happens when data is missing or corrupt?** The pipeline records a real
failure and leaves the item incomplete. It does not substitute another forecast
source, fabricate a row, or silently convert missing data to “no bust.” A final
empirical dataset is published only after corpus-completeness checks pass.

## Model and explanations

**Is this an AI weather forecaster?** No. The candidate model is a
probability-of-forecast-error model. GEFS remains the rainfall forecast;
Synoptiq assesses the reliability risk of that issued forecast.

**What does a probability mean?** Only after the real held-out evaluation is
produced, a probability means the model's estimated chance that the frozen bust
definition is met for that region, issue time, and lead. It must be shown with
its held-out reliability and baseline comparison. Until then, fixture values
are illustrative API/UI values only.

**How will you know whether it helps?** The candidate must be compared on the
untouched 2018–2019 test period with a train-only climatology baseline and, if
measured member-spread data is acquired, a spread-only baseline. The release
must report Brier score, calibration/reliability, sample counts, and an
explicit insufficient-data status where applicable—not selectively chosen
successes.

**Can you explain a flagged region?** A final model may show grouped SHAP score
evidence and up to five earlier analogous forecasts with observed errors. SHAP
identifies score-driving features, not proven meteorological causes; analogs
must predate the query initialization. If those artifacts do not exist, the
dashboard must say so rather than invent explanations.

## Evidence, innovation, and deployment

**What is innovative here?** The design combines a forecast-*reliability*
question with issue-time replay, auditable forecast/observation time-window
matching, region-level coverage/no-data rules, train-only thresholds, and
inspectable provenance. It deliberately refuses a visually convenient but
unsupported Day-10 result. The value is transparent evidence for where a
forecast merits closer review, not a replacement weather forecast.

**Where do the sources come from?** Forecasts are NOAA GEFSv12 reforecasts;
verification is the selected IMD 0.25° daily rainfall product. Every accepted
source object is recorded in `DATA_MANIFEST.csv` with observed key/URL,
retrieval metadata, and decoded details. The source pilots and daily-window
audit are in [`docs/data_audit.md`](data_audit.md).

**Can disaster-management or agricultural teams use this today?** They can
inspect the research replay and its evidence. Operational use requires a
separate deployment validation, operational data feeds, governance, and
monitoring. Synoptiq does not replace an agency forecast or warning workflow.

**What is complete at this checkpoint?** The repository has the audited Day
1–9 label policy, region/coverage contract, fixture API/dashboard integration,
safe streaming acquisition, and baseline/evaluation scaffolding. The real
2010–2019 GEFS corpus, trained candidate, and empirical metrics must be
described only after their respective evidence gates pass.
