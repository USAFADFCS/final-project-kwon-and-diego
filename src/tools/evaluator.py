# src/tools/evaluator.py
"""
Evaluator module for WeeklyAgent outputs.
Generates reproducible quantitative metrics for your report.
"""

import re
from datetime import datetime


DAYS = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]


# -----------------------------------------------------------
# Helper parsers
# -----------------------------------------------------------

def parse_time_block(block):
    """
    Input: '07:00-09:00-Gym'
    Output: start (datetime.time), end (datetime.time), label (string)
    """

    try:
        times, label = block.split("-", 2)[0:2], block.split("-", 2)[2]
        start_str, end_str = times[0], times[1]

        start = datetime.strptime(start_str, "%H:%M")
        end   = datetime.strptime(end_str, "%H:%M")

        return start, end, label.strip()
    except Exception:
        return None, None, None


def extract_day_blocks(schedule_text):
    """
    Returns dictionary:
    {
        "Monday": ["07:00-09:00-Gym", "09:00-17:00-Work", ...],
        ...
    }
    """
    lines = schedule_text.strip().splitlines()
    result = {}
    current_day = None

    for line in lines:
        line = line.strip()

        if line.replace(":", "") in DAYS:
            current_day = line.replace(":", "")
            result[current_day] = []
            continue

        if current_day and line and "-" in line:
            result[current_day].append(line)

    return result


# -----------------------------------------------------------
#  METRIC CALCULATION FUNCTIONS
# -----------------------------------------------------------

def metric_day_completeness(schedule_text):
    parsed = extract_day_blocks(schedule_text)
    missing = [d for d in DAYS if d not in parsed]
    return len(missing) == 0, missing


def metric_sleep_hours(schedule_text, min_sleep=8):
    parsed = extract_day_blocks(schedule_text)
    violations = []

    for day, blocks in parsed.items():
        for blk in blocks:
            if "-Sleep" in blk:
                start, end, _ = parse_time_block(blk)
                if start is None: continue

                # handle rollover sleep (21:00 - 05:00)
                duration = (end - start).seconds / 3600.0
                if duration < 0:
                    duration += 24

                if duration < min_sleep:
                    violations.append((day, duration))

    return len(violations) == 0, violations


def metric_max_24_hours(schedule_text):
    parsed = extract_day_blocks(schedule_text)
    violations = []

    for day, blocks in parsed.items():
        total = 0
        for blk in blocks:
            start, end, _ = parse_time_block(blk)
            if not start: continue

            duration = (end - start).seconds / 3600.0
            if duration < 0:
                duration += 24

            total += duration

        if total > 24:
            violations.append((day, total))

    return len(violations) == 0, violations


def metric_activity_preservation(schedule_text, user_events):
    """
    Checks whether all required user tasks appear at least once.
    user_events format:
    { "Monday": [("Gym",2), ("Work",8)], ... }
    """
    parsed = extract_day_blocks(schedule_text)
    missing = []

    for day, task_list in user_events.items():
        for task, _ in task_list:
            found = any(task in blk for blk in parsed.get(day, []))
            if not found:
                missing.append((day, task))

    return len(missing) == 0, missing


# -----------------------------------------------------------
#  MAIN EVALUATION FUNCTION
# -----------------------------------------------------------

def evaluate_schedule(schedule_text, user_events, min_sleep=8):
    """Run all metrics and return a dictionary of results."""

    results = {}

    # Day completeness
    ok, missing = metric_day_completeness(schedule_text)
    results["day_completeness"] = {"ok": ok, "missing_days": missing}

    # Sleep check
    ok, violations = metric_sleep_hours(schedule_text, min_sleep)
    results["sleep_requirement"] = {"ok": ok, "violations": violations}

    # Total hours
    ok, violations = metric_max_24_hours(schedule_text)
    results["max_24_hours"] = {"ok": ok, "violations": violations}

    # Tasks preserved
    ok, missing = metric_activity_preservation(schedule_text, user_events)
    results["task_preservation"] = {"ok": ok, "missing_tasks": missing}

    return results
