"""
Bus Charging Scheduler - Greedy Simulation with Weighted Priority

Takes a scenario with bus schedules and figures out charging assignments.
Each bus gets assigned charging stations and times, respecting:
- Battery range (240 km max between charges)
- Charger availability (one bus at a time per station)
- Travel times based on distance and speed

The weights influence which bus gets priority when multiple buses
are waiting at the same station.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
import heapq
from collections import defaultdict


class BusChargingScheduler:
    """
    Schedules electric bus charging using greedy simulation with weighted priority.

    When multiple buses contend for the same charger, the priority function
    (influenced by weights) determines who charges first.
    """

    def __init__(self, scenario: Dict, route_config: Dict):
        self.scenario = scenario
        self.route_config = route_config
        self.buses = scenario['buses']
        self.weights = scenario['weights']

        # Pull out the configuration
        self.battery_range = route_config['physical_constants']['battery_range_km']
        self.charging_time = route_config['physical_constants']['charging_time_minutes']
        self.speed = route_config['physical_constants']['speed_kmh']
        self.stations = route_config['route']['stations']
        self.total_distance = route_config['route']['total_distance']
        self.chargers_per_station = route_config['charger_config']

        # Build a lookup: station name -> distance from Bengaluru
        self.station_distances = self._build_station_distances()

    def _build_station_distances(self) -> Dict:
        """Build distance lookup for stations and endpoints."""
        distances = {}
        distances['Bengaluru'] = 0

        for station in self.stations:
            distances[station['id']] = station['distance_from_bengaluru']

        distances['Kochi'] = self.total_distance

        return distances

    def _parse_time(self, time_str: str) -> int:
        """Convert HH:MM to minutes since midnight."""
        h, m = map(int, time_str.split(':'))
        return h * 60 + m

    def _format_time(self, minutes: int) -> str:
        """Convert minutes since midnight back to HH:MM."""
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours:02d}:{mins:02d}"

    def _get_required_stations(self, direction: str) -> List[str]:
        """
        Figure out which stations a bus must use to complete the trip.

        For a 540km trip with 240km range, need at least 2 charges.
        Using stations B (at 220km) and D (at 440km) works well.
        """
        if direction == "Bengaluru→Kochi":
            return ['B', 'D']
        else:  # Kochi→Bengaluru
            return ['D', 'B']

    def _calculate_travel_time(self, distance_km: float) -> int:
        """Calculate travel time in minutes for a given distance."""
        return int(distance_km / self.speed * 60)

    def _calculate_priority(self, bus: Dict, arrival_time: int,
                           current_wait: int, operator_cumulative_wait: int) -> float:
        """
        Calculate priority score for a bus at a charging station.

        Lower score = higher priority (will charge first).

        The weights from the scenario influence this:
        - individual_bus: Prioritize buses that have been waiting longest
        - operator_balance: Prioritize operators with lower cumulative wait
        - overall_efficiency: Prioritize earlier arrivals to minimize total time
        """
        w1 = self.weights['individual_bus']
        w2 = self.weights['operator_balance']
        w3 = self.weights['overall_efficiency']

        # Component 1: Individual wait - buses waiting longer get lower score (higher priority)
        # Negate because higher wait should mean higher priority (lower score)
        individual_score = -w1 * current_wait

        # Component 2: Operator balance - operators with high cumulative wait get lower score
        # So other operators' buses can catch up
        operator_score = w2 * operator_cumulative_wait

        # Component 3: Overall efficiency - earlier arrivals get lower score (process in order)
        efficiency_score = w3 * arrival_time

        return individual_score + operator_score + efficiency_score

    def schedule(self) -> Dict:
        """
        Main scheduling method - greedy simulation with weighted priority.

        For each bus, figure out when it arrives at each required station,
        then assign charger slots based on weighted priority when there's contention.
        """
        # Track state for each bus
        bus_states = {}
        for idx, bus in enumerate(self.buses):
            bus_id = bus['id']
            direction = bus['direction']
            departure_minutes = self._parse_time(bus['departure_time'])

            required_stations = self._get_required_stations(direction)

            bus_states[bus_id] = {
                'bus': bus,
                'direction': direction,
                'departure_time': departure_minutes,
                'required_stations': required_stations,
                'charging_plan': [],
                'total_wait': 0,
                'current_time': departure_minutes  # Tracks bus progress through route
            }

        # Track when chargers become available at each station
        charger_availability = {station: 0 for station in ['A', 'B', 'C', 'D']}

        # Track cumulative wait time per operator (for balancing)
        operator_cumulative_waits = defaultdict(int)

        # Process station by station in route order
        # First handle all buses at station B/D (depending on direction), then move forward

        # Collect all (bus, station) pairs that need scheduling
        scheduling_tasks = []

        for bus_id, state in bus_states.items():
            bus = state['bus']
            direction = state['direction']
            departure_time = state['departure_time']
            required_stations = state['required_stations']

            # Calculate initial arrival times at each required station
            if direction == "Bengaluru→Kochi":
                prev_location = 'Bengaluru'
                prev_time = departure_time

                for station_id in required_stations:
                    distance = self.station_distances[station_id] - self.station_distances[prev_location]
                    travel_time = self._calculate_travel_time(distance)
                    arrival_time = prev_time + travel_time

                    scheduling_tasks.append({
                        'bus_id': bus_id,
                        'station_id': station_id,
                        'arrival_time': arrival_time,
                        'operator': bus['operator']
                    })

                    # For calculating arrival at next station, assume charging happens
                    prev_location = station_id
                    prev_time = arrival_time + self.charging_time

            else:  # Kochi→Bengaluru
                prev_location = 'Kochi'
                prev_time = departure_time

                for station_id in required_stations:
                    distance = self.station_distances[prev_location] - self.station_distances[station_id]
                    travel_time = self._calculate_travel_time(distance)
                    arrival_time = prev_time + travel_time

                    scheduling_tasks.append({
                        'bus_id': bus_id,
                        'station_id': station_id,
                        'arrival_time': arrival_time,
                        'operator': bus['operator']
                    })

                    prev_location = station_id
                    prev_time = arrival_time + self.charging_time

        # Group tasks by station
        station_tasks = defaultdict(list)
        for task in scheduling_tasks:
            station_tasks[task['station_id']].append(task)

        # Store charging assignments
        processed = {}  # (bus_id, station_id) -> charge details

        # Track actual charging end times to adjust subsequent station arrivals
        bus_actual_times = {}  # bus_id -> last_charging_end_time

        # Process each station
        for station_id in ['A', 'B', 'C', 'D']:
            tasks = station_tasks[station_id]
            if not tasks:
                continue

            # Adjust arrival times based on actual previous charging delays
            for task in tasks:
                bus_id = task['bus_id']
                if bus_id in bus_actual_times:
                    # This bus has already charged at a previous station
                    # Adjust arrival time based on when it actually left
                    state = bus_states[bus_id]
                    direction = state['direction']

                    # Find the previous station in this bus's route
                    required_stations = state['required_stations']
                    station_idx = required_stations.index(station_id)

                    if station_idx > 0:
                        prev_station = required_stations[station_idx - 1]
                        prev_charge = processed.get((bus_id, prev_station))
                        if prev_charge:
                            # Travel time from previous station to this one
                            if direction == "Bengaluru→Kochi":
                                distance = self.station_distances[station_id] - self.station_distances[prev_station]
                            else:
                                distance = self.station_distances[prev_station] - self.station_distances[station_id]

                            travel_time = self._calculate_travel_time(distance)
                            task['arrival_time'] = prev_charge['charging_end'] + travel_time

            # Sort tasks by arrival time first, then apply priority for ties/contention
            tasks.sort(key=lambda t: t['arrival_time'])

            # Now schedule in order, but re-sort when there's contention
            pending = list(tasks)

            while pending:
                # Find all buses that could potentially charge next
                # (arrived before the charger becomes free, or within a window)
                charger_free_time = charger_availability[station_id]

                # Buses that have arrived and are waiting
                contending = []
                for task in pending:
                    # If bus arrives before or shortly after charger is free, it's contending
                    if task['arrival_time'] <= charger_free_time + 5:  # 5 min window for contention
                        contending.append(task)

                if not contending:
                    # No contention - take the earliest arrival
                    contending = [pending[0]]

                # If multiple buses contending, use priority to decide
                if len(contending) > 1:
                    # Calculate priority for each
                    for task in contending:
                        bus_id = task['bus_id']
                        operator = task['operator']

                        # Current wait = how long they'd wait if scheduled now
                        potential_wait = max(0, charger_free_time - task['arrival_time'])

                        task['priority'] = self._calculate_priority(
                            bus_states[bus_id]['bus'],
                            task['arrival_time'],
                            potential_wait,
                            operator_cumulative_waits[operator]
                        )

                    # Sort by priority (lower = higher priority = charges first)
                    contending.sort(key=lambda t: t['priority'])

                # Schedule the winner
                winner = contending[0]
                pending.remove(winner)

                bus_id = winner['bus_id']
                arrival_time = winner['arrival_time']
                operator = winner['operator']

                # Assign charger slot
                earliest_start = max(arrival_time, charger_availability[station_id])
                wait_time = earliest_start - arrival_time

                charging_start = earliest_start
                charging_end = charging_start + self.charging_time

                # Update charger availability
                charger_availability[station_id] = charging_end

                # Record this charge
                processed[(bus_id, station_id)] = {
                    'arrival_time': arrival_time,
                    'wait_time': wait_time,
                    'charging_start': charging_start,
                    'charging_end': charging_end
                }

                # Update bus state
                bus_states[bus_id]['total_wait'] += wait_time
                bus_actual_times[bus_id] = charging_end

                # Update operator cumulative wait
                operator_cumulative_waits[operator] += wait_time

        # Build final result
        result = {
            'status': 'SUCCESS',
            'buses': [],
            'station_queues': {station: [] for station in ['A', 'B', 'C', 'D']},
            'metrics': {}
        }

        for bus_id, state in bus_states.items():
            bus = state['bus']
            direction = state['direction']
            required_stations = state['required_stations']

            charging_plan = []
            for station_id in required_stations:
                charge_info = processed.get((bus_id, station_id))
                if charge_info:
                    charging_plan.append({
                        'station': station_id,
                        'arrival_time': self._format_time(charge_info['arrival_time']),
                        'wait_time_minutes': charge_info['wait_time'],
                        'charging_start': self._format_time(charge_info['charging_start']),
                        'charging_end': self._format_time(charge_info['charging_end'])
                    })

                    # Add to station queue
                    result['station_queues'][station_id].append({
                        'bus_id': bus_id,
                        'operator': bus['operator'],
                        'charging_start': self._format_time(charge_info['charging_start']),
                        'charging_end': self._format_time(charge_info['charging_end'])
                    })

            # Calculate final arrival time
            last_station = required_stations[-1]
            last_charge = processed[(bus_id, last_station)]
            last_charge_end = last_charge['charging_end']

            # Travel from last station to destination
            if direction == "Bengaluru→Kochi":
                remaining_distance = self.station_distances['Kochi'] - self.station_distances[last_station]
            else:
                remaining_distance = self.station_distances[last_station] - self.station_distances['Bengaluru']

            remaining_travel_time = self._calculate_travel_time(remaining_distance)
            arrival_time = last_charge_end + remaining_travel_time

            departure_time = state['departure_time']
            trip_time = arrival_time - departure_time

            result['buses'].append({
                'bus_id': bus_id,
                'operator': bus['operator'],
                'direction': direction,
                'departure_time': bus['departure_time'],
                'charging_plan': charging_plan,
                'arrival_time': self._format_time(arrival_time),
                'total_trip_time_minutes': trip_time,
                'total_wait_time_minutes': state['total_wait']
            })

        # Sort station queues by charging start time
        for station in result['station_queues']:
            result['station_queues'][station].sort(
                key=lambda x: self._parse_time(x['charging_start'])
            )

        # Calculate metrics
        all_waits = [bus['total_wait_time_minutes'] for bus in result['buses']]
        result['metrics'] = {
            'max_individual_wait': max(all_waits) if all_waits else 0,
            'avg_wait': sum(all_waits) / len(all_waits) if all_waits else 0,
            'total_system_wait': sum(all_waits)
        }

        # Add per-operator metrics
        operator_waits = defaultdict(list)
        for bus in result['buses']:
            operator_waits[bus['operator']].append(bus['total_wait_time_minutes'])

        result['metrics']['per_operator'] = {
            op: {
                'total_wait': sum(waits),
                'avg_wait': sum(waits) / len(waits) if waits else 0,
                'max_wait': max(waits) if waits else 0,
                'bus_count': len(waits)
            }
            for op, waits in operator_waits.items()
        }

        return result


def load_scenario(scenario_id: int) -> Tuple[Dict, Dict]:
    """Load scenario and route configuration from JSON files."""
    with open(f'scenarios/scenario_{scenario_id}.json', 'r') as f:
        scenario = json.load(f)

    with open('data/route_config.json', 'r') as f:
        route_config = json.load(f)

    return scenario, route_config


def schedule_scenario(scenario_id: int) -> Dict:
    """Main entry point: schedule a scenario by ID."""
    scenario, route_config = load_scenario(scenario_id)
    scheduler = BusChargingScheduler(scenario, route_config)
    return scheduler.schedule()
