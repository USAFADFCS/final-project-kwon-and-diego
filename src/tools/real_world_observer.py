# src/tools/real_world_observer.py

"""
Real-World Observer Module
Gathers real-time external data:
- Global & local current events (NewsAPI)
- Weather conditions & alerts (OpenWeatherMap)
- Traffic & travel disruptions (Google Maps API)

This data feeds into the agent's OBSERVE step so
it can modify schedules based on real-world events.
"""

import requests
import datetime


# -------------------------------------------------------
# CONFIG (INSERT YOUR KEYS HERE)
# -------------------------------------------------------
NEWS_API_KEY = "YOUR_NEWSAPI_KEY"
WEATHER_API_KEY = "YOUR_OPENWEATHERMAP_KEY"
GOOGLE_MAPS_KEY = "YOUR_GOOGLE_MAPS_KEY"

# Default location (USAFA / Colorado Springs)
DEFAULT_LAT = 38.9940
DEFAULT_LON = -104.8439
DEFAULT_CITY = "Colorado Springs"
DEFAULT_STATE = "CO"


# -------------------------------------------------------
# 1. NewsAPI – World & Local Events
# -------------------------------------------------------
def fetch_news(query="Colorado", max_results=5):
    """
    Fetches top news stories relevant to local region or global breaking news.
    """

    url = (
        f"https://newsapi.org/v2/top-headlines?"
        f"q={query}&"
        f"language=en&"
        f"pageSize={max_results}&"
        f"apiKey={NEWS_API_KEY}"
    )

    try:
        resp = requests.get(url).json()
        articles = resp.get("articles", [])
        headlines = [a["title"] for a in articles if "title" in a]

        return {
            "status": "ok",
            "headlines": headlines,
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}


# -------------------------------------------------------
# 2. Weather API – Current Conditions + Alerts
# -------------------------------------------------------
def fetch_weather(lat=DEFAULT_LAT, lon=DEFAULT_LON):
    """
    Gets current conditions + severe weather alerts from OpenWeatherMap.
    """

    url = (
        f"https://api.openweathermap.org/data/2.5/onecall?"
        f"lat={lat}&lon={lon}&units=imperial&appid={WEATHER_API_KEY}"
    )

    try:
        resp = requests.get(url).json()

        current = resp.get("current", {})
        alerts = resp.get("alerts", [])

        weather_summary = {
            "temp": current.get("temp"),
            "conditions": current.get("weather", [{}])[0].get("description"),
        }

        alert_summaries = [
            {
                "event": alert.get("event"),
                "description": alert.get("description"),
                "start": alert.get("start"),
                "end": alert.get("end"),
            }
            for alert in alerts
        ]

        return {
            "status": "ok",
            "current_weather": weather_summary,
            "alerts": alert_summaries,
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}


# -------------------------------------------------------
# 3. Google Maps Traffic API – Live Traffic Summary
# -------------------------------------------------------
def fetch_traffic(origin="USAFA", destination="Colorado Springs"):
    """
    Estimate travel time + delays using Google Maps Distance Matrix API.
    """

    url = (
        f"https://maps.googleapis.com/maps/api/distancematrix/json?"
        f"origins={origin}&destinations={destination}&"
        f"departure_time=now&"
        f"key={GOOGLE_MAPS_KEY}"
    )

    try:
        resp = requests.get(url).json()

        rows = resp.get("rows", [])
        if not rows:
            return {"status": "error", "error": "No traffic data"}

        elements = rows[0].get("elements", [{}])[0]

        travel_time = elements.get("duration", {}).get("text")
        travel_time_traffic = elements.get("duration_in_traffic", {}).get("text")

        return {
            "status": "ok",
            "travel_time": travel_time,
            "traffic_time": travel_time_traffic,
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}


# -------------------------------------------------------
# MASTER OBSERVER
# -------------------------------------------------------
def observe_world():
    """
    Collects ALL external data sources and merges them
    into a single observation dict.
    """
    return {
        "timestamp": datetime.datetime.now().isoformat(),
        "news": fetch_news(),
        "weather": fetch_weather(),
        "traffic": fetch_traffic(),
    }
