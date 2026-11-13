"""Cleaning agent: battery budget, charging at start points, and three trajectory strategies."""

import math
import random
from enum import Enum

from room import DIRTY, Position, Room

RESERVE_FRACTION = 0.05


class Strategy(str, Enum):
    LOCAL_SEARCH = "local_search"
    ZIGZAG = "zigzag"
    RANDOM = "random"


class Cleaner:
    """Each tick the agent either recharges, cleans its cell, walks home, or explores.

    A tick is one action, so cleaning costs one tick and no battery; every move costs one
    battery unit, which is also one cell of the visit budget.
    """

    def __init__(
        self,
        start: Position,
        battery: int,
        strategy: Strategy,
        station_dists: dict[Position, dict[Position, int]],
        route: list[Position],
        rng: random.Random,
    ):
        self.pos = start
        self.capacity = battery
        self.battery = battery
        self.strategy = strategy
        self.station_dists = station_dists  # shared: every agent's start point is a charger
        self.route = route
        self.route_index = route.index(start) if route else 0
        self.rng = rng
        self.reserve = math.ceil(RESERVE_FRACTION * battery)
        self.path: list[Position] = []
        self.target: Position | None = None
        self.visited = {start}
        self.moves = 0
        self.recharges = 0

    def act(self, room: Room, claims: set[Position]) -> None:
        if self.pos in self.station_dists and self.battery < self.capacity:
            self._recharge()
        elif room.state(self.pos) == DIRTY:
            self._clean(room, claims)
        elif self._must_return():
            self._step_home(room, claims)
        else:
            self._explore(room, claims)

    def _distance_home(self) -> int:
        return min(dist.get(self.pos, math.inf) for dist in self.station_dists.values())

    def _must_return(self) -> bool:
        """Head for the nearest charger once the battery left on arrival would be at most 5%."""
        return self.battery - self._distance_home() <= self.reserve

    def _recharge(self) -> None:
        self.battery = self.capacity
        self.recharges += 1

    def _clean(self, room: Room, claims: set[Position]) -> None:
        room.clean(self.pos)
        claims.discard(self.pos)
        self._release_target(claims)  # the target may differ from the cell cleaned here

    def _step_home(self, room: Room, claims: set[Position]) -> None:
        self._release_target(claims)
        nearest = min(self.station_dists.values(), key=lambda d: d.get(self.pos, math.inf))
        self._move(min(room.neighbors(self.pos), key=lambda p: nearest[p]))

    def _explore(self, room: Room, claims: set[Position]) -> None:
        if self.strategy is Strategy.LOCAL_SEARCH:
            self._local_search(room, claims)
        elif self.strategy is Strategy.ZIGZAG:
            self._zigzag(room)
        else:
            self._random_walk(room)

    def _local_search(self, room: Room, claims: set[Position]) -> None:
        """Walk to the nearest dirty cell that no other agent is already heading for."""
        if self.target is not None and room.state(self.target) != DIRTY:
            self._release_target(claims)  # someone else cleaned it on the way
        if not self.path:
            self.path = room.path_to(
                self.pos,
                lambda p: room.state(p) == DIRTY and p not in claims,
            )
            if not self.path:
                return  # nothing left to claim: idle
            self.target = self.path[-1]
            claims.add(self.target)
        self._move(self.path.pop(0))

    def _zigzag(self, room: Room) -> None:
        """Follow the serpentine route cyclically, starting from the agent's own start cell."""
        if not self.path:
            target = self.route[self.route_index]
            if target == self.pos:
                self.route_index = (self.route_index + 1) % len(self.route)
                target = self.route[self.route_index]
            self.path = room.path_to(self.pos, lambda p: p == target)
        self._move(self.path.pop(0))

    def _random_walk(self, room: Room) -> None:
        self._move(self.rng.choice(room.neighbors(self.pos)))

    def _release_target(self, claims: set[Position]) -> None:
        if self.target is not None:
            claims.discard(self.target)
        self.target = None
        self.path = []

    def _move(self, nxt: Position) -> None:
        if self.battery == 0:
            return  # stranded: the return rule should prevent this
        self.pos = nxt
        self.battery -= 1
        self.moves += 1
        self.visited.add(nxt)
