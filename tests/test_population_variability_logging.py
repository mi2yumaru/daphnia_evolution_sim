"""Regression checks for within-step variability logging."""
import math
from pathlib import Path

import numpy as np
import pytest
import yaml

from src.simulation import Simulation


def _simulation(initial_population=5):
    cfg_path = Path(__file__).resolve().parents[1] / "configs/default.yaml"
    with cfg_path.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    config["simulation"]["random_seed"] = 42
    config["organism"]["initial_population"] = initial_population
    config["organism"]["randomize_initial_age"] = False
    config["environment"]["mode"] = "random"
    return Simulation(config)


def test_within_population_std_matches_final_alive_individuals():
    sim = _simulation()
    for index, org in enumerate(sim.organisms):
        org.energy = 10 + index
        org.age = index * 2
        org.generation = index
        org.move = lambda *args, **kwargs: False

    sim.environment.food.clear()
    sim.step()
    record = sim.logger.logs[-1]
    for attr, mean_column, std_column in (
        ("energy", "average_energy", "std_energy"),
        ("age", "average_age", "std_age"),
        ("generation", "average_generation", "std_generation"),
    ):
        values = [getattr(org, attr) for org in sim.organisms]
        assert record[mean_column] == pytest.approx(np.mean(values))
        assert record[std_column] == pytest.approx(np.std(values, ddof=0))
    assert math.isnan(record["std_consumers_per_shared_food"])


def test_shared_food_std_uses_food_cells_not_individuals():
    sim = _simulation(initial_population=5)
    sim.environment.food = {(1, 1), (2, 2)}
    for index, org in enumerate(sim.organisms):
        org.x, org.y = (1, 1) if index < 2 else (2, 2)
        org.move = lambda *args, **kwargs: False

    sim.step()
    row = sim.logger.logs[-1]
    assert row["shared_food_cell_count"] == 2
    assert row["shared_food_consumer_count"] == 5
    assert row["mean_consumers_per_shared_food"] == pytest.approx(2.5)
    assert row["std_consumers_per_shared_food"] == pytest.approx(0.5)
