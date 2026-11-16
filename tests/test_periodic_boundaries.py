"""Regression tests for periodic geometry, movement and exchange behavior."""
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest
import yaml

from src.environment import Environment
from src.initial_placement import initial_placement_candidates
from src.organism import Organism
from src.simulation import Simulation
from src.spatial import (
    axis_distance,
    manhattan_distance,
    squared_euclidean_distance,
    wrap_coordinate,
)

ROOT = Path(__file__).resolve().parents[1]


def config(name: str = "default.yaml") -> dict:
    with (ROOT / "configs" / name).open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def organism(x: int, y: int, organism_id: int = 1) -> Organism:
    agent = Organism(
        x=x, y=y, initial_energy=100.0,
        genome_length=120, genome=np.zeros(120, dtype=int),
        organism_id=organism_id,
    )
    agent.phenotype.update(
        exploration_tendency=0.5,
        site_fidelity=1.0,
        risk_tolerance=1.0,
    )
    return agent


def behavior(**overrides) -> dict:
    settings = dict(
        food_detection_range=1,
        site_memory_steps=20,
        current_cell_food_weight=8.0,
        nearby_food_weight=4.0,
        site_memory_weight=2.0,
        current_step=0,
    )
    settings.update(overrides)
    return settings


def test_toroidal_distance_and_wrap() -> None:
    assert wrap_coordinate(-1, 100, True) == 99
    assert wrap_coordinate(100, 100, True) == 0
    assert wrap_coordinate(-1, 100, False) == -1
    assert axis_distance(0, 99, 100, True) == 1
    assert axis_distance(0, 99, 100, False) == 99
    assert manhattan_distance((0, 0), (99, 99), 100, 100, True) == 2
    assert squared_euclidean_distance((0, 0), (99, 99), 100, 100, True) == 2


@pytest.mark.parametrize(
    ("config_file", "area", "count", "each_area"),
    [
        ("default.yaml", 596, 4, 149),
        ("patch16.yaml", 592, 16, 37),
    ],
)
def test_patch_areas_remain_constant_with_periodic_boundaries(
    config_file: str, area: int, count: int, each_area: int,
) -> None:
    cfg = config(config_file)
    assert cfg["environment"]["periodic_boundary"] is True
    sim = Simulation(cfg)
    assert sim.periodic_boundary
    assert sim.environment.periodic_boundary
    assert len(sim.environment.patch_centers) == count
    assert len(set(sim.environment._get_patch_cells())) == area
    assert len(sim.environment.food) == 500
    assert sim.environment.food <= set(sim.environment._get_patch_cells())
    assert sim.environment.get_food_flow_metrics()["patch_area"] == area

    individual_regions = []
    for center in sim.environment.patch_centers:
        env = Environment(
            100, 100,
            respawn_mode="patch",
            patch_count=1,
            patch_radius=cfg["environment"]["patch_radius"],
            patch_radius_mode="exact",
            periodic_boundary=True,
            patch_centers_config=[center],
        )
        env._init_patch_regions()
        cells = set(env._get_patch_cells())
        assert len(cells) == each_area
        individual_regions.append(cells)
    assert sum(map(len, individual_regions)) == len(
        set().union(*individual_regions)
    )


def test_patch_center_on_corner_wraps_as_single_circular_patch() -> None:
    env = Environment(
        width=100, height=100, respawn_mode="patch",
        patch_count=1, patch_radius=2.0, patch_radius_mode="exact",
        patch_centers_config=[(0, 0)], periodic_boundary=True,
    )
    env._init_patch_regions()
    cells = set(env._get_patch_cells())
    assert len(cells) == 13
    assert {(0, 0), (99, 0), (0, 99), (99, 99), (1, 0)} <= cells

    finite = Environment(
        width=100, height=100, respawn_mode="patch",
        patch_count=1, patch_radius=2.0, patch_radius_mode="exact",
        patch_centers_config=[(0, 0)], periodic_boundary=False,
    )
    finite._init_patch_regions()
    assert len(finite._get_patch_cells()) < len(cells)


def test_food_access_normalizes_outside_coordinates_only_in_periodic_mode() -> None:
    periodic = Environment(100, 100, periodic_boundary=True)
    finite = Environment(100, 100, periodic_boundary=False)
    periodic.food.add((0, 4))
    finite.food.add((0, 4))
    assert periodic.has_food(100, 4)
    assert not finite.has_food(100, 4)
    periodic.remove_food(100, 4)
    assert not periodic.has_food(0, 4)


def test_boundary_food_is_detected_and_single_step_wraps(monkeypatch) -> None:
    env = Environment(100, 100, periodic_boundary=True)
    env.food.add((99, 50))
    agent = organism(0, 50)
    seen = {}

    def choose(n, p):
        seen["probabilities"] = np.array(p)
        return 2  # candidate (-1, 0), after stay and (-1, -1)

    monkeypatch.setattr(np.random, "choice", choose)
    moved = agent.move(
        100, 100, "moore", env, False, behavior(),
        periodic_boundary=True,
    )
    assert moved
    assert (agent.x, agent.y) == (99, 50)
    assert seen["probabilities"][2] > seen["probabilities"][7]
    assert seen["probabilities"].sum() == pytest.approx(1)


def test_memory_prefers_shorter_wrapped_manhattan_distance(monkeypatch) -> None:
    agent = organism(0, 50)
    agent.last_food_position = (99, 50)
    agent.last_food_step = 0
    env = Environment(100, 100, periodic_boundary=True)
    seen = {}

    def choose(n, p):
        seen["probabilities"] = np.array(p)
        return 0  # stay; we only inspect the calculated weights

    monkeypatch.setattr(np.random, "choice", choose)
    agent.move(
        100, 100, "moore", env, False, behavior(),
        periodic_boundary=True,
    )
    assert seen["probabilities"][2] > seen["probabilities"][7]


