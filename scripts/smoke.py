"""Run the fixture API contract checks without requiring a background server."""

from _run_context import emit
from fastapi.testclient import TestClient

from bust.api.main import app

emit("smoke", "data/fixtures/replay_contract.json")
client = TestClient(app)

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

# Verify mounted web distribution serves the shell and fixture-ribbon
root_response = client.get("/")
assert root_response.status_code == 200
assert 'id="fixture-ribbon"' in root_response.text
assert "FIXTURE" in root_response.text
assert "SYNOPTIQ" in root_response.text

# Verify Day 10 fixture response contracts
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
