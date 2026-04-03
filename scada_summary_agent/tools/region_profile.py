################ level 2 #####################
# scada_summary_agent/tools/region_profile.py

from google.adk.tools import FunctionTool
from typing import Dict, Optional
from .scada_mongodb import load_scada_dataframe
from google.adk.tools import ToolContext,FunctionTool

REGION_COLUMNS = [
    "CZ_Demand",
    "EZ_Demand",
    "WZ_Demand",
    "CZ_Total_Schedule",
    "EZ_Total_Schedule",
    "WZ_Total_Schedule",
]


def region_demand_profile(
    tool_context = ToolContext,
    date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict:
    """
    Build region-wise demand and schedule profile for a date or date range.

    Returns per-region:
    - avg_demand
    - peak_demand
    - total_scheduled_energy
    """

    try:
        df = load_scada_dataframe(date=date, start_date=start_date, end_date=end_date)
    except ValueError as e:
        return {"error": str(e)}

    if df.empty:
        span = date or f"{start_date}–{end_date}"
        return {"error": f"No SCADA data found for {span}."}

    region_stats = {}

    for col in REGION_COLUMNS:
        if col not in df.columns:
            continue

        base_name = col.split("_")[0]  # CZ, EZ, WZ
        kind = "demand" if "Demand" in col else "schedule"

        region_key = base_name
        region_stats.setdefault(region_key, {})
        region_stats[region_key][kind] = {
            "avg": float(df[col].mean()),
            "peak": float(df[col].max()),
            "total": float(df[col].sum()),
        }

    return {
        "span": date or f"{start_date}–{end_date}",
        "regions": region_stats,
    }


region_demand_profile_tool = FunctionTool(func=region_demand_profile)
