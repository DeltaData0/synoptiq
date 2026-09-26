"""Guarded placeholder for model training."""

from _run_context import emit

emit("train", "artifacts/model/", split="2010-2015/2016-2017/2018-2019")
raise SystemExit("Training blocked: no audited, aligned data set is available.")

