"""
Debug script to test the scheduling constraints step by step.
"""

import sys
sys.path.insert(0, 'src')

from scheduler import load_scenario, BusChargingScheduler

# Load scenario 1
scenario, route_config = load_scenario(1)

print("=== Scenario 1: Even Spacing ===")
print(f"Buses: {len(scenario['buses'])}")
print(f"Battery range: {route_config['physical_constants']['battery_range_km']} km")
print(f"Speed: {route_config['physical_constants']['speed_kmh']} km/h")

# Check distances
scheduler = BusChargingScheduler(scenario, route_config)

print("\n=== Station Distances ===")
for name, dist in scheduler.station_distances.items():
    print(f"{name}: {dist} km from Bengaluru")

# Check required stations
print("\n=== Required Charging Stations ===")
print(f"Bengaluru→Kochi: {scheduler._get_required_stations('Bengaluru→Kochi')}")
print(f"Kochi→Bengaluru: {scheduler._get_required_stations('Kochi→Bengaluru')}")

# Check if stations are reachable
print("\n=== Range Analysis for Bengaluru→Kochi ===")
print(f"Start: Bengaluru (240 km range)")
print(f"  → A at 100 km: Reachable ✓ (140 km remaining)")
print(f"  → B at 220 km: Reachable ✓ (20 km remaining if no charge)")
print(f"After charging at B (full): 240 km range")
print(f"  → C at 320 km (100 km from B): Reachable ✓ (140 km remaining)")
print(f"  → D at 440 km (120 km from B): Reachable ✓ (120 km remaining)")
print(f"After charging at D (full): 240 km range")
print(f"  → Kochi at 540 km (100 km from D): Reachable ✓")

# Calculate minimum travel time
total_distance = 540
speed = route_config['physical_constants']['speed_kmh']
min_travel_time = (total_distance / speed) * 60
min_charges = 2
charging_time = route_config['physical_constants']['charging_time_minutes']
min_trip_time = min_travel_time + (min_charges * charging_time)

print(f"\n=== Minimum Trip Time ===")
print(f"Pure travel time: {min_travel_time:.0f} minutes ({total_distance} km / {speed} km/h)")
print(f"Minimum charges: {min_charges} × {charging_time} min = {min_charges * charging_time} min")
print(f"Minimum trip time: {min_trip_time:.0f} minutes ({min_trip_time/60:.1f} hours)")

# Try to schedule
print("\n=== Running Scheduler ===")
result = scheduler.schedule()
print(f"Status: {result['status']}")
if result['status'] != 'SUCCESS':
    print(f"Message: {result.get('message', 'No message')}")
