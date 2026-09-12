"""
Weather Tools for ARYA — Exposes weather lookup capabilities to the AI planner.
"""

from .tool_registry import registry
from .tool_schemas import ToolCategory, ToolParam, ParamType, ToolSchema, ToolResult
from ..weather_service import get_weather_data


def _get_weather(params: dict) -> ToolResult:
    """Fetch real-time weather information for a specified city or default location."""
    city = params.get("city")
    data = get_weather_data(city)

    if not data.get("success"):
        return ToolResult(
            success=False,
            message=f"Could not retrieve weather: {data.get('error')}",
            data=data
        )

    location = data.get("location")
    temp = data.get("temperature")
    cond = data.get("condition")
    wind = data.get("windspeed")
    forecast = data.get("forecast_3day", [])

    forecast_str = ", ".join([f"{f['date']}: {f['min_temp']}-{f['max_temp']} ({f['rain_mm']} rain)" for f in forecast])

    msg = f"Weather in {location}: Currently {temp}, {cond} with wind speed {wind}. 3-Day Forecast: {forecast_str}"

    return ToolResult(
        success=True,
        message=msg,
        data=data
    )


# Register Weather Tool
registry.register(
    schema=ToolSchema(
        name="get_weather",
        description="Get current weather conditions and forecast for Guntur or any city.",
        category=ToolCategory.SYSTEM,
        params=[
            ToolParam("city", ParamType.STRING, "Name of the city (optional, defaults to Guntur)", required=False)
        ],
        examples=[
            "what's the weather today?",
            "is it going to rain in Guntur?",
            "what is the weather forecast for Hyderabad?",
            "temperature in Guntur right now"
        ],
    ),
    handler=_get_weather,
)
