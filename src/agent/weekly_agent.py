# src/agent/weeklyagent.py

import re
import datetime
from typing import Dict, List, Tuple

from src.agent.tinyllama import call_tinyllama
from src.tools.google_calendar_api import GoogleCalendarService
from src.tools.sleep_validator import validate_sleep


DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class WeeklyAgent:
    """
    Weekly agent that:
    - Takes weekly user events
    - Reads real calendar events
    - Merges them
    - Sends prompt to TinyLlama
    - Validates sleep & hours
    - Syncs back to Google Calendar
    """

    def __init__(self, min_sleep: float = 8.0):
        self.min_sleep = min_sleep
        self.calendar = GoogleCalendarService()
        self.calendar.authenticate()

        self.user_weekly_events: Dict[str, List[Tuple[str, float]]] = {}
        self.weekly_schedule: Dict[str, Dict] = {}

    # ---------------------------------------------------------
    # Set weekly template events
    # ---------------------------------------------------------
    def set_user_weekly_events(self, weekly_events):
        self.user_weekly_events = weekly_events

    # ---------------------------------------------------------
    # Read existing Google Calendar events for this week
    # ---------------------------------------------------------
    def observe(self):
        events = self.calendar.get_events_this_week()
        result: Dict[str, List[Tuple[str, float]]] = {d: [] for d in DAY_NAMES}

        for ev in events:
            start = ev.get("start", {}).get("dateTime")
            end = ev.get("end", {}).get("dateTime")
            summary = ev.get("summary", "Event")

            if not start or not end:
                continue

            start_dt = datetime.datetime.fromisoformat(start.replace("Z", "+00:00"))
            end_dt = datetime.datetime.fromisoformat(end.replace("Z", "+00:00"))

            duration = (end_dt - start_dt).total_seconds() / 3600.0
            day = start_dt.strftime("%A")

            if day in result:
                result[day].append((summary, duration))

        return result

    # ---------------------------------------------------------
    # Build TinyLlama prompt
    # ---------------------------------------------------------
    def _build_prompt(self, merged_week):
        event_text = "\n".join(
            f"{day}: " + ", ".join(f"{task} ({hours} hours)" for task, hours in tasks)
            for day, tasks in merged_week.items()
        )

        prompt = f"""
Create a weekly schedule.

Rules:
- Each day must include at least {self.min_sleep} hours of sleep.
- No day may exceed 24 total hours.
- Keep tasks on their assigned days.

Events:
{event_text}

Respond ONLY in this format:

Monday:
- Sleep: X hours
- Task: <task> (Y hours)

Tuesday:
- Sleep: X hours
- Task: <task> (Y hours)

No explanations.
"""
        return prompt

    # ---------------------------------------------------------
    # Clean TinyLlama output
    # ---------------------------------------------------------
    def _clean_model_output(self, text):
        cleaned = []

        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue

            if any(line.startswith(day + ":") for day in DAY_NAMES):
                cleaned.append(line)
            elif line.startswith("- Sleep") or ("(" in line and "hours" in line):
                cleaned.append(line)

        return "\n".join(cleaned)

    # ---------------------------------------------------------
    # Call LLM and generate weekly schedule
    # ---------------------------------------------------------
    def plan_week(self):
        if not self.user_weekly_events:
            raise ValueError("Weekly events not set. Call set_user_weekly_events first.")

        calendar_week = self.observe()

        merged_week = {d: [] for d in DAY_NAMES}
        for d in DAY_NAMES:
            merged_week[d].extend(self.user_weekly_events.get(d, []))
            merged_week[d].extend(calendar_week.get(d, []))

        prompt = self._build_prompt(merged_week)
        raw = call_tinyllama(prompt)

        print("\nRAW MODEL OUTPUT:\n", raw, "\n")

        cleaned = self._clean_model_output(raw)
        if not cleaned:
            return "MODEL FAILED TO GENERATE A VALID SCHEDULE"

        return cleaned

    # ---------------------------------------------------------
    # Parse model schedule
    # ---------------------------------------------------------
    def _parse_schedule_text(self, text):
        schedule = {}
        day = None

        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue

            if line.endswith(":") and line[:-1] in DAY_NAMES:
                day = line[:-1]
                schedule[day] = {"sleep": 0.0, "tasks": []}
                continue

            if line.startswith("- Sleep"):
                m = re.search(r"(\d+(\.\d+)?)", line)
                if m:
                    schedule[day]["sleep"] = float(m.group(1))
                continue

            if "(" in line and "hours" in line:
                m = re.match(r"- (.+)\((\d+(\.\d+)?) hours?\)", line)
                if m:
                    task = m.group(1).strip()
                    hours = float(m.group(2))
                    schedule[day]["tasks"].append((task, hours))

        return schedule

    # ---------------------------------------------------------
    # Validate sleep + hours
    # ---------------------------------------------------------
    def validate_schedule(self, text):
        sleep_ok, bad_sleep = validate_sleep(text, self.min_sleep)

        parsed = self._parse_schedule_text(text)
        bad_hours = []

        for day, info in parsed.items():
            total = info["sleep"] + sum(h for _, h in info["tasks"])
            if total > 24:
                bad_hours.append(day)

        all_bad = list(set(bad_sleep + bad_hours))
        return (sleep_ok and len(bad_hours) == 0, all_bad)

    # ---------------------------------------------------------
    # Sync to calendar
    # ---------------------------------------------------------
    def parse_and_sync_to_calendar(self, text):
        parsed = self._parse_schedule_text(text)

        today = datetime.date.today()
        monday = today - datetime.timedelta(days=today.weekday())

        for i, day in enumerate(DAY_NAMES):
            date = monday + datetime.timedelta(days=i)

            if day not in parsed:
                continue

            tasks = parsed[day]["tasks"]
            time = datetime.datetime(date.year, date.month, date.day, 9, 0)

            for task, hours in tasks:
                end = time + datetime.timedelta(hours=hours)
                self.calendar.create_event(task, time, end)
                time = end

    # ---------------------------------------------------------
    # Agent cycle
    # ---------------------------------------------------------
    def run_weekly_cycle(self):
        schedule = self.plan_week()
        print("\nGENERATED WEEKLY SCHEDULE:\n", schedule)

        if schedule == "MODEL FAILED TO GENERATE A VALID SCHEDULE":
            print("Not syncing. Invalid model output.")
            return

        ok, bad_days = self.validate_schedule(schedule)
        if not ok:
            print("\nSCHEDULE INVALID ON DAYS:", bad_days)
            print("Fix manually or regenerate.")
            return

        self.parse_and_sync_to_calendar(schedule)
        print("\nSchedule synced to Google Calendar!")
