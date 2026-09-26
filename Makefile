.DEFAULT_GOAL := help
PYTHON ?= python
NPM ?= npm

.PHONY: help pilot dataset train replay api web smoke test lint demo

help:
	@echo "Targets: pilot dataset train replay api web smoke test lint demo"

pilot:
	$(PYTHON) scripts/pilot.py

dataset:
	$(PYTHON) scripts/build_dataset.py

train:
	$(PYTHON) scripts/train_all.py

replay:
	$(PYTHON) scripts/export_replay.py

api:
	$(PYTHON) scripts/serve.py

web:
	$(PYTHON) scripts/build_web.py

smoke:
	$(PYTHON) scripts/smoke.py

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check src tests scripts

demo: web api
