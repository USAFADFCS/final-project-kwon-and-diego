from src.agent.weekly_agent import WeeklyAgent

def main():
    print("WEEKLY AGENT STARTED")

    agent = WeeklyAgent(min_sleep=8)

    weekly_events = {
        "Monday":   [("Gym", 2), ("Work", 8), ("Leisure", 2)],
        "Tuesday":  [("Gym", 2), ("Project Trip", 3), ("Work", 8)],
        "Wednesday":[("Gym", 2), ("Work", 8), ("Leisure", 2)],
        "Thursday": [("Work", 8), ("Leisure", 2)],
        "Friday":   [("Work", 8), ("Gym", 2), ("Leisure", 3)],
        "Saturday": [("Work", 8), ("Gym", 2), ("Leisure", 3)],
        "Sunday":   [("Work", 8), ("Gym", 2), ("Leisure", 3)],
    }

    agent.set_user_weekly_events(weekly_events)
    agent.run_weekly_cycle()

if __name__ == "__main__":
    main()
