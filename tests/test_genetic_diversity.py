"""STEP2 の最小単体テスト。python -m pytest tests/test_genetic_diversity.py -q"""

from types import SimpleNamespace

import numpy as np
import pytest

from src.genetic_diversity import METRIC_NAMES, calculate_genetic_diversity


class FakeOrganism(SimpleNamespace):
    TRAIT_LABELS = [
        "exploration_tendency", "site_fidelity", "risk_tolerance",
        "reproduction_timing", "gene_exchange_probability", "gene_exchange_fraction",
    ]
    LOCI_PER_TRAIT = 20


def population(*genomes):
    return [FakeOrganism(genome=np.asarray(g, dtype=np.int64)) for g in genomes]


def test_empty_population_is_nan():
    res = calculate_genetic_diversity([])
    assert set(res) == set(METRIC_NAMES)
    assert all(np.isnan(v) for v in res.values())


def test_identical_genomes():
    z = np.zeros(120, dtype=int)
    res = calculate_genetic_diversity(population(z, z))
    assert res["genetic_diversity_all"] == 0
    assert res["genetic_diversity_behavior"] == 0
    assert res["genetic_diversity_exchange"] == 0
    assert res["genotype_diversity"] == 0
    assert res["unique_genotype_ratio"] == 0.5


def test_opposite_genomes():
    res = calculate_genetic_diversity(population(np.zeros(120), np.ones(120)))
    assert res["genetic_diversity_all"] == pytest.approx(0.5)
    assert res["genetic_diversity_behavior"] == pytest.approx(0.5)
    assert res["genetic_diversity_exchange"] == pytest.approx(0.5)
    assert res["genotype_diversity"] == pytest.approx(0.5)
    assert res["unique_genotype_ratio"] == 1


def test_behavior_and_exchange_split():
    a = np.zeros(120, dtype=int)
    b = np.zeros(120, dtype=int)
    b[:80] = 1
    res = calculate_genetic_diversity(population(a, b))
    assert res["genetic_diversity_all"] == pytest.approx(1 / 3)
    assert res["genetic_diversity_behavior"] == pytest.approx(0.5)
    assert res["genetic_diversity_exchange"] == pytest.approx(0)


def test_single_individual():
    res = calculate_genetic_diversity(population(np.ones(120)))
    assert all(v == 0 for k, v in res.items() if k != "unique_genotype_ratio")
    assert res["unique_genotype_ratio"] == 1


def test_bad_genome_rejected():
    with pytest.raises(ValueError):
        calculate_genetic_diversity(population(np.ones(119)))
