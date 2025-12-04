# src/tools/sleep_tracker.py

class SleepTracker:
    def __init__(self, minimum_hours=8):
        self.minimum_hours = minimum_hours
        self.sleep_log = {}

    def record_sleep(self, day, hours):
        self.sleep_log[day] = hours

    def get_sleep(self, day):
        return self.sleep_log.get(day, 0)
