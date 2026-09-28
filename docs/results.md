# Results

## Completed baseline evidence

The train-only regional × season × lead-bucket climatology baseline was evaluated on the frozen 2018–2019 held-out split. It used 1,281,735 eligible 2010–2015 training rows across 390 groups. On 427,050 eligible exact Day 1–9 held-out rows, its Brier score was **0.043586** and bust prevalence was **0.047430**. The corresponding artifact is local and Git-ignored at `artifacts/metrics/climatology_baseline_evaluation.json`, with manifest fingerprint `manifest-fp-12803f75af61`.

## Reduced c00-only candidate: validation evidence

The approved deadline-limited **reduced c00-only candidate** used only issue-time `f_control_mm`, region, season, lead day, and lead bucket. Its feature set explicitly excludes the deferred moisture, circulation, and ensemble-disagreement groups. On 427,635 eligible 2016–2017 validation rows, it achieved a Brier score of **0.027952**, compared with **0.041111** for the train-only climatology baseline on the same current corpus. This is a validation comparison, not a replacement for held-out reporting.

The validation artifact includes one real query and five strictly earlier, forecast-similar training analogs. Their observed errors and labels are post-hoc evidence only, never model features or similarity inputs. The corresponding local, Git-ignored artifact is `artifacts/metrics/reduced_c00_validation.json` with manifest fingerprint `manifest-fp-12803f75af61`.

## Reduced c00-only candidate: held-out evaluation

The saved candidate configuration and serialized Booster were frozen before the evaluation pipeline read test rows. A Platt/sigmoid calibrator was fit only on the same 427,635 eligible validation rows, then the calibrated candidate and train-only climatology baseline were evaluated on the same 427,050 eligible exact Day 1–9 rows from the frozen 2018–2019 test split. The calibrated candidate Brier score was **0.030485**, compared with **0.043586** for climatology (candidate minus climatology: **−0.013101**; bust prevalence: **0.047430**).

Calibration was retained as the validation-only policy requires, but it did **not** improve this metric on the held-out cohort: the uncalibrated candidate Brier score was **0.029493**, lower than the calibrated value. This must be reported with the calibrated result; it is not evidence that calibration improved the candidate. The frozen-run, calibrator, and evaluation artifacts are local Git-ignored files at `artifacts/model/reduced_c00_frozen_run.json`, `artifacts/model/reduced_c00_calibrator.json`, and `artifacts/metrics/reduced_c00_evaluation.json`, all bound to manifest fingerprint `manifest-fp-12803f75af61` and Booster SHA-256 `7428cfb384986c82ac09d1d0edd72762289bcdda597935b5c45d54f4b8f9170b`.

The spread-only baseline remains explicitly blocked because the real c00-only corpus has no measured `rain_member_std`; no spread was synthesized.

## Frozen historical replay slice

`scripts/export_replay.py` now produces a small, read-only replay asset from the saved candidate, validation-only calibrator, frozen evaluation, aligned rows, and fixed geometry. It validates the current manifest fingerprint and the saved Booster SHA-256 before reading held-out rows; it neither retrains nor refits calibration. The deterministic availability-only selection is the first, chronological-middle, and last held-out initializations: **2018-01-01**, **2019-01-01**, and **2019-12-31**. The local Git-ignored artifact at `artifacts/replay/reduced_c00_replay.json` contains 3,360 region/lead records (3 dates × 112 regions × 10 leads), each tied to its source key, GRIB accumulation arithmetic, coverage, and verification interval.

The replay identifies itself as `historical_replay` and as the **reduced c00-only candidate**. It displays saved LightGBM score contributions and strictly earlier c00 analog cases as score evidence, not meteorological cause; moisture, circulation, and ensemble-disagreement remain visibly deferred. Day 10 has no forecast, observation, threshold, probability, or bust value and remains gray/unavailable. The dashboard must be served with `REPLAY_ASSET_PATH=artifacts/replay/reduced_c00_replay.json`; without that explicit local setting it safely serves the fixture asset. A recorded offline browser run remains required before D2-05 and the submission release can be marked complete.
