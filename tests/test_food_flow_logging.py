"""Lightweight tests for FOOD_FLOW_LOGGING_V1. Run after installer."""
from copy import deepcopy
from pathlib import Path
import pandas as pd
import yaml

from src.environment import Environment
from src.simulation import Simulation
from src.last_year_summary import calculate_last_year_metrics


def _config():
    with (Path(__file__).resolve().parents[1] / "configs/default.yaml").open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg["simulation"]["random_seed"] = 42
    return cfg


def test_patch_counts_and_conservation():
    config = _config()
    config["environment"]["mode"] = "patch"
    sim = Simulation(config)
    cells = set(sim.environment._get_patch_cells())
    assert len(cells) == sim.environment.get_food_flow_metrics()["patch_area"]
    old_in = sum(p in cells for p in sim.environment.food)
    old_out = len(sim.environment.food) - old_in
    for _ in range(25):
        sim.step()
        row = sim.logger.logs[-1]
        assert row["food_in"] + row["food_out"] == row["food_count"]
        assert row["food_respawn_in"] + row["food_respawn_out"] == row["food_respawn_count"]
        assert row["food_consumed_in"] + row["food_consumed_out"] == row["food_consumed_count"]
        assert old_in + row["food_respawn_in"] - row["food_consumed_in"] == row["food_in"]
        assert old_out + row["food_respawn_out"] - row["food_consumed_out"] == row["food_out"]
        assert abs(row["density_pre_in"] - (row["food_in"] + row["food_consumed_in"]) / row["patch_area"]) < 1e-12
        old_in, old_out = row["food_in"], row["food_out"]


def test_full_patch_fallback_is_counted_as_outside():
    env = Environment(width=100, height=100, respawn_mode="patch", patch_count=9,
                      patch_radius=5, patch_layout="spread",
                      patch_centers_config=[(1,1), (98,98), (1,98), (98,1),
                                            (49,49), (49,98), (98,49), (1,49), (49,1)])
    cells = set()
    env.init_food(529)
    cells = set(env._get_patch_cells())
    assert len(cells) == 529
    env.reset_food_flow_counters()
    count = env.respawn_food(0.02)
    row = env.get_food_flow_metrics()
    assert count == 200
    assert row["food_respawn_in"] == 0
    assert row["food_respawn_out"] == 200


def test_random_mode_is_not_falsely_treated_as_patch():
    config = _config()
    config["environment"]["mode"] = "random"
    sim = Simulation(config)
    sim.step()
    row = sim.logger.logs[-1]
    assert row["food_in"] is None
    assert row["density_ratio"] is None
    assert row["food_respawn_count"] >= 0


def test_last_year_aggregate_counts_and_fractions():
    df = pd.DataFrame({
        "step": [0, 1, 2, 3], "simulation_year": [1, 1, 1, 1],
        "food_respawn_count": [3, 5, 4, 4],
        "food_consumed_count": [2, 4, 3, 3],
        "food_respawn_in": [2, 4, 3, 3], "food_respawn_out": [1, 1, 1, 1],
        "food_consumed_in": [1, 3, 2, 2], "food_consumed_out": [1, 1, 1, 1],
        "density_in": [.2, .3, .4, .5], "density_out": [.1, .1, .1, .1],
    })
    row = calculate_last_year_metrics(df, steps_per_year=4)
    assert row["last_year_complete"]
    assert row["total_food_respawn_in_last_year"] == 12
    assert row["total_food_consumed_out_last_year"] == 4
    assert row["food_respawn_in_fraction_last_year"] == 12 / 16
    assert row["food_consumed_in_fraction_last_year"] == 8 / 12
    assert abs(row["mean_density_in_last_year"] - .35) < 1e-12
