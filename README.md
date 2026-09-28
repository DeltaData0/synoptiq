# Synoptiq

Synoptiq is a research prototype for identifying the risk that a regional daily-rainfall forecast will be a **forecast bust**. It replays historical GEFSv12 forecast issue times against IMD gridded rainfall; it is not a live warning service and is not validated for NCUM/NEPS operations.

**Start here:** [Synoptiq — Project Reference](docs/SYNOPTIQ.md) brings together the problem, scientific method, architecture, recorded results, current capabilities, development history, and future roadmap in one document.

## Current status

The recorded real-data MVP uses a **reduced c00-only LightGBM candidate**, with a completed 2010–2019 forecast corpus, held-out evaluation, and a three-date historical replay. Exact Days 1–9 are supported; Day 10 and low-coverage regions remain no-data. Full ensemble/atmospheric features and final release acceptance remain outstanding; see the [project reference](docs/SYNOPTIQ.md#3-current-implementation) for scope and evidence.

A fresh clone still runs in **fixture mode** by default. Real generated artifacts are Git-ignored and must be supplied separately; the [real-replay startup instructions](docs/SYNOPTIQ.md#12-repository-and-local-operation) explain how to select them. Fixture values are not model results.

## Quick start

Use Python 3.11 (the locked project target) and Node 20+:

```sh
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
make web
make api
```

The API is available at `http://127.0.0.1:8000`, with interactive OpenAPI documentation at `/docs`. In a second terminal, `make smoke` verifies the fixture contract.

For environments where GRIB bindings are difficult to build, use `conda env create -f environment.yml` and `conda activate synoptiq`.

## Commands

| Command | Purpose |
| --- | --- |
| `make pilot` | Check local source inventory; no remote data is silently substituted. |
| `make dataset` | Build aligned rows when audited source data is available. |
| `make train` | Train only after the data gate passes. |
| `make replay` | Export frozen replay assets. |
| `make api` | Run the fixture/replay FastAPI server. |
| `make web` | Build the offline Vite frontend. |
| `make smoke` | Exercise API endpoints and response contracts. |
| `make test` | Run unit and API tests. |

## Data and safety contract

- Do not commit raw datasets, credentials, or absolute data paths.
- Use `DATA_DIR` to point at local data storage (defaults to `data/`).
- The frozen target is regional 24-hour rain error, with train-only thresholds and explicit UTC verification windows.
- Day 10 is unavailable: the audited target requires a +240–+243-hour amount,
  while the inspected archive supplies +240–+246 hours. See
  [docs/data_audit.md](docs/data_audit.md); do not present a Day-10 value as
  exact without a new approved audit.
- See [DECISIONS.md](docs/DECISIONS.md), [DATA_MANIFEST.csv](DATA_MANIFEST.csv), and [RUN_LOG.md](docs/RUN_LOG.md) for change control.

## Project layout

`src/bust/` contains the data, feature, model, and API packages. `data/fixtures/` is the only committed data directory. The implementation plan and canonical research reference are retained in `docs/` as the source planning record.

## Sources

- [NOAA GEFSv12 reforecast archive](https://registry.opendata.aws/noaa-gefs-reforecast/)
- [IMD 0.25° daily rainfall catalogue](https://imdpune.gov.in/cmpg/Griddata/Rainfall_25_NetCDF.html)
