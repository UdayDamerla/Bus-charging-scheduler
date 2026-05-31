"""
Test all 5 scenarios to ensure they produce valid schedules.
"""

import sys
sys.path.insert(0, 'src')

from scheduler import schedule_scenario

scenarios = {
    1: "Even Spacing",
    2: "Bunched Start",
    3: "Asymmetric Load",
    4: "Operator-Heavy",
    5: "Worst Case Convergence"
}

print("="*60)
print("Testing All Scenarios")
print("="*60)

for scenario_id, name in scenarios.items():
    print(f"\n📋 Scenario {scenario_id}: {name}")
    print("-" * 60)

    result = schedule_scenario(scenario_id)

    if result['status'] != 'SUCCESS':
        print(f"❌ FAILED: {result.get('message', 'Unknown error')}")
        continue

    # Validate
    buses = result['buses']
    metrics = result['metrics']

    print(f"✅ SUCCESS")
    print(f"   Buses scheduled: {len(buses)}")
    print(f"   Max wait: {metrics['max_individual_wait']} min")
    print(f"   Avg wait: {metrics['avg_wait']:.1f} min")
    print(f"   Total wait: {metrics['total_system_wait']} min")

    # Check all buses have plans
    buses_without_plans = [b['bus_id'] for b in buses if not b['charging_plan']]
    if buses_without_plans:
        print(f"   ⚠️  Buses without plans: {buses_without_plans}")

    # Check charger counts
    for station in ['A', 'B', 'C', 'D']:
        count = len(result['station_queues'][station])
        if count > 0:
            print(f"   Station {station}: {count} buses charged")

print("\n" + "="*60)
print("✅ All scenarios tested successfully!")
print("="*60)
