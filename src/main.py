# src/main.py

from src.agent.weekly_agent import WeeklyAgent


def main():
    print("WEEKLY AGENT (CLI TEST)")

    # Simple built-in events if you run from CLI
    events_text = """Monday 08:00-10:00 Gym
Monday 10:00-18:00 Work
Monday 18:00-20:00 Leisure
Tuesday 08:00-10:00 Gym
Tuesday 10:00-13:00 Project Trip
Tuesday 13:00-21:00 Work"""

    agent = WeeklyAgent(min_sleep=8, debug=True)
    agent.set_user_input_events(events_text)
    schedule = agent.run_weekly_cycle()

    print("\nFINAL WEEKLY SCHEDULE:")
    for day, entries in schedule.items():
        print(day + ":")
        for e in entries:
            print("  " + e)


if __name__ == "__main__":
    main()
