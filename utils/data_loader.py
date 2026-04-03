import os
import pandas as pd
import streamlit as st
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

@st.cache_data(ttl=3600)
def load_special_events() -> pd.DataFrame:
    try:
        uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        db_name = os.getenv("MONGODB_DB", "mp_scada_data")
        client = MongoClient(uri, serverSelectionTimeoutMS=2000)
        db = client[db_name]
        collection = db.get_collection("mp_special_events")
        
        data = list(collection.find({}, {"_id": 0}))
        # Cache buster comment: updated special events layout
        if not data:
            return pd.DataFrame()
            
        df_events = pd.DataFrame(data)
        if 'date' in df_events.columns:
            df_events['date'] = pd.to_datetime(df_events['date'])
            df_events['is_special_event'] = True
        return df_events
    except Exception as e:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_scada_data(filepath: str = 'sample_scada.csv') -> pd.DataFrame:
    """
    Loads and preprocesses the SCADA CSV data.
    Caches the result to improve application performance.
    """
    if not os.path.exists(filepath):
        st.error(f"Data file not found at {filepath}")
        return pd.DataFrame()
        
    try:
        df = pd.read_csv(filepath)
        
        # Ensure date format is correct
        if 'date_int' in df.columns:
            # First try parsing as is (YYYY-MM-DD), if that fails pandas will try to infer
            df['date'] = pd.to_datetime(df['date_int'], format='%Y%m%d')
        elif 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
        else:
            st.warning("Missing 'date' column in dataset.")
            
        # Map required column names to common ones if they exist
        column_mapping = {
            'block': 'block_no',
            'MP_Demand': 'demand_energy',
            'Total_Thermal_Gen_Ex_Auxillary': 'thermal_gen',
            'Total_Hydel': 'hydel_gen'
        }
        df.rename(columns=column_mapping, inplace=True)
        
        # Calculate renewable_gen if Solar and Wind exist
        if 'Solar' in df.columns and 'Wind' in df.columns:
            df['renewable_gen'] = df['Solar'] + df['Wind']

        # Ensure numeric types
        numeric_cols = ['demand_energy', 'thermal_gen', 'hydel_gen', 'renewable_gen', 'Raw_Freq']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
        # Define temporal features
        df['day_of_week'] = df['date'].dt.day_name()
        df['is_weekend'] = df['date'].dt.dayofweek >= 5

        # Merge Holidays
        import holidays
        try:
            in_holidays = holidays.India(years=df['date'].dt.year.unique())
            df['is_holiday'] = df['date'].dt.date.apply(lambda d: d in in_holidays)
        except Exception:
            df['is_holiday'] = False
            
        # Merge Special Events
        df_events = load_special_events()
        if not df_events.empty and 'date' in df_events.columns:
            df = df.merge(df_events, on='date', how='left')
            df['is_special_event'] = df['is_special_event'].fillna(False)
            df['event_description'] = df['event_description'].fillna("")
        else:
            df['is_special_event'] = False
            df['event_description'] = ""

        return df
    except Exception as e:
        st.error(f"Error loading SCADA data: {e}")
        return pd.DataFrame()

def get_date_range(df: pd.DataFrame) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Returns the minimum and maximum dates available in the dataset."""
    if df.empty or 'date' not in df.columns:
        return pd.Timestamp('2023-01-01'), pd.Timestamp('2023-12-31')
    return df['date'].min(), df['date'].max()

def filter_data_by_date(df: pd.DataFrame, start_date, end_date) -> pd.DataFrame:
    """Filters the dataframe between start_date and end_date (inclusive)."""
    if df.empty or 'date' not in df.columns:
        return df
    mask = (df['date'].dt.date >= start_date) & (df['date'].dt.date <= end_date)
    return df.loc[mask]

def get_daily_aggregations(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregates the 96-block data into daily summaries."""
    if df.empty:
        return df
        
    # Group by date and calculate daily metrics
    agg_dict = {
        'demand_energy': 'sum',
        'thermal_gen': 'sum',
        'hydel_gen': 'sum',
    }
    
    if 'renewable_gen' in df.columns:
        agg_dict['renewable_gen'] = 'sum'
    if 'Raw_Freq' in df.columns:
        agg_dict['Raw_Freq'] = ['max', 'min', 'mean']
    
    # We aggregate first, then calculate the daily min/max for the blocks later if needed,
    # or just rename the aggregated demand_energy to peak and min demand since max and min
    # refer to blocks.
    
    # To get peak/min demand per day from the 15-min blocks:
    daily_df = df.groupby('date').agg(agg_dict).reset_index()
    
    # Flatten MultiIndex if 'Raw_Freq' is present
    if isinstance(daily_df.columns, pd.MultiIndex):
        daily_df.columns = ['_'.join(col).strip('_') for col in daily_df.columns.values]
        # Rename standard aggregations back
        daily_df.rename(columns={
            'demand_energy_sum': 'demand_energy',
            'thermal_gen_sum': 'thermal_gen',
            'hydel_gen_sum': 'hydel_gen',
            'renewable_gen_sum': 'renewable_gen',
            'Raw_Freq_max': 'frequency_max',
            'Raw_Freq_min': 'frequency_min',
            'Raw_Freq_mean': 'frequency_avg'
        }, inplace=True)
    
    # Calculate peak, min, avg directly from the blocks 
    daily_block_stats = df.groupby('date')['demand_energy'].agg(
        peak_demand='max', 
        min_demand='min', 
        avg_demand='mean'
    ).reset_index()
    
    daily_df = pd.merge(daily_df, daily_block_stats, on='date')
    
    return daily_df

