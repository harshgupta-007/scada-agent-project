from google.adk.tools import FunctionTool, ToolContext
from typing import Dict, Optional
from .scada_mongodb import load_scada_dataframe
# (Duplicate import removed for cleanliness, but works either way)

def _summarize_df(df):
    total_renewables = df.get("Solar", 0).sum() + df.get("Wind", 0).sum()
    total_thermal = df.get("Total_Thermal_Gen_Ex_Auxillary", 0).sum()
    total_hydel = df.get("Total_Hydel", 0).sum()

    return {
        "records": int(len(df)),
        "avg_demand": float(df["MP_Demand"].mean()),
        "peak_demand": float(df["MP_Demand"].max()),
        "total_demand": float(df["MP_Demand"].sum()),
        "thermal_gen": float(total_thermal),
        "hydel_gen": float(total_hydel),
        "renewables": float(total_renewables),
        "avg_frequency": float(df["Raw_Frequency"].mean()),
    }


def compare_scada_dates(
    # ⚠️ CHANGED '=' to ':' to ensure ADK injects the actual object
    tool_context: ToolContext, 
    date1: Optional[str] = None,
    date2: Optional[str] = None,
    start1: Optional[str] = None,
    end1: Optional[str] = None,
    start2: Optional[str] = None,
    end2: Optional[str] = None,
) -> Dict:
    """
    Compare SCADA between two periods.

    Modes:
    - Single-day vs single-day: use date1 & date2.
    - Range vs range: use (start1, end1) and (start2, end2).
    """

    if date1 and date2:
        df1 = load_scada_dataframe(date=date1)
        df2 = load_scada_dataframe(date=date2)
        label1 = date1
        label2 = date2
    elif start1 and end1 and start2 and end2:
        df1 = load_scada_dataframe(start_date=start1, end_date=end1)
        df2 = load_scada_dataframe(start_date=start2, end_date=end2)
        label1 = f"{start1}-{end1}"
        label2 = f"{start2}-{end2}"
    else:
        return {
            "error": "Provide either (date1, date2) for day comparison, or "
                     "(start1, end1, start2, end2) for range comparison."
        }

    if df1.empty or df2.empty:
        # 💾 STATE (Optional): You might want to log failures too
        tool_context.state['last_comparison_error'] = f"Failed to compare {label1} vs {label2}"
        return {"error": f"No SCADA data found for {label1} or {label2}."}

    s1 = _summarize_df(df1)
    s2 = _summarize_df(df2)

    diff = {
        "avg_demand_diff": s2["avg_demand"] - s1["avg_demand"],
        "peak_demand_diff": s2["peak_demand"] - s1["peak_demand"],
        "total_demand_diff": s2["total_demand"] - s1["total_demand"],
        "thermal_gen_diff": s2["thermal_gen"] - s1["thermal_gen"],
        "hydel_gen_diff": s2["hydel_gen"] - s1["hydel_gen"],
        "renewables_diff": s2["renewables"] - s1["renewables"],
        "avg_frequency_diff": s2["avg_frequency"] - s1["avg_frequency"],
    }

    # ======================================================================
    # 💾 STATE IMPLEMENTATION
    # Store the parameters of this comparison so the Agent remembers
    # what "Comparison" we are talking about in the next turn.
    # ======================================================================
    tool_context.state['last_comparison'] = {
        "period1": label1,
        "period2": label2,
        "raw_args": {
            "date1": date1, "date2": date2,
            "start1": start1, "end1": end1,
            "start2": start2, "end2": end2
        }
    }
    
    # Optional: Clear single-day state to avoid confusion between tools
    if 'last_scada_query' in tool_context.state:
        tool_context.state['last_scada_query'] = None

    return {
        "period1": label1,
        "period2": label2,
        "summary": {
            label1: s1,
            label2: s2,
        },
        "difference": diff,
    }


compare_scada_dates_tool = FunctionTool(func=compare_scada_dates)