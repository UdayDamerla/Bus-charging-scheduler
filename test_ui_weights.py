"""
Test what the UI would show for Scenario 2 with different weights
"""
import sys
sys.path.insert(0, 'src')
import copy
from scheduler import BusChargingScheduler, load_scenario

print("Testing Scenario 2 (has contention) with UI weight changes\n")

scenario, route_config = load_scenario(2)

# Test 1: Default weights (like UI initial state)
print("="*70)
print("DEFAULT WEIGHTS (what you see first)")
print("="*70)
result1 = BusChargingScheduler(scenario, route_config).schedule()
print(f"Station B (first 8): {[e['bus_id'] for e in result1['station_queues']['B'][:8]]}")

# Test 2: Move Overall Efficiency to 0.1 (like moving slider left)
print("\n" + "="*70)
print("MOVE OVERALL EFFICIENCY TO 0.1")
print("="*70)
scenario2 = copy.deepcopy(scenario)
scenario2['weights']['overall_efficiency'] = 0.1
result2 = BusChargingScheduler(scenario2, route_config).schedule()
print(f"Station B (first 8): {[e['bus_id'] for e in result2['station_queues']['B'][:8]]}")

# Test 3: Move Overall Efficiency to 5.0 (like moving slider right)
print("\n" + "="*70)
print("MOVE OVERALL EFFICIENCY TO 5.0")
print("="*70)
scenario3 = copy.deepcopy(scenario)
scenario3['weights']['overall_efficiency'] = 5.0
result3 = BusChargingScheduler(scenario3, route_config).schedule()
print(f"Station B (first 8): {[e['bus_id'] for e in result3['station_queues']['B'][:8]]}")

# Compare
print("\n" + "="*70)
print("WHAT YOU SHOULD SEE IN UI:")
print("="*70)
if result1['station_queues']['B'][:8] != result3['station_queues']['B'][:8]:
    print("✅ Moving slider should change the order")
else:
    print("⚠️  Slider doesn't change order (might be cached)")
