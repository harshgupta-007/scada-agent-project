from google.adk.agents import Agent
from .tools import load_scada_file, compute_scada_metrics
from . import config  # ensures .env loads

scada_summary_agent = Agent(
    name="SCADA_Summary_Agent",  # valid identifier
    description="Summarize SCADA CSV demand data.",
    instruction=(  # MUST be 'instruction', not 'instructions'
        "Load the CSV file using tools and generate a clear SCADA summary. "
        "Use min, max, avg, and total demand in your explanation."
    ),
    tools=[load_scada_file, compute_scada_metrics],
    model="gemini-2.5-flash"
)
