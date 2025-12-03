# src/sleep_tracker.py

class SleepTracker:
    def __init__(self, minimum_hours=8):
        self.minimum_hours = minimum_hours
        self.sleep_log = {}  # e.g., {"Monday": 7, "Tuesday": 8}

    def log_sleep(self, day: str, hours: float):
        """Record how many hours were slept on a given day."""
        self.sleep_log[day] = hours

    def get_sleep(self, day: str) -> float:
        """Get recorded sleep hours for a day (0 if missing)."""
        return self.sleep_log.get(day, 0.0)

    def needs_more_sleep(self, day: str) -> bool:
        """Check if the day has below minimum sleep."""
        return self.get_sleep(day) < self.minimum_hours

    def required_additional_sleep(self, day: str) -> float:
        """Compute how many more hours are needed."""
        return max(0.0, self.minimum_hours - self.get_sleep(day))
