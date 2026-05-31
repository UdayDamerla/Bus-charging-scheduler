"""
Demonstration: Adding a New Rule (Priority Buses)

This file shows how to extend the scheduler with a new rule.
In this example, we add support for "priority buses" that get
to charge before regular buses when there's contention.

This demonstrates:
1. Extending the data schema (add priority field to bus)
2. Modifying the priority calculation
3. The change is SMALL and ADDITIVE - no rewrite needed
"""

import sys
import json
import copy
sys.path.insert(0, 'src')

from scheduler import BusChargingScheduler, load_scenario

print("="*70)
print("DEMONSTRATION: Adding Priority Bus Rule")
print("="*70)

# Step 1: Show the original scheduler behavior
print("\n--- STEP 1: Original Behavior (no priority) ---")
scenario, route_config = load_scenario(2)  # Bunched start - has contention

scheduler = BusChargingScheduler(scenario, route_config)
result = scheduler.schedule()

print(f"Station B queue (first 6 buses):")
for entry in result['station_queues']['B'][:6]:
    print(f"  {entry['bus_id']} ({entry['operator']}) - charges at {entry['charging_start']}")

# Step 2: Show how to add priority to the data
print("\n--- STEP 2: Add priority flag to data ---")
print("We mark bus-BK-05 and bus-KB-03 as priority buses.")

# Make a copy and add priority flags
scenario_with_priority = copy.deepcopy(scenario)
for bus in scenario_with_priority['buses']:
    if bus['id'] in ['bus-BK-05', 'bus-KB-03']:
        bus['priority'] = True
        print(f"  Added priority=True to {bus['id']}")

# Step 3: Create a modified scheduler that respects priority
print("\n--- STEP 3: Modify priority calculation (5 lines of code) ---")


class PriorityBusScheduler(BusChargingScheduler):
    """
    Extended scheduler that gives priority buses preferential treatment.

    This is the ONLY change needed - override one method.
    """

    def _calculate_priority(self, bus, arrival_time, current_wait, operator_cumulative_wait):
        # Call parent method to get base priority
        base_priority = super()._calculate_priority(
            bus, arrival_time, current_wait, operator_cumulative_wait
        )

        # Priority buses get a huge boost (subtract 10000 from their score)
        # Lower score = higher priority, so this makes them go first
        if bus.get('priority', False):
            return base_priority - 10000

        return base_priority


print("Code change:")
print("""
class PriorityBusScheduler(BusChargingScheduler):
    def _calculate_priority(self, bus, arrival_time, current_wait, operator_cumulative_wait):
        base_priority = super()._calculate_priority(...)

        # Priority buses get a huge boost
        if bus.get('priority', False):
            return base_priority - 10000

        return base_priority
""")

# Step 4: Run the modified scheduler
print("\n--- STEP 4: Run with priority buses ---")

priority_scheduler = PriorityBusScheduler(scenario_with_priority, route_config)
priority_result = priority_scheduler.schedule()

print(f"Station B queue (first 6 buses):")
for entry in priority_result['station_queues']['B'][:6]:
    is_priority = "⭐ PRIORITY" if entry['bus_id'] in ['bus-BK-05', 'bus-KB-03'] else ""
    print(f"  {entry['bus_id']} ({entry['operator']}) - charges at {entry['charging_start']} {is_priority}")

# Step 5: Compare the results
print("\n--- STEP 5: Compare Results ---")

def find_bus_wait(result, bus_id):
    for bus in result['buses']:
        if bus['bus_id'] == bus_id:
            return bus['total_wait_time_minutes']
    return None

print("\nWait times for priority buses:")
for bus_id in ['bus-BK-05', 'bus-KB-03']:
    original_wait = find_bus_wait(result, bus_id)
    priority_wait = find_bus_wait(priority_result, bus_id)
    improvement = original_wait - priority_wait
    print(f"  {bus_id}: {original_wait} min → {priority_wait} min (saved {improvement} min)")

print("\n" + "="*70)
print("SUMMARY")
print("="*70)
print("""
To add a new rule like "priority buses":

1. DATA CHANGE: Add a field to the bus object
   {"id": "bus-BK-05", ..., "priority": true}

2. CODE CHANGE: Override _calculate_priority() method (5-10 lines)
   - Check for the new field
   - Adjust priority score accordingly

That's it! No rewrite of the scheduling engine needed.
The rule is ADDITIVE - it slots into the existing priority framework.
""")

# Verify the priority buses actually improved
bk05_original = find_bus_wait(result, 'bus-BK-05')
bk05_priority = find_bus_wait(priority_result, 'bus-BK-05')

if bk05_priority < bk05_original:
    print("✅ VERIFIED: Priority bus rule works! Priority buses wait less.")
else:
    print("⚠️  Priority bus had no effect (may have arrived with no contention)")
