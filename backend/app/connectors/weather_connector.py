import json
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from typing import Any


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

_WEATHER_CODES = {
    0: "Ясно", 1: "Преимущественно ясно", 2: "Переменная облачность", 3: "Пасмурно",
    45: "Туман", 48: "Изморозь",
    51: "Лёгкая морось", 53: "Морось", 55: "Сильная морось",
    56: "Лёгкая ледяная морось", 57: "Ледяная морось",
    61: "Небольшой дождь", 63: "Дождь", 65: "Сильный дождь",
    66: "Лёгкий ледяной дождь", 67: "Ледяной дождь",
    71: "Небольшой снег", 73: "Снег", 75: "Сильный снег", 77: "Снежные зёрна",
    80: "Небольшие ливни", 81: "Ливни", 82: "Сильные ливни",
    85: "Снежные заряды", 86: "Сильные снежные заряды",
    95: "Гроза", 96: "Гроза с градом", 99: "Сильная гроза с градом",
}


def _http_json(url: str) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": "HomeAgent-weather/1.0"})
    with urlopen(request, timeout=8) as response:
        if response.status >= 400:
            raise RuntimeError(f"Weather provider returned HTTP {response.status}")
        data = json.loads(response.read().decode("utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError("Weather provider returned an invalid response")
    if data.get("error"):
        raise RuntimeError(data.get("reason", "Weather provider returned an error"))
    return data


def _condition(code: Any) -> str:
    try:
        return _WEATHER_CODES.get(int(code), "Неизвестные условия")
    except (TypeError, ValueError):
        return "Неизвестные условия"


def get_weather(city: str, forecast_days: int = 5) -> dict[str, Any]:
    city = city.strip()
    if len(city) < 2:
        return {"status": "error", "message": "Укажите город для прогноза погоды."}
    forecast_days = max(1, min(forecast_days, 7))

    geo_query = urlencode({"name": city, "count": 1, "language": "ru", "format": "json"})
    geo = _http_json(f"{GEOCODING_URL}?{geo_query}")
    results = geo.get("results") or []
    if not results:
        return {"status": "error", "message": f"Не удалось найти город «{city}»."}
    location = results[0]

    params = {
        "latitude": location["latitude"], "longitude": location["longitude"],
        "current": "temperature_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "forecast_days": forecast_days, "timezone": "auto", "temperature_unit": "celsius",
        "wind_speed_unit": "kmh", "precipitation_unit": "mm",
    }
    forecast = _http_json(f"{FORECAST_URL}?{urlencode(params)}")
    current = forecast.get("current") or {}
    daily = forecast.get("daily") or {}
    daily_rows = []
    for index, date in enumerate(daily.get("time") or []):
        daily_rows.append({
            "date": date,
            "weather_code": daily.get("weather_code", [None])[index],
            "condition": _condition((daily.get("weather_code") or [None])[index]),
            "temperature_min_c": (daily.get("temperature_2m_min") or [None])[index],
            "temperature_max_c": (daily.get("temperature_2m_max") or [None])[index],
            "precipitation_probability_percent": (daily.get("precipitation_probability_max") or [None])[index],
        })

    return {
        "status": "success",
        "location": {
            "name": location.get("name", city), "country": location.get("country", ""),
            "latitude": location.get("latitude"), "longitude": location.get("longitude"),
            "timezone": forecast.get("timezone", location.get("timezone", "")),
        },
        "current": {
            "observed_at": current.get("time"), "temperature_c": current.get("temperature_2m"),
            "apparent_temperature_c": current.get("apparent_temperature"),
            "precipitation_mm": current.get("precipitation"), "wind_speed_kmh": current.get("wind_speed_10m"),
            "weather_code": current.get("weather_code"), "condition": _condition(current.get("weather_code")),
        },
        "daily": daily_rows,
        "source": {
            "provider": "Open-Meteo", "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "forecast_url": FORECAST_URL, "geocoding_url": GEOCODING_URL,
        },
    }
