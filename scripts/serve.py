"""Start the local API and print reproducibility metadata."""

from __future__ import annotations

import os

import uvicorn
from _run_context import emit

emit("api", "http://127.0.0.1:8000")
uvicorn.run(
    "bust.api.main:app",
    host=os.getenv("API_HOST", "127.0.0.1"),
    port=int(os.getenv("API_PORT", "8000")),
    reload=False,
)

