"""File-backed source of replay assets; default fixture is intentionally safe."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


@lru_cache(maxsize=1)
def load_store() -> dict:
    if os.getenv("SYNOPTIQ_DEMO_MODE") == "1":
        from bust.api.demo_fixture import build_demo_store

        return build_demo_store()

    path = Path(os.getenv("REPLAY_ASSET_PATH", _project_root() / "data/fixtures/replay_contract.json"))
    if not path.exists():
        raise FileNotFoundError(f"Replay asset not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def available_inits() -> list[str]:
    return load_store()["available_inits"]


def replay(init: str, lead: int) -> dict | None:
    return load_store().get("replays", {}).get(init, {}).get(str(lead))


def region(init: str, lead: int, region_id: str) -> dict | None:
    return load_store().get("regions", {}).get(f"{init}:{lead}:{region_id}")


def evaluation() -> dict:
    return load_store()["evaluation"]
