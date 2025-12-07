# src/agent/fair_weekly_agent.py

import asyncio
import re
from fairlib import (
    SimpleAgent,
    HuggingFaceAdapter,
    SimpleReActPlanner,
    ToolRegistry,
    ToolExecutor,
    RoleDefinition,
    WorkingMemory,
    Message,
)

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAY_HEADERS = {d + ":" for d in DAYS}


class FairWeeklyAgent:
    def __init__(self, min_sleep: int = 8):
        self.min_sleep = min_sleep
        self.weekly_events = {d: [] for d in DAYS}

        # --------------------------
        # 1. Build LLM brain
        # --------------------------
        self.llm = HuggingFaceAdapter("microsoft/Phi-3.5-mini-instruct")

        # --------------------------
        # 2. Build planner + agent
        # --------------------------
        self.registry = ToolRegistry()
        self.executor = ToolExecutor(self.registry)
        self.memory = WorkingMemory()

        self.planner = SimpleReActPlanner(self.llm, self.registry)
        self.planner.prompt_builder.role_definition = RoleDefinition(
            "You are an AI weekly scheduling assistant. "
            "You take structured events and output a formatted weekly schedule in strict format."
        )

        self.agent = SimpleAgent(
            llm=self.llm,
            planner=self.planner,
            tool_executor=self.executor,
            memory=self.memory,
            max_steps=5,
        )

    # --------------------------------------------------------
    # User-provided events
    # --------------------------------------------------------
    def set_user_weekly_events(self, events_dict):
        """
        events_dict = {
            'Monday': [('Work', 8), ('Leisure', 3)],
            ...
        }
        """
        self.weekly_events = events_dict

    # --------------------------------------------------------
    # Prompt Builder
    # --------------------------------------------------------
    def _build_prompt(self) -> str:
        event_lines = []
        for day, events in self.weekly_events.items():
            if events:
                ev = ", ".join(f"{task} ({hrs} hrs)" for task, hrs in events)
                event_lines.append(f"{day}: {ev}")
            else:
                event_lines.append(f"{day}: (none)")

        event_block = "\n".join(event_lines)

        prompt = f"""
You MUST output a valid weekly schedule.

RULES:
- Output format must be EXACT.
- Each day MUST appear once and only once.
- Activities must be in HH:MM-HH:MM-Activity format (24-hr).
- Every day must include ≥ {self.min_sleep} hours of sleep.
- Sleep may cross midnight (e.g., 21:00-05:00).
- Tasks must remain on the correct day.
- DO NOT invent new tasks not listed.
- If times are unspecified, you assign reasonable times but obey constraints.
- DO NOT output explanations, examples, or notes.

User Events:
{event_block}

FORMAT TO FOLLOW EXACTLY:

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

ONLY output the schedule in this format.
"""
        return prompt.strip()

    # --------------------------------------------------------
    # Cleaner — keep only days + blocks of form HH:MM-HH:MM-Activity
    # --------------------------------------------------------
    def _clean_output(self, text: str) -> str:
        lines = text.splitlines()
        out = []
        block_re = re.compile(r"^\d\d:\d\d-\d\d:\d\d-")

        for ln in lines:
            ln = ln.strip()
            if not ln:
                continue
            # Day header
            if ln in DAY_HEADERS:
                out.append(ln)
                continue
            # Time block
            if block_re.match(ln):
                out.append(ln)

        return "\n".join(out)

    # --------------------------------------------------------
    # Fixer — ensure each day appears once and has exactly one Sleep block
    # --------------------------------------------------------
    def _fix_schedule(self, text: str) -> str:
        lines = text.splitlines()
        final_lines = []
        seen_days = set()

        current_day = None
        blocks = []
        block_re = re.compile(r"^\d\d:\d\d-\d\d:\d\d-")

        def flush_day():
            nonlocal current_day, blocks, final_lines
            if current_day is None:
                return

            # Remove any model-provided sleep blocks
            non_sleep_blocks = [b for b in blocks if "sleep" not in b.lower()]

            # Append our single canonical sleep block at the end
            non_sleep_blocks.append("21:00-05:00-Sleep")

            final_lines.append(f"{current_day}:")
            for b in non_sleep_blocks:
                final_lines.append(f"    {b}")

        for ln in lines:
            ln = ln.strip()
            if not ln:
                continue

            if ln in DAY_HEADERS:
                # Flush previous
                if current_day is not None:
                    flush_day()

                day_name = ln[:-1]
                if day_name in seen_days:
                    # skip duplicate day header
                    current_day = day_name
                    blocks = []
                    continue

                current_day = day_name
                seen_days.add(day_name)
                blocks = []
                continue

            # Block line
            if block_re.match(ln) and current_day is not None:
                blocks.append(ln)

        # Flush last day
        flush_day()

        # Fill in missing days with just sleep
        for day in DAYS:
            if day not in seen_days:
                final_lines.append(f"{day}:")
                final_lines.append("    21:00-05:00-Sleep")

        return "\n".join(final_lines)

    # --------------------------------------------------------
    # Main execution
    # --------------------------------------------------------
    def run_weekly_cycle(self) -> str:
        prompt = self._build_prompt()
        messages = [Message(role="user", content=prompt)]

        # SimpleAgent is async → use asyncio.run on .arun(...)
        result = asyncio.run(self.agent.arun(messages))

        cleaned = self._clean_output(result)
        fixed = self._fix_schedule(cleaned)
        return fixed
