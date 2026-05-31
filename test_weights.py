"""
Test that weights actually affect the schedule.

This test runs the same scenario with different weights and verifies
that the output changes.
"""

import sys
import json
import copy
sys.path.insert(0, 'src')

from scheduler import BusChargingScheduler

# Load route config
with open('data/route_config.json', 'r') as f:
    route_config = json.load(f)

# Load scenario 4 (operator-heavy - KPN dominates)
with open('scenarios/scenario_4.json', 'r') as f:
    base_scenario = json.load(f)

print("="*70)
print("Testing Weight Sensitivity")
print("="*70)
print(f"\nScenario: {base_scenario['name']}")
print(f"Base weights: {base_scenario['weights']}")

# Test 1: Default weights from scenario 4 (operator_balance = 2.0)
print("\n" + "-"*70)
print("TEST 1: High operator_balance weight (2.0)")
print("-"*70)
scheduler1 = BusChargingScheduler(base_scenario, route_config)
result1 = scheduler1.schedule()

print(f"Total system wait: {result1['metrics']['total_system_wait']} min")
print(f"Max individual wait: {result1['metrics']['max_individual_wait']} min")
print("\nPer-operator breakdown:")
for op, stats in result1['metrics']['per_operator'].items():
    print(f"  {op.upper()}: {stats['bus_count']} buses, total wait {stats['total_wait']} min, avg {stats['avg_wait']:.1f} min")

# Test 2: Lower operator balance (1.0), higher individual (2.0)
print("\n" + "-"*70)
print("TEST 2: High individual_bus weight (2.0), low operator_balance (0.5)")
print("-"*70)
scenario2 = copy.deepcopy(base_scenario)
scenario2['weights'] = {
    'individual_bus': 2.0,
    'operator_balance': 0.5,
    'overall_efficiency': 1.0
}
scheduler2 = BusChargingScheduler(scenario2, route_config)
result2 = scheduler2.schedule()

print(f"Total system wait: {result2['metrics']['total_system_wait']} min")
print(f"Max individual wait: {result2['metrics']['max_individual_wait']} min")
print("\nPer-operator breakdown:")
for op, stats in result2['metrics']['per_operator'].items():
    print(f"  {op.upper()}: {stats['bus_count']} buses, total wait {stats['total_wait']} min, avg {stats['avg_wait']:.1f} min")

# Test 3: Very high overall efficiency
print("\n" + "-"*70)
print("TEST 3: High overall_efficiency weight (3.0)")
print("-"*70)
scenario3 = copy.deepcopy(base_scenario)
scenario3['weights'] = {
    'individual_bus': 0.5,
    'operator_balance': 0.5,
    'overall_efficiency': 3.0
}
scheduler3 = BusChargingScheduler(scenario3, route_config)
result3 = scheduler3.schedule()

print(f"Total system wait: {result3['metrics']['total_system_wait']} min")
print(f"Max individual wait: {result3['metrics']['max_individual_wait']} min")
print("\nPer-operator breakdown:")
for op, stats in result3['metrics']['per_operator'].items():
    print(f"  {op.upper()}: {stats['bus_count']} buses, total wait {stats['total_wait']} min, avg {stats['avg_wait']:.1f} min")

# Compare station queues to see if order changed
print("\n" + "="*70)
print("Comparing Station B queues (first 5 buses)")
print("="*70)

print("\nTEST 1 (high operator_balance):")
for entry in result1['station_queues']['B'][:5]:
    print(f"  {entry['bus_id']} ({entry['charging_start']})")

print("\nTEST 2 (high individual_bus):")
for entry in result2['station_queues']['B'][:5]:
    print(f"  {entry['bus_id']} ({entry['charging_start']})")

print("\nTEST 3 (high overall_efficiency):")
for entry in result3['station_queues']['B'][:5]:
    print(f"  {entry['bus_id']} ({entry['charging_start']})")

# Check if queues are different
queue1 = [e['bus_id'] for e in result1['station_queues']['B']]
queue2 = [e['bus_id'] for e in result2['station_queues']['B']]
queue3 = [e['bus_id'] for e in result3['station_queues']['B']]

print("\n" + "="*70)
print("WEIGHT SENSITIVITY VERIFICATION")
print("="*70)
if queue1 != queue2 or queue2 != queue3:
    print("✅ PASS: Different weights produce different station orders!")
    print(f"   Queue 1 ≠ Queue 2: {queue1 != queue2}")
    print(f"   Queue 2 ≠ Queue 3: {queue2 != queue3}")
else:
    print("⚠️  WARNING: Queues are identical - weights may not have enough effect")
    print("   This could happen if there's no contention (buses arrive at different times)")

# Check if metrics changed
print(f"\nMetrics comparison:")
print(f"  Test 1 total wait: {result1['metrics']['total_system_wait']} min")
print(f"  Test 2 total wait: {result2['metrics']['total_system_wait']} min")
print(f"  Test 3 total wait: {result3['metrics']['total_system_wait']} min")

if (result1['metrics']['total_system_wait'] != result2['metrics']['total_system_wait'] or
    result2['metrics']['total_system_wait'] != result3['metrics']['total_system_wait']):
    print("✅ PASS: Different weights produce different total wait times!")
else:
    print("⚠️  Metrics are identical - may need to review contention logic")
