"""One cleaning run: Simulation 1 (one agent) or Simulation 2 (several agents, shared chargers)."""

import random
from dataclasses import dataclass

from cleaner import Cleaner, Strategy
from room import Position, Room, make_room, serpentine_route


@dataclass(frozen=True)
class SimConfig:
    rows: int = 20
    cols: int = 20
    dirty_fraction: float = 0.30
    locked_fraction: float = 0.10
    n_agents: int = 1
    battery: int = 250
    max_steps: int = 1000
    strategy: Strategy = Strategy.LOCAL_SEARCH
    seed: int = 0


@dataclass(frozen=True)
class RunResult:
    finished: bool
    time_to_clean: int | None
    visited_pct: float
    cleaned_pct: float
    moves: tuple[int, ...]
    recharges: int

    @property
    def mean_moves(self) -> float:
        return sum(self.moves) / len(self.moves)


@dataclass
class Frame:
    time: int
    cells: list[list[int]]
    agents: list[Position]


class CleaningSimulation:
    def __init__(self, config: SimConfig, record: bool = False):
        self.config = config
        self.rng = random.Random(config.seed)
        self.room: Room = make_room(
            config.rows,
            config.cols,
            config.dirty_fraction,
            config.locked_fraction,
            self.rng,
        )
        self.initial_dirty = self.room.dirty_left
        starts = self.rng.sample(self.room.walkable_cells(), config.n_agents)
        station_dists = {start: self.room.distances_from(start) for start in starts}
        route = serpentine_route(self.room)
        self.cleaners = [
            Cleaner(start, config.battery, config.strategy, station_dists, route, self.rng)
            for start in starts
        ]
        self.claims: set[Position] = set()
        self.time = 0
        self.time_to_clean: int | None = None
        self.frames: list[Frame] | None = [] if record else None
        self._record()

    def tick(self) -> None:
        """Every agent acts once, in list order."""
        for cleaner in self.cleaners:
            cleaner.act(self.room, self.claims)
        self.time += 1
        if self.room.dirty_left == 0 and self.time_to_clean is None:
            self.time_to_clean = self.time
        self._record()

    def run(self) -> RunResult:
        while self.time < self.config.max_steps and self.room.dirty_left > 0:
            self.tick()
        return self.result()

    def result(self) -> RunResult:
        visited = set().union(*(cleaner.visited for cleaner in self.cleaners))
        walkable = len(self.room.walkable_cells())
        cleaned = self.initial_dirty - self.room.dirty_left
        return RunResult(
            finished=self.room.dirty_left == 0,
            time_to_clean=self.time_to_clean,
            visited_pct=100 * len(visited) / walkable,
            cleaned_pct=100 * cleaned / self.initial_dirty,
            moves=tuple(cleaner.moves for cleaner in self.cleaners),
            recharges=sum(cleaner.recharges for cleaner in self.cleaners),
        )

    def _record(self) -> None:
        if self.frames is not None:
            self.frames.append(
                Frame(
                    time=self.time,
                    cells=[row[:] for row in self.room.cells],
                    agents=[cleaner.pos for cleaner in self.cleaners],
                )
            )
