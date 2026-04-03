import os
import pymongo
from pymongo import MongoClient
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

def aggregate_and_store():
    print("Connecting to MongoDB...")
    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGODB_DB", "mp_scada_data")
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    db = client[db_name]
    
    # Load Raw Weather
    collection_raw = db.get_collection(os.getenv("All_India_IBM_Weather_96_RTM", "All_India_IBM_Weather_96_RTM"))
    print("Fetching raw weather data...")
    raw_data = list(collection_raw.find({}, {"_id": 0}))
    if not raw_data:
        print("No raw weather data found.")
        return
    df_weather = pd.DataFrame(raw_data)
    
    if 'date_int' in df_weather.columns:
        df_weather['date'] = pd.to_datetime(df_weather['date_int'], format='%Y%m%d', errors='coerce')
    elif 'date' in df_weather.columns:
        df_weather['date'] = pd.to_datetime(df_weather['date'], errors='coerce')
        
    # Load Mapping
    collection_map = db.get_collection("Geo_Master_All_India")
    print("Fetching Geo mappings...")
    map_data = list(collection_map.find({}, {"_id": 0}))
    df_map = pd.DataFrame(map_data) if map_data else pd.DataFrame()
    
    if not df_map.empty and 'ZoneName' not in df_map.columns:
        df_map['ZoneName'] = None
    if not df_map.empty:
        fallback_zones = {"Ashoknagar": "CZ_Demand", "Indore": "WZ_Demand", "Ujjain": "WZ_Demand", 
                          "Bhopal": "CZ_Demand", "Gwalior": "CZ_Demand", "Jabalpur": "EZ_Demand", 
                          "Rewa": "EZ_Demand", "Satna": "EZ_Demand", "Sagar": "CZ_Demand"}
        if 'city' in df_map.columns:
            df_map['ZoneName'] = df_map['ZoneName'].fillna(df_map['city'].map(fallback_zones))
    
    print("Transforming and Aggregating data...")
    if 'GeoCode' in df_weather.columns and not df_map.empty and 'GeoCode' in df_map.columns:
        df_w_mapped = df_weather.merge(df_map[['GeoCode', 'ZoneName']], on='GeoCode', how='left')
    else:
        df_w_mapped = df_weather.copy()
        print("Warning: GeoCode missing. Data might not group by ZoneName properly.")
        
    if 'ZoneName' in df_w_mapped.columns and 'date' in df_w_mapped.columns:
        num_cols = df_w_mapped.select_dtypes(include='number').columns.tolist()
        num_cols = [c for c in num_cols if c not in ['date_int', 'block_no', 'Block']]
        
        groupby_cols = ['date', 'ZoneName']
        if 'Block' in df_w_mapped.columns:
            df_w_mapped['block_no'] = df_w_mapped['Block']
            groupby_cols.append('block_no')
        elif 'block_no' in df_w_mapped.columns:
            groupby_cols.append('block_no')
            
        df_w_agg = df_w_mapped.groupby(groupby_cols)[num_cols].mean(numeric_only=True).reset_index()
        
        if 'wxPhraseShort' in df_w_mapped.columns:
            df_w_text = df_w_mapped.groupby(groupby_cols)['wxPhraseShort'].agg(lambda x: pd.Series.mode(x)[0] if not pd.Series.mode(x).empty else None).reset_index()
            df_w_agg = df_w_agg.merge(df_w_text, on=groupby_cols, how='left')
        
        pivot_idx = [c for c in groupby_cols if c != 'ZoneName']
        all_vals = num_cols.copy()
        if 'wxPhraseShort' in df_w_agg.columns:
            all_vals.append('wxPhraseShort')
            
        df_w_pivot = df_w_agg.pivot_table(index=pivot_idx, columns='ZoneName', values=all_vals, aggfunc='first')
        df_w_pivot.columns = [f"{col[1].split('_')[0]}_{col[0]}" if isinstance(col[1], str) and pd.notna(col[1]) else f"Unknown_{col[0]}" for col in df_w_pivot.columns]
        df_w_pivot = df_w_pivot.reset_index()
        
        # Add MP State-Wide Averages
        base_weather_cols = list(set([c.split('_', 1)[1] for c in df_w_pivot.columns if '_' in c and c.split('_', 1)[0] in ['WZ', 'CZ', 'EZ']]))
        for param in base_weather_cols:
            if param == 'wxPhraseShort':
                if 'CZ_wxPhraseShort' in df_w_pivot.columns:
                    df_w_pivot['MP_wxPhraseShort'] = df_w_pivot['CZ_wxPhraseShort']
            else:
                zone_params = [f"{z}_{param}" for z in ['WZ', 'CZ', 'EZ'] if f"{z}_{param}" in df_w_pivot.columns]
                if zone_params:
                    df_w_pivot[f"MP_{param}"] = df_w_pivot[zone_params].mean(axis=1)
                    
        print(f"Aggregation complete. Output shape: {df_w_pivot.shape}")
        
        # Write to MongoDB
        collection_agg = db.get_collection("mp_weather_aggregated")
        collection_agg.drop() 
        print("Dropped old aggregated collection.")
        
        records = df_w_pivot.to_dict('records')
        print(f"Preparing to insert {len(records)} aggregated records into MongoDB...")
        
        if records:
            collection_agg.insert_many(records)
            print("Successfully inserted aggregated records into mp_weather_aggregated.")
            
            # Create Index
            index_cols = [("date", pymongo.ASCENDING)]
            if 'block_no' in df_w_pivot.columns:
                index_cols.append(("block_no", pymongo.ASCENDING))
            collection_agg.create_index(index_cols, unique=True)
            print(f"MongoDB indexed on {index_cols}.")
    else:
        print("Could not aggregate due to missing ZoneName or date columns!")

if __name__ == "__main__":
    aggregate_and_store()
