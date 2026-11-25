"""Side-by-side MP4s: one Simulation 1 run (1 agent) next to one Simulation 2 run (N agents), per trajectory type."""

from dataclasses import replace
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib import animation  # noqa: E402
from matplotlib.colors import ListedColormap  # noqa: E402

from cleaner import Strategy  # noqa: E402
from simulation import CleaningSimulation, SimConfig  # noqa: E402

CMAP = ListedColormap(["#ffffff", "#8b5a2b"])  # clean = white, dirty = brown
FPS = 5


def _cells(frame, cols: int, rows: int) -> np.ndarray:
    grid = np.zeros(rows * cols, dtype=int)
    for n in frame.dirty:
        grid[n] = 1
    return grid.reshape(rows, cols)


def _agent_xy(frame, cols: int) -> tuple[list[float], list[float]]:
    """Agents on the same cell are drawn side by side, so every agent stays visible."""
    xs, ys, seen = [], [], {}
    for node in frame.agents:
        k = seen.get(node, 0)
        seen[node] = k + 1
        row, col = divmod(node, cols)
        xs.append(col + 0.22 * k)
        ys.append(row)
    return xs, ys


def render_side_by_side(left: SimConfig, right: SimConfig, path: Path) -> None:
    left_sim = CleaningSimulation(left, record=True)
    right_sim = CleaningSimulation(right, record=True)
    left_result = left_sim.run()
    right_result = right_sim.run()
    frames_total = max(len(left_sim.frames), len(right_sim.frames))
    rows, cols = left.rows, left.cols

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6.2))
    panels = (
        (ax1, left_sim, f"Simulation 1: {left.n_agents} agent (clean in {left_result.time_to_clean} ticks)"),
        (ax2, right_sim, f"Simulation 2: {right.n_agents} agents (clean in {right_result.time_to_clean} ticks)"),
    )
    artists = []
    for ax, sim, title in panels:
        image = ax.imshow(_cells(sim.frames[0], cols, rows), cmap=CMAP, vmin=0, vmax=1,
                          interpolation="nearest", extent=(-0.5, cols - 0.5, rows - 0.5, -0.5))
        dots, = ax.plot([], [], "o", color="tab:blue", markersize=9, markeredgecolor="white", linestyle="")
        ax.set_title(title)
        ax.set_xticks([])
        ax.set_yticks([])
        artists.append((image, dots, sim))

    def update(index: int):
        for image, dots, sim in artists:
            frame = sim.frames[min(index, len(sim.frames) - 1)]
            image.set_data(_cells(frame, cols, rows))
            dots.set_data(*_agent_xy(frame, cols))
        fig.suptitle(
            f"{left.strategy.value} strategy, tick {min(index, frames_total - 1)}   "
            "(white = clean, brown = dirty, blue = agent)"
        )
        return []

    anim = animation.FuncAnimation(fig, update, frames=frames_total, interval=1000 // FPS, blit=False)
    anim.save(path, writer=animation.FFMpegWriter(fps=FPS, bitrate=1800), dpi=110)
    plt.close(fig)


def write_videos(base: SimConfig, many_agents: int, output: Path) -> list[Path]:
    """One video per trajectory type, all on the same grid, dirt seed and start cell."""
    output.mkdir(parents=True, exist_ok=True)
    paths = []
    for strategy in Strategy:
        left = replace(base, n_agents=1, strategy=strategy)
        right = replace(base, n_agents=many_agents, strategy=strategy)
        path = output / f"simulation-{strategy.value}.mp4"
        render_side_by_side(left, right, path)
        paths.append(path)
    return paths
