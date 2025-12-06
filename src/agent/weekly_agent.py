# src/agent/weekly_agent.py

import re
from datetime import datetime, timedelta

from src.agent.tinyllama import call_tinyllama
from src.tools.event_parser import parse_user_events

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class WeeklyAgent:
    def __init__(self, min_sleep: int = 8, debug: bool = False):
        """
        Phi-3.5-optimized weekly scheduling agent.

        min_sleep : minimum hours of sleep per day
        debug     : if True, prints extra logs; also a good flag for Streamlit mode.
        """
        self.min_sleep = min_sleep
        self.debug = debug
        self.user_weekly_events: dict[str, list[tuple[str, float]]] = {}
        self.last_raw_output: str | None = None
        self.last_clean_output: str | None = None

        if self.debug:
            print("AGENT CREATED (Phi-3.5, debug mode ON)")

    # ------------------------------------------------------------------
    # Debug logger
    # ------------------------------------------------------------------
    def log(self, *args):
        if self.debug:
            print(*args)

    # ------------------------------------------------------------------
    # Accept events as structured dict
    # ------------------------------------------------------------------
    def set_user_weekly_events(self, weekly_events: dict):
        """
        weekly_events format:
            {
                "Monday": [("Gym", 2.0), ("Work", 8.0), ...],
                ...
            }
        """
        self.user_weekly_events = weekly_events

    # ------------------------------------------------------------------
    # Accept raw text input (from Streamlit text_area)
    # ------------------------------------------------------------------
    def set_user_input_events(self, text: str):
        parsed = parse_user_events(text)
        self.user_weekly_events = parsed
        self.log("Parsed user events:", parsed)

    # ------------------------------------------------------------------
    # Prompt builder
    # ------------------------------------------------------------------
    def _build_prompt(self) -> str:
        if not self.user_weekly_events:
            # fallback example if nothing provided
            fallback = {
                "Monday": [("Gym", 2), ("Work", 8), ("Leisure", 2)],
                "Tuesday": [("Gym", 2), ("Project Trip", 3), ("Work", 8)],
            }
            events_dict = fallback
        else:
            events_dict = self.user_weekly_events

        event_text = "\n".join(
            f"{day}: " + ", ".join(f"{task} ({hours:.1f} hrs)" for task, hours in tasks)
            for day, tasks in events_dict.items()
        )

        prompt = f"""
You are an AI scheduling engine.

Your task is to generate a 7-day weekly schedule using the EXACT format below.

REQUIREMENTS:
- Output MUST contain all 7 days in this exact order:
  Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday.
- Every day must include at least {self.min_sleep} hours of Sleep.
- Sleep must ALWAYS be the final block of each day.
- Sleep may cross midnight (e.g., 21:00-05:00-Sleep is allowed).
- If sleep crosses midnight, record it under the day where the sleep begins.
- Activities must remain on their correct day.
- A day should be close to 24 total hours (it is okay if slightly under or over).
- NO explanations. NO examples. NO commentary.

OUTPUT FORMAT (USE THIS EXACTLY):

Monday:
    HH:MM-HH:MM-Activity
    HH:MM-HH:MM-Activity

Tuesday:
    HH:MM-HH:MM-Activity
    HH:MM-HH:MM-Activity

Wednesday:
    HH:MM-HH:MM-Activity
    HH:MM-HH:MM-Activity

Thursday:
    HH:MM-HH:MM-Activity
    HH:MM-HH:MM-Activity

Friday:
    HH:MM-HH:MM-Activity
    HH:MM-HH:MM-Activity

Saturday:
    HH:MM-HH:MM-Activity
    HH:MM-HH:MM-Activity

Sunday:
    HH:MM-HH:MM-Activity
    HH:MM-HH:MM-Activity

EVENT INPUT:
{event_text}

Now output ONLY the weekly schedule in the exact format above.
"""
        return prompt

    # ------------------------------------------------------------------
    # Clean model output: keep only day headers + valid time lines
    # ------------------------------------------------------------------
    def _clean_model_output(self, text: str) -> str:
        cleaned_lines: list[str] = []
        day_headers = {f"{d}:" for d in DAYS}

        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue

            if stripped in day_headers:
                cleaned_lines.append(stripped)
                continue

            # e.g., "08:00-10:00-Gym"
            if re.match(r"^\d{1,2}:\d{2}-\d{1,2}:\d{2}-", stripped):
                cleaned_lines.append(stripped)
                continue

        return "\n".join(cleaned_lines)

    # ------------------------------------------------------------------
    # Parse cleaned schedule into dict[day] -> [ "HH:MM-HH:MM-Activity", ... ]
    # ------------------------------------------------------------------
    def _parse_schedule(self, cleaned_text: str) -> dict:
        schedule = {day: [] for day in DAYS}
        current_day: str | None = None

        for line in cleaned_text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue

            if stripped in [f"{d}:" for d in DAYS]:
                current_day = stripped[:-1]
                continue

            if re.match(r"^\d{1,2}:\d{2}-\d{1,2}:\d{2}-", stripped) and current_day:
                schedule[current_day].append(stripped)

        return schedule

    # ------------------------------------------------------------------
    # Ensure Sleep is last each day
    # ------------------------------------------------------------------
    def _force_sleep_last(self, schedule: dict) -> dict:
        fixed = {}
        for day, entries in schedule.items():
            non_sleep = []
            sleep_blocks = []
            for e in entries:
                if "-Sleep" in e:
                    sleep_blocks.append(e)
                else:
                    non_sleep.append(e)
            fixed[day] = non_sleep + sleep_blocks
        return fixed

    # ------------------------------------------------------------------
    # Adjust last Sleep block so day is exactly 24h (if possible)
    # ------------------------------------------------------------------
    def _fix_day_to_24_hours(self, entries: list[str]) -> list[str]:
        """
        Preserves activity order and individual durations.
        Only adjusts the final Sleep block so that total = 24 hours.
        If no Sleep, adds one at the end to fill remaining time.
        """
        if not entries:
            return entries

        def parse_time(t: str) -> datetime:
            return datetime.strptime(t, "%H:%M")

        blocks = []
        total_hours = 0.0

        for e in entries:
            t1, t2, act = e.split("-", 2)
            start = parse_time(t1)
            end = parse_time(t2)

            # Allow crossing midnight
            if end <= start:
                end += timedelta(days=1)

            dur = (end - start).total_seconds() / 3600.0
            blocks.append((start, end, act, dur))
            total_hours += dur

        has_sleep = any("Sleep" in b[2] for b in blocks)

        # If no sleep exists, add a Sleep block at the end to fill up to 24 hours
        if not has_sleep:
            remaining = 24.0 - total_hours
            if remaining < 0:
                remaining = 0.0

            last_end = blocks[-1][1]
            new_end = last_end + timedelta(hours=remaining)
            blocks.append((last_end, new_end, "Sleep", remaining))
            return self._blocks_to_strings(blocks)

        # Sleep exists, assumed to be last (we enforce with _force_sleep_last)
        *non_sleep_blocks, last_block = blocks
        last_start, last_end, last_act, _ = last_block

        non_sleep_total = sum(b[3] for b in non_sleep_blocks)
        new_sleep_duration = 24.0 - non_sleep_total
        if new_sleep_duration < 0:
            # Overfull day – clamp sleep to zero rather than go negative
            new_sleep_duration = 0.0

        new_end = last_start + timedelta(hours=new_sleep_duration)
        fixed_blocks = non_sleep_blocks + [(last_start, new_end, last_act, new_sleep_duration)]

        return self._blocks_to_strings(fixed_blocks)

    def _blocks_to_strings(self, blocks):
        results = []
        for start, end, act, _ in blocks:
            s = start.strftime("%H:%M")
            e = end.strftime("%H:%M")
            results.append(f"{s}-{e}-{act}")
        return results

    # ------------------------------------------------------------------
    # Main planning pipeline
    # ------------------------------------------------------------------
    def plan_week(self) -> dict:
        prompt = self._build_prompt()
        raw = call_tinyllama(prompt)
        self.last_raw_output = raw
        self.log("\nRAW MODEL OUTPUT:\n", raw)

        cleaned = self._clean_model_output(raw)
        self.last_clean_output = cleaned
        self.log("\nCLEANED MODEL OUTPUT:\n", cleaned)

        schedule = self._parse_schedule(cleaned)

        # If totally empty, retry once with a stronger reminder
        if all(len(v) == 0 for v in schedule.values()):
            self.log("[WARNING] Empty schedule on first attempt. Retrying...")
            retry_prompt = prompt + "\nREMINDER: Output ONLY the schedule, no explanations.\n"
            raw2 = call_tinyllama(retry_prompt)
            self.last_raw_output = raw2
            cleaned2 = self._clean_model_output(raw2)
            self.last_clean_output = cleaned2
            schedule = self._parse_schedule(cleaned2)

        # Enforce Sleep last
        schedule = self._force_sleep_last(schedule)

        # Fix each day to exactly 24 hours using Sleep block
        final_schedule = {
            day: self._fix_day_to_24_hours(entries)
            for day, entries in schedule.items()
        }

        return final_schedule

    # ------------------------------------------------------------------
    # Public entrypoint
    # ------------------------------------------------------------------
    def run_weekly_cycle(self) -> dict:
        return self.plan_week()
