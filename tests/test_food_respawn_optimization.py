"""Regressions for the cached patch-food respawn implementation.

The reference below is the pre-optimization respawn_food implementation,
including list membership and re-building patch geometry each call.
Keep it independent from production respawn_food for RNG/behavior comparisons.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from src.environment import Environment
from src.simulation import Simulation


def reference_respawn_food(env: Environment, rate: float) -> int:
    """Original implementation for exact output and RNG-state comparisons."""
    before_count = len(env.food)
    if rate <= 0.0:
        return 0
    total = env.width * env.height
    to_add = int(total * rate)
    if to_add <= 0:
        return 0

    if env.respawn_mode == "patch":
        env._init_patch_regions()
        # The original version rebuilt list(set(cells)) at every respawn.
        env._patch_cells_cache = None
        patch_cells = env._get_patch_cells()
        if env._food_flow_patch_cells is None:
            env._food_flow_patch_cells = set(patch_cells)
        empty_patch = [p for p in patch_cells if p not in env.food]

        outside_frac = max(0.0, min(1.0, env.outside_respawn_fraction))
        patch_target = int(to_add * (1.0 - outside_frac))
        outside_target = to_add - patch_target

        added = 0
        if empty_patch and patch_target > 0:
            max_patch = max(1, int(len(empty_patch) * env.patch_density))
            add_patch = min(patch_target, max_patch, len(empty_patch))
            chosen = np.random.choice(len(empty_patch), size=add_patch, replace=False)
            for i in chosen:
                env.food.add(empty_patch[int(i)])
            added += add_patch
            env._food_flow_respawn_in += add_patch

        if outside_target > 0:
            empty_outside = [
                (x, y)
                for x in range(env.width)
                for y in range(env.height)
                if (x, y) not in env.food and (x, y) not in patch_cells
            ]
            if empty_outside:
                add_out = min(outside_target, len(empty_outside))
                chosen_out = np.random.choice(
                    len(empty_outside), size=add_out, replace=False
                )
                for i in chosen_out:
                    env.food.add(empty_outside[int(i)])
                added += add_out
                env._food_flow_respawn_out += add_out

        if added < to_add:
            env._add_random_food(to_add - added, track_food_flow=True)
        return len(env.food) - before_count

    env._add_random_food(to_add)
    return len(env.food) - before_count


def assert_rng_states_equal(a: tuple, b: tuple) -> None:
    assert a[0] == b[0]
    np.testing.assert_array_equal(a[1], b[1])
    assert a[2:] == b[2:]


def environment_for(
    patch_count: int,
    radius: float,
    centers: list[tuple[int, int]],
    *,
    periodic: bool,
    exact: bool,
    outside_fraction: float,
) -> Environment:
    return Environment(
        width=100,
        height=100,
        respawn_mode="patch",
        patch_count=patch_count,
        patch_radius=radius,
        patch_radius_mode="exact" if exact else "legacy",
        patch_centers_config=centers,
        periodic_boundary=periodic,
        outside_respawn_fraction=outside_fraction,
        patch_density=0.8,
    )


FOUR = [(x, y) for x in (25, 75) for y in (25, 75)]
SIXTEEN = [(x, y) for x in (12, 37, 62, 87) for y in (12, 37, 62, 87)]
ARCHIVED_NINE = [(x, y) for x in (1, 49, 98) for y in (1, 49, 98)]


@pytest.mark.parametrize(
    ("centers", "radius", "periodic", "exact", "outside_fraction", "initial"),
    [
        (FOUR, 7.0, True, True, 0.05, 500),
        (SIXTEEN, 3.2, True, True, 0.05, 500),
        (FOUR, 7.0, True, True, 0.0, 500),
        (FOUR, 7.0, True, True, 1.0, 500),
        (FOUR, 7.0, True, True, 0.05, 0),
        (ARCHIVED_NINE, 5.0, False, False, 0.05, 529),
    ],
)
def test_cached_respawn_matches_original_results_and_rng(
    centers: list[tuple[int, int]],
    radius: float,
    periodic: bool,
    exact: bool,
    outside_fraction: float,
    initial: int,
) -> None:
    kwargs = dict(
        patch_count=len(centers),
        radius=radius,
        centers=centers,
        periodic=periodic,
        exact=exact,
        outside_fraction=outside_fraction,
    )
    baseline = environment_for(**kwargs)
    optimized = environment_for(**kwargs)

    np.random.seed(42)
    baseline.init_food(initial)
    baseline_initial_rng = np.random.get_state()
    np.random.seed(42)
    optimized.init_food(initial)
    assert_rng_states_equal(baseline_initial_rng, np.random.get_state())
    assert baseline.food == optimized.food

    rng_state = baseline_initial_rng
    for rate in (0.02, 0.02, 0.01, 0.0, 0.03, 0.02, 0.02):
        baseline.reset_food_flow_counters()
        optimized.reset_food_flow_counters()

        np.random.set_state(rng_state)
        before_count = len(baseline.food)
        before_added = reference_respawn_food(baseline, rate)
        baseline_rng_state = np.random.get_state()

        np.random.set_state(rng_state)
        after_added = optimized.respawn_food(rate)
        optimized_rng_state = np.random.get_state()

        assert before_added == after_added
        assert before_added == len(baseline.food) - before_count
        assert baseline.food == optimized.food
        assert_rng_states_equal(baseline_rng_state, optimized_rng_state)
        np.testing.assert_equal(
            baseline.get_food_flow_metrics(),
            optimized.get_food_flow_metrics(),
        )

        # Mimic consumption, including the food-flow count. No randomness
        # is needed and both versions must start the next cycle identically.
        eaten = sorted(baseline.food)[::11]
        for x, y in eaten:
            baseline.remove_food(x, y)
            optimized.remove_food(x, y)
        assert baseline.food == optimized.food
        np.testing.assert_equal(
            baseline.get_food_flow_metrics(),
            optimized.get_food_flow_metrics(),
        )
        rng_state = baseline_rng_state


def test_cached_geometry_list_is_not_mutable_by_callers() -> None:
    env = environment_for(
        4, 7.0, FOUR, periodic=True, exact=True, outside_fraction=0.05
    )
    env.init_food(500)
    expected = env._get_patch_cells()
    exposed = env._get_patch_cells()
    exposed.clear()
    assert env._get_patch_cells() == expected
    assert len(expected) == 596


@pytest.mark.parametrize("config_name", ["default.yaml", "patch16.yaml"])
def test_short_simulation_matches_reference_respawn(
    config_name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = Path(__file__).resolve().parents[1]
    with (root / "configs" / config_name).open(encoding="utf-8") as fh:
        conf = yaml.safe_load(fh)
    conf["simulation"]["random_seed"] = 0
    conf["simulation"]["steps"] = 25

    with monkeypatch.context() as patch:
        patch.setattr(Environment, "respawn_food", reference_respawn_food)
        baseline = Simulation(deepcopy(conf))
        for _ in range(25):
            baseline.step()
        baseline_rng_state = np.random.get_state()

    optimized = Simulation(deepcopy(conf))
    for _ in range(25):
        optimized.step()
    optimized_rng_state = np.random.get_state()

    assert_rng_states_equal(baseline_rng_state, optimized_rng_state)
    assert baseline.environment.food == optimized.environment.food
    assert len(baseline.organisms) == len(optimized.organisms)
    assert [
        (o.organism_id, o.x, o.y, o.energy, o.age)
        for o in baseline.organisms
    ] == [
        (o.organism_id, o.x, o.y, o.energy, o.age)
        for o in optimized.organisms
    ]
    pd.testing.assert_frame_equal(
        baseline.logger.to_dataframe(),
        optimized.logger.to_dataframe(),
        check_exact=True,
    )
    pd.testing.assert_frame_equal(
        pd.DataFrame(baseline.lineage_records).T,
        pd.DataFrame(optimized.lineage_records).T,
        check_exact=True,
    )
