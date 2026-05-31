"""
Bus Charging Scheduler - Greedy Simulation Approach

Takes a scenario with bus schedules and figures out charging assignments.
Each bus gets assigned charging stations and times, respecting:
- Battery range (240 km max between charges)
- Charger availability (one bus at a time per station)
- Travel times based on distance and speed

The approach is simple: process buses in arrival order at each station,
assign the next available charger slot, track waits.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
import heapq
from collections import defaultdict


class BusChargingScheduler:
    """
    Schedules electric bus charging using a greedy first-come-first-served approach.

    Buses arrive at stations in order, get the next available charger slot.
    Wait times accumulate when chargers are busy.
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

    def _calculate_priority(self, bus: Dict, current_wait: int) -> float:
        """
        Calculate priority score for a bus at a charging station.

        Lower score = higher priority (will charge first).

        Incorporates:
        - Individual wait time (penalize long waits)
        - Operator balance (penalize operators with high cumulative waits)
        - Departure order (earlier departures get slight priority)
        """
        w1 = self.weights['individual_bus']
        w2 = self.weights['operator_balance']
        w3 = self.weights['overall_efficiency']

        # Component 1: Individual wait (current wait for this bus)
        individual_score = w1 * current_wait

        # Component 2: Operator balance (use cumulative operator wait from state)
        # This will be updated dynamically during scheduling
        operator_score = w2 * bus.get('_operator_cumulative_wait', 0)

        # Component 3: Overall efficiency (favor earlier departures to minimize total time)
        departure_order = bus.get('_departure_order', 0)
        efficiency_score = w3 * departure_order

        return individual_score + operator_score + efficiency_score

    def schedule(self) -> Dict:
        """
        Main scheduling method - greedy simulation.

        For each bus, figure out when it arrives at each required station,
        then assign charger slots in arrival order.
        """
        # Track when each bus arrives at each station
        bus_states = {}
        for idx, bus in enumerate(self.buses):
            bus_id = bus['id']
            direction = bus['direction']
            departure_minutes = self._parse_time(bus['departure_time'])

            # Add some metadata for potential priority scoring later
            bus['_departure_order'] = idx
            bus['_operator_cumulative_wait'] = 0

            required_stations = self._get_required_stations(direction)

            bus_states[bus_id] = {
                'bus': bus,
                'direction': direction,
                'departure_time': departure_minutes,
                'required_stations': required_stations,
                'current_station_idx': 0,
                'current_time': departure_minutes,
                'charging_plan': [],
                'total_wait': 0
            }

        # Track when chargers become available
        charger_availability = {station: 0 for station in ['A', 'B', 'C', 'D']}

        # Track operator cumulative waits
        operator_waits = defaultdict(int)

        # Station queues for output
        station_queues = {station: [] for station in ['A', 'B', 'C', 'D']}

        # Calculate arrival times at each station for each bus
        events = []  # (arrival_time, bus_id, station)

        for bus_id, state in bus_states.items():
            bus = state['bus']
            direction = state['direction']
            departure_time = state['departure_time']
            required_stations = state['required_stations']

            # Calculate when this bus arrives at each required station
            if direction == "Bengaluru→Kochi":
                prev_location = 'Bengaluru'
                prev_time = departure_time

                for station_id in required_stations:
                    distance = self.station_distances[station_id] - self.station_distances[prev_location]
                    travel_time = self._calculate_travel_time(distance)
                    arrival_time = prev_time + travel_time

                    heapq.heappush(events, (arrival_time, bus_id, station_id))

                    # Assume charging happens (for next station calculation)
                    prev_location = station_id
                    prev_time = arrival_time + self.charging_time

            else:  # Kochi→Bengaluru
                prev_location = 'Kochi'
                prev_time = departure_time

                for station_id in required_stations:
                    distance = self.station_distances[prev_location] - self.station_distances[station_id]
                    travel_time = self._calculate_travel_time(distance)
                    arrival_time = prev_time + travel_time

                    heapq.heappush(events, (arrival_time, bus_id, station_id))

                    prev_location = station_id
                    prev_time = arrival_time + self.charging_time

        # Now assign charging slots
        processed = {}  # (bus_id, station_id) -> charge details

        # Group arrivals by station
        station_events = defaultdict(list)
        for arrival_time, bus_id, station_id in events:
            station_events[station_id].append((arrival_time, bus_id))

        # Process each station's queue
        for station_id in ['A', 'B', 'C', 'D']:
            arrivals = sorted(station_events[station_id])  # Sort by arrival time

            for arrival_time, bus_id in arrivals:
                bus = bus_states[bus_id]['bus']

                # Charger available = max(when bus arrives, when charger is free)
                earliest_start = max(arrival_time, charger_availability[station_id])
                wait_time = earliest_start - arrival_time

                charging_start = earliest_start
                charging_end = charging_start + self.charging_time

                # Update when this charger is next available
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

                # Update operator wait
                operator = bus['operator']
                operator_waits[operator] += wait_time
                bus['_operator_cumulative_wait'] = operator_waits[operator]

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

        # Sort station queues
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
