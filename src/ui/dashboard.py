# src/ui/dashboard.py

import streamlit as st

from src.agent.weekly_agent import WeeklyAgent


def main():
    st.title("Agentic AI Weekly Scheduler")

    st.markdown(
        """
Enter your weekly events below, one per line, in this format:

`Day HH:MM-HH:MM Activity`

Examples:
- `Monday 08:00-10:00 Gym`
- `Monday 10:00-18:00 Work`
- `Tuesday 09:00-12:00 Project Trip`
- `Friday 21:00-05:00 Sleep`
"""
    )

    default_text = """Monday 08:00-10:00 Gym
Monday 10:00-18:00 Work
Monday 18:00-20:00 Leisure
Tuesday 08:00-10:00 Gym
Tuesday 10:00-13:00 Project Trip
Tuesday 13:00-21:00 Work
Wednesday 08:00-10:00 Gym
Wednesday 10:00-18:00 Work
Wednesday 18:00-20:00 Leisure
Thursday 08:00-16:00 Work
Thursday 16:00-18:00 Leisure
Friday 08:00-10:00 Gym
Friday 10:00-18:00 Work
Friday 18:00-21:00 Leisure
Saturday 10:00-18:00 Work
Saturday 18:00-21:00 Leisure
Sunday 10:00-18:00 Work
Sunday 18:00-21:00 Leisure
"""

    user_text = st.text_area("Weekly Events", value=default_text, height=250)

    if st.button("Generate Schedule"):
        agent = WeeklyAgent(min_sleep=8, debug=True)
        agent.set_user_input_events(user_text)
        schedule = agent.run_weekly_cycle()

        st.subheader("Generated Schedule")
        for day, entries in schedule.items():
            st.markdown(f"### {day}")
            if not entries:
                st.write("_No schedule parsed_")
            else:
                for e in entries:
                    st.write(f"- {e}")


if __name__ == "__main__":
    main()
