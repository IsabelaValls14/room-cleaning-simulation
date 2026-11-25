"""Cleaning agent on the grid, with the three trajectory strategies (the three planning methods)."""

import random
from enum import Enum

from grid import Grid


class Strategy(str, Enum):
    LOCAL_SEARCH = "local_search"
    ZIGZAG = "zigzag"
    RANDOM = "random"


class Cleaner:
    """Each tick the agent either cleans the cell it stands on (no move) or moves to one neighbour.

    A tick is one action. Cleaning costs a tick. Each move costs a tick and is recorded in the route.
    """

    def __init__(self, start: int, strategy: Strategy, grid: Grid, rng: random.Random):
        self.pos = start
        self.strategy = strategy
        self.grid = grid
        self.rng = rng
        self.route = [start]
        self.visited = {start}
        self.target: int | None = None
        self.loop = grid.cycle_route() if strategy is Strategy.ZIGZAG else []
        self.loop_index = self.loop.index(start) if self.loop else 0

    @property
    def moves(self) -> int:
        return len(self.route) - 1

    def act(self, dirty: set[int], claims: set[int]) -> None:
        if self.pos in dirty:
            dirty.discard(self.pos)
            claims.discard(self.pos)
            self._release(claims)
            return
        if self.strategy is Strategy.LOCAL_SEARCH:
            self._local_search(dirty, claims)
        elif self.strategy is Strategy.ZIGZAG:
            self._zigzag()
        else:
            self._random_walk()

    def _local_search(self, dirty: set[int], claims: set[int]) -> None:
        """Walk the shortest path to the nearest dirty cell that no other agent is heading for."""
        if self.target is not None and self.target not in dirty:
            self._release(claims)
        if self.target is None:
            path = self.grid.path_to(self.pos, lambda n: n in dirty and n not in claims)
            if not path:
                return  # nothing left to claim: wait
            self.target = path[-1]
            claims.add(self.target)
        path = self.grid.path_to(self.pos, lambda n: n == self.target)
        self._move(path[0])

    def _zigzag(self) -> None:
        self.loop_index = (self.loop_index + 1) % len(self.loop)
        self._move(self.loop[self.loop_index])

    def _random_walk(self) -> None:
        """Next cell drawn from row pos of the probability matrix P."""
        row = self.grid.P[self.pos]
        nxt = self.rng.choices(range(self.grid.size), weights=row)[0]
        self._move(nxt)

    def _release(self, claims: set[int]) -> None:
        if self.target is not None:
            claims.discard(self.target)
        self.target = None

    def _move(self, nxt: int) -> None:
        self.pos = nxt
        self.route.append(nxt)
        self.visited.add(nxt)
