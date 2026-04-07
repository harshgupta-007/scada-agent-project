import streamlit as st
import pandas as pd
import asyncio
import concurrent.futures

from utils.data_loader import load_scada_data, get_date_range, filter_data_by_date
from utils.charts import (
    plot_demand_trend, plot_demand_stats, plot_regional_distribution,
    plot_generation_mix, plot_intraday_curve, generate_intraday_insights,
    generate_regional_insights, plot_regional_contribution,
    plot_variability, generate_variability_insights,
    plot_ramp_trend, generate_ramp_insights,
    plot_demand_with_anomalies, generate_anomaly_insights,
    plot_intraday_with_anomalies, generate_intraday_anomaly_insights
)
from utils.insights import generate_master_insights
from utils.ai_insights import build_intraday_summary, build_regional_summary

from google.genai import types
from scada_summary_agent.agent import root_agent
from google.adk.sessions import DatabaseSessionService
from google.adk.runners import Runner


# ─────────────────────────────────────────────
# SAFE ASYNC HANDLER (FINAL FIX)
# ─────────────────────────────────────────────
def run_agent_sync(runner, session_id, message):

    async def _run():
        events = []
        async for event in runner.run_async(
            user_id="streamlit_user",
            session_id=session_id,
            new_message=message,
        ):
            events.append(event)
        return events

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_running():
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(lambda: asyncio.run(_run()))
            return future.result()
    else:
        return loop.run_until_complete(_run())


# ─────────────────────────────────────────────
# INIT AGENT
# ─────────────────────────────────────────────
def init_agent_system():
    if "agent_runner" not in st.session_state:

        session_service = DatabaseSessionService(
            "sqlite+aiosqlite:///scada_streamlit_session.db"
        )

        runner = Runner(
            app_name="scada_summary_agent",
            agent=root_agent,
            session_service=session_service,
        )

        async def create_session():
            existing_session = await session_service.get_session(
                app_name="scada_summary_agent",
                user_id="streamlit_user",
                session_id="streamlit_demo_session",
            )
            if not existing_session:
                await session_service.create_session(
                    app_name="scada_summary_agent",
                    user_id="streamlit_user",
                    session_id="streamlit_demo_session",
                )

        try:
            asyncio.run(create_session())
        except RuntimeError:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(create_session())

        st.session_state["agent_runner"] = runner
        st.session_state["chat_session_id"] = "streamlit_demo_session"


# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(page_title="SCADA Dashboard", layout="wide")


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
def build_sidebar():
    st.sidebar.subheader("Navigation")

    page = st.sidebar.radio(
        "Select View",
        ["Overview", "Regional Analysis", "Generation Mix",
         "Intraday Profile", "Agent Chat"],
        label_visibility="collapsed",
    )

    df = load_scada_data()

    if not df.empty:
        min_date, max_date = get_date_range(df)

        start_date, end_date = st.sidebar.date_input(
            "Date Range",
            value=(min_date.date(), max_date.date()),
        )

        st.session_state["filtered_df"] = filter_data_by_date(df, start_date, end_date)

    return page


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    init_agent_system()

    st.title("⚡ SCADA Intelligence Dashboard")

    df = load_scada_data()
    if df.empty:
        st.error("No data found")
        return

    page = build_sidebar()

    if page == "Overview":
        render_overview()
    elif page == "Regional Analysis":
        render_regional()
    elif page == "Generation Mix":
        render_generation()
    elif page == "Intraday Profile":
        render_intraday()
    elif page == "Agent Chat":
        render_chat()


# ─────────────────────────────────────────────
# OVERVIEW
# ─────────────────────────────────────────────
def render_overview():
    df = st.session_state.get("filtered_df")

    if df is None or df.empty:
        st.info("No data")
        return

    col1, col2 = st.columns(2)

    with col1:
        st.plotly_chart(plot_demand_trend(df), width="stretch")

    with col2:
        st.plotly_chart(plot_demand_stats(df), width="stretch")

    st.subheader("Insights")
    for i in generate_master_insights(df):
        st.success(i)

    st.subheader("Anomaly Detection")
    st.plotly_chart(plot_demand_with_anomalies(df), width="stretch")
    st.warning(generate_anomaly_insights(df))


# ─────────────────────────────────────────────
# REGIONAL
# ─────────────────────────────────────────────
def render_regional():
    df = st.session_state.get("filtered_df")

    if df is None or df.empty:
        return

    st.plotly_chart(plot_regional_contribution(df), width="stretch")
    st.plotly_chart(plot_variability(df), width="stretch")

    st.success(generate_regional_insights(df))
    st.warning(generate_variability_insights(df))

    if st.button("Explain Regional Behavior"):
        runner = st.session_state["agent_runner"]
        session_id = st.session_state["chat_session_id"]

        summary = build_regional_summary(df)
        message = types.Content(role="user", parts=[types.Part(text=summary)])

        try:
            events = run_agent_sync(runner, session_id, message)

            response = ""
            for e in reversed(events):
                if getattr(e, "content", None):
                    parts = [p.text for p in e.content.parts if hasattr(p, "text")]
                    if parts:
                        response = "".join(parts)
                        break

            st.info(response)

        except Exception as e:
            st.error(f"AI Error: {e}")


# ─────────────────────────────────────────────
# GENERATION
# ─────────────────────────────────────────────
def render_generation():
    df = st.session_state.get("filtered_df")
    if df is not None:
        st.plotly_chart(plot_generation_mix(df), width="stretch")


# ─────────────────────────────────────────────
# INTRADAY
# ─────────────────────────────────────────────
def render_intraday():
    df = load_scada_data()

    min_date, _ = get_date_range(df)

    selected_date = st.date_input("Select Date", min_date.date())

    df_intraday = df[df["date"].dt.date == selected_date]

    if df_intraday.empty:
        return

    st.plotly_chart(plot_intraday_curve(df_intraday), width="stretch")
    st.success(generate_intraday_insights(df_intraday))

    if st.button("Explain Intraday Pattern"):
        runner = st.session_state["agent_runner"]
        session_id = st.session_state["chat_session_id"]

        summary = build_intraday_summary(df_intraday)
        message = types.Content(role="user", parts=[types.Part(text=summary)])

        try:
            events = run_agent_sync(runner, session_id, message)

            response = ""
            for e in reversed(events):
                if getattr(e, "content", None):
                    parts = [p.text for p in e.content.parts if hasattr(p, "text")]
                    if parts:
                        response = "".join(parts)
                        break

            st.info(response)

        except Exception as e:
            st.error(f"AI Error: {e}")


# ─────────────────────────────────────────────
# CHAT
# ─────────────────────────────────────────────
def render_chat():
    st.header("AI Assistant")

    runner = st.session_state["agent_runner"]
    session_id = st.session_state["chat_session_id"]

    if prompt := st.chat_input("Ask something..."):

        msg = types.Content(role="user", parts=[types.Part(text=prompt)])

        try:
            events = run_agent_sync(runner, session_id, msg)

            response = ""
            for e in reversed(events):
                if getattr(e, "content", None):
                    parts = [p.text for p in e.content.parts if hasattr(p, "text")]
                    if parts:
                        response = "".join(parts)
                        break

            st.write(response)

        except Exception as e:
            st.error(str(e))


# ─────────────────────────────────────────────
if __name__ == "__main__":
    main()
