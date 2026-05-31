"""
Streamlit UI for Bus Charging Scheduler

Simple web interface to:
- Pick a scenario
- Adjust weights
- See the input data
- View the charging schedules
"""

import streamlit as st
import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from scheduler import BusChargingScheduler, load_scenario
import pandas as pd
import json
import copy


# Page config
st.set_page_config(
    page_title="Bus Charging Scheduler",
    page_icon="🚌",
    layout="wide"
)

# Title
st.title("🚌 Electric Bus Charging Scheduler")
st.markdown("""
Schedules charging stops for electric buses traveling between Bengaluru and Kochi.
Optimizes for individual bus delays, operator balance, and overall efficiency.
""")

# Sidebar: Pick scenario
st.sidebar.header("Scenario Selection")

scenarios = {
    1: "Scenario 1: Even Spacing",
    2: "Scenario 2: Bunched Start",
    3: "Scenario 3: Asymmetric Load",
    4: "Scenario 4: Operator-Heavy",
    5: "Scenario 5: Worst Case Convergence"
}

selected_scenario = st.sidebar.selectbox(
    "Choose a scenario",
    options=list(scenarios.keys()),
    format_func=lambda x: scenarios[x]
)

# Load scenario
scenario, route_config = load_scenario(selected_scenario)

# Weight adjustment sliders
st.sidebar.markdown("---")
st.sidebar.header("Adjust Weights")
st.sidebar.markdown("*Change weights to see how the schedule adapts*")

w1 = st.sidebar.slider(
    "Individual Bus",
    min_value=0.0,
    max_value=5.0,
    value=float(scenario['weights']['individual_bus']),
    step=0.5,
    help="Higher = prioritize reducing worst-case individual wait"
)

w2 = st.sidebar.slider(
    "Operator Balance",
    min_value=0.0,
    max_value=5.0,
    value=float(scenario['weights']['operator_balance']),
    step=0.5,
    help="Higher = prioritize fairness across operators"
)

w3 = st.sidebar.slider(
    "Overall Efficiency",
    min_value=0.0,
    max_value=5.0,
    value=float(scenario['weights']['overall_efficiency']),
    step=0.5,
    help="Higher = prioritize FCFS order for throughput"
)

# Create modified scenario with adjusted weights
scenario_copy = copy.deepcopy(scenario)
scenario_copy['weights'] = {
    'individual_bus': w1,
    'operator_balance': w2,
    'overall_efficiency': w3
}

# Show if weights changed from default
default_weights = scenario['weights']
if (w1 != default_weights['individual_bus'] or
    w2 != default_weights['operator_balance'] or
    w3 != default_weights['overall_efficiency']):
    st.sidebar.info("⚡ Weights modified from scenario defaults")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📋 Input",
    "🚌 Per-Bus",
    "⚡ Per-Station",
    "📊 Metrics"
])

# Run scheduler with adjusted weights
with st.spinner("Computing schedule..."):
    scheduler = BusChargingScheduler(scenario_copy, route_config)
    result = scheduler.schedule()

# Tab 1: Scenario Input
with tab1:
    st.header(f"{scenarios[selected_scenario]}")
    st.markdown(f"**Description**: {scenario['description']}")

    st.subheader("Route Configuration")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Battery Range", f"{route_config['physical_constants']['battery_range_km']} km")
    with col2:
        st.metric("Charging Time", f"{route_config['physical_constants']['charging_time_minutes']} min")
    with col3:
        st.metric("Speed", f"{route_config['physical_constants']['speed_kmh']} km/h")

    st.subheader("Route Stations")
    stations_data = []
    stations_data.append({"Station": "Bengaluru (Start)", "Distance from Bengaluru": "0 km", "Chargers": "-"})
    for station in route_config['route']['stations']:
        stations_data.append({
            "Station": station['id'],
            "Distance from Bengaluru": f"{station['distance_from_bengaluru']} km",
            "Chargers": route_config['charger_config'][station['id']]
        })
    stations_data.append({"Station": "Kochi (End)", "Distance from Bengaluru": f"{route_config['route']['total_distance']} km", "Chargers": "-"})

    st.dataframe(pd.DataFrame(stations_data), use_container_width=True, hide_index=True)

    st.subheader("Bus Departure Schedule")
    buses_df = pd.DataFrame(scenario['buses'])
    buses_df = buses_df.rename(columns={
        'id': 'Bus ID',
        'operator': 'Operator',
        'direction': 'Direction',
        'departure_time': 'Departure Time'
    })
    st.dataframe(buses_df, use_container_width=True, hide_index=True)

    # Show current weights
    st.subheader("Current Weights")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Individual Bus", w1)
    with col2:
        st.metric("Operator Balance", w2)
    with col3:
        st.metric("Overall Efficiency", w3)

