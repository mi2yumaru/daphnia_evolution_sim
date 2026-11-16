"""Tests for new patch4/patch16 geometry and legacy reproducibility."""
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest
import yaml

from src.environment import Environment
from src.simulation import Simulation

ROOT = Path(__file__).resolve().parents[1]
AXES = {
    "default.yaml": (25, 75),
    "patch16.yaml": (12, 37, 62, 87),
}
EXPECTED = {
    "default.yaml": (4, 7.0, 149, 596),
    "patch16.yaml": (16, 3.2, 37, 592),
}


def config_for(name: str) -> dict:
    with (ROOT / "configs" / name).open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


@pytest.mark.parametrize("name", ["default.yaml", "patch16.yaml"])
def test_exact_patch_area_centers_and_food_placement(name: str) -> None:
    cfg = config_for(name)
    env_cfg = cfg["environment"]
    n, radius, individual_area, total_area = EXPECTED[name]
    axis = AXES[name]
    expected_centers = {(x, y) for x in axis for y in axis}

    assert env_cfg["mode"] == "patch"
    assert env_cfg["patch_radius_mode"] == "exact"
    assert env_cfg["patch_count"] == n
    assert env_cfg["patch_radius"] == radius
    assert {tuple(c) for c in env_cfg["patch_centers"]} == expected_centers
    assert len(env_cfg["patch_centers"]) == n
    assert env_cfg["initial_food_count"] == 500

    sim = Simulation(deepcopy(cfg))
    environment = sim.environment
    mask = set(environment._get_patch_cells())
    assert len(mask) == total_area
    assert len(environment.food) == 500
    assert environment.food <= mask
    assert environment.get_food_flow_metrics()["patch_area"] == total_area

    patches = []
    for center in expected_centers:
        single = Environment(
            width=100,
            height=100,
            respawn_mode="patch",
            patch_count=1,
            patch_radius=radius,
            patch_radius_mode="exact",
            patch_centers_config=[center],
        )
        single._init_patch_regions()
        cells = set(single._get_patch_cells())
        assert len(cells) == individual_area
        assert all(0 <= x < 100 and 0 <= y < 100 for x, y in cells)
        patches.append(cells)
    assert sum(len(part) for part in patches) == len(set().union(*patches))


@pytest.mark.parametrize(("name", "spacing"), [("default.yaml", 50), ("patch16.yaml", 25)])
def test_centers_evenly_spaced_when_viewed_as_periodic(name: str, spacing: int) -> None:
    axis = AXES[name]
    # Cyclic gaps include the wrap-around from the last to first center.
    assert [((axis[(i + 1) % len(axis)] - axis[i]) % 100) for i in range(len(axis))] == [
        spacing
    ] * len(axis)


@pytest.mark.parametrize("seed", [0, 42])
def test_four_and_sixteen_patches_have_paired_initial_founders(seed: int) -> None:
    c4, c16 = config_for("default.yaml"), config_for("patch16.yaml")
    for config in (c4, c16):
        config["simulation"]["random_seed"] = seed
    sim4, sim16 = Simulation(c4), Simulation(c16)
    assert len(sim4.organisms) == len(sim16.organisms) == 100
    for a, b in zip(sim4.organisms, sim16.organisms):
        assert (a.x, a.y) == (b.x, b.y)
        assert np.array_equal(a.genome, b.genome)
        assert a.lifespan == b.lifespan
        assert a.phenotype == b.phenotype


@pytest.mark.parametrize(("name", "expected"), [
    ("step4_patch9.yaml", 529),
    ("step4_patch25.yaml", 525),
])
def test_archived_patch_geometries_still_match_old_areas(name: str, expected: int) -> None:
    cfg = config_for(name)
    assert "patch_radius_mode" not in cfg["environment"]
    sim = Simulation(cfg)
    assert sim.environment.patch_radius_mode == "legacy"
    assert len(set(sim.environment._get_patch_cells())) == expected


@pytest.mark.parametrize("name", ["default.yaml", "patch16.yaml", "step4_patch9.yaml"])
def test_founder_analysis_uses_identical_patch_mask(name: str) -> None:
    from analyze_step2_founder_placement import build_patch_cells

    cfg = config_for(name)
    sim = Simulation(cfg)
    assert build_patch_cells(cfg["environment"]) == set(sim.environment._get_patch_cells())


def test_invalid_radius_mode_is_rejected() -> None:
    with pytest.raises(ValueError, match="patch_radius_mode"):
        Environment(width=100, height=100, patch_radius_mode="bad")
