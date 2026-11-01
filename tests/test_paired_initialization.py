"""STEP4: paired founder initial conditions under random, 9 and 25 patch food environments."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest
import yaml

from src.simulation import Simulation

ROOT = Path(__file__).resolve().parents[1]


def config_for(kind: str, seed: int) -> dict:
    with (ROOT / "configs" / "default.yaml").open(encoding="utf-8") as f:
        c = yaml.safe_load(f)
    c["simulation"]["random_seed"] = seed
    c["organism"]["paired_initialization"] = True
    c["organism"]["initial_placement_mode"] = "uniform"
    env = c["environment"]
    if kind == "random":
        env["mode"] = "random"
    elif kind == "patch9":
        env["mode"] = "patch"
        env["patch_count"] = 9
        env["patch_radius"] = 5
        axis = (1, 49, 98)
        env["patch_centers"] = [[x, y] for x in axis for y in axis]
    elif kind == "patch25":
        env["mode"] = "patch"
        env["patch_count"] = 25
        env["patch_radius"] = 2
        axis = (2, 26, 49, 73, 97)
        env["patch_centers"] = [[x, y] for x in axis for y in axis]
    else:
        raise ValueError(kind)
    return c


def founders(sim: Simulation):
    return sorted(sim.organisms, key=lambda o: o.organism_id)


@pytest.mark.parametrize("seed", [0, 42])
def test_founders_match_across_three_environments(seed: int) -> None:
    cases = {kind: Simulation(config_for(kind, seed)) for kind in ("random", "patch9", "patch25")}
    reference = founders(cases["random"])
    assert len(reference) == 100
    for kind, sim in cases.items():
        current = founders(sim)
        assert len(current) == 100
        for a, b in zip(reference, current):
            assert a.organism_id == b.organism_id
            assert a.founder_id == b.founder_id
            assert (a.x, a.y) == (b.x, b.y)
            assert np.array_equal(a.genome, b.genome)
            assert a.phenotype == b.phenotype
            assert a.lifespan == b.lifespan
            assert a.age == b.age
            assert a.energy == b.energy
        assert len(sim.environment.food) == 500
        if kind == "patch9":
            assert len(set(sim.environment._get_patch_cells())) == 529
        if kind == "patch25":
            assert len(set(sim.environment._get_patch_cells())) == 525


def test_repeated_initialization_is_reproducible() -> None:
    c = config_for("patch25", 42)
    a = founders(Simulation(deepcopy(c)))
    b = founders(Simulation(deepcopy(c)))
    assert all(
        x.x == y.x and x.y == y.y and np.array_equal(x.genome, y.genome)
        for x, y in zip(a, b)
    )


def test_different_seed_changes_founder_genomes_and_positions() -> None:
    a = founders(Simulation(config_for("patch25", 42)))
    b = founders(Simulation(config_for("patch25", 43)))
    assert any(not np.array_equal(x.genome, y.genome) for x, y in zip(a, b))
    assert any((x.x, x.y) != (y.x, y.y) for x, y in zip(a, b))


def test_original_genome_generator_remains_available() -> None:
    from src.organism import Organism
    np.random.seed(123)
    genome = Organism._generate_random_genome()
    assert len(genome) == len(Organism.TRAIT_LABELS) * Organism.LOCI_PER_TRAIT
    assert set(np.unique(genome)).issubset({0, 1})
