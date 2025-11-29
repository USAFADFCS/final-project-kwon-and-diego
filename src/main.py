from src.schedule_logic import ScheduleAgent

def main():
    events = [
        ("Monday", "Study ML", 3),
        ("Monday", "Gym", 1),
        ("Tuesday", "Project Work", 4),
    ]

    agent = ScheduleAgent()
    schedule = agent.generate_schedule(events)

    print("\nGenerated Schedule:\n")
    print(schedule)

if __name__ == "__main__":
    main()
