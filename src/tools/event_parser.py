# src/tools/event_parser.py

import re
from datetime import datetime, timedelta

DAY_ALIASES = {
    "mon": "Monday",
    "monday": "Monday",
    "tue": "Tuesday",
    "tues": "Tuesday",
    "tuesday": "Tuesday",
    "wed": "Wednesday",
    "weds": "Wednesday",
    "wednesday": "Wednesday",
    "thu": "Thursday",
    "thur": "Thursday",
    "thurs": "Thursday",
    "thursday": "Thursday",
    "fri": "Friday",
    "friday": "Friday",
    "sat": "Saturday",
    "saturday": "Saturday",
    "sun": "Sunday",
    "sunday": "Sunday",
}

ALL_DAYS = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
]


def _normalize_time_str(t: str) -> str:
    """Convert '8' or '8:30' into '08:00' or '08:30'."""
    t = t.strip()
    if ":" not in t:
        t = f"{t}:00"
    dt = datetime.strptime(t, "%H:%M")
    return dt.strftime("%H:%M")


def parse_user_events(text: str) -> dict:
    """
    Parse user-input event lines like:
        Monday 08:00-10:00 Gym
        Tue 9-11 Work
        Fri 21-5 Sleep

    Return:
        {
          "Monday": [("Gym", 2.0), ("Work", 8.0), ...],
          ...
        }
    where durations are in hours (float), for the LLM prompt.
    """
    events = {day: [] for day in ALL_DAYS}

    for raw_line in text.strip().splitlines():
        line = raw_line.strip()
        if not line:
            continue

        parts = line.split()
        if len(parts) < 3:
            # Need at least: Day, time-range, activity
            continue

        day_token = parts[0].lower()
        day = DAY_ALIASES.get(day_token)
        if day is None:
            continue

        # Find time range like 08:00-10:00 or 8-10 or 8:30-10
        match = re.search(r"(\d{1,2}(:\d{2})?)-(\d{1,2}(:\d{2})?)", line)
        if not match:
            continue

        start_raw = match.group(1)
        end_raw = match.group(3)

        start_str = _normalize_time_str(start_raw)
        end_str = _normalize_time_str(end_raw)

        start_dt = datetime.strptime(start_str, "%H:%M")
        end_dt = datetime.strptime(end_str, "%H:%M")

        # Allow crossing midnight
        if end_dt <= start_dt:
            end_dt += timedelta(days=1)

        duration_hours = (end_dt - start_dt).total_seconds() / 3600.0

        # Activity label is everything after the time range
        activity = line.split(match.group(0), 1)[-1].strip()
        if not activity:
            activity = "Task"

        events[day].append((activity, duration_hours))

    return events
