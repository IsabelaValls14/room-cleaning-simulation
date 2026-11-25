"""One cleaning run on the grid: Simulation 1 (one agent) or Simulation 2 (several agents, one start cell)."""

import random
from dataclasses import dataclass

from cleaner import Cleaner, Strategy
from grid import Grid


@dataclass(frozen=True)
class SimConfig:
    rows: int = 8
    cols: int = 8
    dirty_fraction: float = 0.30
    n_agents: int = 1
    strategy: Strategy = Strategy.LOCAL_SEARCH
    max_steps: int = 1000
    start: int = 0
    seed: int = 0


@dataclass(frozen=True)
class RunResult:
    finished: bool
    time_to_clean: int | None
    visited_pct: float
    cleaned_pct: float
    moves: tuple[int, ...]
    distance_m: float

    @property
    def mean_moves(self) -> float:
        return sum(self.moves) / len(self.moves)

    @property
    def total_moves(self) -> int:
        return sum(self.moves)


@dataclass(frozen=True)
class Frame:
    time: int
    dirty: frozenset[int]
    agents: tuple[int, ...]


def random_dirt(grid: Grid, fraction: float, rng: random.Random) -> set[int]:
    """Dirty cells chosen at random: round(fraction * cells) of them."""
    if not 0 <= fraction <= 1:
        raise ValueError("dirty fraction must be between 0 and 1")
    return set(rng.sample(range(grid.size), round(fraction * grid.size)))


class CleaningSimulation:
    def __init__(self, config: SimConfig, record: bool = False):
        if config.n_agents < 1:
            raise ValueError("n_agents must be at least 1")
        self.config = config
        self.grid = Grid(config.rows, config.cols)
        if not 0 <= config.start < self.grid.size:
            raise ValueError(f"start cell {config.start} is outside the {config.rows}x{config.cols} grid")
        self.dirty = random_dirt(self.grid, config.dirty_fraction, random.Random(config.seed))
        self.dirty_at_start = frozenset(self.dirty)
        self.initial_dirty = len(self.dirty)
        self.claims: set[int] = set()
        # Every agent starts at the same cell (Simulation 2 rule; Simulation 1 has one agent).
        self.cleaners = [
            Cleaner(config.start, config.strategy, self.grid, random.Random(config.seed * 1000 + i))
            for i in range(config.n_agents)
        ]
        self.time = 0
        self.time_to_clean: int | None = None
        self.frames: list[Frame] | None = [] if record else None
        self._record()

    def tick(self) -> None:
        """Every agent acts once, in list order."""
        for cleaner in self.cleaners:
            cleaner.act(self.dirty, self.claims)
        self.time += 1
        if not self.dirty and self.time_to_clean is None:
            self.time_to_clean = self.time
        self._record()

    def run(self) -> RunResult:
        while self.time < self.config.max_steps and self.dirty:
            self.tick()
        return self.result()

    def result(self) -> RunResult:
        visited = set().union(*(cleaner.visited for cleaner in self.cleaners))
        cleaned = self.initial_dirty - len(self.dirty)
        distance = sum(
            self.grid.D[a, b]
            for cleaner in self.cleaners
            for a, b in zip(cleaner.route, cleaner.route[1:])
        )
        return RunResult(
            finished=not self.dirty,
            time_to_clean=self.time_to_clean,
            visited_pct=100 * len(visited) / self.grid.size,
            cleaned_pct=100 * cleaned / self.initial_dirty if self.initial_dirty else 100.0,
            moves=tuple(cleaner.moves for cleaner in self.cleaners),
            distance_m=float(distance),
        )

    def routes(self) -> dict[int, list[int]]:
        return {i + 1: list(cleaner.route) for i, cleaner in enumerate(self.cleaners)}

    def _record(self) -> None:
        if self.frames is not None:
            self.frames.append(Frame(
                time=self.time,
                dirty=frozenset(self.dirty),
                agents=tuple(cleaner.pos for cleaner in self.cleaners),
            ))
