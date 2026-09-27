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


def test_guided_demo_mode_is_fixture_only_and_keeps_day_10_unavailable(monkeypatch) -> None:
    """The richer recording walkthrough is isolated behind an opt-in fixture-only flag."""
    from bust.api import store

    monkeypatch.setenv("SYNOPTIQ_DEMO_MODE", "1")
    store.load_store.cache_clear()
    try:
        demo_client = TestClient(app)
        assert demo_client.get("/health").json()["data_mode"] == "fixture"

        day_1 = demo_client.get("/v1/replay", params={"init": "2018-08-01", "lead": 1})
        assert day_1.status_code == 200
        assert day_1.json()["data_mode"] == "fixture"
        assert len(day_1.json()["features"]) == 65

        day_9 = demo_client.get("/v1/replay", params={"init": "2018-08-01", "lead": 9})
        assert day_9.status_code == 200
        assert day_9.json()["data_mode"] == "fixture"

        day_10 = demo_client.get("/v1/replay", params={"init": "2018-08-01", "lead": 10})
        assert day_10.status_code == 200
        assert {item["properties"]["window_quality"] for item in day_10.json()["features"]} == {"unavailable"}
        assert {item["properties"]["p_bust"] for item in day_10.json()["features"]} == {None}

        evaluation = demo_client.get("/v1/evaluation").json()
        assert evaluation["data_mode"] == "fixture"
        assert evaluation["metrics"] is None
        assert "No held-out evaluation" in evaluation["message"]
    finally:
        store.load_store.cache_clear()


def test_strict_offline_frontend_has_no_remote_tiles_or_cdns() -> None:
    """web/src/ must remain strictly offline: no remote URLs, CartoDB, tileLayer, or CDN references."""
    import re
    from pathlib import Path

    web_src = Path(__file__).resolve().parents[1] / "web/src"
    assert web_src.exists()

    forbidden_patterns = [
        "cartocdn",
        "cartodb",
        "tilelayer",
        "openstreetmap",
        "mapbox",
        "{z}/{x}/{y}",
    ]

    url_regex = re.compile(r"https?://[^\s\"'`<>]+", re.IGNORECASE)
    allowed_local_url = "http://127.0.0.1:8000"

    violations = []
    for f in sorted(web_src.rglob("*")):
        if f.is_file() and f.suffix in (".js", ".html", ".css", ".json"):
            content = f.read_text(encoding="utf-8")
            content_lower = content.lower()

            # 1. Retain checks for tileLayer, CartoDB, mapbox, OpenStreetMap, and {z}/{x}/{y}
            for pat in forbidden_patterns:
                if pat in content_lower:
                    violations.append(f"{f.name} contains forbidden remote pattern {pat!r}")

            # 2. Strict URL rule: reject every http:// or https:// occurrence;
            # allow only the exact local URL http://127.0.0.1:8000 in web/src/api.js
            urls = url_regex.findall(content)
            for url in urls:
                if f.name == "api.js" and url == allowed_local_url:
                    continue
                violations.append(f"{f.name} contains forbidden URL: {url!r}")

    assert not violations, "Strict offline violation(s) detected:\n" + "\n".join(violations)

    # 3. Regression assertion: fixture Forecast view contains "Forecast total unavailable in fixture"
    # and contains no tier-to-rainfall mapping (such as 32.0 mm / 14.0 mm).
    map_code = (web_src / "map.js").read_text(encoding="utf-8")
    legend_code = (web_src / "legend.js").read_text(encoding="utf-8")
    heatmap_code = (web_src / "heatmap.js").read_text(encoding="utf-8")

    assert "Forecast total unavailable in fixture" in map_code
    assert "Forecast total unavailable in fixture" in legend_code

    tier_rain_patterns = [
        r'tier\s*===?\s*["\']high["\']\s*\?\s*32',
        r'tier\s*===?\s*["\']watch["\']\s*\?\s*14',
        r'32\.0\s*mm',
        r'14\.0\s*mm',
    ]
    for pat in tier_rain_patterns:
        assert not re.search(pat, map_code), f"map.js contains tier-to-rainfall mapping matching {pat!r}"
        assert not re.search(pat, heatmap_code), f"heatmap.js contains tier-to-rainfall mapping matching {pat!r}"
