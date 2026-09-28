"""Start the local API and print reproducibility metadata."""

from __future__ import annotations

import os

import uvicorn
from _run_context import ROOT, emit
from bust.data.dataset import get_manifest_fingerprint
from bust.model.evaluate import FROZEN_SPLIT_ID

demo_mode = os.getenv("SYNOPTIQ_DEMO_MODE") == "1"
replay_asset = os.getenv("REPLAY_ASSET_PATH")
host = os.getenv("API_HOST", "127.0.0.1")
port = int(os.getenv("API_PORT", "8000"))
if replay_asset and not demo_mode:
    emit(
        "api",
        f"http://{host}:{port}",
        split=FROZEN_SPLIT_ID,
        manifest_id=get_manifest_fingerprint(ROOT / "DATA_MANIFEST.csv"),
    )
    print(f"data_mode=historical_replay; replay_asset={replay_asset}")
else:
    emit("demo-fixture" if demo_mode else "api", f"http://{host}:{port}")
if demo_mode:
    print("data_mode=fixture; guided prototype walkthrough only; no validated model or metrics")
uvicorn.run(
    "bust.api.main:app",
    host=host,
    port=port,
    reload=False,
)
