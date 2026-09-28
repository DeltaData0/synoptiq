"""Smoke-test either the safe fixture or an explicitly supplied replay asset."""

import os

from _run_context import ROOT, emit
from fastapi.testclient import TestClient

from bust.api.main import app
from bust.data.dataset import get_manifest_fingerprint
from bust.model.evaluate import FROZEN_SPLIT_ID

client = TestClient(app)

replay_asset = os.getenv("REPLAY_ASSET_PATH")
if replay_asset:
    emit(
        "smoke",
        replay_asset,
        split=FROZEN_SPLIT_ID,
        manifest_id=get_manifest_fingerprint(ROOT / "DATA_MANIFEST.csv"),
    )
    health = client.get("/health").json()
    assert health == {"status": "ok", "data_mode": "historical_replay"}
    init = "2018-01-01"
    replay = client.get("/v1/replay", params={"init": init, "lead": 1})
    assert replay.status_code == 200
    payload = replay.json()
    assert payload["data_mode"] == "historical_replay"
    assert len(payload["features"]) == 112
    scored = [feature for feature in payload["features"] if feature["properties"]["p_bust"] is not None]
    assert scored
    assert all(feature["properties"]["f_control_mm"] is not None for feature in scored)

    region_id = scored[0]["properties"]["region_id"]
    region = client.get(f"/v1/region/{region_id}", params={"init": init, "lead": 1})
    assert region.status_code == 200
    detail = region.json()
    assert detail["source_key"] and detail["grib_steps"]
    assert detail["valid_start_utc"] and detail["valid_end_utc"]
    assert detail["reasons"] and detail["analogs"]

    replay_d10 = client.get("/v1/replay", params={"init": init, "lead": 10})
    assert replay_d10.status_code == 200
    for feature in replay_d10.json()["features"]:
        props = feature["properties"]
        assert props["window_quality"] == "unavailable"
        assert props["p_bust"] is None
        assert props["f_control_mm"] is None
        assert props["tier"] == "no_data"
else:
    emit("smoke", "data/fixtures/replay_contract.json")
    assert client.get("/health").json() == {"status": "ok", "data_mode": "fixture"}
    replay = client.get("/v1/replay", params={"init": "2018-08-01", "lead": 1})
    assert replay.status_code == 200
    assert replay.json()["data_mode"] == "fixture"
    assert replay.json()["features"][2]["properties"]["p_bust"] is None
    region = client.get(
        "/v1/region/R20N-078E", params={"init": "2018-08-01", "lead": 1}
    )
    assert region.status_code == 200
    assert region.json()["data_mode"] == "fixture"
    assert client.get("/v1/evaluation").json()["status"] == "insufficient_test_data"
    assert client.get("/v1/replay", params={"init": "2018-08-02", "lead": 1}).status_code == 404

    # Verify mounted web distribution serves the shell and fixture-ribbon.
    root_response = client.get("/")
    assert root_response.status_code == 200
    assert 'id="fixture-ribbon"' in root_response.text
    assert "FIXTURE" in root_response.text
    assert "SYNOPTIQ" in root_response.text

    # Verify Day 10 fixture response contracts.
    replay_d10 = client.get("/v1/replay", params={"init": "2018-08-01", "lead": 10})
    assert replay_d10.status_code == 200
    d10_props = replay_d10.json()["features"][0]["properties"]
    assert d10_props["window_quality"] == "unavailable"
    assert d10_props["no_data_reason"] == (
        "Day 10 is unavailable because the exact +240–+243-hour accumulation is not evidenced."
    )
    assert d10_props["p_bust"] is None
    assert d10_props["tier"] == "no_data"

print("smoke=passed")
