"""
Bus Charging Scheduler - Greedy Simulation with Weighted Priority

Schedules charging for electric buses on the Bengaluru-Kochi route.
When multiple buses are waiting for a charger, weights determine priority.
"""

import json
from typing import Dict, List, Tuple, Any
from collections import defaultdict


class BusChargingScheduler:
    """
    Schedules bus charging using greedy simulation with weighted priority.

    When multiple buses are waiting at a station, the priority function
    (based on scenario weights) determines who charges next.
    """

    def __init__(self, scenario: Dict, route_config: Dict):
        self.scenario = scenario
        self.route_config = route_config
        self.buses = scenario['buses']
        self.weights = scenario['weights']

        # Configuration
        self.battery_range = route_config['physical_constants']['battery_range_km']
        self.charging_time = route_config['physical_constants']['charging_time_minutes']
        self.speed = route_config['physical_constants']['speed_kmh']
        self.stations = route_config['route']['stations']
        self.total_distance = route_config['route']['total_distance']
        self.chargers_per_station = route_config['charger_config']

        # Station distances from Bengaluru
        self.station_distances = self._build_station_distances()

    def _build_station_distances(self) -> Dict:
        distances = {'Bengaluru': 0}
        for station in self.stations:
            distances[station['id']] = station['distance_from_bengaluru']
        distances['Kochi'] = self.total_distance
        return distances

    def _parse_time(self, time_str: str) -> int:
        """HH:MM to minutes since midnight."""
        h, m = map(int, time_str.split(':'))
        return h * 60 + m

    def _format_time(self, minutes: int) -> str:
        """Minutes since midnight to HH:MM."""
        return f"{minutes // 60:02d}:{minutes % 60:02d}"

    def _get_required_stations(self, direction: str) -> List[str]:
        """Which stations must this bus use? B and D for the 540km trip."""
        if direction == "Bengaluru→Kochi":
            return ['B', 'D']
        else:
            return ['D', 'B']

    def _travel_time(self, distance_km: float) -> int:
        """Minutes to travel a given distance."""
        return int(distance_km / self.speed * 60)

    def _calculate_priority(self, bus_id: str, operator: str, arrival_time: int,
                           charger_free_time: int, operator_total_waits: Dict[str, int]) -> float:
        """
        Calculate priority score. LOWER = charges first.

        Weights:
        - individual_bus: Prioritize buses that arrived earlier (reduce max wait)
        - operator_balance: Prioritize operators with less cumulative wait time
        - overall_efficiency: Prioritize by arrival order (FCFS for throughput)
        """
        w1 = self.weights['individual_bus']
        w2 = self.weights['operator_balance']
        w3 = self.weights['overall_efficiency']

        # How long has this bus been waiting?
        wait_so_far = max(0, charger_free_time - arrival_time)

        # Individual: buses waiting longer should have LOWER score (higher priority)
        # So we use negative wait
        individual_component = -w1 * wait_so_far

        # Operator balance: operators with MORE cumulative wait should have LOWER score
        # So other operators can catch up
        operator_component = -w2 * operator_total_waits.get(operator, 0)

        # Overall efficiency: earlier arrivals have LOWER score (FCFS)
        efficiency_component = w3 * arrival_time

        return individual_component + operator_component + efficiency_component

    def schedule(self) -> Dict:
        """
        Main scheduling algorithm.

        1. Calculate when each bus arrives at each required station
        2. At each station, process waiting buses by priority
        3. Track wait times and update operator totals
        """
        # Track cumulative wait per operator (for balancing)
        operator_total_waits = defaultdict(int)

        # Store results
        bus_schedules = {}  # bus_id -> {charging_plan, total_wait, ...}
        station_queues = {s: [] for s in ['A', 'B', 'C', 'D']}

        # Initialize bus data
        for bus in self.buses:
            bus_id = bus['id']
            bus_schedules[bus_id] = {
                'bus': bus,
                'direction': bus['direction'],
                'operator': bus['operator'],
                'departure_time': self._parse_time(bus['departure_time']),
                'charging_events': {},  # station -> {arrival, wait, start, end}
                'total_wait': 0
            }

        # Process each station independently
        # Both directions use B and D, so we handle all buses together at each station

        for station_id in ['B', 'D']:  # Only B and D are used
            # Collect all buses that need to charge at this station
            # and calculate their arrival times

            arrivals = []  # [(arrival_time, bus_id, operator)]

            for bus_id, data in bus_schedules.items():
                direction = data['direction']
                required = self._get_required_stations(direction)

                if station_id not in required:
                    continue

                # Calculate arrival time at this station
                station_idx = required.index(station_id)

                if station_idx == 0:
                    # First charging station
                    if direction == "Bengaluru→Kochi":
                        # From Bengaluru to station
                        distance = self.station_distances[station_id]
                        arrival = data['departure_time'] + self._travel_time(distance)
                    else:
                        # From Kochi to station (D is first for Kochi->Bengaluru)
                        distance = self.total_distance - self.station_distances[station_id]
                        arrival = data['departure_time'] + self._travel_time(distance)
                else:
                    # Second charging station - need to account for first station's delay
                    prev_station = required[0]
                    prev_event = data['charging_events'].get(prev_station)

                    if prev_event:
                        # Travel from previous station to this one
                        if direction == "Bengaluru→Kochi":
                            distance = self.station_distances[station_id] - self.station_distances[prev_station]
                        else:
                            distance = self.station_distances[prev_station] - self.station_distances[station_id]
                        arrival = prev_event['charging_end'] + self._travel_time(distance)
                    else:
                        # Shouldn't happen, but calculate from departure as fallback
                        if direction == "Bengaluru→Kochi":
                            distance = self.station_distances[station_id]
                        else:
                            distance = self.total_distance - self.station_distances[station_id]
                        arrival = data['departure_time'] + self._travel_time(distance)

                arrivals.append((arrival, bus_id, data['operator']))

            # Sort by arrival time initially
            arrivals.sort(key=lambda x: x[0])

            # Now assign charger slots using priority when there's contention
            charger_free_time = 0
            pending = list(arrivals)  # Buses waiting to be scheduled

            while pending:
                # Find all buses that have arrived and are waiting
                # A bus is "waiting" if it arrived before or when the charger becomes free
                waiting = [(arr, bid, op) for arr, bid, op in pending if arr <= charger_free_time]

                if not waiting:
                    # No one waiting yet - take the next arrival
                    waiting = [pending[0]]

                if len(waiting) == 1:
                    # No contention - just schedule this bus
                    winner = waiting[0]
                else:
                    # CONTENTION! Multiple buses waiting - use priority
                    scored = []
                    for arr, bid, op in waiting:
                        priority = self._calculate_priority(
                            bid, op, arr, charger_free_time, operator_total_waits
                        )
                        scored.append((priority, arr, bid, op))

                    # Sort by priority (lowest first)
                    scored.sort(key=lambda x: x[0])
                    winner = (scored[0][1], scored[0][2], scored[0][3])

                # Schedule the winner
                arrival_time, bus_id, operator = winner
                pending.remove(winner)

                # Calculate charging times
                charging_start = max(arrival_time, charger_free_time)
                wait_time = charging_start - arrival_time
                charging_end = charging_start + self.charging_time

                # Update charger availability
                charger_free_time = charging_end

                # Record the charging event
                bus_schedules[bus_id]['charging_events'][station_id] = {
                    'arrival_time': arrival_time,
                    'wait_time': wait_time,
                    'charging_start': charging_start,
                    'charging_end': charging_end
                }
                bus_schedules[bus_id]['total_wait'] += wait_time

                # Update operator cumulative wait
                operator_total_waits[operator] += wait_time

                # Add to station queue
                station_queues[station_id].append({
                    'bus_id': bus_id,
                    'operator': operator,
                    'charging_start': self._format_time(charging_start),
                    'charging_end': self._format_time(charging_end)
                })

        # Build final result
        result = {
            'status': 'SUCCESS',
            'buses': [],
            'station_queues': station_queues,
            'metrics': {}
        }

        for bus_id, data in bus_schedules.items():
            bus = data['bus']
            direction = data['direction']
            required = self._get_required_stations(direction)

            # Build charging plan
            charging_plan = []
            for station_id in required:
                event = data['charging_events'].get(station_id)
                if event:
                    charging_plan.append({
                        'station': station_id,
                        'arrival_time': self._format_time(event['arrival_time']),
                        'wait_time_minutes': event['wait_time'],
                        'charging_start': self._format_time(event['charging_start']),
                        'charging_end': self._format_time(event['charging_end'])
                    })

            # Calculate final arrival time
            last_station = required[-1]
            last_event = data['charging_events'][last_station]

            if direction == "Bengaluru→Kochi":
                remaining = self.total_distance - self.station_distances[last_station]
            else:
                remaining = self.station_distances[last_station]

            final_arrival = last_event['charging_end'] + self._travel_time(remaining)
            trip_time = final_arrival - data['departure_time']

            result['buses'].append({
                'bus_id': bus_id,
                'operator': bus['operator'],
                'direction': direction,
                'departure_time': bus['departure_time'],
                'charging_plan': charging_plan,
                'arrival_time': self._format_time(final_arrival),
                'total_trip_time_minutes': trip_time,
                'total_wait_time_minutes': data['total_wait']
            })

        # Sort station queues by time
        for station in result['station_queues']:
            result['station_queues'][station].sort(
                key=lambda x: self._parse_time(x['charging_start'])
            )

        # Calculate metrics
        all_waits = [b['total_wait_time_minutes'] for b in result['buses']]
        result['metrics'] = {
            'max_individual_wait': max(all_waits) if all_waits else 0,
            'avg_wait': sum(all_waits) / len(all_waits) if all_waits else 0,
            'total_system_wait': sum(all_waits)
        }

        # Per-operator metrics
        op_waits = defaultdict(list)
        for bus in result['buses']:
            op_waits[bus['operator']].append(bus['total_wait_time_minutes'])

        result['metrics']['per_operator'] = {
            op: {
                'bus_count': len(waits),
                'total_wait': sum(waits),
                'avg_wait': sum(waits) / len(waits),
                'max_wait': max(waits)
            }
            for op, waits in op_waits.items()
        }

        return result


def load_scenario(scenario_id: int) -> Tuple[Dict, Dict]:
    """Load scenario and route config from JSON files."""
    with open(f'scenarios/scenario_{scenario_id}.json', 'r') as f:
        scenario = json.load(f)
    with open('data/route_config.json', 'r') as f:
        route_config = json.load(f)
    return scenario, route_config


def schedule_scenario(scenario_id: int) -> Dict:
    """Main entry point."""
    scenario, route_config = load_scenario(scenario_id)
    return BusChargingScheduler(scenario, route_config).schedule()
