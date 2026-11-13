"""Records a side-by-side MP4 of one Simulation 1 run and one Simulation 2 run on the same kind of room."""

from dataclasses import replace
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import animation  # noqa: E402
from matplotlib.colors import ListedColormap  # noqa: E402

from cleaner import Strategy  # noqa: E402
from room import CLEAN, DIRTY, LOCKED  # noqa: E402
from simulation import CleaningSimulation, SimConfig  # noqa: E402

OUTPUT = Path(__file__).parent / "output"
SEED = 0
SIM1 = replace(SimConfig(), n_agents=1, strategy=Strategy.LOCAL_SEARCH, seed=SEED)
SIM2 = replace(SimConfig(), n_agents=4, strategy=Strategy.LOCAL_SEARCH, seed=SEED)
# Colors: clean = white, dirty = brown, locked = black.
CMAP = ListedColormap(["#ffffff", "#8b5a2b", "#222222"])


def record(config: SimConfig):
    sim = CleaningSimulation(config, record=True)
    result = sim.run()
    return sim, result


def main() -> None:
    OUTPUT.mkdir(exist_ok=True)
    sim1, result1 = record(SIM1)
    sim2, result2 = record(SIM2)
    frames_total = max(len(sim1.frames), len(sim2.frames))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6.2))
    titles = [
        f"Simulation 1: 1 agent (clean in {result1.time_to_clean} ticks)",
        f"Simulation 2: 4 agents (clean in {result2.time_to_clean} ticks)",
    ]
    artists = []
    for ax, sim, title in ((ax1, sim1, titles[0]), (ax2, sim2, titles[1])):
        image = ax.imshow(sim.frames[0].cells, cmap=CMAP, vmin=0, vmax=2, interpolation="nearest")
        dots, = ax.plot([], [], "o", color="tab:blue", markersize=9, markeredgecolor="white")
        ax.set_title(title)
        ax.set_xticks([])
        ax.set_yticks([])
        artists.append((image, dots, sim))

    def update(index: int):
        for image, dots, sim in artists:
            frame = sim.frames[min(index, len(sim.frames) - 1)]
            image.set_data(frame.cells)
            dots.set_data([c for _, c in frame.agents], [r for r, _ in frame.agents])
        fig.suptitle(f"Tick {min(index, frames_total - 1)}   (white = clean, brown = dirty, black = locked, blue = agent)")
        return []

    anim = animation.FuncAnimation(fig, update, frames=frames_total, interval=60, blit=False)
    anim.save(OUTPUT / "simulation.mp4", writer=animation.FFMpegWriter(fps=15, bitrate=1800), dpi=110)
    print(f"Saved {OUTPUT / 'simulation.mp4'} ({frames_total} ticks)")


if __name__ == "__main__":
    main()
