"""STEP4: ensure only food spatial environment differs, and paired founders match."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import numpy as np
import yaml
from src.simulation import Simulation

ROOT = Path(__file__).resolve().parents[1]
NAMES = ("step4_random", "step4_patch9", "step4_patch25")
SPATIAL_KEYS = ("mode", "patch_count", "patch_radius", "patch_centers")


def load_configs():
    configs = {}
    for name in NAMES:
        with (ROOT / "configs" / f"{name}.yaml").open(encoding="utf-8") as f:
            configs[name] = yaml.safe_load(f)
    return configs


def test_configs_only_differ_spatially():
    configs = load_configs()
    expected = {"step4_random":"random", "step4_patch9":"patch", "step4_patch25":"patch"}
    for name, conf in configs.items():
        assert conf["environment"]["mode"] == expected[name]
        assert conf["organism"]["initial_placement_mode"] == "uniform"
        assert conf["organism"]["paired_initialization"] is True
        assert conf["organism"]["initial_population"] == 100
        assert conf["environment"]["initial_food_count"] == 500
        assert conf["simulation"]["duration_years"] == 3
        assert conf["seasonal_food"]["enabled"] is True
    baseline = None
    for config in configs.values():
        canonical = deepcopy(config)
        for key in SPATIAL_KEYS:
            canonical["environment"].pop(key, None)
        if baseline is None:
            baseline = canonical
        else:
            assert canonical == baseline, "A nonspatial setting differs across STEP4 configs"


def test_patch_area_and_initial_food_seed42():
    configs = load_configs()
    for name, conf in configs.items():
        conf = deepcopy(conf)
        conf["simulation"]["random_seed"] = 42
        sim = Simulation(conf)
        assert len(sim.organisms) == 100
        assert len(sim.environment.food) == 500
        if name != "step4_random":
            cells = set(sim.environment._get_patch_cells())
            expected_area = 529 if name == "step4_patch9" else 525
            expected_count = 9 if name == "step4_patch9" else 25
            assert len(sim.environment.patch_centers) == expected_count
            assert len(cells) == expected_area
            assert sim.environment.food <= cells
        else:
            assert sim.environment.respawn_mode == "random"


def test_paired_initial_founders_across_modes():
    configs = load_configs()
    for seed in (0, 42):
        runs = {}
        for name, original in configs.items():
            conf = deepcopy(original)
            conf["simulation"]["random_seed"] = seed
            runs[name] = Simulation(conf)
        ref = runs["step4_random"].organisms
        for name in ("step4_patch9", "step4_patch25"):
            founders = runs[name].organisms
            assert len(founders) == len(ref) == 100
            for a, b in zip(ref, founders):
                assert a.organism_id == b.organism_id
                assert (a.x,a.y) == (b.x,b.y), f"Initial positions differ for seed={seed}, condition={name}"
                assert np.array_equal(a.genome,b.genome), f"Founder genome differs for seed={seed}, condition={name}"
                assert a.phenotype == b.phenotype
                assert a.lifespan == b.lifespan
                assert a.age == b.age
                assert a.energy == b.energy
