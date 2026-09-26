from fastapi.testclient import TestClient

from bust.api.main import app

client = TestClient(app)


def test_fixture_replay_contract_and_day_10_no_data() -> None:
    response = client.get("/v1/replay", params={"init": "2018-08-01", "lead": 10})
    assert response.status_code == 200
    payload = response.json()
    assert payload["data_mode"] == "fixture"
    assert payload["features"][0]["properties"]["p_bust"] is None
    assert payload["features"][0]["properties"]["window_quality"] == "unavailable"


def test_invalid_replay_returns_available_dates() -> None:
    response = client.get("/v1/replay", params={"init": "2018-08-10", "lead": 1})
    assert response.status_code == 404
    assert response.json()["detail"]["available_inits"] == ["2018-08-01"]

