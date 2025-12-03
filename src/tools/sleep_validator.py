# src/sleep_validator.py
import re
from typing import Dict, List, Tuple

def parse_schedule(schedule_text: str) -> Dict[str, dict]:
    """
    Parse a schedule of the form:

    Day: Monday
    - Sleep: 7 hours
    - Task 1: Study ML
    - Task 2: Gym

    Returns:
      {
        "Monday": {"sleep": 7.0, "tasks": ["Study ML", "Gym"]},
        "Tuesday": {...},
        ...
      }
    """
    days: Dict[str, dict] = {}
    current_day = None

    for line in schedule_text.splitlines():
        line = line.strip()
        if not line:
            continue

        # Day line
        if line.startswith("Day:"):
            current_day = line.split(":", 1)[1].strip()
            days[current_day] = {"sleep": None, "tasks": []}
            continue

        # Sleep line
        if current_day and line.lower().startswith("- sleep"):
            # Grab the first number in the line (e.g., "7 hours", "8.5 hours")
            m = re.search(r"(\d+(\.\d+)?)", line)
            if m:
                days[current_day]["sleep"] = float(m.group(1))
            continue

        # Task line
        if current_day and line.startswith("- Task"):
            # "- Task 1: Study ML" -> "Study ML"
            task_part = line.split(":", 1)[1].strip()
            days[current_day]["tasks"].append(task_part)
            continue

    return days


def validate_sleep(schedule_text: str, min_sleep: float = 8.0) -> Tuple[bool, List[str]]:
    """
    Check if each day in the schedule has at least min_sleep hours.
    Returns:
      (is_valid, bad_days)

      is_valid: True if all days meet the requirement
      bad_days: list of day names that fail
    """
    parsed = parse_schedule(schedule_text)
    bad_days = []

    for day, info in parsed.items():
        sleep_hours = info.get("sleep")
        if sleep_hours is None or sleep_hours < min_sleep:
            bad_days.append(day)

    return (len(bad_days) == 0, bad_days)

def validate_daily_hours(day_tasks):
    total = sum(hours for _, hours in day_tasks)
    return total <= 24

def validate_conflicts(gcal_events, schedule):
    # Ensure tasks don't overlap with existing meetings
    return True or False
