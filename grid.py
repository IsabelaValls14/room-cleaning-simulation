"""The room as an M x N grid, with the matrices from the course notebook.

Nodes are numbered row by row (node = row * N + col), as in numpy.ravel_multi_index.
  S: adjacency (which cells an agent can move to; 8 neighbours, diagonals included)
  D: distances in metres between every pair of cells (30 cm per tile)
  P: transition probabilities, uniform over the neighbours of each cell
"""

from collections import deque

import numpy as np

D_BASE = 0.3  # metres per tile (30 cm floor tiles), as in the supplementary notebook


class Grid:
    def __init__(self, rows: int, cols: int):
        if rows < 1 or cols < 1:
            raise ValueError("the grid needs at least one row and one column")
        self.rows = rows
        self.cols = cols
        self.size = rows * cols
        self.S = self._adjacency()
        self.D = self._distances()
        self.P = self._probabilities()
        self.adjacent = {n: [int(m) for m in np.flatnonzero(self.S[n])] for n in range(self.size)}

    def node(self, row: int, col: int) -> int:
        return row * self.cols + col

    def coords(self, node: int) -> tuple[int, int]:
        return divmod(node, self.cols)

    def point(self, node: int) -> tuple[int, int, int]:
        """(x, y, z) as written to Nodes.csv: x is the column, y is the row."""
        row, col = self.coords(node)
        return (col, row, 0)

    def _adjacency(self) -> np.ndarray:
        S = np.zeros((self.size, self.size))
        for row in range(self.rows):
            for col in range(self.cols):
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        r, c = row + dr, col + dc
                        if 0 <= r < self.rows and 0 <= c < self.cols:
                            S[self.node(row, col), self.node(r, c)] = 1
        return S

    def _distances(self) -> np.ndarray:
        D = np.zeros((self.size, self.size))
        for n in range(self.size):
            i, j = self.coords(n)
            for m in range(self.size):
                if n == m:
                    continue
                k, l = self.coords(m)
                D[n, m] = D_BASE * np.linalg.norm([i - k, j - l])
        return D

    def _probabilities(self) -> np.ndarray:
        P = self.S.copy()
        for i in range(self.size):
            P[i, :] /= P[i, :].sum()
        return P

    def path_to(self, start: int, is_goal) -> list[int]:
        """Shortest path (in moves) from start, start excluded, to the first goal node found by BFS.

        Neighbours are tried in increasing node number, so ties are always broken the same way.
        Returns an empty list when no goal node is reachable.
        """
        parents: dict[int, int | None] = {start: None}
        queue = deque([start])
        while queue:
            current = queue.popleft()
            if current != start and is_goal(current):
                path = []
                while current != start:
                    path.append(current)
                    current = parents[current]
                return path[::-1]
            for nxt in self.adjacent[current]:
                if nxt not in parents:
                    parents[nxt] = current
                    queue.append(nxt)
        return []

    def snake_route(self) -> list[int]:
        """Zigzag order used by the notebook: left to right on even rows, right to left on odd rows."""
        route = []
        for row in range(self.rows):
            cols = range(self.cols) if row % 2 == 0 else range(self.cols - 1, -1, -1)
            route.extend(self.node(row, col) for col in cols)
        return route

    def cycle_route(self) -> list[int]:
        """The snake route closed into a loop: the last cell walks back to the first by the shortest path."""
        route = self.snake_route()
        back = self.path_to(route[-1], lambda n: n == route[0])
        return route + back[:-1]
