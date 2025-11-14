#!/usr/bin/env python
"""
Script to populate mock transit data with recent timestamps.
Run this with: docker compose exec web uv run python scripts/populate_mock_data.py
"""

import os
import sys
import django
import random
from datetime import timedelta

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "infobus_data.settings")
django.setup()

from django.utils import timezone
from django.db import connection

def populate_data():
    """Populate mock transit data with recent timestamps"""
    
    now = timezone.now()
    print(f"Current time: {now}")
    
    # Routes and their stops
    routes = [
        ('101', ['STOP_A', 'STOP_B']),
        ('102', ['STOP_A', 'STOP_C']),
        ('103', ['STOP_B', 'STOP_C'])
    ]
    
    with connection.cursor() as cursor:
        # Generate arrivals for the last 2 hours
        arrivals_data = []
        for minutes_ago in range(120, 0, -3):  # Every 3 minutes
            timestamp = now - timedelta(minutes=minutes_ago)
            
            for route_id, stops in routes:
                for stop_id in stops:
                    # Generate realistic delays
                    delay = random.choice([
                        -30, -20, -10, 0, 0, 0, 10, 20, 30,  # Most on time
                        45, 60, 90, 120, 150,  # Some late
                        -45, -60  # Some early
                    ])
                    
                    trip_id = f"TRIP_{route_id}_{minutes_ago % 10}"
                    vehicle_id = f"VEH_{route_id}_{(minutes_ago // 30) % 3}"
                    
                    arrivals_data.append((
                        route_id, stop_id, trip_id, vehicle_id,
                        timestamp, timestamp - timedelta(seconds=delay), delay
                    ))
        
        # Insert arrivals
        print(f"Inserting {len(arrivals_data)} arrival records...")
        arrivals_sql = """
        INSERT INTO arrivals (route_id, stop_id, trip_id, vehicle_id, 
                             observed_at, scheduled_at, delay_s)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.executemany(arrivals_sql, arrivals_data)
        print(f"✅ Inserted {len(arrivals_data)} arrivals")
        
        # Generate occupancy data
        occupancy_data = []
        for minutes_ago in range(120, 0, -5):  # Every 5 minutes
            timestamp = now - timedelta(minutes=minutes_ago)
            
            for route_id, _ in routes:
                # Random occupancy between 0.15 and 0.85
                ratio = random.uniform(0.15, 0.85)
                vehicle_id = f"VEH_{route_id}_{(minutes_ago // 30) % 3}"
                trip_id = f"TRIP_{route_id}_{minutes_ago % 10}"
                
                occupancy_data.append((route_id, vehicle_id, trip_id, timestamp, ratio))
        
        # Insert occupancy
        print(f"Inserting {len(occupancy_data)} occupancy records...")
        occupancy_sql = """
        INSERT INTO occupancy (route_id, vehicle_id, trip_id, observed_at, ratio)
        VALUES (%s, %s, %s, %s, %s)
        """
        cursor.executemany(occupancy_sql, occupancy_data)
        print(f"✅ Inserted {len(occupancy_data)} occupancy records")
        
        # Verify data ranges
        cursor.execute("""
            SELECT 
                MIN(observed_at) as oldest,
                MAX(observed_at) as newest,
                COUNT(*) as total
            FROM arrivals
        """)
        result = cursor.fetchone()
        print(f"\nArrivals data range:")
        print(f"  Oldest: {result[0]}")
        print(f"  Newest: {result[1]}")
        print(f"  Total: {result[2]}")
        
        cursor.execute("""
            SELECT 
                MIN(observed_at) as oldest,
                MAX(observed_at) as newest,
                COUNT(*) as total
            FROM occupancy
        """)
        result = cursor.fetchone()
        print(f"\nOccupancy data range:")
        print(f"  Oldest: {result[0]}")
        print(f"  Newest: {result[1]}")
        print(f"  Total: {result[2]}")
        
        print(f"\n✅ Mock data populated successfully!")
        print(f"You can now run Celery tasks to compute KPIs")

if __name__ == "__main__":
    populate_data()
