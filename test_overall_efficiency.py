"""
Test Overall Efficiency Weight - Does it actually affect the schedule?
"""

import sys
import copy
sys.path.insert(0, 'src')

from scheduler import BusChargingScheduler, load_scenario

print("="*70)
print("Testing Overall Efficiency Weight")
print("="*70)

# Use Scenario 2 (bunched start) - has lots of contention
scenario, route_config = load_scenario(2)

# Test 1: Low overall_efficiency (0.1)
print("\n--- Test 1: Low Overall Efficiency (0.1) ---")
scenario_low = copy.deepcopy(scenario)
scenario_low['weights'] = {
    'individual_bus': 1.0,
    'operator_balance': 1.0,
    'overall_efficiency': 0.1  # LOW
}

scheduler_low = BusChargingScheduler(scenario_low, route_config)
result_low = scheduler_low.schedule()

station_b_low = [e['bus_id'] for e in result_low['station_queues']['B'][:8]]
print(f"Station B order (first 8): {station_b_low}")
print(f"Max wait: {result_low['metrics']['max_individual_wait']} min")
print(f"Avg wait: {result_low['metrics']['avg_wait']:.1f} min")

# Test 2: High overall_efficiency (5.0)
print("\n--- Test 2: High Overall Efficiency (5.0) ---")
scenario_high = copy.deepcopy(scenario)
scenario_high['weights'] = {
    'individual_bus': 1.0,
    'operator_balance': 1.0,
    'overall_efficiency': 5.0  # HIGH
}

scheduler_high = BusChargingScheduler(scenario_high, route_config)
result_high = scheduler_high.schedule()

station_b_high = [e['bus_id'] for e in result_high['station_queues']['B'][:8]]
print(f"Station B order (first 8): {station_b_high}")
print(f"Max wait: {result_high['metrics']['max_individual_wait']} min")
print(f"Avg wait: {result_high['metrics']['avg_wait']:.1f} min")

# Compare
print("\n" + "="*70)
print("COMPARISON")
print("="*70)

if station_b_low != station_b_high:
    print("✅ Overall Efficiency weight DOES affect the schedule!")
    print(f"\nOrder changed:")
    for i, (low, high) in enumerate(zip(station_b_low, station_b_high), 1):
        if low != high:
            print(f"  Position {i}: {low} → {high}")
else:
    print("❌ Overall Efficiency weight has NO effect - same order")

print(f"\nMetrics difference:")
print(f"  Max wait: {result_low['metrics']['max_individual_wait']} → {result_high['metrics']['max_individual_wait']} min")
print(f"  Avg wait: {result_low['metrics']['avg_wait']:.1f} → {result_high['metrics']['avg_wait']:.1f} min")

# Test 3: Check if it's actually FCFS when high
print("\n" + "="*70)
print("Test 3: Does HIGH overall_efficiency = FCFS order?")
print("="*70)

# Get arrival times at station B
scenario_test = copy.deepcopy(scenario)
scenario_test['weights'] = {
    'individual_bus': 0.1,
    'operator_balance': 0.1,
    'overall_efficiency': 10.0  # VERY HIGH - should be pure FCFS
}

scheduler_fcfs = BusChargingScheduler(scenario_test, route_config)
result_fcfs = scheduler_fcfs.schedule()

station_b_fcfs = [e['bus_id'] for e in result_fcfs['station_queues']['B'][:8]]
print(f"With overall_efficiency=10.0: {station_b_fcfs}")
print("\nIf this matches the order buses arrive at Station B, it's working!")
