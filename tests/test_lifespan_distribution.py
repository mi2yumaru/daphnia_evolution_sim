"""Regression tests for configurable lifespan sampling."""
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest
import yaml

from src.simulation import Simulation


CONFIG = Path(__file__).resolve().parents[1] / "configs" / "default.yaml"


def make_config(seed: int = 42, population: int = 5) -> dict:
    with CONFIG.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    config["simulation"]["random_seed"] = seed
    config["organism"]["initial_population"] = population
    config["organism"]["randomize_initial_age"] = False
    config["environment"]["mode"] = "random"
    config["seasonal_food"]["enabled"] = False
    return config


def test_truncated_normal_distribution_bounds_and_shape() -> None:
    sim = Simulation(make_config())
    assert sim.lifespan_distribution == "truncated_normal"

    values = np.asarray([sim._sample_lifespan() for _ in range(20000)])
    assert np.issubdtype(values.dtype, np.integer)
    assert np.all((values >= 200) & (values <= 400))
    assert abs(float(values.mean()) - 300) < 2
    # Because the normal is truncated at mean +/- 2 sigma,
    # the actual standard deviation is below the configured 50.
    assert 40 < float(values.std(ddof=0)) < 48
    assert len(set(values.tolist())) > 100


def test_truncated_normal_is_reproducible_by_seed() -> None:
    config = make_config(seed=17)
    a, b = Simulation(deepcopy(config)), Simulation(deepcopy(config))
    assert [o.lifespan for o in a.organisms] == [
        o.lifespan for o in b.organisms
    ]
    assert [a._sample_lifespan() for _ in range(100)] == [
        b._sample_lifespan() for _ in range(100)
    ]


def test_legacy_uniform_without_distribution_key_keeps_rng_sequence() -> None:
    config = make_config(seed=42, population=5)
    config["organism"].pop("lifespan_distribution")
    config["organism"]["lifespan_min"] = 150
    config["organism"]["lifespan_max"] = 250
    sim = Simulation(config)

    rng = np.random.default_rng(np.random.SeedSequence([42, 2]))
    expected = rng.integers(150, 251, size=5).tolist()
    assert sim.lifespan_distribution == "uniform"
    assert [o.lifespan for o in sim.organisms] == expected
    assert 150 <= sim._sample_lifespan() <= 250


def test_fixed_lifespan_remains_available() -> None:
    config = make_config()
    config["organism"]["randomize_lifespan"] = False
    config["organism"]["max_age"] = 225
    sim = Simulation(config)
    assert [o.lifespan for o in sim.organisms] == [225] * 5
    assert sim._sample_lifespan() == 225


@pytest.mark.parametrize(
    ("setting", "value", "message"),
    [
        ("lifespan_distribution", "unknown", "lifespan_distribution"),
        ("lifespan_mean", 401, "lifespan_mean"),
        ("lifespan_std", 0, "lifespan_std"),
        ("lifespan_std", float("nan"), "lifespan_std"),
        ("lifespan_min", 400, "lifespan_min < lifespan_max"),
    ],
)
def test_invalid_truncated_normal_settings_raise(
    setting: str, value: object, message: str
) -> None:
    config = make_config()
    config["organism"][setting] = value
    with pytest.raises(ValueError, match=message):
        Simulation(config)


def test_founders_and_newborns_receive_lifespans_and_age_death_uses_them() -> None:
    sim = Simulation(make_config(population=1))
    parent = sim.organisms[0]
    assert 200 <= parent.lifespan <= 400
    parent.energy = 100.0
    parent.move = lambda *args, **kwargs: False
    sim.environment.food.clear()

    sim.step()

    children = [o for o in sim.organisms if o.parent_id == parent.organism_id]
    assert len(children) == 1
    child = children[0]
    assert 200 <= child.lifespan <= 400
    assert child.age == 0
    assert sim.lineage_records[child.organism_id]["lifespan"] == child.lifespan

    child.energy = 10.0
    child.age = child.lifespan - 1
    assert child.death_cause(200) is None
    child.age_one_step()
    assert child.death_cause(200) == "age"
