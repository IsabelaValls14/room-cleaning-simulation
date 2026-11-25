"""Batch experiments for Simulation 1 and Simulation 2. Writes CSV, JSON, the matrix figures and charts."""

import csv
import json
import statistics
from dataclasses import asdict, replace
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from cleaner import Strategy  # noqa: E402
from grid import Grid  # noqa: E402
from simulation import CleaningSimulation, SimConfig  # noqa: E402


def build_experiments(base: SimConfig, agent_counts: list[int], scaling_agents: int) -> dict[str, SimConfig]:
    """Simulation 1 for every strategy; Simulation 2 (local search) for each agent count; and the
    other two strategies in Simulation 2 at the scaling agent count."""
    experiments = {}
    for strategy in Strategy:
        experiments[f"sim1-{strategy.value}"] = replace(base, n_agents=1, strategy=strategy)
    for n_agents in agent_counts:
        experiments[f"sim2-local_search-n{n_agents}"] = replace(
            base, n_agents=n_agents, strategy=Strategy.LOCAL_SEARCH)
    for strategy in (Strategy.ZIGZAG, Strategy.RANDOM):
        experiments[f"sim2-{strategy.value}-n{scaling_agents}"] = replace(
            base, n_agents=scaling_agents, strategy=strategy)
    return experiments


def run_all(experiments: dict[str, SimConfig], seeds: range) -> list[dict]:
    rows = []
    for name, config in experiments.items():
        for seed in seeds:
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
                "total_moves": result.total_moves,
                "distance_m": round(result.distance_m, 2),
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
            "distance_m_mean": _mean([row["distance_m"] for row in group]),
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


def plot_matrices(grid: Grid, path: Path) -> None:
    """The three matrices of the notebook: adjacency S, distances D, probabilities P."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    titles = [
        "S: adjacency (allowed moves)",
        "D: distances (metres)",
        "P: transition probabilities",
    ]
    for ax, matrix, title in zip(axes, (grid.S, grid.D, grid.P), titles):
        image = ax.imshow(matrix, cmap="viridis")
        ax.set_title(title)
        ax.set_xlabel("node")
        ax.set_ylabel("node")
        fig.colorbar(image, ax=ax, fraction=0.046)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_agent_scaling(summary: dict[str, dict], agent_counts: list[int], path: Path) -> None:
    """Simulation 2 with local search: 1 agent (Simulation 1) up to the largest agent count."""
    names = ["sim1-local_search"] + [f"sim2-local_search-n{n}" for n in agent_counts]
    xs = [summary[name]["n_agents"] for name in names]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))

    axes[0].errorbar(xs, [summary[n]["time_to_clean_mean"] or 0 for n in names],
                     yerr=[summary[n]["time_to_clean_std"] or 0 for n in names], marker="o", capsize=4)
    axes[0].set_title("Time to clean all dirt (finished runs)")
    axes[0].set_ylabel("Ticks")

    axes[1].errorbar(xs, [summary[n]["cleaned_pct_mean"] for n in names],
                     yerr=[summary[n]["cleaned_pct_std"] or 0 for n in names],
                     marker="o", capsize=4, color="tab:green")
    axes[1].set_title("Dirt cleaned within the time limit")
    axes[1].set_ylabel("% of dirty cells")
    axes[1].set_ylim(0, 105)

    axes[2].plot(xs, [summary[n]["mean_moves_per_agent"] for n in names], marker="o", color="tab:orange")
    axes[2].set_title("Moves per agent")
    axes[2].set_ylabel("Moves")

    for ax in axes:
        ax.set_xlabel("Number of agents")
        ax.set_xticks(xs, [str(x) for x in xs])
        ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def plot_strategies(summary: dict[str, dict], scaling_agents: int, path: Path) -> None:
    """Trajectory comparison: one agent (Simulation 1) and the scaling agent count (Simulation 2)."""
    labels, cleaned, moves = [], [], []
    for strategy in Strategy:
        for name in (f"sim1-{strategy.value}", f"sim2-{strategy.value}-n{scaling_agents}"):
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


def write_outputs(base: SimConfig, agent_counts: list[int], scaling_agents: int, seeds: range,
                  output: Path) -> dict[str, dict]:
    """Runs every experiment and writes runs.csv, summary.json, config.json and the figures."""
    output.mkdir(parents=True, exist_ok=True)
    experiments = build_experiments(base, agent_counts, scaling_agents)
    rows = run_all(experiments, seeds)
    summary = summarize(rows)

    write_csv(rows, output / "runs.csv")
    (output / "summary.json").write_text(json.dumps(summary, indent=2))
    (output / "config.json").write_text(json.dumps({
        name: asdict(config) | {"strategy": config.strategy.value} for name, config in experiments.items()
    }, indent=2))
    plot_matrices(Grid(base.rows, base.cols), output / "matrices.png")
    plot_agent_scaling(summary, agent_counts, output / "agent_scaling.png")
    plot_strategies(summary, scaling_agents, output / "strategies.png")
    return summary


def probability_table(summary: dict[str, dict], names: list[str], seeds: int) -> list[tuple[str, float, int]]:
    """(experiment, estimated probability that all dirt is cleaned, number of successful seeds)."""
    out = []
    for name in names:
        successes = round(summary[name]["finished_rate_pct"] * seeds / 100)
        out.append((name, successes / seeds, successes))
    return out
