"""Room environment: an M x N grid of clean, dirty and locked cells, plus path helpers."""

import random
from collections import deque
from dataclasses import dataclass

CLEAN = 0
DIRTY = 1
LOCKED = 2

MOVES = ((-1, 0), (1, 0), (0, -1), (0, 1))

Position = tuple[int, int]


@dataclass
class Room:
    cells: list[list[int]]
    dirty_left: int

    @property
    def rows(self) -> int:
        return len(self.cells)

    @property
    def cols(self) -> int:
        return len(self.cells[0])

    def state(self, pos: Position) -> int:
        r, c = pos
        return self.cells[r][c]

    def clean(self, pos: Position) -> None:
        if self.state(pos) != DIRTY:
            raise ValueError(f"cell {pos} is not dirty")
        r, c = pos
        self.cells[r][c] = CLEAN
        self.dirty_left -= 1

    def is_walkable(self, pos: Position) -> bool:
        r, c = pos
        return 0 <= r < self.rows and 0 <= c < self.cols and self.cells[r][c] != LOCKED

    def walkable_cells(self) -> list[Position]:
        return [
            (r, c)
            for r in range(self.rows)
            for c in range(self.cols)
            if self.cells[r][c] != LOCKED
        ]

    def neighbors(self, pos: Position) -> list[Position]:
        r, c = pos
        candidates = ((r + dr, c + dc) for dr, dc in MOVES)
        return [nxt for nxt in candidates if self.is_walkable(nxt)]

    def distances_from(self, start: Position) -> dict[Position, int]:
        """BFS distance from start to every reachable walkable cell."""
        dist = {start: 0}
        queue = deque([start])
        while queue:
            current = queue.popleft()
            for nxt in self.neighbors(current):
                if nxt not in dist:
                    dist[nxt] = dist[current] + 1
                    queue.append(nxt)
        return dist

    def path_to(self, start: Position, is_goal) -> list[Position]:
        """Shortest path from start (start excluded) to the nearest cell where is_goal holds.

        Returns an empty list when no such cell is reachable.
        """
        parents: dict[Position, Position | None] = {start: None}
        queue = deque([start])
        while queue:
            current = queue.popleft()
            if current != start and is_goal(current):
                path = []
                while current != start:
                    path.append(current)
                    current = parents[current]
                return path[::-1]
            for nxt in self.neighbors(current):
                if nxt not in parents:
                    parents[nxt] = current
                    queue.append(nxt)
        return []


def serpentine_route(room: Room) -> list[Position]:
    """Walkable cells in boustrophedon order: left to right, then right to left, row by row."""
    route = []
    for r in range(room.rows):
        columns = range(room.cols) if r % 2 == 0 else range(room.cols - 1, -1, -1)
        route.extend((r, c) for c in columns if room.is_walkable((r, c)))
    return route


def make_room(
    rows: int,
    cols: int,
    dirty_fraction: float,
    locked_fraction: float,
    rng: random.Random,
    max_attempts: int = 100,
) -> Room:
    """Random dirty and locked cells. Regenerates until every walkable cell is reachable."""
    total = rows * cols
    n_locked = round(total * locked_fraction)
    n_dirty = round(total * dirty_fraction)
    for _ in range(max_attempts):
        order = rng.sample(range(total), total)
        cells = [[CLEAN] * cols for _ in range(rows)]
        for index in order[:n_locked]:
            cells[index // cols][index % cols] = LOCKED
        for index in order[n_locked:n_locked + n_dirty]:
            cells[index // cols][index % cols] = DIRTY
        room = Room(cells, dirty_left=n_dirty)
        if _is_connected(room):
            return room
    raise RuntimeError("could not generate a connected room; lower locked_fraction")


def _is_connected(room: Room) -> bool:
    walkable = room.walkable_cells()
    return len(room.distances_from(walkable[0])) == len(walkable)