# from here start one by one
def get_intraday_profile(df: pd.DataFrame):
    """
    Returns intraday demand profile (96 blocks)
    """
    if df.empty:
        return None

    # Group by block (average across days if multiple)
    profile = df.groupby('block_no')['demand_energy'].mean().reset_index()

    return profile

from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

@st.cache_data(ttl=3600)
def load_weather_mapping() -> pd.DataFrame:
    try:
        uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        db_name = os.getenv("MONGODB_DB", "mp_scada_data")
        client = MongoClient(uri, serverSelectionTimeoutMS=2000)
        db = client[db_name]
        collection = db.get_collection(os.getenv("All_India_IBM_Weather_96_RTM", "Geo_Master_All_India"))
        
        data = list(collection.find({}, {"_id": 0}))
        if not data:
            st.warning("No weather mapping data found in MongoDB. Using empty mapping.")
            return pd.DataFrame()
            
        df_map = pd.DataFrame(data)
        
        # Fallback dictionary for common NaN cities
        fallback_zones = {
            "Ashoknagar": "CZ_Demand",
            "Indore": "WZ_Demand",
            "Ujjain": "WZ_Demand",
            "Bhopal": "CZ_Demand",
            "Gwalior": "CZ_Demand",
            "Jabalpur": "EZ_Demand",
            "Rewa": "EZ_Demand",
            "Satna": "EZ_Demand",
            "Sagar": "CZ_Demand"
        }
        
        # Apply fallback where ZoneName is missing or NaN
        if 'ZoneName' not in df_map.columns:
            df_map['ZoneName'] = None
            
        df_map['ZoneName'] = df_map['ZoneName'].fillna(df_map['city'].map(fallback_zones))
        return df_map
    except Exception as e:
        st.warning(f"Could not load weather mapping from MongoDB: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_weather_data() -> pd.DataFrame:
    df_weather = pd.DataFrame()
    try:
        uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        db_name = os.getenv("MONGODB_DB", "mp_scada_data")
        client = MongoClient(uri, serverSelectionTimeoutMS=2000)
        db = client[db_name]
        collection = db.get_collection("mp_weather_aggregated")
        
        data = list(collection.find({}, {"_id": 0}))
        if data:
            df_weather = pd.DataFrame(data)
            df_weather['source'] = 'mongodb_aggregated'
    except Exception as e:
        st.warning(f"MongoDB aggregated weather fetch failed: {e}.")
            
    if 'date' in df_weather.columns:
        df_weather['date'] = pd.to_datetime(df_weather['date'], errors='coerce')
        
    return df_weather

@st.cache_data(ttl=3600)
def get_merged_scada_weather() -> pd.DataFrame:
    df_scada = load_scada_data()
    df_weather = load_weather_data()
    
    if df_scada.empty or df_weather.empty:
        return df_scada
        
    merge_cols = ['date']
    if 'block_no' in df_weather.columns and 'block_no' in df_scada.columns:
        merge_cols.append('block_no')
        
    df_merged = df_scada.merge(df_weather, on=merge_cols, how='left')
    
    # Ensure MP_Demand alias exists for downstream charts
    if 'MP_Demand' not in df_merged.columns and 'demand_energy' in df_merged.columns:
        df_merged['MP_Demand'] = df_merged['demand_energy']

    return df_merged
