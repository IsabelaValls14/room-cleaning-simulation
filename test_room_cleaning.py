"""Behavior tests for the room, the cleaning agents and full runs."""

import random

import pytest

from cleaner import Cleaner, Strategy
from room import CLEAN, DIRTY, LOCKED, Room, make_room, serpentine_route
from simulation import CleaningSimulation, SimConfig


def test_make_room_has_requested_dirty_and_locked_counts():
    room = make_room(20, 20, dirty_fraction=0.30, locked_fraction=0.10, rng=random.Random(1))
    flat = [cell for row in room.cells for cell in row]
    assert flat.count(DIRTY) == 120
    assert flat.count(LOCKED) == 40
    assert room.dirty_left == 120


def test_make_room_keeps_every_walkable_cell_reachable():
    room = make_room(20, 20, dirty_fraction=0.30, locked_fraction=0.10, rng=random.Random(2))
    walkable = room.walkable_cells()
    assert len(room.distances_from(walkable[0])) == len(walkable)


def test_serpentine_route_visits_every_walkable_cell_once_with_adjacent_steps():
    room = make_room(6, 5, dirty_fraction=0.2, locked_fraction=0.0, rng=random.Random(3))
    route = serpentine_route(room)
    assert sorted(route) == sorted(room.walkable_cells())
    assert all(abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1 for a, b in zip(route, route[1:]))


@pytest.mark.parametrize("strategy", list(Strategy))
def test_agents_never_enter_locked_cells_and_battery_never_goes_negative(strategy):
    sim = CleaningSimulation(SimConfig(n_agents=3, strategy=strategy, seed=4), record=True)
    sim.run()
    for frame in sim.frames:
        for r, c in frame.agents:
            assert frame.cells[r][c] != LOCKED
    for cleaner in sim.cleaners:
        assert 0 <= cleaner.battery <= cleaner.capacity


def test_agent_cleans_the_cell_it_stands_on_and_costs_no_battery():
    room = Room(cells=[[DIRTY, CLEAN]], dirty_left=1)
    cleaner = Cleaner((0, 0), battery=10, strategy=Strategy.LOCAL_SEARCH,
                      station_dists={(0, 0): room.distances_from((0, 0))},
                      route=[], rng=random.Random(0))
    claims: set = set()
    cleaner.act(room, claims)
    assert room.state((0, 0)) == CLEAN
    assert cleaner.battery == 10
    assert cleaner.moves == 0


def test_agent_walks_home_when_only_five_percent_would_remain():
    room = Room(cells=[[CLEAN] * 10], dirty_left=0)
    dists = {(0, 0): room.distances_from((0, 0))}
    cleaner = Cleaner((0, 0), battery=100, strategy=Strategy.RANDOM,
                      station_dists=dists, route=[], rng=random.Random(0))
    cleaner.pos = (0, 6)
    cleaner.battery = 6 + 5  # arriving at (0,0) would leave exactly the 5% reserve
    assert cleaner._must_return()
    cleaner.battery = 6 + 6
    assert not cleaner._must_return()


def test_run_finishes_and_reports_metrics_when_battery_is_enough():
    result = CleaningSimulation(SimConfig(battery=400, seed=5)).run()
    assert result.finished
    assert result.cleaned_pct == 100.0
    assert result.time_to_clean is not None
    assert 0 < result.visited_pct <= 100


def test_low_battery_forces_recharges_at_start_points():
    result = CleaningSimulation(SimConfig(battery=60, seed=6)).run()
    assert result.recharges > 0


def test_no_target_stays_claimed_after_all_dirt_is_gone():
    # Regression: an agent that cleaned a cell on the way to another target left that target claimed.
    sim = CleaningSimulation(SimConfig(n_agents=4, seed=0))
    sim.run()
    assert sim.room.dirty_left == 0
    assert sim.claims == set()


def test_same_seed_gives_same_result():
    config = SimConfig(n_agents=4, seed=7)
    assert CleaningSimulation(config).run() == CleaningSimulation(config).run()
