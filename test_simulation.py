"""Behavior tests: the grid matrices (checked against the course notebook), the agents, the files and the CLI."""

import random

import numpy as np
import pytest

from cleaner import Strategy
from cli import build_parser, main, parse_video_urls
from data import load_nodes, load_routes, write_nodes, write_routes
from grid import Grid
from simulation import CleaningSimulation, SimConfig, random_dirt


@pytest.fixture(scope="module")
def grid():
    return Grid(8, 8)


def test_neighbours_of_cell_8_match_the_notebook(grid):
    # Notebook: numpy.where(S[8,:] != 0)[0] -> [0, 1, 9, 16, 17]
    assert list(np.flatnonzero(grid.S[8, :])) == [0, 1, 9, 16, 17]


def test_notebook_path_is_valid_and_has_the_same_probability_score(grid):
    # Notebook path [0,1,2,3,4,5,6,15] gives -log(prod P) = 10.755239763272712
    path = [0, 1, 2, 3, 4, 5, 6, 15]
    assert all(grid.S[a, b] == 1 for a, b in zip(path, path[1:]))
    score = -np.log(np.prod([grid.P[a, b] for a, b in zip(path, path[1:])]))
    assert score == pytest.approx(10.755239763272712)


def test_distance_between_diagonal_neighbours_is_0_3_times_root_2(grid):
    assert grid.D[0, 9] == pytest.approx(0.3 * np.sqrt(2))


def test_every_row_of_P_is_a_probability_distribution(grid):
    assert np.allclose(grid.P.sum(axis=1), 1.0)


def test_zigzag_route_matches_the_notebook_order(grid):
    # Notebook B: rows left to right, then right to left on odd rows (0..7, 15..8, 16..23, ...)
    expected = list(range(8)) + list(range(15, 7, -1)) + list(range(16, 24)) + list(range(31, 23, -1))
    assert grid.snake_route()[:32] == expected


def test_cycle_route_visits_every_cell_with_connected_steps(grid):
    loop = grid.cycle_route()
    assert set(loop) == set(range(grid.size))
    assert all(grid.S[a, b] == 1 for a, b in zip(loop, loop[1:] + loop[:1]))


def test_dirt_count_is_the_requested_percentage_and_changes_with_the_seed(grid):
    a = random_dirt(grid, 0.3, random.Random(0))
    b = random_dirt(grid, 0.3, random.Random(1))
    assert len(a) == round(0.3 * 64) == 19
    assert a != b


def test_simulation_one_agent_local_search_finishes_and_routes_are_adjacent():
    sim = CleaningSimulation(SimConfig(n_agents=1, strategy=Strategy.LOCAL_SEARCH, seed=0))
    result = sim.run()
    assert result.finished and result.cleaned_pct == 100.0
    route = sim.routes()[1]
    assert all(sim.grid.S[a, b] == 1 for a, b in zip(route, route[1:]))


@pytest.mark.parametrize("strategy", list(Strategy))
def test_every_strategy_finishes_with_several_agents(strategy):
    result = CleaningSimulation(SimConfig(n_agents=4, strategy=strategy, seed=3)).run()
    assert result.finished


def test_all_agents_start_at_the_same_cell():
    sim = CleaningSimulation(SimConfig(n_agents=4, start=5))
    assert {cleaner.pos for cleaner in sim.cleaners} == {5}
    assert all(route[0] == 5 for route in sim.routes().values())


def test_random_strategy_is_reproducible_for_the_same_seed():
    config = SimConfig(n_agents=3, strategy=Strategy.RANDOM, seed=5)
    assert CleaningSimulation(config).run() == CleaningSimulation(config).run()


def test_nodes_and_routes_files_round_trip(tmp_path):
    sim = CleaningSimulation(SimConfig(n_agents=2, strategy=Strategy.ZIGZAG, seed=1))
    sim.run()
    grid = sim.grid
    write_nodes(tmp_path / "Nodes.csv", [grid.point(n) for n in range(grid.size)], sim.dirty_at_start)
    write_routes(tmp_path / "Routes.csv", sim.routes())
    nodes = load_nodes(tmp_path / "Nodes.csv")
    routes = load_routes(tmp_path / "Routes.csv")
    assert set(nodes) == set(range(64))
    assert {n for n, node in nodes.items() if node.dirt == 1} == set(sim.dirty_at_start)
    assert routes == sim.routes()


def test_parser_has_exactly_the_simulate_and_experiment_subcommands():
    subparsers = next(a for a in build_parser()._actions if a.dest == "command")
    assert set(subparsers.choices) == {"simulate", "experiment"}


def test_simulate_takes_room_agents_strategy_and_seed_as_parameters():
    args = build_parser().parse_args([
        "simulate", "--rows", "10", "--cols", "12", "--dirty", "0.25", "--agents", "4",
        "--strategy", "zigzag", "--seed", "9", "--start", "7",
    ])
    assert (args.rows, args.cols, args.dirty, args.agents, args.seed, args.start) == (10, 12, 0.25, 4, 9, 7)
    assert args.strategy is Strategy.ZIGZAG


def test_simulate_writes_nodes_and_routes_files(tmp_path):
    main(["simulate", "--agents", "4", "--strategy", "local_search", "--data-dir", str(tmp_path)])
    assert len(load_nodes(tmp_path / "Nodes.csv")) == 64
    assert set(load_routes(tmp_path / "Routes.csv")) == {1, 2, 3, 4}


def test_experiment_rejects_fewer_than_four_agents_for_simulation_two(tmp_path):
    with pytest.raises(SystemExit):
        main(["experiment", "--scaling-agents", "3", "--output", str(tmp_path), "--skip-videos", "--skip-report"])


def test_video_urls_map_each_strategy_to_its_link():
    urls = parse_video_urls(["local_search=https://drive.google.com/a", "zigzag=https://drive.google.com/b"])
    assert urls == {"local_search": "https://drive.google.com/a", "zigzag": "https://drive.google.com/b"}


def test_video_url_with_unknown_strategy_is_rejected():
    with pytest.raises(SystemExit):
        parse_video_urls(["spiral=https://drive.google.com/c"])
