import os
import pymongo
from pymongo import MongoClient
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

def init_special_events_db():
    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGODB_DB", "mp_scada_data")
    
    print(f"Connecting to MongoDB at {uri}...")
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        db = client[db_name]
        collection = db.get_collection("mp_special_events")
        
        # Insert a sample event that aligns with common SCADA dates
        # e.g., Let's insert "2025-05-15" as Severe Heatwave.
        sample_events = [
            {
                "date": "2025-05-15",
                "event_description": "Severe Heatwave alert - Industrial Load Shedding implemented",
                "impact_type": "Weather Warning"
            },
            {
                "date": "2025-04-10",
                "event_description": "Unexpected Local Factory Shutdowns due to heavy rain",
                "impact_type": "Operational"
            },
            {
                "date": "2025-11-14",
                "event_description": "Children's Day",
                "impact_type": "Cultural Observance"
            }
        ]
        
        # Upsert logic to avoid duplicates if run multiple times
        for event in sample_events:
            collection.update_one(
                {"date": event["date"]},
                {"$set": event},
                upsert=True
            )
            
        print("Successfully created 'mp_special_events' collection and inserted sample events.")
        
        # Create an Index on the 'date' field for faster lookups
        collection.create_index([("date", pymongo.ASCENDING)], unique=True)
        print("Successfully indexed 'date' field in mp_special_events.")
        
    except Exception as e:
        print(f"Failed to initialize database: {e}")

if __name__ == "__main__":
    init_special_events_db()
