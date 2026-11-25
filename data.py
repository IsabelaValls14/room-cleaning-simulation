"""Nodes.csv (cell number, position and dirt) and Routes.csv (agent and the node it moves to, in order).

The format is the one written by the course notebook. Main.py reads the same two files.
"""

import ast
import csv
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent  # same folder as Main.py, which reads the same files
NODES_FILE = "Nodes.csv"
ROUTES_FILE = "Routes.csv"


@dataclass(frozen=True)
class Node:
    node: int
    point: tuple[float, float, float]
    dirt: int


def load_nodes(path: Path) -> dict[int, Node]:
    nodes: dict[int, Node] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            point = tuple(float(v) for v in ast.literal_eval(row["Points"]))
            if len(point) != 3:
                raise ValueError(f"node {row['Node']}: expected 3 coordinates, got {point}")
            dirt = int(row["Dirt"])
            if dirt not in (0, 1):
                raise ValueError(f"node {row['Node']}: Dirt must be 0 or 1, got {dirt}")
            node = int(row["Node"])
            if node in nodes:
                raise ValueError(f"node {node} appears twice in {path.name}")
            nodes[node] = Node(node, point, dirt)
    return nodes


def load_routes(path: Path) -> dict[int, list[int]]:
    routes: dict[int, list[int]] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            routes.setdefault(int(row["Agent"]), []).append(int(row["Node"]))
    return routes


def write_nodes(path: Path, points: list[tuple[int, int, int]], dirty: set[int]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Node", "Points", "Dirt"])
        for n, point in enumerate(points):
            writer.writerow([n, f"({point[0]},{point[1]},{point[2]})", 1 if n in dirty else 0])


def write_routes(path: Path, routes: dict[int, list[int]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Agent", "Node"])
        for agent in sorted(routes):
            for n in routes[agent]:
                writer.writerow([agent, n])
