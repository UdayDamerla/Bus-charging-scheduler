"""
Test that weights actually affect the schedule.

This is PROOF that different weights produce different results.
"""

import sys
import copy
sys.path.insert(0, 'src')

from scheduler import BusChargingScheduler, load_scenario

print("="*70)
print("PROOF: Weights Affect the Schedule")
print("="*70)

# Use Scenario 2 (bunched start) - has lots of contention
scenario, route_config = load_scenario(2)

# Test configurations
configs = [
    {"name": "Default (balanced)", "weights": {"individual_bus": 1.0, "operator_balance": 1.0, "overall_efficiency": 1.0}},
    {"name": "High individual_bus", "weights": {"individual_bus": 5.0, "operator_balance": 0.1, "overall_efficiency": 0.1}},
    {"name": "High operator_balance", "weights": {"individual_bus": 0.1, "operator_balance": 5.0, "overall_efficiency": 0.1}},
    {"name": "High overall_efficiency", "weights": {"individual_bus": 0.1, "operator_balance": 0.1, "overall_efficiency": 5.0}},
]

results = []
for config in configs:
    scenario_copy = copy.deepcopy(scenario)
    scenario_copy['weights'] = config['weights']

    result = BusChargingScheduler(scenario_copy, route_config).schedule()
    results.append({
        'name': config['name'],
        'queue': [e['bus_id'] for e in result['station_queues']['B']],
        'operator_waits': {op: stats['total_wait'] for op, stats in result['metrics']['per_operator'].items()},
        'max_wait': result['metrics']['max_individual_wait'],
        'total_wait': result['metrics']['total_system_wait']
    })

# Print results
for r in results:
    print(f"\n{r['name']}:")
    print(f"  Station B order (first 8): {r['queue'][:8]}")
    print(f"  Operator waits: KPN={r['operator_waits']['kpn']}, Freshbus={r['operator_waits']['freshbus']}, Flixbus={r['operator_waits']['flixbus']}")
    print(f"  Max individual wait: {r['max_wait']} min")

# Verify differences
print("\n" + "="*70)
print("VERIFICATION")
print("="*70)

all_same = True
for i in range(1, len(results)):
    if results[i]['queue'] != results[0]['queue']:
        all_same = False
        print(f"✅ '{results[i]['name']}' produces DIFFERENT order than default")
    else:
        print(f"⚠️  '{results[i]['name']}' produces SAME order as default")

if not all_same:
    print("\n✅ CONFIRMED: Different weights produce different schedules!")
else:
    print("\n❌ PROBLEM: All weights produce the same schedule")

# Show specific impact
print("\n" + "="*70)
print("IMPACT OF OPERATOR_BALANCE WEIGHT")
print("="*70)
print("\nWhen operator_balance is HIGH (5.0):")
print(f"  Freshbus total wait: {results[2]['operator_waits']['freshbus']} min")
print("\nWhen operator_balance is LOW (0.1):")
print(f"  Freshbus total wait: {results[1]['operator_waits']['freshbus']} min")
print(f"\nDifference: {results[1]['operator_waits']['freshbus'] - results[2]['operator_waits']['freshbus']} minutes saved for Freshbus!")
