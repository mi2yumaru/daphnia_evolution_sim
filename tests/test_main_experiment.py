"""Checks for initial exchange traits and the 20-condition main design."""
from copy import deepcopy
from pathlib import Path

import yaml

from src.simulation import Simulation
from src.run_main_experiment import EXCHANGE, conditions, build_config

ROOT = Path(__file__).resolve().parents[1]


def baseline():
    with (ROOT / "configs/default.yaml").open(encoding="utf-8") as fp:
        return yaml.safe_load(fp)


def test_20_unique_conditions():
    cases = conditions()
    assert len(cases) == len(set(cases)) == 20
    assert len(EXCHANGE) == 5
    for spatial, season, exchange in cases:
        cfg = build_config(baseline(), spatial, season, exchange, seed=0)
        assert cfg["simulation"]["duration_years"] == 5
        assert cfg["organism"]["paired_initialization"]
        assert cfg["analysis"]["offspring_outcomes"]["enabled"]
        assert cfg["analysis"]["gene_flow"]["enabled"]
        assert cfg["seasonal_food"]["enabled"] == season
        if exchange == "evolvable_zero":
            assert cfg["gene_exchange"]["initial_trait_mode"] == "zero"


def test_initial_zero_only_affects_exchange_genes():
    base = baseline()
    base["simulation"]["random_seed"] = 42
    zero = deepcopy(base)
    zero["gene_exchange"]["initial_trait_mode"] = "zero"
    random = deepcopy(base)
    random["gene_exchange"]["initial_trait_mode"] = "random"
    a, b = Simulation(zero), Simulation(random)
    for founder_a, founder_b in zip(a.organisms, b.organisms):
        assert (founder_a.genome[:80] == founder_b.genome[:80]).all()
        assert (founder_a.genome[80:] == 0).all()
        assert (founder_a.x, founder_a.y, founder_a.lifespan) == (
            founder_b.x, founder_b.y, founder_b.lifespan
        )


def test_patch16_is_five_years():
    with (ROOT / "configs/patch16.yaml").open(encoding="utf-8") as fp:
        cfg = yaml.safe_load(fp)
    assert cfg["simulation"]["duration_mode"] == "years"
    assert cfg["simulation"]["duration_years"] == 5
