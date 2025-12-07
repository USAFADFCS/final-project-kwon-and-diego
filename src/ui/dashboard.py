# src/ui/dashboard.py

import streamlit as st
import plotly.express as px
import pandas as pd

from src.agent.fair_weekly_agent import FairWeeklyAgent
from src.tools.evaluator import evaluate_schedule

DAYS = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]


def parse_blocks(schedule_text):
    """
    Parses lines like 'HH:MM-HH:MM-Activity' under each day header
    into a list of dicts for visualization.
    """
    rows = []
    current_day = None

    for ln in schedule_text.splitlines():
        raw = ln.strip()
        if not raw:
            continue

        # Detect day header
        if raw.rstrip(":") in DAYS:
            current_day = raw.rstrip(":")
            continue

        # Detect blocks: we expect them indented, e.g. '    21:00-05:00-Sleep'
        if current_day and "-" in raw and ":" in raw:
            try:
                # Expect exactly: start-end-activity
                start, end, activity = raw.split("-", 2)
                start = start.strip()
                end = end.strip()
                activity = activity.strip()
            except ValueError:
                # Not in expected format; skip
                continue

            rows.append({
                "Day": current_day,
                "Start": start,
                "End": end,
                "Activity": activity,
            })

    return rows


def main():
    st.title("📅 AI Weekly Schedule Generator (FAIR-LLM + Phi-3.5)")

    if "events" not in st.session_state:
        st.session_state.events = {d: [] for d in DAYS}

    # ------------------------------------------------
    # Event input
    # ------------------------------------------------
    st.subheader("➕ Add an Event")

    c1, c2, c3 = st.columns([1, 2, 1])

    with c1:
        day = st.selectbox("Day", DAYS)
    with c2:
        activity = st.text_input("Activity")
    with c3:
        duration = st.number_input("Duration (hours)", 0.5, 16.0, 1.0, 0.5)

    if st.button("Add Event"):
        if activity.strip():
            st.session_state.events[day].append((activity, duration))
            st.success(f"Added {activity} ({duration} hrs) to {day}")
        else:
            st.error("Activity name is required.")

    st.subheader("🧾 Current Weekly Events")
    st.json(st.session_state.events)

    st.markdown("---")

    # ------------------------------------------------
    # Generate schedule
    # ------------------------------------------------
    if st.button("Generate AI Schedule"):
        st.info("⏳ Running FAIR Weekly Agent...")

        agent = FairWeeklyAgent(min_sleep=8)
        agent.set_user_weekly_events(st.session_state.events)
        schedule_text = agent.run_weekly_cycle()

        st.subheader("📄 Generated Schedule")
        st.text(schedule_text)

        # --------------------------
        # Evaluation Metrics
        # --------------------------
        st.subheader("📈 Evaluation Metrics")
        metrics = evaluate_schedule(schedule_text, st.session_state.events, min_sleep=8)

        for name, info in metrics.items():
            st.markdown(f"**{name.replace('_', ' ').title()}:**")
            st.json(info)

        # --------------------------
        # Timeline visualization
        # --------------------------
        st.subheader("📊 Weekly Timeline Visualization")

        blocks = parse_blocks(schedule_text)
        if not blocks:
            st.warning("No schedule blocks could be parsed.")
        else:
            df = pd.DataFrame(blocks)

            # Convert to datetime for timeline axis
            df["Start_dt"] = pd.to_datetime(df["Start"], format="%H:%M")
            df["End_dt"] = pd.to_datetime(df["End"], format="%H:%M")

            fig = px.timeline(
                df,
                x_start="Start_dt",
                x_end="End_dt",
                y="Day",
                color="Activity",
                title="Weekly Schedule Timeline",
            )
            fig.update_yaxes(autorange="reversed")
            fig.update_layout(
                height=500,
                margin=dict(l=20, r=20, t=40, b=20)
            )
            st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()
