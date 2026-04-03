from google.adk.tools import FunctionTool, ToolContext
from pymongo import MongoClient
import pandas as pd
import os
from typing import Dict
from datetime import datetime

def detect_scada_anomalies(
    # ⚠️ ToolContext is already correctly placed first
    tool_context: ToolContext,
    date: str
) -> Dict:
    """
    Detect anomalies directly from MongoDB using date input.
    Valid anomalies:
    - Missing blocks
    - Demand spikes (>15%)
    - Frequency violations (<49.90 or >50.05 Hz)
    """

    # Connect and fetch data
    client = MongoClient(os.getenv("MONGODB_URI"))
    db = client[os.getenv("MONGODB_DB")]
    col = db[os.getenv("MONGODB_COLLECTION")]

    date_clean = date.replace("-", "")
    records = list(col.find({"date": date_clean}, {"_id": 0, "block": 1, "MP_Demand": 1, "Raw_Frequency": 1}))

    if not records:
        # 💾 STATE: Log the error so the agent knows the last attempt failed
        tool_context.state['last_query_error'] = f"No SCADA data found for {date_clean}"
        return {"error": f"No SCADA data found for {date_clean}"}

    df = pd.DataFrame(records)

    # 🛑 Missing Blocks
    expected = set(range(1, 97))
    actual = set(df["block"].unique())
    missing = sorted(expected - actual)

    # ⚡ Demand Spikes
    df["change_pct"] = df["MP_Demand"].pct_change() * 100
    spikes = df[df["change_pct"].abs() > 15]

    demand_spikes = [
        f"Block {int(row['block'])}: Δ {row['change_pct']:.1f}%, Demand {row['MP_Demand']:.1f} MW"
        for _, row in spikes.iterrows()
    ] or ["No demand spikes detected"]

    # 🚨 Frequency Violations
    freq_issues = df[(df["Raw_Frequency"] < 49.90) | (df["Raw_Frequency"] > 50.05)]
    frequency_violations = [
        f"Block {int(row['block'])}: Frequency {row['Raw_Frequency']:.2f} Hz"
        for _, row in freq_issues.iterrows()
    ] or ["No frequency violations detected"]

    # ======================================================================
    # 💾 STATE IMPLEMENTATION
    # ======================================================================
    
    # Check if there were actual issues (bool flags)
    has_missing = len(missing) > 0
    has_spikes = not spikes.empty
    has_freq_issues = not freq_issues.empty
    
    # Store the anomaly context. 
    # The agent can use this to know if the day was "clean" or "problematic"
    tool_context.state['last_anomaly_check'] = {
        "date": date_clean,
        "timestamp": datetime.now().isoformat(),
        "status": "critical" if (has_missing or has_spikes or has_freq_issues) else "normal",
        "summary": {
            "missing_blocks_count": len(missing),
            "demand_spikes_count": len(spikes),
            "freq_violations_count": len(freq_issues)
        }
    }

    return {
        "date": date_clean,
        "missing_blocks": ", ".join(map(str, missing)) if missing else "None",
        "demand_spikes": demand_spikes,
        "frequency_violations": frequency_violations,
    }


detect_scada_anomalies_tool = FunctionTool(func=detect_scada_anomalies)