def test_periodic_small_grid_does_not_duplicate_destinations(monkeypatch) -> None:
    env = Environment(2, 2, periodic_boundary=True)
    agent = organism(0, 0)
    candidates = []

    def choose(n, p):
        candidates.append(n)
        assert len(p) == 4  # stay and three distinct destination cells
        return 0

    monkeypatch.setattr(np.random, "choice", choose)
    assert agent.move(2, 2, "moore", env, False, behavior(), True) is False
    assert candidates == [4]

    single = Environment(1, 1, periodic_boundary=True)
    assert organism(0, 0).move(
        1, 1, "moore", single, False, behavior(), True
    ) is False


def test_periodic_offspring_placement_wraps(monkeypatch) -> None:
    parent = organism(0, 0)
    monkeypatch.setattr(np.random, "randint", lambda low, high: -2)
    child = parent.reproduce(
        width=100, height=100, offspring_energy=5,
        reproduction_cost=10, mutation_rate=0, genome_length=120,
        child_organism_id=2, birth_step=1, periodic_boundary=True,
    )
    assert (child.x, child.y) == (98, 98)
    assert parent.energy == pytest.approx(90)


@pytest.mark.parametrize("periodic", [False, True])
def test_donor_search_respects_boundary_setting(periodic: bool) -> None:
    cfg = config()
    cfg["environment"].update(
        width=100, height=100, mode="random",
        periodic_boundary=periodic, initial_food_count=0,
    )
    cfg["organism"]["initial_population"] = 0
    sim = Simulation(cfg)
    parent = organism(0, 50, organism_id=0)
    neighbor = organism(99, 50, organism_id=1)
    indexed = {(0, 50): [parent], (99, 50): [neighbor]}
    donors = sim._get_gene_exchange_donor_candidates(parent, indexed)
    assert donors == ([neighbor] if periodic else [])


def test_donor_search_does_not_duplicate_small_grid_candidates() -> None:
    cfg = config()
    cfg["environment"].update(
        width=2, height=2, mode="random",
        periodic_boundary=True, initial_food_count=0,
    )
    cfg["organism"]["initial_population"] = 0
    sim = Simulation(cfg)
    parent = organism(0, 0, organism_id=0)
    donor = organism(1, 0, organism_id=1)
    donors = sim._get_gene_exchange_donor_candidates(
        parent, {(0, 0): [parent], (1, 0): [donor]},
    )
    assert donors == [donor]


def test_initial_placement_uses_shortest_wrapped_distance() -> None:
    region = {(0, 5)}
    near_periodic = initial_placement_candidates(
        10, 10, region, "near", 1.0, 3.0,
        periodic_boundary=True,
    )
    near_finite = initial_placement_candidates(
        10, 10, region, "near", 1.0, 3.0,
        periodic_boundary=False,
    )
    assert (9, 5) in near_periodic
    assert (9, 5) not in near_finite
    assert (1, 5) in near_periodic


def test_periodic_random_and_both_patch_modes_have_paired_founders() -> None:
    configs = [
        config("random_periodic.yaml"),
        config("default.yaml"),
        config("patch16.yaml"),
    ]
    assert [c["environment"]["mode"] for c in configs] == [
        "random", "patch", "patch"
    ]
    for case in configs:
        case["simulation"]["random_seed"] = 123
        assert case["environment"]["periodic_boundary"] is True
    sims = [Simulation(case) for case in configs]
    for other in sims[1:]:
        assert len(other.organisms) == len(sims[0].organisms) == 100
        for left, right in zip(sims[0].organisms, other.organisms):
            assert (left.x, left.y) == (right.x, right.y)
            assert np.array_equal(left.genome, right.genome)
            assert left.lifespan == right.lifespan


def test_vertical_wrap_and_diagonal_sensing(monkeypatch) -> None:
    env = Environment(100, 100, periodic_boundary=True)
    env.food.add((99, 99))
    agent = organism(0, 0)
    captured = {}

    def choose(n, p):
        captured["p"] = np.array(p)
        return 1  # (-1, -1) crosses both boundaries

    monkeypatch.setattr(np.random, "choice", choose)
    agent.move(100, 100, "moore", env, False, behavior(), True)
    assert (agent.x, agent.y) == (99, 99)
    assert captured["p"][1] > captured["p"][7]


def test_patch_region_food_flow_on_wrapped_edge() -> None:
    env = Environment(
        width=100, height=100, respawn_mode="patch",
        patch_count=1, patch_radius=2, patch_radius_mode="exact",
        patch_centers_config=[(0, 0)], periodic_boundary=True,
    )
    env.init_food(13)
    region = set(env._get_patch_cells())
    assert len(region) == 13
    assert env.food == region
    assert env.get_food_flow_metrics()["patch_area"] == 13
    env.reset_food_flow_counters()
    env.remove_food(-1, 0)
    stats = env.get_food_flow_metrics()
    assert stats["food_consumed_in"] == 1
    assert stats["food_in"] == 12


def test_legacy_config_remains_nonperiodic() -> None:
    cfg = config("step4_patch9.yaml")
    assert cfg["environment"].get("periodic_boundary", False) is False
    sim = Simulation(cfg)
    assert not sim.periodic_boundary
    assert len(sim.environment._get_patch_cells()) == 529
