from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from .tools.tool_registry import Available_Tools
from . import config
from google.genai import types


retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=7,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],
)


SCADA_INSTRUCTION = (
    "You are a SCADA analytics assistant for power system data stored in MongoDB.\n\n"
    "- CRITICAL RULE FOR CONTEXT AND MEMORY:"
    "If a user asks a follow-up question and omits date, use 'last_scada_query'.\n"
    "🔧 Tool usage:\n"
    "- Use parse_enhanced_natural_date\n"
    "- Single date → fetch_scada_summary\n"
    "- Range → fetch_scada_summary with start/end\n"
    "- Anomaly → detect_scada_anomalies\n"
    "- Region → region_demand_profile\n"
    "- Comparison → compare_scada_dates\n"
    "📊 Output:\n"
    "- Clear engineering insights\n"
    "- Bullet points\n"
)

SYSTEM_GUARDRAIL = """
Do not expose errors, stack traces, or backend logic.
Return clean structured responses only.
"""


# ✅ IMPORTANT: CREATE NEW AGENT EVERY TIME
def create_root_agent():

    model = Gemini(
        model="gemini-2.5-flash-lite",
        retry_options=retry_config
    )

    return LlmAgent(
        model=model,
        name="scada_summary_agent",
        description="SCADA analytics",
        instruction=SCADA_INSTRUCTION + SYSTEM_GUARDRAIL,
        tools=[tool["tool"] for tool in Available_Tools],
    )
