"""Tests for Euclidean distance and normalized TOTAL site-memory weight."""
from __future__ import annotations

from copy import deepcopy
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from src.environment import Environment
from src.organism import Organism
from src.simulation import Simulation


ROOT = Path(__file__).resolve().parents[1]
MOORE = (
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1), (0, 1),
    (1, -1), (1, 0), (1, 1),
)
VON_NEUMANN = ((-1, 0), (0, -1), (0, 1), (1, 0))


def agent(x: int, y: int, *, fidelity: float = 1.0) -> Organism:
    result = Organism(
        x=x, y=y, initial_energy=100, genome_length=120,
        genome=np.zeros(120, dtype=int), organism_id=1,
    )
    result.phenotype.update(
        exploration_tendency=0.5,
        risk_tolerance=1.0,
        site_fidelity=fidelity,
    )
    result.last_food_position = (23, 22)
    result.last_food_step = 0
    return result


def settings(*, memory_weight: float = 0.2, mode: str = "euclidean_inverse_total"):
    return {
        "food_detection_range": 1,
        "site_memory_steps": 20,
        "current_step": 5,
        "current_cell_food_weight": 1.0,
        "nearby_food_weight": 0.5,
        "site_memory_weight": memory_weight,
        "site_memory_mode": mode,
    }


def probabilities(
    individual: Organism,
    env: Environment,
    config: dict,
    monkeypatch: pytest.MonkeyPatch,
    move_type: str = "moore",
) -> np.ndarray:
    seen = {}

    def intercept_choice(n, p):
        seen["count"] = n
        seen["p"] = np.array(p, copy=True)
        return 0  # Do not move: measure the distribution only.

    with monkeypatch.context() as patch:
        patch.setattr(np.random, "choice", intercept_choice)
        assert individual.move(
            env.width, env.height, move_type, env, False, config,
            periodic_boundary=env.periodic_boundary,
        ) is False
    assert seen["count"] == len(seen["p"])
    return seen["p"]


