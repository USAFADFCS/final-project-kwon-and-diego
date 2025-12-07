import re
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

DAYS = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

# --------------------------------------------------------------------
# Helper formatting functions
# --------------------------------------------------------------------
def normalize_day(day: str):
    d = day.strip().rstrip(":").lower()
    for real_day in DAYS:
        if real_day.lower() == d:
            return real_day
    return None

def parse_timeblock(line):
    """
    Example line:
    07:00-09:00-Work
    """
    match = re.match(r"\s*(\d\d:\d\d)-(\d\d:\d\d)-(.+)", line)
    if not match:
        return None
    start, end, act = match.groups()
    return start, end, act.strip()


# --------------------------------------------------------------------
# WeeklyAgent Class
# --------------------------------------------------------------------
class WeeklyAgent:
    def __init__(self, min_sleep=8):
        self.min_sleep = min_sleep
        self.user_weekly_events = {day: [] for day in DAYS}

        # --------------------------
        # Phi-3.5 Mini Instruct model
        # --------------------------
        print("Loading Phi-3.5 Mini Instruct...")
        self.tokenizer = AutoTokenizer.from_pretrained(
            "microsoft/Phi-3.5-mini-instruct"
        )
        self.model = AutoModelForCausalLM.from_pretrained(
            "microsoft/Phi-3.5-mini-instruct",
            torch_dtype=torch.float32,
            device_map="cpu"
        )
        print("Loaded successfully.")

    # ----------------------------------------------------------
    # Accept user events from StreamLit or main app
    # ----------------------------------------------------------
    def set_user_weekly_events(self, events: dict):
        """Events format: {"Monday":[("Work",8),("Gym",2)], ... }"""
        self.user_weekly_events = events

    # ----------------------------------------------------------
    # Build prompt that Phi can actually understand
    # ----------------------------------------------------------
    def build_prompt(self):
        event_lines = []
        for day, tasks in self.user_weekly_events.items():
            formatted = ", ".join(f"{name} ({hours} hrs)" for name, hours in tasks)
            if formatted == "":
                formatted = "None"
            event_lines.append(f"{day}: {formatted}")

        event_text = "\n".join(event_lines)

        PROMPT = f"""
You are an AI weekly scheduling assistant.

You MUST build a valid weekly schedule using ALL tasks listed below.
Any schedule missing tasks is INVALID.

RULES:
- Every listed task MUST appear on the correct day.
- Sleep must appear once and only once per day.
- Sleep may span midnight (example: 21:00-05:00).
- Total hours per day must NOT exceed 24.
- Format MUST match EXACTLY:

Monday:
    HH:MM-HH:MM-Activity
Tuesday:
    HH:MM-HH:MM-Activity
...
Sunday:
    HH:MM-HH:MM-Activity

WEEKLY TASKS:
{event_text}

Now generate the schedule.
"""
        return PROMPT

    # ----------------------------------------------------------
    # Clean the model output before parsing
    # ----------------------------------------------------------
    def clean_output(self, text: str):
        """
        Removes:
        - code fences
        - '[Answer]:' artifacts
        - Explanations
        - Duplicate intro text from model
        """
        # Remove code fences
        text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)

        # Remove [Answer]: artifacts
        text = text.replace("[Answer]:", "")

        # Remove any trailing explanation sections by cutting after last valid day
        last_day_pos = 0
        for day in DAYS:
            pos = text.lower().rfind(day.lower() + ":")
            if pos > last_day_pos:
                last_day_pos = pos

        text = text[last_day_pos:]  # keep only real schedule portion

        return text.strip()

    # ----------------------------------------------------------
    # Parse cleaned text into structured schedule
    # ----------------------------------------------------------
    def parse_schedule(self, text: str):
        schedule = {day: [] for day in DAYS}

        current_day = None

        for line in text.splitlines():
            line = line.strip()

            # Identify day headers
            if line.rstrip(":") in DAYS or normalize_day(line):
                current_day = normalize_day(line)
                continue

            if not current_day:
                continue

            # Parse time blocks
            tb = parse_timeblock(line)
            if tb:
                schedule[current_day].append(tb)

        return schedule

    # ----------------------------------------------------------
    # Enforce that all required tasks exist
    # ----------------------------------------------------------
    def enforce_task_preservation(self, parsed_schedule):
        missing = []

        for day, tasks in self.user_weekly_events.items():
            required = {t[0] for t in tasks}
            present = {act for (_,_,act) in parsed_schedule[day]}
            missing_for_day = required - present
            if missing_for_day:
                missing.append((day, list(missing_for_day)))

        return missing

    # ----------------------------------------------------------
    # Run Phi-3.5 and generate text
    # ----------------------------------------------------------
    def call_model(self, prompt: str):
        inputs = self.tokenizer(prompt, return_tensors="pt")
        output = self.model.generate(
            **inputs,
            max_new_tokens=900,
            temperature=0.4,
            do_sample=True,
        )
        return self.tokenizer.decode(output[0], skip_special_tokens=True)

    # ----------------------------------------------------------
    # MAIN PIPELINE
    # ----------------------------------------------------------
    def run_weekly_cycle(self):
        print("Running schedule generation...")

        # Step 1: Build prompt
        prompt = self.build_prompt()

        # Step 2: Call model
        raw_output = self.call_model(prompt)

        print("\nRAW MODEL OUTPUT:")
        print(raw_output[:5000])  # preview

        # Step 3: Clean output
        cleaned = self.clean_output(raw_output)

        # Step 4: Parse into structure
        parsed = self.parse_schedule(cleaned)

        # Step 5: Validate tasks
        missing = self.enforce_task_preservation(parsed)

        if missing:
            print("\n❌ Missing tasks detected:", missing)
        else:
            print("\n✅ All tasks preserved")

        # StreamLit needs the *cleaned text*
        return cleaned
