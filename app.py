import streamlit as st
import nest_asyncio
nest_asyncio.apply()
import pandas as pd
from utils.data_loader import load_scada_data, get_date_range, filter_data_by_date
from utils.charts import plot_demand_trend, plot_demand_stats, plot_regional_distribution, plot_generation_mix, plot_intraday_profile,plot_regional_trend,plot_intraday_curve,generate_intraday_insights
from utils.charts import generate_regional_insights,plot_regional_contribution, plot_variability , generate_variability_insights
from utils.charts import plot_ramp_trend,generate_ramp_insights,plot_demand_with_anomalies,generate_anomaly_insights,plot_intraday_with_anomalies,generate_intraday_anomaly_insights
from utils.insights import generate_master_insights
from utils.ai_insights import build_intraday_summary, build_regional_summary
import asyncio
from google.genai import types
from scada_summary_agent.agent import root_agent
from google.adk.sessions import DatabaseSessionService
from google.adk.runners import Runner


# ─────────────────────────────────────────────
# Async helper — always runs in a fresh loop
# ─────────────────────────────────────────────
def run_agent_sync(runner, session_id, message):
    """Run the ADK runner in a brand-new event loop to avoid sniffio conflicts."""
    async def _run():
        events = []
        async for event in runner.run_async(
            user_id="streamlit_user",
            session_id=session_id,
            new_message=message,
        ):
            events.append(event)
        return events

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_run())
    finally:
        # Gracefully shut down pending tasks before closing
        try:
            pending = asyncio.all_tasks(loop)
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception:
            pass
        loop.close()


# ─────────────────────────────────────────────
# Agent initialisation (once per session)
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

        st.session_state["agent_runner"] = runner
        st.session_state["chat_session_id"] = "streamlit_demo_session"

        nest_asyncio.apply()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            existing_session = loop.run_until_complete(
                session_service.get_session(
                    app_name="scada_summary_agent",
                    user_id="streamlit_user",
                    session_id="streamlit_demo_session",
                )
            )
            if not existing_session:
                loop.run_until_complete(
                    session_service.create_session(
                        app_name="scada_summary_agent",
                        user_id="streamlit_user",
                        session_id="streamlit_demo_session",
                    )
                )
        finally:
            # Don't close this loop — nest_asyncio keeps it alive for later use
            pass


# ─────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="SCADA Demand Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)


