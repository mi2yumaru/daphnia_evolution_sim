"""STEP3 initial founder placement tests."""
from copy import deepcopy
from pathlib import Path

import yaml

from src.initial_placement import initial_placement_candidates
from src.simulation import Simulation


def test_zone_selection():
    patches = {(5, 5)}
    inside = initial_placement_candidates(11, 11, patches, "inside")
    near = initial_placement_candidates(11, 11, patches, "near", 2.0, 4.0)
    far = initial_placement_candidates(11, 11, patches, "far", 2.0, 4.0)
    assert inside == [(5, 5)]
    assert (5, 6) in near and (5, 7) in near
    assert (5, 8) not in near
    assert (5, 9) in far
    assert (5, 5) not in near and (5, 5) not in far
    assert not (set(inside) & set(near))
    assert not (set(near) & set(far))


def test_founders_position_only_changes_with_same_seed():
    config_path = Path(__file__).resolve().parents[1] / "configs" / "default.yaml"
    with config_path.open(encoding="utf-8") as f:
        base = yaml.safe_load(f)
    base["simulation"]["random_seed"] = 42
    base["organism"]["initial_population"] = 15
    base["environment"]["mode"] = "patch"
    base["organism"]["randomize_initial_age"] = False

    sims = {}
    for mode in ("uniform", "inside", "near", "far"):
        config = deepcopy(base)
        config["organism"]["initial_placement_mode"] = mode
        sims[mode] = Simulation(config)

    ref = sims["uniform"]
    ref_founders = list(ref.organisms)
    for mode in ("inside", "near", "far"):
        sim = sims[mode]
        patch_cells = set(sim.environment._get_patch_cells())
        eligible = set(initial_placement_candidates(
            sim.environment.width, sim.environment.height, patch_cells, mode,
            base["organism"]["initial_placement_near_max_distance"],
            base["organism"]["initial_placement_far_min_distance"],
        ))
        assert all((o.x, o.y) in eligible for o in sim.organisms)
        assert [o.lifespan for o in sim.organisms] == [o.lifespan for o in ref_founders]
        assert [o.phenotype for o in sim.organisms] == [o.phenotype for o in ref_founders]
