"""
Quick validation test for the scheduler.
Tests basic functionality and constraint satisfaction.
"""

import sys
sys.path.insert(0, 'src')

from scheduler import schedule_scenario

def validate_schedule(result):
    """Validate that the schedule satisfies hard constraints."""
    if result['status'] != 'SUCCESS':
        print(f"❌ Schedule failed: {result.get('message', 'Unknown error')}")
        return False

    print("✅ Schedule generated successfully")

    # Check 1: All buses have charging plans
    for bus in result['buses']:
        if not bus['charging_plan']:
            print(f"❌ Bus {bus['bus_id']} has no charging plan")
            return False

    print(f"✅ All {len(result['buses'])} buses have charging plans")

    # Check 2: All charges are exactly 25 minutes
    for bus in result['buses']:
        for charge in bus['charging_plan']:
            start_h, start_m = map(int, charge['charging_start'].split(':'))
            end_h, end_m = map(int, charge['charging_end'].split(':'))
            duration = (end_h * 60 + end_m) - (start_h * 60 + start_m)

            if duration != 25:
                print(f"❌ Bus {bus['bus_id']} at station {charge['station']}: charge duration = {duration} min (expected 25)")
                return False

    print("✅ All charges are exactly 25 minutes")

    # Check 3: No charger conflicts (simplified check)
    for station in ['A', 'B', 'C', 'D']:
        queue = result['station_queues'][station]
        for i in range(len(queue) - 1):
            curr_end = queue[i]['charging_end']
            next_start = queue[i+1]['charging_start']

            curr_h, curr_m = map(int, curr_end.split(':'))
            next_h, next_m = map(int, next_start.split(':'))

            curr_minutes = curr_h * 60 + curr_m
            next_minutes = next_h * 60 + next_m

            if curr_minutes > next_minutes:
                print(f"❌ Station {station}: overlap detected between {queue[i]['bus_id']} and {queue[i+1]['bus_id']}")
                return False

    print("✅ No charger conflicts detected")

    # Check 4: Print metrics
    print(f"\n📊 Metrics:")
    print(f"   Max individual wait: {result['metrics']['max_individual_wait']} min")
    print(f"   Average wait: {result['metrics']['avg_wait']:.1f} min")
    print(f"   Total system wait: {result['metrics']['total_system_wait']} min")

    return True

if __name__ == "__main__":
    print("Testing Scenario 1: Even Spacing\n" + "="*50)
    result = schedule_scenario(1)
    success = validate_schedule(result)

    if success:
        print("\n✅ All validation checks passed!")
    else:
        print("\n❌ Validation failed!")
        sys.exit(1)