# Tab 2: Per-Bus Schedule
with tab2:
    st.header("Per-Bus Charging Schedule")

    if result['status'] != 'SUCCESS':
        st.error(f"❌ {result['message']}")
    else:
        # Add filter options
        col1, col2 = st.columns(2)
        with col1:
            operator_filter = st.multiselect(
                "Filter by Operator",
                options=['kpn', 'freshbus', 'flixbus'],
                default=['kpn', 'freshbus', 'flixbus']
            )
        with col2:
            direction_filter = st.multiselect(
                "Filter by Direction",
                options=['Bengaluru→Kochi', 'Kochi→Bengaluru'],
                default=['Bengaluru→Kochi', 'Kochi→Bengaluru']
            )

        # Filter buses
        filtered_buses = [
            bus for bus in result['buses']
            if bus['operator'] in operator_filter and bus['direction'] in direction_filter
        ]

        for bus in filtered_buses:
            with st.expander(f"**{bus['bus_id']}** ({bus['operator'].upper()}) - {bus['direction']}", expanded=False):
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric("Departure", bus['departure_time'])
                with col2:
                    st.metric("Arrival", bus['arrival_time'])
                with col3:
                    st.metric("Trip Time", f"{bus['total_trip_time_minutes']} min")
                with col4:
                    st.metric("Total Wait", f"{bus['total_wait_time_minutes']} min")

                if bus['charging_plan']:
                    st.markdown("**Charging Plan:**")
                    charging_df = pd.DataFrame(bus['charging_plan'])
                    charging_df = charging_df.rename(columns={
                        'station': 'Station',
                        'arrival_time': 'Arrival',
                        'wait_time_minutes': 'Wait (min)',
                        'charging_start': 'Charge Start',
                        'charging_end': 'Charge End'
                    })
                    st.dataframe(charging_df, use_container_width=True, hide_index=True)
                else:
                    st.info("No charging stops (should not happen)")

# Tab 3: Per-Station View
with tab3:
    st.header("Per-Station Charging Queue")

    if result['status'] != 'SUCCESS':
        st.error(f"❌ {result['message']}")
    else:
        for station in ['A', 'B', 'C', 'D']:
            queue = result['station_queues'][station]

            if queue:
                st.subheader(f"Station {station}")
                st.markdown(f"**Total buses charged**: {len(queue)}")

                queue_df = pd.DataFrame(queue)
                queue_df = queue_df.rename(columns={
                    'bus_id': 'Bus ID',
                    'operator': 'Operator',
                    'charging_start': 'Charge Start',
                    'charging_end': 'Charge End'
                })
                queue_df.index = range(1, len(queue_df) + 1)
                st.dataframe(queue_df, use_container_width=True)
            else:
                st.subheader(f"Station {station}")
                st.info("No buses charged at this station")

# Tab 4: Metrics
with tab4:
    st.header("Schedule Metrics")

    if result['status'] != 'SUCCESS':
        st.error(f"❌ {result['message']}")
    else:
        metrics = result['metrics']

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Max Individual Wait",
                f"{metrics['max_individual_wait']} min",
                help="Longest wait time experienced by any single bus"
            )

        with col2:
            st.metric(
                "Average Wait",
                f"{metrics['avg_wait']:.1f} min",
                help="Average wait time across all buses"
            )

        with col3:
            st.metric(
                "Total System Wait",
                f"{metrics['total_system_wait']} min",
                help="Sum of all wait times across the network"
            )

        st.subheader("Wait Time Distribution by Operator")

        # Use the per-operator metrics from the result if available
        if 'per_operator' in metrics:
            operator_summary = []
            for op, stats in metrics['per_operator'].items():
                operator_summary.append({
                    'Operator': op.upper(),
                    'Buses': stats['bus_count'],
                    'Total Wait (min)': stats['total_wait'],
                    'Avg Wait (min)': f"{stats['avg_wait']:.1f}",
                    'Max Wait (min)': stats['max_wait']
                })
            st.dataframe(pd.DataFrame(operator_summary), use_container_width=True, hide_index=True)
        else:
            # Fallback: calculate from bus data
            operator_stats = {}
            for bus in result['buses']:
                op = bus['operator']
                if op not in operator_stats:
                    operator_stats[op] = []
                operator_stats[op].append(bus['total_wait_time_minutes'])

            operator_summary = []
            for op, waits in operator_stats.items():
                operator_summary.append({
                    'Operator': op.upper(),
                    'Buses': len(waits),
                    'Total Wait (min)': sum(waits),
                    'Avg Wait (min)': f"{sum(waits) / len(waits):.1f}",
                    'Max Wait (min)': max(waits)
                })
            st.dataframe(pd.DataFrame(operator_summary), use_container_width=True, hide_index=True)

        st.subheader("Station Utilization")

        station_util = []
        for station in ['A', 'B', 'C', 'D']:
            queue = result['station_queues'][station]
            total_charging_time = len(queue) * route_config['physical_constants']['charging_time_minutes']

            station_util.append({
                'Station': station,
                'Buses Charged': len(queue),
                'Total Charging Time (min)': total_charging_time,
            })

        st.dataframe(pd.DataFrame(station_util), use_container_width=True, hide_index=True)

# Footer
st.markdown("---")
st.markdown("""
**How it works**: This scheduler uses a greedy simulation with weighted priority.
When multiple buses contend for the same charger, the weights determine who goes first.
Adjust the sliders in the sidebar to see how different weight settings affect the schedule.
""")
