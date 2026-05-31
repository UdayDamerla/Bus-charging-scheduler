# Electric Bus Charging Scheduler

This is a scheduler for electric buses traveling between Bengaluru and Kochi. It figures out when and where each bus should stop to charge along the route.

## The Problem

Electric buses run on a 540 km route with 4 charging stations (A, B, C, D) in between. Each bus:
- Has a 240 km range on a full charge
- Takes 25 minutes to charge (always charges to full)
- Belongs to one of 3 operators (KPN, Freshbus, Flixbus)

The scheduler needs to decide which stations each bus uses and when, while making sure:
- No bus runs out of battery
- Only one bus charges at a time per station
- Individual wait times stay reasonable
- The overall system runs efficiently

## Live Demo

Hosted at: [Add your Streamlit URL after deployment]

## Project Structure

```
├── app.py                  # Streamlit web interface
├── src/
│   └── scheduler.py        # Main scheduling logic
├── scenarios/              # 5 test scenarios
│   ├── scenario_1.json     
│   ├── scenario_2.json     
│   ├── scenario_3.json     
│   ├── scenario_4.json     
│   └── scenario_5.json     
├── data/
│   └── route_config.json   # Route details and constants
├── requirements.txt        
├── README.md               
└── ARCHITECTURE.md         # Design decisions
```

## What I Used

- Python 3.9+
- Streamlit for the web UI
- Pandas for tables

The scheduler uses a greedy algorithm - processes buses in order of arrival at each station and assigns the next available charger slot. Simple but effective for this problem size.

## Running It Locally

You'll need Python 3.9 or higher.

```bash
# Clone the repo
git clone <your-repo-url>
cd SDE-Assignment

# Install packages
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

It should open automatically in your browser at `http://localhost:8501`

## Using the App

1. Pick a scenario from the dropdown (1-5)
2. Check the input data in the first tab
3. Browse through:
   - Per-Bus Schedule: see each bus's route and wait times
   - Per-Station View: see the queue at each charging station
   - Metrics: overall statistics

## Changing Weights

The scheduler balances three objectives using weights:
- individual_bus: minimize max wait for any single bus
- operator_balance: keep operators' fleets balanced
- overall_efficiency: minimize total system time

To change them, edit the scenario JSON:

```json
// scenarios/scenario_4.json
{
  "weights": {
    "individual_bus": 1.0,
    "operator_balance": 3.0,  // increased from 1.0
    "overall_efficiency": 1.0
  }
}
```

Save and restart the app to see the difference.

You could also add UI sliders in `app.py` for real-time tweaking:

```python
# Add to sidebar
st.sidebar.header("Adjust Weights")
w1 = st.sidebar.slider("Individual Bus", 0.0, 5.0, 1.0)
w2 = st.sidebar.slider("Operator Balance", 0.0, 5.0, 1.0)
w3 = st.sidebar.slider("Overall Efficiency", 0.0, 5.0, 1.0)

scenario['weights'] = {
    'individual_bus': w1,
    'operator_balance': w2,
    'overall_efficiency': w3
}
```

## Adding New Rules

Say you want to add priority buses that get to charge first. Here's how:

**Step 1: Update the data**

Add a priority field to buses in your scenario:

```json
{
  "id": "bus-BK-01",
  "operator": "kpn",
  "direction": "Bengaluru→Kochi",
  "departure_time": "19:00",
  "priority": true
}
```

**Step 2: Update the scheduler**

In `src/scheduler.py`, modify the station processing loop to sort by priority:

```python
# Around line 145, when processing station arrivals
for station_id in ['A', 'B', 'C', 'D']:
    arrivals = sorted(station_events[station_id])
    
    # Sort by priority if it exists
    def get_priority(arrival):
        arrival_time, bus_id = arrival
        bus = next(b for b in self.buses if b['id'] == bus_id)
        return (not bus.get('priority', False), arrival_time)  # False sorts first
    
    arrivals = sorted(station_events[station_id], key=get_priority)
```

That's it. Priority buses now charge before regular buses at each station.

## How It Works

The scheduler is pretty straightforward:

1. For each bus, calculate when it'll arrive at each required station based on departure time and speed
2. Process each station independently
3. At each station, handle buses in order of arrival
4. Assign charger when available (either when bus arrives or when previous bus finishes)
5. Track wait times and update charger availability

I initially tried using constraint programming (Google OR-Tools), but it was overengineered for this problem. The greedy approach is simpler, easier to debug, and always produces valid schedules.

## Why This Design

Everything configurable is in JSON files:
- Want another station? Add it to route_config.json
- More buses? Add them to the scenario file
- Different battery range? Change the physical_constants
- More chargers at a station? Update charger_config

You only touch code when adding new types of constraints (like priority buses or time-based pricing).

## The Scenarios

1. Scenario 1 - Even Spacing: Buses leave every 15 minutes. Baseline case.
2. Scenario 2 - Bunched Start: Everyone leaves within 50 minutes. Tests heavy congestion.
3. Scenario 3 - Asymmetric Load: 10 buses one way, 4 the other way. Unbalanced traffic.
4. Scenario 4 - Operator-Heavy: KPN has 8 out of 10 buses. Tests operator weight.
5. Scenario 5 - Worst Case: All 20 buses within 72 minutes. Maximum chaos.

All of them produce valid schedules. The waits get longer in scenarios with more bunching, which makes sense.

## Testing

Run the test suite:

```bash
python test_all_scenarios.py
```

It validates:
- All buses have charging plans
- No bus exceeds 240 km between charges
- Charging is always 25 minutes
- No two buses use same charger simultaneously

## Future Ideas

Things I didn't implement but would be straightforward:

- UI sliders to adjust weights in real-time
- Gantt chart showing charger utilization
- Support for multiple routes sharing stations
- Dynamic rescheduling if a bus breaks down
- Different charging speeds or battery sizes per bus

Check ARCHITECTURE.md for more details on how to extend this.

## Deployment

To deploy on Streamlit Community Cloud:

1. Push code to GitHub (make repo public)
2. Go to share.streamlit.io
3. Click "New app" and point to your repo
4. Select app.py as the main file
5. Deploy

It's free for public repos and takes about 2 minutes.

See DEPLOYMENT.md for detailed steps.

## References

- Streamlit docs: https://docs.streamlit.io/
- The assignment spec is in the PDF

---

Built for the May 2026 SDE take-home assignment.
