"""Behavior-preserving regression tests for Organism.move optimization.

The baseline movement function is frozen from the earlier main commit and
must not import the optimized implementation.
"""
from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

import src.organism as organism_module
from src.environment import Environment
from src.organism import Organism
from src.simulation import Simulation
from reference_move_baseline import reference_move


ROOT = Path(__file__).resolve().parents[1]


def new_agent(x: int, y: int, *, memory: bool, expired: bool = False) -> Organism:
    agent = Organism(
        x=x,
        y=y,
        initial_energy=100.0,
        genome_length=120,
        genome=np.zeros(120, dtype=int),
        organism_id=1,
    )
    agent.phenotype.update(
        exploration_tendency=0.5,
        site_fidelity=0.7,
        risk_tolerance=0.3,
    )
    if memory:
        agent.last_food_position = (99, 99)
        agent.last_food_step = -100 if expired else 0
    return agent


def behavior_settings(*, detection_range: int) -> dict:
    return {
        "food_detection_range": detection_range,
        "current_cell_food_weight": 8.0,
        "nearby_food_weight": 4.0,
        "site_memory_weight": 2.0,
        "site_memory_steps": 20,
        "current_step": 5,
    }


def rng_equal(left: tuple, right: tuple) -> None:
    assert left[0] == right[0]
    np.testing.assert_array_equal(left[1], right[1])
    assert left[2:] == right[2:]


# Finite edges, both periodic boundaries, tiny grids with aliased directions,
# memory on/off/expired, food search over multiple cells, and movement styles.
SCENARIOS = [
    (100, 100, True, "moore", 0, 0, True, False, 1, True, [(99, 99), (1, 1)]),
    (100, 100, True, "moore", 99, 99, True, False, 2, False, [(0, 99), (0, 0)]),
    (100, 100, False, "moore", 0, 0, True, False, 1, False, [(99, 99), (1, 0)]),
    (100, 100, False, "moore", 50, 50, False, False, 1, False, [(49, 50)]),
    (100, 100, True, "von_neumann", 0, 50, True, False, 3, True, [(99, 50)]),
    (100, 100, False, "von_neumann", 0, 50, True, True, 1, True, [(0, 49)]),
    (100, 100, True, "moore", 99, 50, False, False, 0, True, [(99, 50)]),
    (2, 2, True, "moore", 0, 0, True, False, 2, False, [(1, 0)]),
    (2, 2, False, "moore", 1, 1, True, False, 1, False, [(0, 0)]),
    (1, 1, True, "moore", 0, 0, True, False, 1, False, [(0, 0)]),
    (1, 1, False, "von_neumann", 0, 0, False, False, 1, False, [(0, 0)]),
]


@pytest.mark.parametrize("seed", [0, 1, 42])
@pytest.mark.parametrize(
    ("width", "height", "periodic", "move_type", "x", "y",
     "memory", "expired", "detection", "low_energy", "food"),
    SCENARIOS,
)
def test_move_probabilities_and_rng_match_frozen_original(
    seed: int,
    width: int,
    height: int,
    periodic: bool,
    move_type: str,
    x: int,
    y: int,
    memory: bool,
    expired: bool,
    detection: int,
    low_energy: bool,
    food: list[tuple[int, int]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = new_agent(x, y, memory=memory, expired=expired)
    optimized = deepcopy(original)
    env = Environment(width=width, height=height, periodic_boundary=periodic)
    env.food = set(food)
    settings = behavior_settings(detection_range=detection)

    # Intercept the probability arrays, then use NumPy's original RNG
    # function to preserve draws and advance its state normally.
    actual_choice = np.random.choice
    distributions = []

    def capture_choice(*args, **kwargs):
        distributions.append(np.asarray(kwargs["p"]).copy())
        return actual_choice(*args, **kwargs)

    with monkeypatch.context() as m:
        m.setattr(np.random, "choice", capture_choice)

        np.random.seed(seed)
        was_moved = reference_move(
            original, width, height, move_type, env,
            low_energy, settings, periodic,
        )
        before_state = np.random.get_state()
        original_probabilities = [x.copy() for x in distributions]
        distributions.clear()

        np.random.seed(seed)
        is_moved = optimized.move(
            width, height, move_type, env,
            low_energy, settings, periodic,
        )
        after_state = np.random.get_state()
        optimized_probabilities = [x.copy() for x in distributions]

    assert was_moved == is_moved
    assert (original.x, original.y) == (optimized.x, optimized.y)
    rng_equal(before_state, after_state)
    assert len(original_probabilities) == len(optimized_probabilities)
    for before_p, after_p in zip(original_probabilities, optimized_probabilities):
        # Exact byte-for-byte equivalence, not only approximate values.
        np.testing.assert_array_equal(before_p, after_p, strict=True)


def test_memory_distance_calculated_once_per_move(monkeypatch: pytest.MonkeyPatch) -> None:
    agent = new_agent(50, 50, memory=True)
    env = Environment(100, 100, periodic_boundary=True)
    original_distance = organism_module.manhattan_distance
    calls = []

    def counting_distance(*args, **kwargs):
        calls.append(args)
        return original_distance(*args, **kwargs)

    monkeypatch.setattr(organism_module, "manhattan_distance", counting_distance)
    np.random.seed(1)
    agent.move(100, 100, "moore", env, False, behavior_settings(detection_range=1), True)
    # One from current position, then one for each of 8 move directions.
    assert len(calls) == 9
    assert calls[0][1] == (50, 50)


def load_config(name: str, seed: int) -> dict:
    with (ROOT / "configs" / name).open(encoding="utf-8") as stream:
        cfg = yaml.safe_load(stream)
    cfg["simulation"]["random_seed"] = seed
    return cfg


def run_steps(config: dict, n: int) -> tuple[Simulation, tuple]:
    sim = Simulation(deepcopy(config))
    for _ in range(n):
        sim.step()
    return sim, np.random.get_state()


@pytest.mark.parametrize(
    "name", [
        "default.yaml", "patch16.yaml",
        "random_periodic.yaml", "step4_patch9.yaml",
    ],
)
def test_full_simulation_same_seed_has_identical_outputs(
    name: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = load_config(name, seed=0)
    with monkeypatch.context() as m:
        m.setattr(Organism, "move", reference_move)
        before, before_rng = run_steps(cfg, 30)
    after, after_rng = run_steps(cfg, 30)

    rng_equal(before_rng, after_rng)
    assert before.environment.food == after.environment.food
    assert len(before.organisms) == len(after.organisms)
    for a, b in zip(before.organisms, after.organisms):
        assert (a.organism_id, a.x, a.y, a.age, a.energy) == (
            b.organism_id, b.x, b.y, b.age, b.energy
        )
        np.testing.assert_array_equal(a.genome, b.genome)
        assert a.phenotype == b.phenotype
        assert a.last_food_position == b.last_food_position

    pd.testing.assert_frame_equal(
        before.logger.to_dataframe(),
        after.logger.to_dataframe(),
        check_exact=True,
    )
    pd.testing.assert_frame_equal(
        pd.DataFrame.from_dict(before.lineage_records, orient="index").sort_index(),
        pd.DataFrame.from_dict(after.lineage_records, orient="index").sort_index(),
        check_exact=True,
    )
