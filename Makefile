.DEFAULT_GOAL := help
PYTHON ?= python
NPM ?= npm

.PHONY: help pilot dataset train candidate evaluate-candidate replay api web smoke replay-smoke test lint demo

help:
	@echo "Targets: pilot dataset train candidate evaluate-candidate replay api web smoke replay-smoke test lint demo"

pilot:
	$(PYTHON) scripts/pilot.py

dataset:
	$(PYTHON) scripts/build_dataset.py

train:
	$(PYTHON) scripts/train_all.py --replace

candidate:
	$(PYTHON) scripts/train_reduced_c00.py

evaluate-candidate:
	$(PYTHON) scripts/evaluate_reduced_c00.py

replay:
	$(PYTHON) scripts/export_replay.py --replace

api:
	$(PYTHON) scripts/serve.py

web:
	$(PYTHON) scripts/build_web.py

smoke:
	$(PYTHON) scripts/smoke.py

replay-smoke:
	REPLAY_ASSET_PATH=artifacts/replay/reduced_c00_replay.json $(PYTHON) scripts/smoke.py

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check src tests scripts

demo: web
	SYNOPTIQ_DEMO_MODE=1 $(PYTHON) scripts/serve.py