@pytest.mark.parametrize(("move_type", "directions"), [
    ("moore", MOORE), ("von_neumann", VON_NEUMANN),
])
@pytest.mark.parametrize("fidelity", [1.0, 0.4, 0.0])
def test_total_memory_bonus_and_inverse_euclidean_ratios(
    move_type: str, directions: tuple, fidelity: float,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    individual = agent(20, 20, fidelity=fidelity)
    env = Environment(100, 100, periodic_boundary=False)
    p = probabilities(individual, env, settings(), monkeypatch, move_type)
    base = np.array([0.5] + [0.5 / len(directions)] * len(directions))

    # Independent expected formula for this *finite interior* position:
    # memory (23,22), current (20,20), Euclidean before sqrt(13).
    d_before = math.dist((20, 20), (23, 22))
    unnormalized = []
    for dx, dy in directions:
        d_after = math.dist((20 + dx, 20 + dy), (23, 22))
        unnormalized.append(
            (1.0 / (1.0 + d_after)) if d_after < d_before else 0.0
        )
    scores = np.array(unnormalized)
    bonus = np.zeros(len(directions) + 1)
    if scores.sum() > 0:
        bonus[1:] = 0.2 * fidelity * scores / scores.sum()

    # All direction probabilities, not just the chosen direction, must match.
    np.testing.assert_allclose(p, (base + bonus) / (1.0 + 0.2 * fidelity), atol=1e-15)
    assert bonus.sum() == pytest.approx(0.2 * fidelity)
    assert p.sum() == pytest.approx(1.0)

    if move_type == "moore" and fidelity > 0:
        # Right-up is closest; right is next; up is third.
        assert p[8] > p[7] > p[5]
        assert np.count_nonzero(bonus) == 3



def test_euclidean_closer_direction_not_manhattan_closer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # From (20,20) to (23,21), going (1,-1) decreases Euclidean
    # distance sqrt(10) -> sqrt(8), while Manhattan stays at 4.
    individual = agent(20, 20)
    individual.last_food_position = (23, 21)
    env = Environment(100, 100, periodic_boundary=False)
    p = probabilities(individual, env, settings(), monkeypatch)
    # Moore index 6 is direction (1,-1). It must receive a memory bonus.
    baseline_move_weight = 0.5 / 8
    assert p[6] > baseline_move_weight / 1.2


def test_wrap_around_distance_selects_single_shortest_direction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    individual = agent(0, 50)
    individual.last_food_position = (99, 50)
    env = Environment(100, 100, periodic_boundary=True)
    p = probabilities(individual, env, settings(), monkeypatch)

    expected = np.array([0.5] + [0.5 / 8] * 8)
    # Only (-1,0) actually decreases toroidal Euclidean distance 1 -> 0.
    expected[2] += 0.2
    expected /= 1.2
    np.testing.assert_allclose(p, expected, atol=1e-15)


@pytest.mark.parametrize("invalid_memory", ["no_location", "expired", "already_here"])
def test_no_memory_bonus_when_not_usable(
    invalid_memory: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    individual = agent(20, 20)
    if invalid_memory == "no_location":
        individual.last_food_position = None
    elif invalid_memory == "expired":
        individual.last_food_step = -100
    else:
        individual.last_food_position = (20, 20)
    env = Environment(100, 100, periodic_boundary=False)
    p = probabilities(individual, env, settings(), monkeypatch)
    np.testing.assert_allclose(p, [0.5] + [0.5 / 8] * 8, atol=1e-15)


def test_food_weights_are_independent_of_site_memory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    individual = agent(20, 20)
    individual.last_food_position = None
    env = Environment(100, 100, periodic_boundary=False)
    env.food = {(20, 20), (21, 20)}
    p = probabilities(individual, env, settings(), monkeypatch)

    expected = np.array([0.5] + [0.5 / 8] * 8)
    expected[0] += 1.0  # food at current cell
    expected[7] += 0.5  # food to the right
    expected /= 2.5
    np.testing.assert_allclose(p, expected, atol=1e-15)


def test_zero_memory_weight_and_invalid_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    individual = agent(20, 20)
    env = Environment(100, 100, periodic_boundary=True)
    p = probabilities(
        individual, env, settings(memory_weight=0.0), monkeypatch
    )
    np.testing.assert_allclose(p, [0.5] + [0.5 / 8] * 8, atol=1e-15)

    with pytest.raises(ValueError, match="site_memory_mode"):
        individual.move(
            100, 100, "moore", env, False,
            settings(mode="unrecognized"), periodic_boundary=True,
        )


@pytest.mark.parametrize("name", [
    "default.yaml", "patch16.yaml", "random_periodic.yaml",
])
def test_active_config_uses_new_model(name: str) -> None:
    with (ROOT / "configs" / name).open(encoding="utf-8") as stream:
        conf = yaml.safe_load(stream)
    behavior = conf["behavior"]
    assert behavior["current_cell_food_weight"] == 1.0
    assert behavior["nearby_food_weight"] == 0.5
    assert behavior["site_memory_weight"] == 0.2
    assert behavior["site_memory_mode"] == "euclidean_inverse_total"
    assert behavior["site_memory_steps"] == 20


@pytest.mark.parametrize("name", [
    "step4_random.yaml", "step4_patch9.yaml", "step4_patch25.yaml",
])
def test_archived_config_keeps_original_memory_model(name: str) -> None:
    with (ROOT / "configs" / name).open(encoding="utf-8") as stream:
        conf = yaml.safe_load(stream)
    behavior = conf["behavior"]
    assert behavior.get("site_memory_mode", "legacy_manhattan") == "legacy_manhattan"
    assert behavior["current_cell_food_weight"] == 8.0
    assert behavior["nearby_food_weight"] == 4.0
    assert behavior["site_memory_weight"] == 2.0


@pytest.mark.parametrize("name", [
    "default.yaml", "patch16.yaml", "random_periodic.yaml",
])
def test_new_model_reproducible_for_same_seed(name: str) -> None:
    with (ROOT / "configs" / name).open(encoding="utf-8") as stream:
        conf = yaml.safe_load(stream)
    conf["simulation"]["random_seed"] = 0

    def simulate():
        sim = Simulation(deepcopy(conf))
        for _ in range(20):
            sim.step()
        return sim

    first = simulate()
    second = simulate()

    pd.testing.assert_frame_equal(
        first.logger.to_dataframe(), second.logger.to_dataframe(),
        check_exact=True,
    )
    assert first.environment.food == second.environment.food
    assert len(first.organisms) == len(second.organisms)
    for a, b in zip(first.organisms, second.organisms):
        assert (a.organism_id, a.x, a.y, a.energy, a.age) == (
            b.organism_id, b.x, b.y, b.energy, b.age,
        )
        np.testing.assert_array_equal(a.genome, b.genome)
        assert a.last_food_position == b.last_food_position


@pytest.mark.parametrize("name", [
    "default.yaml", "patch16.yaml", "random_periodic.yaml",
])
def test_simulation_passes_new_memory_mode_to_move(
    name: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    with (ROOT / "configs" / name).open(encoding="utf-8") as stream:
        conf = yaml.safe_load(stream)
    sim = Simulation(conf)
    observed_modes = set()
    original_move = Organism.move

    def inspecting_move(self, *args, **kwargs):
        # Simulation.step passes (width, height, move_type, environment,
        # low_energy, behavior_settings) as positional arguments.
        observed_modes.add(args[5]["site_memory_mode"])
        return original_move(self, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Organism, "move", inspecting_move)
        sim.step()
    assert observed_modes == {"euclidean_inverse_total"}