def build_sidebar():
    st.sidebar.image("Images/scada_architecture.png", width="stretch")
    st.sidebar.markdown("---")

    st.sidebar.subheader("Navigation")
    page = st.sidebar.radio(
        "Select View",
        ["Overview", "Regional Analysis", "Generation Mix", "Intraday Profile", "Weather Correlation", "Agent Chat"],
        label_visibility="collapsed",
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("Global Filters")
    df = load_scada_data()

    if not df.empty:
        min_date, max_date = get_date_range(df)

        date_input = st.sidebar.date_input(
            "Select Date Range",
            value=(min_date.date(), max_date.date()),
            min_value=min_date.date(),
            max_value=max_date.date(),
        )

        if isinstance(date_input, (tuple, list)):
            if len(date_input) == 2:
                start_date, end_date = date_input
            elif len(date_input) == 1:
                start_date = end_date = date_input[0]
            else:
                start_date = end_date = min_date.date()
        else:
            start_date = end_date = date_input

        if start_date > end_date:
            st.sidebar.error("Start date cannot be after end date")
            return page

        st.sidebar.markdown("---")
        st.sidebar.subheader("Data Exclusion Filters")
        exclude_weekends = st.sidebar.checkbox("Exclude Weekends (Sat/Sun)", value=False)
        exclude_holidays = st.sidebar.checkbox("Exclude Holidays", value=False)
        exclude_events = st.sidebar.checkbox("Exclude Special Events", value=False)

        st.session_state["exclude_weekends"] = exclude_weekends
        st.session_state["exclude_holidays"] = exclude_holidays
        st.session_state["exclude_events"] = exclude_events

        temp_df = filter_data_by_date(df, start_date, end_date)

        if exclude_weekends and "is_weekend" in temp_df.columns:
            temp_df = temp_df[~temp_df["is_weekend"]]
        if exclude_holidays and "is_holiday" in temp_df.columns:
            temp_df = temp_df[~temp_df["is_holiday"]]
        if exclude_events and "is_special_event" in temp_df.columns:
            temp_df = temp_df[~temp_df["is_special_event"]]

        st.session_state["filtered_df"] = temp_df
        st.session_state["start_date"] = start_date
        st.session_state["end_date"] = end_date
    else:
        st.sidebar.warning("Unable to initialize filters. Data not loaded.")

    st.sidebar.markdown("---")
    st.sidebar.caption("Powered by Google Gemini 🤖")

    return page


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
def main():
    init_agent_system()
    st.title("SCADA System Intelligence Dashboard ⚡")
    st.markdown("Monitor, analyze, and query power system demand data.")

    df = load_scada_data()
    if df.empty:
        st.error("Application cannot start without SCADA data.")
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
        render_agent_chat()
    elif page == "Weather Correlation":
        render_weather_correlation()


# ─────────────────────────────────────────────
# Pages
# ─────────────────────────────────────────────
def render_overview():
    st.header("System Overview")

    if "filtered_df" in st.session_state and not st.session_state["filtered_df"].empty:
        df = st.session_state["filtered_df"]
        from utils.kpi_cards import render_kpi_cards
        render_kpi_cards(df)

        col1, col2 = st.columns(2)
        with col1:
            fig1 = plot_demand_trend(df)
            if fig1:
                st.plotly_chart(fig1, width="stretch")
        with col2:
            fig2 = plot_demand_stats(df)
            if fig2:
                st.plotly_chart(fig2, width="stretch")

        insights = generate_master_insights(df)
        st.subheader("🔍 Key System Insights")
        for insight in insights:
            st.success(insight)

        st.subheader("Anomaly Detection 🚨")
        fig_anomaly = plot_demand_with_anomalies(df)
        if fig_anomaly:
            st.plotly_chart(fig_anomaly, width="stretch")
        st.warning(generate_anomaly_insights(df))
    else:
        st.info("Please select a valid date range containing data.")


def render_regional():
    st.header("Regional Demand Intelligence 🌍")

    if "filtered_df" not in st.session_state or st.session_state["filtered_df"].empty:
        st.info("Please select a valid date range containing data.")
        return

    df = st.session_state["filtered_df"]

    st.subheader("Regional Contribution (%)")
    fig_pct = plot_regional_contribution(df)
    if fig_pct:
        st.plotly_chart(fig_pct, width="stretch")

    st.subheader("Regional Demand Trend")
    fig_trend = plot_regional_trend(df)
    if fig_trend:
        st.plotly_chart(fig_trend, width="stretch")

    st.subheader("Demand Distribution")
    fig_box = plot_regional_distribution(df)
    if fig_box:
        st.plotly_chart(fig_box, width="stretch")

    st.success(generate_regional_insights(df))

    st.subheader("Demand Variability & Risk Analysis")
    fig_var = plot_variability(df)
    if fig_var:
        st.plotly_chart(fig_var, width="stretch")
    st.warning(generate_variability_insights(df))

    st.subheader("AI Explanation 🤖")
    if st.button("Explain Regional Behavior"):
        runner = st.session_state["agent_runner"]
        session_id = st.session_state["chat_session_id"]
        summary = build_regional_summary(df)

        with st.spinner("Analyzing regional demand... 🌍"):
            try:
                prompt = f"""
You are an expert power system analyst.

Analyze the following regional SCADA data:

{summary}

Explain:
1. Which region dominates and why
2. Whether demand is balanced or skewed
3. Possible reasons (urbanization, industry, weather)
4. Operational insights for load management
"""
                message = types.Content(role="user", parts=[types.Part(text=prompt)])
                events = run_agent_sync(runner, session_id, message)

                response = ""
                for event in reversed(events):
                    if getattr(event, "content", None):
                        parts = [p.text for p in event.content.parts if hasattr(p, "text")]
                        if parts:
                            response = "".join(parts)
                            break

                st.info(response)
            except Exception as e:
                st.error(f"AI Error: {e}")


def render_generation():
    st.header("Generation Mix")
    st.markdown("View the proportion of energy generated from Thermal, Hydel, and Renewable sources.")

    if "filtered_df" in st.session_state and not st.session_state["filtered_df"].empty:
        fig = plot_generation_mix(st.session_state["filtered_df"])
        if fig:
            st.plotly_chart(fig, width="stretch")
    else:
        st.info("Please select a valid date range containing data.")


def render_intraday():
    st.header("Intraday Demand Intelligence ⚡")

    df = load_scada_data()
    if df.empty:
        st.error("Data not available")
        return

    min_date, max_date = get_date_range(df)
    selected_date = st.date_input(
        "Select Date for Intraday Analysis",
        value=min_date.date(),
        min_value=min_date.date(),
        max_value=max_date.date(),
    )
    st.info(f"Showing intraday profile for {selected_date}")

    df_intraday = df[df["date"].dt.date == selected_date]
    if df_intraday.empty:
        st.warning("No data available for selected date")
        return

    fig = plot_intraday_curve(df_intraday)
    if fig:
        st.plotly_chart(fig, width="stretch")
    st.success(generate_intraday_insights(df_intraday))

    st.subheader("Ramp Analysis ⚡")
    fig_ramp = plot_ramp_trend(df_intraday)
    if fig_ramp:
        st.plotly_chart(fig_ramp, width="stretch")
    st.warning(generate_ramp_insights(df_intraday))

    st.subheader("Intraday Anomaly Detection 🚨")
    fig_anom = plot_intraday_with_anomalies(df_intraday)
    if fig_anom:
        st.plotly_chart(fig_anom, width="stretch")
    st.warning(generate_intraday_anomaly_insights(df_intraday))

    st.subheader("AI Explanation 🤖")
    if st.button("Explain Intraday Pattern"):
        runner = st.session_state["agent_runner"]
        session_id = st.session_state["chat_session_id"]
        summary = build_intraday_summary(df_intraday)

        with st.spinner("Analyzing demand pattern... ⚡"):
            try:
                prompt = f"""
You are an expert power system analyst.

Analyze the following intraday SCADA data:

{summary}

Explain:
1. Why peak demand occurred at that time
2. Daily demand pattern
3. Operational insights for DISCOM
"""
                message = types.Content(role="user", parts=[types.Part(text=prompt)])
                events = run_agent_sync(runner, session_id, message)

                response = ""
                for event in reversed(events):
                    if getattr(event, "content", None):
                        parts = [p.text for p in event.content.parts if hasattr(p, "text")]
                        if parts:
                            response = "".join(parts)
                            break

                st.info(response)
            except Exception as e:
                st.error(f"AI Error: {e}")


def render_agent_chat():
    st.header("SCADA AI Assistant")
    st.markdown("Interact with the intelligent SCADA agent to ask questions about the data, anomalies, or regional demand.")

    import scada_summary_agent.config  # ensures API key checking

    runner = st.session_state["agent_runner"]
    session_id = st.session_state["chat_session_id"]

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask about the SCADA data..."):
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):
            message_placeholder = st.empty()

            with st.spinner("Agent is thinking..."):
                try:
                    msg = types.Content(role="user", parts=[types.Part(text=prompt)])
                    # Use the safe async runner for chat too
                    events = run_agent_sync(runner, session_id, msg)

                    full_response = ""
                    for event in reversed(events):
                        if getattr(event, "author", "") != "user" and not getattr(event, "partial", False):
                            if getattr(event, "content", None) and getattr(event.content, "parts", None):
                                parts_text = [p.text for p in event.content.parts if hasattr(p, "text") and p.text]
                                if parts_text:
                                    full_response = "".join(parts_text)
                                    break

                    if not full_response:
                        full_response = "Sorry, I couldn't generate a response."

                    message_placeholder.markdown(full_response)
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
                except Exception as e:
                    st.error(f"Error communicating with agent: {e}")


