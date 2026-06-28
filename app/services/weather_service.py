"""
Flora OS — Weather Service
OpenWeatherMap current conditions + forecast.
"""

from typing import Optional
import requests

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger("services.weather")

_BASE = "https://api.openweathermap.org/data/2.5"

_ICONS = {
    "Clear": "☀️", "Clouds": "☁️", "Rain": "🌧️", "Drizzle": "🌦️",
    "Thunderstorm": "⛈️", "Snow": "❄️", "Mist": "🌫️", "Fog": "🌫️",
    "Haze": "🌫️", "Smoke": "🌫️", "Dust": "🌪️", "Sand": "🌪️",
    "Ash": "🌋", "Squall": "💨", "Tornado": "🌪️",
}


def get_weather(city: str) -> Optional[dict]:
    """Return current weather for a city."""
    if not settings.openweather_api_key or not city:
        return None
    try:
        resp = requests.get(
            f"{_BASE}/weather",
            params={
                "q": city,
                "appid": settings.openweather_api_key,
                "units": "metric",
            },
            timeout=10,
        )
        resp.raise_for_status()
        d = resp.json()
        main_condition = d["weather"][0]["main"]
        return {
            "city": d.get("name", city),
            "country": d.get("sys", {}).get("country", ""),
            "temp_c": round(d["main"]["temp"]),
            "feels_like": round(d["main"]["feels_like"]),
            "humidity": d["main"]["humidity"],
            "description": d["weather"][0]["description"].title(),
            "condition": main_condition,
            "icon": _ICONS.get(main_condition, "🌡️"),
            "wind_kph": round(d.get("wind", {}).get("speed", 0) * 3.6),
        }
    except Exception as exc:
        logger.warning("Weather fetch failed for city=%s: %s", city, exc)
        return None


def get_weather_by_coords(lat: float, lon: float) -> Optional[dict]:
    """Return current weather for a GPS coordinate pair."""
    if not settings.openweather_api_key:
        return None
    try:
        resp = requests.get(
            f"{_BASE}/weather",
            params={
                "lat": lat, "lon": lon,
                "appid": settings.openweather_api_key,
                "units": "metric",
            },
            timeout=10,
        )
        resp.raise_for_status()
        d = resp.json()
        main_condition = d["weather"][0]["main"]
        return {
            "city": d.get("name", f"{lat:.1f},{lon:.1f}"),
            "country": d.get("sys", {}).get("country", ""),
            "temp_c": round(d["main"]["temp"]),
            "feels_like": round(d["main"]["feels_like"]),
            "humidity": d["main"]["humidity"],
            "description": d["weather"][0]["description"].title(),
            "condition": main_condition,
            "icon": _ICONS.get(main_condition, "🌡️"),
            "wind_kph": round(d.get("wind", {}).get("speed", 0) * 3.6),
        }
    except Exception as exc:
        logger.warning("Weather fetch by coords failed lat=%s lon=%s: %s", lat, lon, exc)
        return None


def get_forecast(city: str, days: int = 3) -> list[dict]:
    """Return a simplified daily forecast."""
    if not settings.openweather_api_key or not city:
        return []
    try:
        resp = requests.get(
            f"{_BASE}/forecast",
            params={
                "q": city,
                "appid": settings.openweather_api_key,
                "units": "metric",
                "cnt": days * 8,  # 3h intervals
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json().get("list", [])

        # Group by date and pick midday reading
        days_seen: dict[str, dict] = {}
        for entry in data:
            date = entry["dt_txt"][:10]
            hour = entry["dt_txt"][11:13]
            if date not in days_seen and hour in ("12", "13", "14"):
                cond = entry["weather"][0]["main"]
                days_seen[date] = {
                    "date": date,
                    "temp_high": round(entry["main"]["temp_max"]),
                    "temp_low": round(entry["main"]["temp_min"]),
                    "condition": cond,
                    "icon": _ICONS.get(cond, "🌡️"),
                    "description": entry["weather"][0]["description"].title(),
                }
        return list(days_seen.values())[:days]
    except Exception as exc:
        logger.warning("Forecast fetch failed for city=%s: %s", city, exc)
        return []
