from google.adk.tools import FunctionTool,ToolContext
from typing import Dict, Optional, Any
# Assuming this is the correct path/module for your data loading function
from .scada_mongodb import load_scada_dataframe 
from google.adk.tools import ToolContext,FunctionTool
from datetime import datetime


def fetch_scada_summary(
    tool_context: ToolContext,
    date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    # ⚠️ ADDED: The tool_context parameter is now active
    
) -> Dict:
    """
    Fetch SCADA summary over a single day or a date range.
    
    The queried dates are stored in the agent's state for context recall.

    Args:
        date: 'YYYYMMDD' for single-day analysis.
        start_date: Start of range (YYYYMMDD) if doing range analysis.
        end_date: End of range (YYYYMMDD) if doing range analysis.
        tool_context: ADK object used for state management.

    Returns:
        Dict with demand, generation and frequency statistics.
    """

    try:
        df = load_scada_dataframe(date=date, start_date=start_date, end_date=end_date)
    except ValueError as e:
        # ⚠️ Context can be useful even in error cases
        tool_context.state['last_query_error'] = str(e)
        return {"error": str(e)}

    if df.empty:
        span = date or f"{start_date}–{end_date}"
        tool_context.state['last_query_error'] = f"No SCADA data found for {span}."
        return {"error": f"No SCADA data found for {span}."}

    # --- Calculation Logic (Unchanged) ---
    total_renewables = df.get("Solar", 0).sum() + df.get("Wind", 0).sum()
    total_thermal = df.get("Total_Thermal_Gen_Ex_Auxillary", 0).sum()
    total_hydel = df.get("Total_Hydel", 0).sum()

    denominator = total_thermal + total_hydel
    renewable_share = round(100 * total_renewables / denominator, 2) if denominator > 0 else 0.0
    # --- End Calculation Logic ---

    # 💾 STORE CONTEXT: Save the current query parameters to the agent's state
    tool_context.state['last_scada_query'] = {
        "mode": "single_day" if date else "range",
        "date": date,
        "start_date": start_date,
        "end_date": end_date,
        "timestamp": datetime.now().isoformat()
    }
    
    summary = {
        "mode": "single_day" if date else "range",
        "date": date,
        "start_date": start_date,
        "end_date": end_date,
        "records_found": int(len(df)),
        "peak_demand": float(df["MP_Demand"].max()),
        "min_demand": float(df["MP_Demand"].min()),
        "avg_demand": float(df["MP_Demand"].mean()),
        "total_demand_energy": float(df["MP_Demand"].sum()),
        "total_thermal_gen": float(total_thermal),
        "total_hydel_gen": float(total_hydel),
        "renewable_gen_total": float(total_renewables),
        "renewable_share_percent": renewable_share,
        "frequency_min": float(df["Raw_Frequency"].min()),
        "frequency_max": float(df["Raw_Frequency"].max()),
        "frequency_avg": float(df["Raw_Frequency"].mean()),
    }

    return summary


# ⚙️ TOOL DEFINITION: The tool definition is already correct for passing context
fetch_scada_summary_tool = FunctionTool(func=fetch_scada_summary)



