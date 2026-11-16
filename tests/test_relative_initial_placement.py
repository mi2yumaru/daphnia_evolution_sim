"""Relative founder placement thresholds based on periodic patch spacing."""
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest
import yaml

from src.initial_placement import (
    initial_placement_candidates,
    minimum_patch_center_distance,
    resolve_initial_placement_distances,
)
from src.simulation import Simulation

ROOT = Path(__file__).resolve().parents[1]


def load(name: str) -> dict:
    with (ROOT / "configs" / name).open(encoding="utf-8") as stream:
        return yaml.safe_load(stream)


@pytest.mark.parametrize(
    ("name", "spacing", "near", "far", "near_count", "far_count"),
    [
        ("default.yaml", 50.0, 10.0, 20.0, 2928, 1428),
        ("patch16.yaml", 25.0, 5.0, 10.0, 2816, 1600),
    ],
)
def test_relative_distances_and_region_sizes(
    name: str,
    spacing: float,
    near: float,
    far: float,
    near_count: int,
    far_count: int,
) -> None:
    cfg = load(name)
    assert cfg["organism"]["initial_placement_distance_mode"] == "relative"
    sim = Simulation(cfg)
    env = sim.environment
    assert env.periodic_boundary
    assert minimum_patch_center_distance(
        env.patch_centers, env.width, env.height, True
    ) == pytest.approx(spacing)
    calculated_near, calculated_far = resolve_initial_placement_distances(
        cfg["organism"], env.patch_centers,
        env.width, env.height, env.periodic_boundary,
    )
    assert (calculated_near, calculated_far) == pytest.approx((near, far))
    patches = set(env._get_patch_cells())
    near_cells = set(initial_placement_candidates(
        env.width, env.height, patches, "near", near, far,
        periodic_boundary=True,
    ))
    far_cells = set(initial_placement_candidates(
        env.width, env.height, patches, "far", near, far,
        periodic_boundary=True,
    ))
    assert len(near_cells) == near_count
    assert len(far_cells) == far_count
    assert not (near_cells & patches)
    assert not (far_cells & patches)
    assert not (near_cells & far_cells)


@pytest.mark.parametrize(
    ("name", "expected_near", "expected_far"),
    [("default.yaml", 10.0, 20.0), ("patch16.yaml", 5.0, 10.0)],
)
@pytest.mark.parametrize("placement", ["inside", "near", "far"])
def test_founders_are_sampled_from_correct_periodic_regions(
    name: str, expected_near: float, expected_far: float, placement: str
) -> None:
    cfg = load(name)
    cfg["organism"]["initial_placement_mode"] = placement
    cfg["organism"]["initial_population"] = 30
    sim = Simulation(cfg)
    patches = set(sim.environment._get_patch_cells())
    possible = set(initial_placement_candidates(
        100, 100, patches, placement, expected_near, expected_far,
        periodic_boundary=True,
    ))
    assert possible
    assert len(sim.organisms) == 30
    assert all((o.x, o.y) in possible for o in sim.organisms)


def test_relative_placement_is_invariant_under_periodic_shift() -> None:
    axis = (25, 75)
    centers = [(x, y) for x in axis for y in axis]
    shifted = [((x + 49) % 100, (y + 17) % 100) for x, y in centers]
    assert minimum_patch_center_distance(
        centers, 100, 100, True
    ) == minimum_patch_center_distance(
        shifted, 100, 100, True
    ) == 50.0


def test_fixed_mode_preserves_existing_distances() -> None:
    org = {
        "initial_placement_distance_mode": "fixed",
        "initial_placement_near_max_distance": 3.0,
        "initial_placement_far_min_distance": 15.0,
    }
    assert resolve_initial_placement_distances(
        org, [], 100, 100, False
    ) == (3.0, 15.0)
    assert resolve_initial_placement_distances(
        {}, [], 100, 100, False
    ) == (3.0, 15.0)


def test_invalid_config_and_layout_are_rejected() -> None:
    centers = [(25, 25), (75, 75)]
    base = {"initial_placement_distance_mode": "relative"}
    cases = [
        {"initial_placement_near_fraction": 0},
        {"initial_placement_near_fraction": 0.4},
        {"initial_placement_far_fraction": float("inf")},
        {"initial_placement_far_fraction": float("nan")},
    ]
    for changes in cases:
        with pytest.raises(ValueError, match="fractions"):
            resolve_initial_placement_distances(
                {**base, **changes}, centers, 100, 100, True
            )
    with pytest.raises(ValueError, match="distance_mode"):
        resolve_initial_placement_distances(
            {"initial_placement_distance_mode": "wrong"},
            centers, 100, 100, True,
        )
    with pytest.raises(ValueError, match="at least two"):
        minimum_patch_center_distance([(25, 25)], 100, 100, True)
    with pytest.raises(ValueError, match="distinct"):
        minimum_patch_center_distance(
            [(25, 25), (25, 25)], 100, 100, True,
        )


def test_uniform_founders_unaffected_by_relative_distance_settings() -> None:
    cfg = load("default.yaml")
    fixed = deepcopy(cfg)
    fixed["organism"]["initial_placement_distance_mode"] = "fixed"
    a = Simulation(cfg).organisms
    b = Simulation(fixed).organisms
    assert [(o.x, o.y) for o in a] == [(o.x, o.y) for o in b]
    assert all(np.array_equal(left.genome, right.genome) for left, right in zip(a, b))
    assert [o.lifespan for o in a] == [o.lifespan for o in b]
