from backend.app.connectors import weather_connector


def test_weather_connector_builds_structured_card(monkeypatch):
    def fake_http_json(url: str):
        if "geocoding" in url:
            return {"results": [{"name": "Эрфурт", "country": "Германия", "latitude": 50.9, "longitude": 11.0}]}
        return {
            "timezone": "Europe/Berlin",
            "current": {"time": "2026-07-30T12:00", "temperature_2m": 24.0, "apparent_temperature": 24.5, "precipitation": 0.0, "wind_speed_10m": 8.0, "weather_code": 1},
            "daily": {"time": ["2026-07-30"], "weather_code": [1], "temperature_2m_min": [15.0], "temperature_2m_max": [26.0], "precipitation_probability_max": [10]},
        }

    monkeypatch.setattr(weather_connector, "_http_json", fake_http_json)
    result = weather_connector.get_weather("Erfurt", 1)

    assert result["status"] == "success"
    assert result["location"]["name"] == "Эрфурт"
    assert result["current"]["condition"] == "Преимущественно ясно"
    assert result["daily"][0]["temperature_max_c"] == 26.0


def test_weather_connector_reports_unknown_city(monkeypatch):
    monkeypatch.setattr(weather_connector, "_http_json", lambda _url: {"results": []})
    result = weather_connector.get_weather("zzzzzzzz", 5)
    assert result["status"] == "error"
