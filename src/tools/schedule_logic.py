# src/schedule_agent.py
from src.google_calendar_api import GoogleCalendarService
from src.tinyllama import call_tinyllama, clean_model_output
from src.sleep_tracker import SleepTracker

import datetime
import re

DAY_TO_DATE = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6
}

class ScheduleAgent:
    def __init__(self, min_sleep=8):
        self.sleep_tracker = SleepTracker(minimum_hours=min_sleep)
        self.calendar = GoogleCalendarService()
        self.calendar.authenticate()

    def parse_and_sync_to_calendar(self, schedule_text):
        """Parse TinyLlama's text output and send events to Google Calendar."""
        lines = schedule_text.splitlines()
        current_day = None

        for line in lines:
            line = line.strip()

            # Detect day header
            if line.endswith(":") and line[:-1] in DAY_TO_DATE:
                current_day = line[:-1]
                continue

            if current_day and line.startswith("-") and "Sleep" not in line:
                # Example line: "- Study ML (3 hrs)"
                activity = line[2:]
                task, duration = activity.rsplit("(", 1)

                match = re.search(r"(\d+(\.\d+)?)", duration)
                if match:
                    hours = float(match.group(1))
                else:
                    continue   # skip badly formatted lines


                # Construct event datetime
                today = datetime.date.today()
                target_date = today + datetime.timedelta(days=DAY_TO_DATE[current_day])

                start_time = datetime.datetime(target_date.year, target_date.month, target_date.day, 9)  # 9 AM start
                end_time = start_time + datetime.timedelta(hours=hours)

                # Add to Google Calendar!
                self.calendar.create_event(task.strip(), start_time, end_time)

    def generate_schedule(self, events):
        event_text = "\n".join(
            f"- {day}: {task} ({hours} hrs)" 
            for day, task, hours in events
        )

        sleep_info = "\n".join(
            f"- {day}: slept {hrs} hours"
            for day, hrs in self.sleep_tracker.sleep_log.items()
        )

        prompt = f"""
Create a schedule with sleep.

Minimum sleep: {self.sleep_tracker.minimum_hours} hours.

Events:
{event_text}

Sleep logs:
{sleep_info or "None"}

Output ONLY in this layout:

Monday:
- Sleep: X hours
- Task: <task>

Tuesday:
- Sleep: X hours
- Task: <task>

No explanations.
"""



        raw = call_tinyllama(prompt)
        print("\nRAW MODEL OUTPUT:\n", raw, "\n")

        schedule_text = clean_model_output(raw)

        if not schedule_text or "Sleep" not in schedule_text:
            print("TinyLlama returned invalid output. Not syncing.")
            return "MODEL FAILED TO GENERATE A VALID SCHEDULE"
        return schedule_text