def render_weather_correlation():
    st.header("Weather & Demand Correlation 🌦⚡")
    st.markdown("Analyze how regional weather conditions impact power demand.")

    from utils.data_loader import get_merged_scada_weather

    with st.spinner("Fetching and merging weather data from MongoDB..."):
        df_merged = get_merged_scada_weather()

    if df_merged.empty:
        st.error("Failed to load or merge weather data.")
        return

    if st.session_state.get("exclude_weekends", False) and "is_weekend" in df_merged.columns:
        df_merged = df_merged[~df_merged["is_weekend"]]
    if st.session_state.get("exclude_holidays", False) and "is_holiday" in df_merged.columns:
        df_merged = df_merged[~df_merged["is_holiday"]]
    if st.session_state.get("exclude_events", False) and "is_special_event" in df_merged.columns:
        df_merged = df_merged[~df_merged["is_special_event"]]

    zone_options = {
        "Madhya Pradesh (MP)": "MP",
        "Western Zone (WZ)": "WZ",
        "Central Zone (CZ)": "CZ",
        "Eastern Zone (EZ)": "EZ",
    }
    selected_zone_name = st.selectbox("Select Demand Zone for Analysis", list(zone_options.keys()))
    zone_key = zone_options[selected_zone_name]

    min_date, max_date = get_date_range(df_merged)
    selected_date = st.date_input(
        "Select Date for Analysis",
        value=max_date.date() if pd.notnull(max_date) else None,
        min_value=min_date.date() if pd.notnull(min_date) else None,
        max_value=max_date.date() if pd.notnull(max_date) else None,
        key="intraday_weather_date",
    )

    from utils.insights import generate_weather_insights
    from utils.charts import plot_intraday_weather_correlation, plot_regional_weather_scatter, plot_weather_heatmap

    if selected_date is not None:
        try:
            day_data = df_merged[df_merged["date"].dt.date == selected_date]
            if not day_data.empty:
                evt_row = day_data.iloc[0]
                alerts = []
                if evt_row.get("is_weekend"):
                    alerts.append("Weekend")
                if evt_row.get("is_holiday"):
                    alerts.append("Holiday")
                if evt_row.get("is_special_event") and evt_row.get("event_description"):
                    alerts.append(f"Special Event: {evt_row['event_description']}")
                if alerts:
                    st.warning("🚨 **Notice for Selected Date:** This day is flagged as: " + ", ".join(alerts))
        except Exception:
            pass

    insights = generate_weather_insights(df_merged, zone=zone_key, selected_date=selected_date)

    active_filters = []
    if st.session_state.get("exclude_weekends"):
        active_filters.append("Weekends")
    if st.session_state.get("exclude_holidays"):
        active_filters.append("Holidays")
    if st.session_state.get("exclude_events"):
        active_filters.append("Special Events")

    insights += f"\n\n**Data Source**: {'Filtered (Excluded: ' + ', '.join(active_filters) + ')' if active_filters else 'All Days Included'}"
    st.info(insights)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Daily Impact Scatter")
        scatter_param = st.selectbox(
            "Select Weather Parameter",
            ["temperature", "relativeHumidity", "cloudCover", "windSpeed", "temperatureFeelsLike"],
            index=0,
            key="scatter_param",
        )
        fig_scatter = plot_regional_weather_scatter(df_merged, zone=zone_key, param=scatter_param)
        if fig_scatter:
            st.plotly_chart(fig_scatter, width="stretch")
        else:
            st.warning("Insufficient data for correlation scatter plot.")

    with col2:
        st.subheader("Condition Heatmap")
        fig_heat = plot_weather_heatmap(df_merged, zone=zone_key)
        if fig_heat:
            st.plotly_chart(fig_heat, width="stretch")
        else:
            st.warning("Heatmap data unavailable. Ensure wxPhraseShort is present.")

    st.markdown("---")
    st.subheader("Intraday Elasticity (Dual-Axis)")
    intra_param = st.selectbox(
        "Select Weather Parameter",
        ["temperature", "relativeHumidity", "cloudCover", "windSpeed", "temperatureFeelsLike"],
        index=0,
        key="intra_param",
    )

    if selected_date:
        fig_intra = plot_intraday_weather_correlation(df_merged, selected_date, zone=zone_key, param=intra_param)
        if fig_intra:
            st.plotly_chart(fig_intra, width="stretch")
        else:
            st.warning(f"No block-level intraday data found for {selected_date}.")

    st.subheader("AI Explanation 🤖")
    if st.button("Explain Weather Impact"):
        runner = st.session_state.get("agent_runner")
        session_id = st.session_state.get("chat_session_id")
        if runner and session_id:
            from utils.ai_insights import build_weather_summary
            summary = build_weather_summary(df_merged, zone_key)
            with st.spinner(f"Analyzing weather impact on {zone_key}... 🌦"):
                try:
                    prompt = (
                        f"Analyze the following weather data correlation for MP SCADA Demand:\n\n{summary}\n\n"
                        "Explain:\n1. The significance of the correlation\n"
                        "2. How temperature changes might be affecting demand\n"
                        "3. Recommendations for load forecasting."
                    )
                    msg = types.Content(role="user", parts=[types.Part(text=prompt)])
                    events = run_agent_sync(runner, session_id, msg)

                    response = ""
                    for event in reversed(events):
                        if getattr(event, "content", None):
                            parts = [p.text for p in event.content.parts if hasattr(p, "text")]
                            if parts:
                                response = "".join(parts)
                                break
                    st.info(response)
                except Exception as e:
                    st.error(f"AI Error: {e}")
        else:
            st.error("Agent system not initialized.")


if __name__ == "__main__":
    main()
