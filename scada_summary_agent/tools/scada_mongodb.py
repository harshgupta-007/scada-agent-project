# from pymongo import MongoClient
import pandas as pd
import os
from typing import Optional
from google.adk.tools import ToolContext

# Mocking MongoDB by using a local CSV file
# This allows the agent to run without a local MongoDB instance
# CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sample_scada.csv")
CSV_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "sample_scada.csv"
)

def _get_collection():
    """
    Mock collection - not used when reading from CSV.
    Kept for compatibility if we switch back.
    """
    pass

def load_scada_dataframe(
    date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """
    Load SCADA data as a pandas DataFrame from a CSV file (Mock DB).

    - If `date` is provided → returns that day's data.
    - If `start_date` and `end_date` are provided → returns all data in that range (inclusive).

    Dates must be in 'YYYYMMDD' (string). Hyphens are tolerated and removed.
    """
    if not os.path.exists(CSV_PATH):
        print(f"Error: CSV file not found at {CSV_PATH}")
        return pd.DataFrame()

    # Load the entire CSV
    try:
        df = pd.read_csv(CSV_PATH)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return pd.DataFrame()

    # Ensure date column exists
    if 'date' not in df.columns:
        # If date is missing, assume the data belongs to the requested date (or today/yesterday)
        # This allows the minimal sample CSV to work with date queries
        default_date = date if date else (start_date if start_date else "20231126")
        # Format default_date from YYYYMMDD to YYYY-MM-DD for consistency if needed, 
        # but here we just need it to parse into date_int.
        df['date'] = default_date
        print(f"Warning: 'date' column not found in CSV. Assigned default date: {default_date}")

    # Normalize CSV dates to int YYYYMMDD
    try:
        # Ensure date column is string to avoid timestamp interpretation
        df['date'] = df['date'].astype(str)
        # Handle YYYYMMDD string or YYYY-MM-DD
        # Using explicit format if possible, or letting pandas infer but forcing string helps
        df['date_int'] = pd.to_datetime(df['date']).dt.strftime('%Y%m%d').astype(int)
    except Exception as e:
         print(f"Error parsing dates: {e}")
         return pd.DataFrame()

    if start_date and end_date:
        start_int = int(start_date.replace("-", ""))
        end_int = int(end_date.replace("-", ""))
        filtered_df = df[(df['date_int'] >= start_int) & (df['date_int'] <= end_int)]
    elif date:
        date_int = int(date.replace("-", ""))
        filtered_df = df[df['date_int'] == date_int]
    else:
        # If no date specified, return everything
        filtered_df = df

    return filtered_df

