# Multi-Agent Room Cleaning Simulation (TC2008B A2)

Agents clean an M x N grid in which a random share of the cells is dirty. The model follows the
course notebook: the adjacency matrix S (8 neighbours), the distance matrix D (0.3 m per tile) and the
transition probability matrix P (uniform over the neighbours).

- Simulation 1: one agent.
- Simulation 2: several agents (at least 4) that all start at the same cell.
- Trajectory types: local search (nearest dirty cell, shared claims), zigzag (closed boustrophedon loop),
  random (next cell drawn from row P).

## Run

    pip install numpy matplotlib reportlab pytest flask
    python -m pytest                                              # tests
    python cli.py simulate --agents 4 --strategy zigzag --seed 0  # one run; writes Nodes.csv and Routes.csv
    python cli.py experiment --rows 8 --cols 8 --dirty 0.3 \
        --video-url local_search=URL --video-url zigzag=URL --video-url random=URL \
        --author "Name" --code-url https://github.com/...

`experiment` writes `output/runs.csv`, `summary.json`, `config.json`, the matrix and result figures,
three videos (one per trajectory type, one agent next to four agents) and `output/report.pdf`.
Use `--skip-videos` or `--skip-report` to skip those steps.

`Main.py` is the Flask app that serves `Nodes.csv` and `Routes.csv` at `/api/data`. It needs a
`templates/index.html`, which is not in this repository yet.

## Files

- `grid.py`: the grid and the matrices S, D, P; shortest paths; the zigzag loop
- `cleaner.py`: agent and the three strategies
- `simulation.py`: one run, its metrics and its routes
- `data.py`: reads and writes `Nodes.csv` and `Routes.csv`
- `experiments.py`: batch runs, matrix figure and charts
- `video.py`: side-by-side MP4s
- `report.py`: PDF report
- `cli.py`: the two subcommands (`simulate`, `experiment`)
- `test_simulation.py`: tests, including checks against the notebook values
