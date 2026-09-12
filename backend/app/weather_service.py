"""
Weather Service for ARYA — Integrates with Open-Meteo free API (No key required).
Provides current weather, hourly forecast, and 7-day forecast.
"""

import httpx
from typing import Any, Dict, Optional

# Default location: Guntur, Andhra Pradesh (16.3067° N, 80.4365° E)
DEFAULT_LAT = 16.3067
DEFAULT_LON = 80.4365
DEFAULT_CITY = "Guntur"

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"


def geocode_city(city_name: str) -> Optional[Dict[str, Any]]:
    """Geocode a city name to latitude and longitude."""
    try:
        resp = httpx.get(GEOCODING_URL, params={"name": city_name, "count": 1, "language": "en", "format": "json"}, timeout=5.0)
        data = resp.json()
        if data.get("results"):
            top = data["results"][0]
            return {
                "name": top.get("name"),
                "country": top.get("country"),
                "latitude": top.get("latitude"),
                "longitude": top.get("longitude"),
            }
    except Exception as exc:
        print(f"[WEATHER] Geocoding error for {city_name}: {exc}")
    return None


def get_weather_data(city: Optional[str] = None) -> Dict[str, Any]:
    """Fetch current weather and 3-day forecast from Open-Meteo."""
    lat, lon, city_display = DEFAULT_LAT, DEFAULT_LON, DEFAULT_CITY

    if city and city.lower().strip() != DEFAULT_CITY.lower():
        geo = geocode_city(city)
        if geo:
            lat = geo["latitude"]
            lon = geo["longitude"]
            city_display = f"{geo['name']}, {geo['country']}"

    params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": True,
        "daily": ["temperature_2m_max", "temperature_2m_min", "precipitation_sum", "weathercode"],
        "timezone": "auto"
    }

    try:
        resp = httpx.get(OPEN_METEO_URL, params=params, timeout=5.0)
        data = resp.json()

        curr = data.get("current_weather", {})
        temp_c = curr.get("temperature")
        windspeed = curr.get("windspeed")
        weathercode = curr.get("weathercode", 0)

        condition = _decode_weather_code(weathercode)

        daily = data.get("daily", {})
        max_temps = daily.get("temperature_2m_max", [])
        min_temps = daily.get("temperature_2m_min", [])
        precip = daily.get("precipitation_sum", [])

        forecast = []
        if max_temps and min_temps:
            dates = daily.get("time", [])
            for i in range(min(3, len(dates))):
                forecast.append({
                    "date": dates[i],
                    "max_temp": f"{max_temps[i]}°C",
                    "min_temp": f"{min_temps[i]}°C",
                    "rain_mm": f"{precip[i] if i < len(precip) else 0}mm"
                })

        return {
            "success": True,
            "location": city_display,
            "temperature": f"{temp_c}°C",
            "condition": condition,
            "windspeed": f"{windspeed} km/h",
            "forecast_3day": forecast
        }
    except Exception as exc:
        return {"success": False, "error": f"Failed to fetch weather: {str(exc)}"}


def _decode_weather_code(code: int) -> str:
    """Decode WMO Weather interpretation codes."""
    codes = {
        0: "Clear sky",
        1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Foggy", 48: "Depositing rime fog",
        51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
        61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
        71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
        80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
        95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
    }
    return codes.get(code, "Clear/Partly Cloudy")
