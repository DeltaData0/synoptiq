# Method (frozen intent)

The target is the absolute difference between GEFSv12 control-member regional 24-hour accumulated rain and aligned IMD daily regional rain. A bust label is an error above the train-only regional × season × lead-bucket 90th percentile, subject to a 10 mm/day floor. Exact verification intervals and source provenance are mandatory fields; `init_utc + lead_day` is not a verification interval.

Analog candidates are ranked only from issue-time features selected by the
future model pipeline. An accepted analog initialization must be strictly
earlier than the query initialization; same-init and future candidates are
rejected. Observations, error, threshold, bust, and model-probability fields
must not determine retrieval. Fewer than five valid earlier candidates is an
explicit `insufficient_earlier_analogs` fallback, never padded evidence.
(Plan §4; Reference §5)

Candidate probabilities are calibrated only with eligible exact Day 1–9
validation rows. The held-out 2018–2019 test partition is never used to fit a
calibrator or select hyperparameters. Every eventual model/evaluation artifact
must carry the input manifest ID, commit, frozen split ID, seed, ordered feature
set hash, and JSON-serializable hyperparameters. If validation or test evidence
is insufficient, its artifact has an explicit status with null metrics rather
than an invented score. (Plan §§3–4, §6)
