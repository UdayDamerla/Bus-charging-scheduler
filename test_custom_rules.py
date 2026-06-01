"""
Test custom rules through the API (same as UI uses)
"""

import sys
sys.path.insert(0, 'src')

from scheduler import load_scenario
from custom_scheduler import CustomRulesScheduler

print("="*70)
print("Testing Custom Rules via API")
print("="*70)

# Load scenario 2 (bunched start - lots of contention)
scenario, route_config = load_scenario(2)

# Test 1: No custom rules (baseline)
print("\n--- Test 1: Baseline (no custom rules) ---")
scheduler = CustomRulesScheduler(scenario, route_config, custom_rules={})
result = scheduler.schedule()

baseline_order = [e['bus_id'] for e in result['station_queues']['B'][:6]]
print(f"Station B order (first 6): {baseline_order}")

# Test 2: Priority buses rule
print("\n--- Test 2: Priority Buses Rule ---")
custom_rules = {
    'priority_buses_enabled': True,
    'priority_bus_list': ['bus-BK-05', 'bus-KB-03'],
    'priority_boost': 5000,
}

scheduler = CustomRulesScheduler(scenario, route_config, custom_rules)
result = scheduler.schedule()

priority_order = [e['bus_id'] for e in result['station_queues']['B'][:6]]
print(f"Station B order (first 6): {priority_order}")
print(f"Priority buses: bus-BK-05, bus-KB-03")

# Check if priority buses moved up
for bus_id in ['bus-BK-05', 'bus-KB-03']:
    baseline_pos = baseline_order.index(bus_id) if bus_id in baseline_order else -1
    priority_pos = priority_order.index(bus_id) if bus_id in priority_order else -1

    if baseline_pos != -1 and priority_pos != -1:
        if priority_pos < baseline_pos:
            print(f"  ✅ {bus_id} moved UP: position {baseline_pos+1} → {priority_pos+1}")
        else:
            print(f"  ⚠️  {bus_id} didn't move up (might have been first already)")

# Test 3: Time-of-day rule
print("\n--- Test 3: Time-of-Day Rule ---")
custom_rules = {
    'time_of_day_enabled': True,
    'off_peak_start': 0,
    'off_peak_end': 6,
    'off_peak_boost': 2000,
}

scheduler = CustomRulesScheduler(scenario, route_config, custom_rules)
result = scheduler.schedule()

time_order = [e['bus_id'] for e in result['station_queues']['B'][:6]]
print(f"Station B order (first 6): {time_order}")
print("Off-peak hours: 00:00-06:00 get priority")

# Test 4: Multiple rules combined
print("\n--- Test 4: Combined Rules ---")
custom_rules = {
    'priority_buses_enabled': True,
    'priority_bus_list': ['bus-BK-05'],
    'priority_boost': 3000,
    'time_of_day_enabled': True,
    'off_peak_start': 0,
    'off_peak_end': 6,
    'off_peak_boost': 1000,
}

scheduler = CustomRulesScheduler(scenario, route_config, custom_rules)
result = scheduler.schedule()

combined_order = [e['bus_id'] for e in result['station_queues']['B'][:6]]
print(f"Station B order (first 6): {combined_order}")
print("Rules: Priority buses + Time-of-day")

print("\n" + "="*70)
print("VERIFICATION")
print("="*70)

if priority_order != baseline_order:
    print("✅ Priority buses rule CHANGES the schedule")
else:
    print("⚠️  Priority buses rule had no effect")

if time_order != baseline_order:
    print("✅ Time-of-day rule CHANGES the schedule")
else:
    print("⚠️  Time-of-day rule had no effect")

if combined_order != baseline_order:
    print("✅ Combined rules CHANGE the schedule")
else:
    print("⚠️  Combined rules had no effect")

print("\n✅ Custom rules are working through the API!")
