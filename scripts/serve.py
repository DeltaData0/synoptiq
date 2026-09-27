"""Start the local API and print reproducibility metadata."""

from __future__ import annotations

import os

import uvicorn
from _run_context import emit

demo_mode = os.getenv("SYNOPTIQ_DEMO_MODE") == "1"
emit("demo-fixture" if demo_mode else "api", "http://127.0.0.1:8000")
if demo_mode:
    print("data_mode=fixture; guided prototype walkthrough only; no validated model or metrics")
uvicorn.run(
    "bust.api.main:app",
    host=os.getenv("API_HOST", "127.0.0.1"),
    port=int(os.getenv("API_PORT", "8000")),
    reload=False,
)
