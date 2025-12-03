import streamlit as st

def run_dashboard(agent):
    st.title("Weekly AI Schedule")
    st.write("Your AI-generated weekly schedule:")

    schedule = agent.weekly_schedule

    for day, tasks in schedule.items():
        st.subheader(day)
        for task, hours in tasks:
            st.write(f"- {task}: {hours} hours")

    if st.button("Regenerate Week"):
        agent.regenerate()
        st.experimental_rerun()

    if st.button("Sync to Google Calendar"):
        agent.sync()
