from google.adk.tools import FunctionTool, ToolContext
import holidays
from datetime import datetime, timedelta
import dateparser
import re

# Load holidays for last, current, and next year
today = datetime.today().date()
CURRENT_YEAR = today.year
indian_holidays = holidays.India(years=[CURRENT_YEAR - 1, CURRENT_YEAR, CURRENT_YEAR + 1])

# Custom non-public recurring holidays
SPECIAL_FIXED_HOLIDAYS = {
    "children's day": (11, 14),
    "childrens day": (11, 14),
    "children day": (11, 14),
    "teachers day": (9, 5),
    "engineers day": (9, 15),
}


def extract_target_year(text: str):
    """Detects explicit or relative year from the text, if any."""
    current_year = datetime.today().year

    # Explicit numeric year like 2024
    match = re.search(r"\b(20\d{2})\b", text)
    if match:
        return int(match.group(1))

    if "this year" in text:
        return current_year
    if "next year" in text or "coming year" in text:
        return current_year + 1
    if "last year" in text or "previous year" in text:
        return current_year - 1
    if "year after next" in text or "two years from now" in text:
        return current_year + 2
    if "year before last" in text or "two years ago" in text:
        return current_year - 2

    return None


def _resolve_primary_date(text: str):
    """Internal helper: resolve main date (holiday/custom/natural)."""
    # 1️⃣ Holiday-based match from holidays.India()
    for day, name in indian_holidays.items():
        if name.lower() in text:
            return day

    # 2️⃣ Custom fixed holidays
    for key, (month, day) in SPECIAL_FIXED_HOLIDAYS.items():
        if key in text:
            return datetime(CURRENT_YEAR, month, day).date()

    # 3️⃣ Fallback: natural language (yesterday, last Sunday, 2 days ago)
    parsed = dateparser.parse(text)
    if parsed:
        return parsed.date()

    return None


def parse_enhanced_natural_date(tool_context: ToolContext, date_text: str):
    """
    Smarter natural language date parser.

    Supports:
    - Single dates: 'yesterday', '2025-11-14', 'Diwali this year'
    - Relative pairs: 'Children's Day and the day before that',
      'Diwali and the next day', 'yesterday and day before that'
    - Ranges: 'Diwali week', 'last 7 days', 'week before Diwali',
      '10 days before Diwali', '5 days after Holi'

    Returns one of:
    - {'parsed_date': 'YYYYMMDD'}
    - {'primary_date': 'YYYYMMDD', 'secondary_date': 'YYYYMMDD'}
    - {'range_start': 'YYYYMMDD', 'range_end': 'YYYYMMDD'}
    """
    raw_input = date_text
    text = date_text.lower().strip()

    target_year = extract_target_year(text)

    # If holiday name + year context
    primary_date = None
    for holiday_date, holiday_name in indian_holidays.items():
        if holiday_name.lower() in text:
            if target_year is None or holiday_date.year == target_year:
                primary_date = holiday_date
                break
    
    if not primary_date:
        primary_date = _resolve_primary_date(text)

    if not primary_date:
        # 💾 STATE: Log failure to state
        tool_context.state['last_date_parse_error'] = raw_input
        return {"error": f"The date \"{raw_input}\" could not be interpreted. Please provide YYYYMMDD."}

    # ---------------- Secondary relative date (before/after that day) ----------------
    secondary_date = None

    # Simple phrases
    if re.search(r"(day before that|previous day|1 day before)", text):
        secondary_date = primary_date - timedelta(days=1)
    elif re.search(r"(day after that|next day|1 day after)", text):
        secondary_date = primary_date + timedelta(days=1)

    # General 'N days before/after'
    match_rel = re.search(r"(\d+)\s+days?\s+(before|after)", text)
    if match_rel:
        n = int(match_rel.group(1))
        if match_rel.group(2) == "before":
            secondary_date = primary_date - timedelta(days=n)
        else:
            secondary_date = primary_date + timedelta(days=n)

    # ---------------- Range handling (Diwali week, last 7 days, week before, etc.) ----------------
    range_start = None
    range_end = None

    # Last 7 days from 'today'
    if "last 7 days" in text:
        range_start = today - timedelta(days=7)
        range_end = today

    # Week before primary date
    if "week before" in text:
        range_start = primary_date - timedelta(days=7)
        range_end = primary_date - timedelta(days=1)

    # Week after / next 7 days from primary
    if "week after" in text or "next 7 days" in text:
        range_start = primary_date + timedelta(days=1)
        range_end = primary_date + timedelta(days=7)

    # "Diwali week", "Holi week" → ±3 days around holiday
    if "week" in text and any(k in text for k in ["diwali", "holi", "eid"]):
        range_start = primary_date - timedelta(days=3)
        range_end = primary_date + timedelta(days=3)

    # Generic: "N days before/after <date>" as range
    match_span = re.search(r"(\d+)\s+days?\s+(before|after)", text)
    if match_span and "to" in text:
        # E.g., "from 5 days before Diwali to 3 days after"
        n = int(match_span.group(1))
        if match_span.group(2) == "before":
            range_start = primary_date - timedelta(days=n)
            range_end = primary_date
        else:
            range_start = primary_date
            range_end = primary_date + timedelta(days=n)

    # ======================================================================
    # 💾 STATE IMPLEMENTATION
    # Store the parsed result so the Agent knows what "that day" or "that range"
    # refers to if the user asks a follow-up question.
    # ======================================================================
    
    # Initialize the result dictionary
    result = {"input": raw_input}

    if range_start and range_end:
        result["range_start"] = range_start.strftime("%Y%m%d")
        result["range_end"] = range_end.strftime("%Y%m%d")
        result["type"] = "range"
        
        # Store in State
        tool_context.state['last_parsed_date'] = {
            "type": "range",
            "start": result["range_start"],
            "end": result["range_end"],
            "original_text": raw_input
        }
        
    elif secondary_date:
        result["primary_date"] = primary_date.strftime("%Y%m%d")
        result["secondary_date"] = secondary_date.strftime("%Y%m%d")
        result["type"] = "comparison"
        
        # Store in State
        tool_context.state['last_parsed_date'] = {
            "type": "comparison",
            "date1": result["primary_date"],
            "date2": result["secondary_date"],
            "original_text": raw_input
        }
        
    else:
        result["parsed_date"] = primary_date.strftime("%Y%m%d")
        result["type"] = "single_day"
        
        # Store in State
        tool_context.state['last_parsed_date'] = {
            "type": "single_day",
            "date": result["parsed_date"],
            "original_text": raw_input
        }

    return result


parse_natural_date_tool = FunctionTool(func=parse_enhanced_natural_date)