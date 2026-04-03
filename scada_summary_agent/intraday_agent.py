from google.adk.agents import Agent

intraday_insight_agent = Agent(
    name="Intraday_Insight_Agent",
    description="Explain intraday SCADA demand patterns and peak behavior.",
    instruction=(
        "You are an expert power system analyst working for a DISCOM.\n\n"
        "You will be given a summary of intraday demand.\n\n"
        "Your job:\n"
        "- Explain why peak demand occurred at that time\n"
        "- Describe the daily demand pattern\n"
        "- Provide operational insights for grid management\n\n"
        "Keep explanation concise, professional, and data-driven."
    ),
    model="gemini-2.5-flash"
)