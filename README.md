# Multi-Agent Room Cleaning Simulation

A discrete-time simulation of cleaning agents in an M x N room with random dirty
and locked cells. Agents have a battery (a move budget) and recharge at a start
point when they are almost out.

- Simulation 1: one agent in the room.
- Simulation 2: several agents at random start points that can recharge at any agent's start point.
- Strategies: local search, zigzag, random walk.

## Run

    pip install numpy matplotlib reportlab pytest
    python -m pytest              # tests
    python experiments.py         # 270 runs -> output/runs.csv, summary.json, charts
    python video.py               # output/simulation.mp4
    python report.py              # output/report.pdf

## Files

- `room.py`: grid, dirty and locked cells, path helpers
- `cleaner.py`: agent, battery and strategies
- `simulation.py`: one run and its metrics
- `experiments.py`: batch runs and charts
- `video.py`, `report.py`: video and PDF outputs
- `test_room_cleaning.py`: behavior tests
