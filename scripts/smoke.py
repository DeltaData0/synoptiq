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
print("smoke=passed")

