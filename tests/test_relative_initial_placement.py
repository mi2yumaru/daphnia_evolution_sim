"""Test scale-relative founder near/far thresholds on periodic patch grids."""
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest
import yaml

from src.initial_placement import (
    initial_placement_candidates,
    nearest_patch_center_spacing,
    resolve_initial_placement_distances,
)
from src.simulation import Simulation
from src.spatial import squared_euclidean_distance

ROOT = Path(__file__).resolve().parents[1]


def load_config(name: str) -> dict:
    with (ROOT / "configs" / name).open(encoding="utf-8") as stream:
        return yaml.safe_load(stream)


@pytest.mark.parametrize(
    ("name", "spacing", "near_expected", "far_expected"),
    [
        ("default.yaml", 50.0, 10.0, 20.0),
        ("patch16.yaml", 25.0, 5.0, 10.0),
    ],
)
def test_patch_center_spacing_and_relative_thresholds(
    name: str, spacing: float, near_expected: float, far_expected: float
) -> None:
    cfg = load_config(name)
    env, org = cfg["environment"], cfg["organism"]
    assert env["periodic_boundary"] is True
    assert org["initial_placement_distance_mode"] == "relative"
    assert org["initial_placement_near_fraction"] == pytest.approx(0.2)
    assert org["initial_placement_far_fraction"] == pytest.approx(0.4)
    centers = [tuple(p) for p in env["patch_centers"]]

    L = nearest_patch_center_spacing(
        env["width"], env["height"], centers, periodic_boundary=True,
    )
    assert L == spacing
    near, far = resolve_initial_placement_distances(
        env["width"], env["height"], centers,
        periodic_boundary=True, distance_mode=org["initial_placement_distance_mode"],
        near_max_distance=1e6, far_min_distance=2e6,  # relative ignores absolute overrides
        near_fraction=org["initial_placement_near_fraction"],
        far_fraction=org["initial_placement_far_fraction"],
    )
    assert (near, far) == (near_expected, far_expected)


def test_toroidal_center_spacing_wraps_across_boundary() -> None:
    centers = [(2, 30), (98, 30), (50, 30)]
    assert nearest_patch_center_spacing(100, 100, centers, True) == 4.0
    assert nearest_patch_center_spacing(100, 100, centers, False) == 48.0


@pytest.mark.parametrize(
    ("name", "near_count", "far_count"),
    [("default.yaml", 2928, 1428), ("patch16.yaml", 2816, 1600)],
)
def test_near_far_regions_nonempty_disjoint_and_scaled(
    name: str, near_count: int, far_count: int
) -> None:
    cfg = load_config(name)
    sim = Simulation(deepcopy(cfg))
    env = sim.environment
    org = cfg["organism"]
    near, far = resolve_initial_placement_distances(
        env.width, env.height, env.patch_centers,
        periodic_boundary=sim.periodic_boundary,
        distance_mode=org["initial_placement_distance_mode"],
        near_fraction=org["initial_placement_near_fraction"],
        far_fraction=org["initial_placement_far_fraction"],
    )
    patch_cells = set(env._get_patch_cells())
    near_candidates = set(initial_placement_candidates(
        env.width, env.height, patch_cells, "near", near, far, True
    ))
    far_candidates = set(initial_placement_candidates(
        env.width, env.height, patch_cells, "far", near, far, True
    ))
    assert len(near_candidates) == near_count
    assert len(far_candidates) == far_count
    assert not (near_candidates & far_candidates)
    assert not (patch_cells & near_candidates)
    assert not (patch_cells & far_candidates)


