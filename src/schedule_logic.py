# src/schedule_agent.py
from src.tinyllama import call_tinyllama

class ScheduleAgent:
    def __init__(self):
        pass

    def generate_schedule(self, events):
        event_text = "\n".join(
            f"- {d}: {task} ({hrs} hrs)" for d, task, hrs in events
        )

        prompt = f"""
You are a helpful scheduling assistant.
Build an optimized schedule based on these tasks:

{event_text}

Return the schedule in a clear daily list format.
"""
        return call_tinyllama(prompt)
