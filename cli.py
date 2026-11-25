"""Command-line entry point with two subcommands: `simulate` (one run) and `experiment` (batch, videos, report).

Every setting is a parameter. `simulate` writes Nodes.csv and Routes.csv, which Main.py reads.
"""

import argparse
import json
from pathlib import Path

from cleaner import Strategy
from data import DATA_DIR, NODES_FILE, ROUTES_FILE, write_nodes, write_routes
from grid import Grid
from simulation import CleaningSimulation, SimConfig


def add_room_arguments(parser: argparse.ArgumentParser) -> None:
    base = SimConfig()
    parser.add_argument("--rows", type=int, default=base.rows, help="grid rows (M)")
    parser.add_argument("--cols", type=int, default=base.cols, help="grid columns (N)")
    parser.add_argument("--dirty", type=float, default=base.dirty_fraction,
                        help="fraction of grid cells that start dirty, e.g. 0.3")
    parser.add_argument("--max-steps", type=int, default=base.max_steps, help="maximum simulation time in ticks")
    parser.add_argument("--start", type=int, default=base.start,
                        help="start cell (numbered row by row, from 0); Simulation 2 agents all start here")


def sim_config(args: argparse.Namespace, **overrides) -> SimConfig:
    return SimConfig(rows=args.rows, cols=args.cols, dirty_fraction=args.dirty,
                     max_steps=args.max_steps, start=args.start, **overrides)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Multi-agent room cleaning simulation (TC2008B A2).")
    commands = parser.add_subparsers(dest="command", required=True)

    simulate = commands.add_parser("simulate", help="run one simulation, print its metrics, write Nodes.csv and Routes.csv")
    add_room_arguments(simulate)
    simulate.add_argument("--agents", type=int, default=1, help="number of agents (all start at --start)")
    simulate.add_argument("--strategy", type=Strategy, choices=list(Strategy),
                          default=Strategy.LOCAL_SEARCH, help="trajectory type")
    simulate.add_argument("--seed", type=int, default=0, help="random seed for the dirt and the random strategy")
    simulate.add_argument("--data-dir", type=Path, default=DATA_DIR,
                          help="folder where Nodes.csv and Routes.csv are written")

    experiment = commands.add_parser(
        "experiment",
        help="run every setting over many seeds and write CSV, JSON, figures, videos and the PDF report",
    )
    add_room_arguments(experiment)
    experiment.add_argument("--seeds", type=int, default=30, help="random seeds per setting")
    experiment.add_argument("--agent-counts", type=int, nargs="+", default=[4, 8, 12, 16],
                            help="Simulation 2 agent counts (local search); all at least 4")
    experiment.add_argument("--scaling-agents", type=int, default=4,
                            help="agent count for the strategy comparison and the videos (at least 4)")
    experiment.add_argument("--output", type=Path, default=Path("output"), help="output folder")
    experiment.add_argument("--skip-videos", action="store_true", help="do not render the MP4 files")
    experiment.add_argument("--skip-report", action="store_true", help="do not build the PDF report")
    experiment.add_argument("--video-url", action="append", default=[], metavar="STRATEGY=URL",
                            help="shared link for one trajectory video, e.g. local_search=https://drive.google.com/...")
    experiment.add_argument("--code-url", default="[to be added]", help="URL of the code repository")
    experiment.add_argument("--author", default="[to be added]", help="author name for the cover")
    experiment.add_argument("--course", default="TC2008B", help="course name for the cover")
    experiment.add_argument("--assignment", default="A2: Multi-agent room cleaning", help="assignment name")
    return parser


def run_simulate(args: argparse.Namespace) -> None:
    config = sim_config(args, n_agents=args.agents, strategy=args.strategy, seed=args.seed)
    sim = CleaningSimulation(config)
    result = sim.run()
    grid = Grid(config.rows, config.cols)
    args.data_dir.mkdir(parents=True, exist_ok=True)
    write_nodes(args.data_dir / NODES_FILE, [grid.point(n) for n in range(grid.size)], sim.dirty_at_start)
    write_routes(args.data_dir / ROUTES_FILE, sim.routes())
    print(json.dumps({
        "finished": result.finished,
        "time_to_clean": result.time_to_clean,
        "visited_pct": round(result.visited_pct, 2),
        "cleaned_pct": round(result.cleaned_pct, 2),
        "moves": list(result.moves),
        "distance_m": round(result.distance_m, 2),
        "wrote": [str(args.data_dir / NODES_FILE), str(args.data_dir / ROUTES_FILE)],
    }, indent=2))


def parse_video_urls(pairs: list[str]) -> dict[str, str]:
    urls = {}
    for pair in pairs:
        strategy, sep, url = pair.partition("=")
        if not sep or strategy not in {s.value for s in Strategy}:
            raise SystemExit(f"--video-url expects STRATEGY=URL with STRATEGY in "
                             f"{[s.value for s in Strategy]}, got {pair!r}")
        urls[strategy] = url
    return urls


def run_experiment(args: argparse.Namespace) -> None:
    # Imported here so `simulate` does not need matplotlib or reportlab.
    from experiments import write_outputs
    from report import ReportInputs, build_report
    from video import write_videos

    if args.scaling_agents < 4 or min(args.agent_counts) < 4:
        raise SystemExit("Simulation 2 needs at least 4 agents: check --scaling-agents and --agent-counts")
    base = sim_config(args)
    output = args.output
    summary = write_outputs(base, args.agent_counts, args.scaling_agents, range(args.seeds), output)
    print(f"Wrote runs.csv, summary.json, config.json and figures to {output}")

    if not args.skip_videos:
        for path in write_videos(base, args.scaling_agents, output):
            print(f"Wrote {path}")

    if not args.skip_report:
        inputs = ReportInputs(
            output=output, base=base, agent_counts=args.agent_counts, scaling_agents=args.scaling_agents,
            seeds=args.seeds, video_urls=parse_video_urls(args.video_url), code_url=args.code_url,
            author=args.author, course=args.course, assignment=args.assignment,
        )
        pdf = output / "report.pdf"
        build_report(inputs, pdf)
        print(f"Wrote {pdf}")

    for name, stats in summary.items():
        print(f"{name:28s} finished={stats['finished_rate_pct']:5.1f}%  time={stats['time_to_clean_mean']}  "
              f"cleaned={stats['cleaned_pct_mean']}%  visited={stats['visited_pct_mean']}%  "
              f"moves/agent={stats['mean_moves_per_agent']}")


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.command == "simulate":
        run_simulate(args)
    else:
        run_experiment(args)


if __name__ == "__main__":
    main()
