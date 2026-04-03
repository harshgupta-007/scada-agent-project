from .date_parser import parse_natural_date_tool
from .scada_analysis import fetch_scada_summary_tool
from .scada_anomaly import detect_scada_anomalies_tool
from .region_profile import region_demand_profile_tool
from .compare_scada_dates import compare_scada_dates_tool

Available_Tools = [
    {
        "name": parse_natural_date_tool.name,
        "tool": parse_natural_date_tool,
        "description": parse_natural_date_tool.description,
    },
    {
        "name": fetch_scada_summary_tool.name,
        "tool": fetch_scada_summary_tool,
        "description": fetch_scada_summary_tool.description,
    },
    {
        "name": detect_scada_anomalies_tool.name,
        "tool": detect_scada_anomalies_tool,
        "description": detect_scada_anomalies_tool.description,
    },
    {
        "name": region_demand_profile_tool.name,
        "tool": region_demand_profile_tool,
        "description": region_demand_profile_tool.description,
    },
    {
        "name": compare_scada_dates_tool.name,
        "tool": compare_scada_dates_tool,
        "description": compare_scada_dates_tool.description,
    },
]