@pytest.mark.parametrize("name", ["default.yaml", "patch16.yaml"])
@pytest.mark.parametrize("mode", ["near", "far"])
def test_simulation_founders_are_in_expected_relative_region(
    name: str, mode: str
) -> None:
    cfg = load_config(name)
    cfg["organism"]["initial_placement_mode"] = mode
    cfg["organism"]["initial_population"] = 25
    cfg["simulation"]["random_seed"] = 42
    sim = Simulation(cfg)
    env = sim.environment
    patch_cells = list(env._get_patch_cells())
    org = cfg["organism"]
    near, far = resolve_initial_placement_distances(
        env.width, env.height, env.patch_centers,
        periodic_boundary=True, distance_mode=org["initial_placement_distance_mode"],
        near_fraction=org["initial_placement_near_fraction"],
        far_fraction=org["initial_placement_far_fraction"],
    )

    assert len(sim.organisms) == 25
    for agent in sim.organisms:
        assert (agent.x, agent.y) not in patch_cells
        distance2 = min(
            squared_euclidean_distance(
                (agent.x, agent.y), cell, env.width, env.height, True
            )
            for cell in patch_cells
        )
        if mode == "near":
            assert 0 < distance2 <= near * near
        else:
            assert distance2 >= far * far


def test_legacy_configs_keep_absolute_thresholds() -> None:
    cfg = load_config("step4_patch9.yaml")
    env, org = cfg["environment"], cfg["organism"]
    assert "initial_placement_distance_mode" not in org
    near, far = resolve_initial_placement_distances(
        env["width"], env["height"],
        [tuple(p) for p in env["patch_centers"]],
        periodic_boundary=env.get("periodic_boundary", False),
        distance_mode=org.get("initial_placement_distance_mode", "absolute"),
        near_max_distance=org["initial_placement_near_max_distance"],
        far_min_distance=org["initial_placement_far_min_distance"],
    )
    assert (near, far) == (3.0, 15.0)


def test_absolute_mode_can_override_new_relative_settings() -> None:
    cfg = load_config("patch16.yaml")
    cfg["organism"].update(
        initial_placement_mode="far",
        initial_placement_distance_mode="absolute",
        initial_placement_far_min_distance=10.0,
    )
    cfg["organism"]["initial_population"] = 10
    sim = Simulation(cfg)
    assert len(sim.organisms) == 10
    patches = set(sim.environment._get_patch_cells())
    assert all(
        min(
            squared_euclidean_distance(
                (a.x, a.y), p, 100, 100, True
            )
            for p in patches
        ) >= 100
        for a in sim.organisms
    )


def test_inside_and_uniform_are_not_restricted_by_relative_spacing() -> None:
    # A single patch has no center-to-center distance; inside/uniform still work.
    for mode in ("uniform", "inside"):
        cfg = load_config("default.yaml")
        cfg["environment"].update(
            patch_count=1,
            patch_centers=[[25, 25]],
            initial_food_count=10,
        )
        cfg["organism"].update(initial_placement_mode=mode, initial_population=5)
        sim = Simulation(cfg)
        assert len(sim.organisms) == 5
        if mode == "inside":
            patches = set(sim.environment._get_patch_cells())
            assert all((a.x, a.y) in patches for a in sim.organisms)


@pytest.mark.parametrize(
    ("centers", "error"),
    [
        ([(25, 25)], "at least two"),
        ([(25, 25), (25, 25)], "distinct"),
        ([(25, 25), (100, 25)], "outside"),
    ],
)
def test_invalid_relative_center_config_is_rejected(
    centers: list[tuple[int, int]], error: str
) -> None:
    with pytest.raises(ValueError, match=error):
        nearest_patch_center_spacing(100, 100, centers, True)


@pytest.mark.parametrize(
    ("mode", "near_ratio", "far_ratio"),
    [("invalid", 0.2, 0.4), ("relative", 0.0, 0.4), ("relative", 0.5, 0.4)],
)
def test_invalid_distance_configuration_is_rejected(
    mode: str, near_ratio: float, far_ratio: float
) -> None:
    with pytest.raises(ValueError):
        resolve_initial_placement_distances(
            100, 100, [(25, 25), (75, 75)],
            periodic_boundary=True, distance_mode=mode,
            near_fraction=near_ratio, far_fraction=far_ratio,
        )
