# src/agent/weekly_agent.py

import re
from src.agent.tinyllama import call_tinyllama


DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class WeeklyAgent:
    def __init__(self, min_sleep=8):
        self.min_sleep = min_sleep
        self.user_events = {}

    # ---------------------------------------------------------------------
    # User assigns weekly events
    # ---------------------------------------------------------------------
    def set_user_weekly_events(self, weekly_events: dict):
        """
        weekly_events must be:
        {
            "Monday": [("Gym", 2), ("Work", 8), ...],
            ...
        }
        """
        self.user_events = weekly_events

    # ---------------------------------------------------------------------
    # Core method: generate weekly schedule
    # ---------------------------------------------------------------------
    def plan_week(self):
        event_text = "\n".join(
            f"{day}: " + ", ".join(f"{task} ({hrs} hours)" for task, hrs in tasks)
            for day, tasks in self.user_events.items()
        )

        prompt = f"""
You are an AI scheduling model. You MUST output a weekly schedule in EXACT FORMAT below.

FORMAT (NO deviations):

Monday:
    HH:MM-HH:MM-Activity
Tuesday:
    HH:MM-HH:MM-Activity
Wednesday:
    HH:MM-HH:MM-Activity
Thursday:
    HH:MM-HH:MM-Activity
Friday:
    HH:MM-HH:MM-Activity
Saturday:
    HH:MM-HH:MM-Activity
Sunday:
    HH:MM-HH:MM-Activity

RULES:
- Every day must appear EXACTLY once and in this EXACT order.
- Every day must have at least one Sleep block.
- You must schedule at least {self.min_sleep} hours of sleep daily.
- No day may exceed 24 hours.
- Keep tasks assigned to the correct day.
- NO explanations, NO examples, NO text after Sunday.

Events:
{event_text}

Now output ONLY the schedule.
"""

        raw_output = call_tinyllama(prompt)
        print("\nRAW MODEL OUTPUT:\n", raw_output)

        cleaned = self.clean_model_output(raw_output)
        print("\nCLEANED MODEL OUTPUT:\n", cleaned)

        parsed = self.parse_weekly_schedule(cleaned)
        return parsed

    # ---------------------------------------------------------------------
    # Clean model output → keep only valid structured lines
    # ---------------------------------------------------------------------
    def clean_model_output(self, text: str):
        cleaned_lines = []
        allowed_days = [f"{d}:" for d in DAYS]

        for line in text.splitlines():
            stripped = line.strip()

            # Valid day label
            if stripped in allowed_days:
                cleaned_lines.append(stripped)
                continue

            # Valid activity line must have:
            # HH:MM-HH:MM-ActivityName
            if re.match(r"^\d{2}:\d{2}-\d{2}:\d{2}-", stripped):
                cleaned_lines.append("    " + stripped)
                continue

        return "\n".join(cleaned_lines)

    # ---------------------------------------------------------------------
    # Parse cleaned text into schedule dictionary
    # ---------------------------------------------------------------------
    def parse_weekly_schedule(self, cleaned_text: str):
        schedule = {day: [] for day in DAYS}
        current_day = None

        for line in cleaned_text.splitlines():
            line = line.strip()

            # Identify day
            if line in [d + ":" for d in DAYS]:
                current_day = line[:-1]   # Remove colon
                continue

            # Parse activity
            if re.match(r"^\d{2}:\d{2}-\d{2}:\d{2}-", line):
                schedule[current_day].append(line)

        return schedule

    # ---------------------------------------------------------------------
    # Unified method used by main/dashboard.py
    # ---------------------------------------------------------------------
    def run_weekly_cycle(self):
        schedule_dict = self.plan_week()
        return schedule_dict
