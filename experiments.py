"""Batch experiments for Simulation 1 and Simulation 2. Writes CSV, JSON summary and charts to output/."""

import csv
import json
import statistics
from dataclasses import asdict, replace
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from cleaner import Strategy  # noqa: E402
from simulation import CleaningSimulation, SimConfig  # noqa: E402

OUTPUT = Path(__file__).parent / "output"
SEEDS = range(30)
BASE = SimConfig()
AGENT_COUNTS = (2, 4, 8, 16)
SCALING_STRATEGY_AGENTS = 4


def build_experiments() -> dict[str, SimConfig]:
    experiments = {}
    for strategy in Strategy:
        experiments[f"sim1-{strategy.value}"] = replace(BASE, n_agents=1, strategy=strategy)
    for n_agents in AGENT_COUNTS:
        experiments[f"sim2-local_search-n{n_agents}"] = replace(
            BASE, n_agents=n_agents, strategy=Strategy.LOCAL_SEARCH
        )
    for strategy in (Strategy.ZIGZAG, Strategy.RANDOM):
        experiments[f"sim2-{strategy.value}-n{SCALING_STRATEGY_AGENTS}"] = replace(
            BASE, n_agents=SCALING_STRATEGY_AGENTS, strategy=strategy
        )
    return experiments


def run_all(experiments: dict[str, SimConfig]) -> list[dict]:
    rows = []
    for name, config in experiments.items():
        for seed in SEEDS:
            result = CleaningSimulation(replace(config, seed=seed)).run()
            rows.append({
                "experiment": name,
                "n_agents": config.n_agents,
                "strategy": config.strategy.value,
                "seed": seed,
                "finished": result.finished,
                "time_to_clean": result.time_to_clean,
                "visited_pct": round(result.visited_pct, 2),
                "cleaned_pct": round(result.cleaned_pct, 2),
                "mean_moves_per_agent": round(result.mean_moves, 2),
                "total_moves": sum(result.moves),
                "recharges": result.recharges,
            })
    return rows


def summarize(rows: list[dict]) -> dict[str, dict]:
    summary = {}
    for name in dict.fromkeys(row["experiment"] for row in rows):
        group = [row for row in rows if row["experiment"] == name]
        finished_times = [row["time_to_clean"] for row in group if row["finished"]]
        summary[name] = {
            "n_agents": group[0]["n_agents"],
            "strategy": group[0]["strategy"],
            "runs": len(group),
            "finished_rate_pct": 100 * len(finished_times) / len(group),
            "time_to_clean_mean": _mean(finished_times),
            "time_to_clean_std": _std(finished_times),
            "visited_pct_mean": _mean([row["visited_pct"] for row in group]),
            "cleaned_pct_mean": _mean([row["cleaned_pct"] for row in group]),
            "cleaned_pct_std": _std([row["cleaned_pct"] for row in group]),
            "mean_moves_per_agent": _mean([row["mean_moves_per_agent"] for row in group]),
            "total_moves_mean": _mean([row["total_moves"] for row in group]),
            "recharges_mean": _mean([row["recharges"] for row in group]),
        }
    return summary


def _mean(values: list[float]) -> float | None:
    return round(statistics.fmean(values), 2) if values else None


def _std(values: list[float]) -> float | None:
    return round(statistics.stdev(values), 2) if len(values) > 1 else None


def write_csv(rows: list[dict], path: Path) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def plot_agent_scaling(summary: dict[str, dict], path: Path) -> None:
    """Simulation 2 with local search: 1 agent (Simulation 1) up to 16 agents."""
    names = ["sim1-local_search"] + [f"sim2-local_search-n{n}" for n in AGENT_COUNTS]
    xs = [summary[name]["n_agents"] for name in names]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))

    axes[0].errorbar(
        xs,
        [summary[n]["time_to_clean_mean"] or 0 for n in names],
        yerr=[summary[n]["time_to_clean_std"] or 0 for n in names],
        marker="o", capsize=4,
    )
    axes[0].set_title("Time to clean all dirt (finished runs)")
    axes[0].set_ylabel("Ticks")

    axes[1].errorbar(
        xs,
        [summary[n]["cleaned_pct_mean"] for n in names],
        yerr=[summary[n]["cleaned_pct_std"] or 0 for n in names],
        marker="o", capsize=4, color="tab:green",
    )
    axes[1].set_title("Dirt cleaned within the time limit")
    axes[1].set_ylabel("% of dirty cells")
    axes[1].set_ylim(0, 105)

    axes[2].plot(xs, [summary[n]["mean_moves_per_agent"] for n in names], marker="o", color="tab:orange")
    axes[2].set_title("Moves per agent")
    axes[2].set_ylabel("Moves")

    for ax in axes:
        ax.set_xlabel("Number of agents")
        ax.set_xscale("log", base=2)
        ax.set_xticks(xs, [str(x) for x in xs])
        ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def plot_strategies(summary: dict[str, dict], path: Path) -> None:
    """Trajectory comparison: one agent (Simulation 1) and four agents (Simulation 2)."""
    labels = []
    cleaned = []
    moves = []
    for strategy in Strategy:
        for name in (f"sim1-{strategy.value}", f"sim2-{strategy.value}-n{SCALING_STRATEGY_AGENTS}"):
            if name in summary:
                labels.append(name.replace("-", "\n", 1))
                cleaned.append(summary[name]["cleaned_pct_mean"])
                moves.append(summary[name]["mean_moves_per_agent"])
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    axes[0].bar(labels, cleaned, color="tab:green")
    axes[0].set_title("Dirt cleaned within the time limit")
    axes[0].set_ylabel("% of dirty cells")
    axes[1].bar(labels, moves, color="tab:orange")
    axes[1].set_title("Moves per agent")
    axes[1].set_ylabel("Moves")
    for ax in axes:
        ax.tick_params(axis="x", labelsize=8)
        ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def main() -> None:
    OUTPUT.mkdir(exist_ok=True)
    experiments = build_experiments()
    rows = run_all(experiments)
    summary = summarize(rows)

    write_csv(rows, OUTPUT / "runs.csv")
    (OUTPUT / "summary.json").write_text(json.dumps(summary, indent=2))
    (OUTPUT / "config.json").write_text(json.dumps(
        {name: asdict(config) | {"strategy": config.strategy.value} for name, config in experiments.items()},
        indent=2,
    ))
    plot_agent_scaling(summary, OUTPUT / "agent_scaling.png")
    plot_strategies(summary, OUTPUT / "strategies.png")

    for name, stats in summary.items():
        print(f"{name:32s} finished={stats['finished_rate_pct']:5.1f}%  "
              f"time={stats['time_to_clean_mean']}  cleaned={stats['cleaned_pct_mean']}%  "
              f"visited={stats['visited_pct_mean']}%  moves/agent={stats['mean_moves_per_agent']}")


if __name__ == "__main__":
    main()
