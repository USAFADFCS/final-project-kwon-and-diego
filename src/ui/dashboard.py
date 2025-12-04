# src/ui/dashboard.py
import streamlit as st
from src.agent.weekly_agent import WeeklyAgent

def main():
    st.title("Weekly AI Schedule (Local Model)")

    if st.button("Generate Weekly Schedule"):
        agent = WeeklyAgent(min_sleep=8)

        weekly_events = {
            "Monday": [("Gym", 2), ("Work", 8), ("Leisure", 2)],
            "Tuesday": [("Gym", 2), ("Project Trip", 3), ("Work", 8)],
            "Wednesday": [("Gym", 2), ("Work", 8), ("Leisure", 2)],
            "Thursday": [("Work", 8), ("Leisure", 2)],
            "Friday": [("Work", 8), ("Gym", 2), ("Leisure", 3)],
            "Saturday": [("Work", 8), ("Gym", 2), ("Leisure", 3)],
            "Sunday": [("Work", 8), ("Gym", 2), ("Leisure", 3)],
        }

        agent.set_user_weekly_events(weekly_events)
        schedule = agent.run_weekly_cycle()

        st.subheader("Generated Schedule")
        for day, entries in schedule.items():
            st.markdown(f"### {day}")
            if not entries:
                st.write("_No schedule parsed_")
            for e in entries:
                st.write(f"- {e}")

if __name__ == "__main__":
    main()
