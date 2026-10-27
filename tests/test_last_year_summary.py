"""STEP4 short synthetic tests; no 3-year simulation needed."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.last_year_summary import (
    calculate_last_year_metrics, across_seed_summary, backfill_experiment,
)


def fake_log(steps_per_year=4):
    # Two entire years; year 1 values deliberately very different.
    n = 2 * steps_per_year
    df = pd.DataFrame({
        "step": range(n),
        "simulation_year": [1] * steps_per_year + [2] * steps_per_year,
        "population_size": [100] * steps_per_year + [10, 20, 30, 40][:steps_per_year],
        "food_count": [999] * steps_per_year + [20] * steps_per_year,
        "food_respawn_rate": [0.1] * steps_per_year + [0.01, 0.03, 0.01, 0.03][:steps_per_year],
        "birth_count": [10] * steps_per_year + [1, 9, 0, 0][:steps_per_year],
        "gene_exchange_eligible_count": [0] * steps_per_year + [1, 9, 0, 0][:steps_per_year],
        "gene_exchange_event_count": [0] * steps_per_year + [1, 1, 0, 0][:steps_per_year],
        "gene_exchange_effective_count": [0] * steps_per_year + [1, 0, 0, 0][:steps_per_year],
        "gene_exchange_selected_loci_count": [0] * steps_per_year + [2, 2, 0, 0][:steps_per_year],
        "gene_exchange_changed_bit_count": [0] * steps_per_year + [1, 0, 0, 0][:steps_per_year],
        "genetic_diversity_all": [0.5] * steps_per_year + [0.2] * steps_per_year,
        "active_lineage_count": [90] * steps_per_year + [5, 4, 3, 2][:steps_per_year],
    })
    return df


def test_means_exclude_first_year_and_100step_bias():
    s = calculate_last_year_metrics(fake_log(), steps_per_year=4)
    assert s["last_year_complete"] is True
    assert s["last_year_start_step"] == 4
    assert s["last_year_end_step"] == 7
    assert s["last_year_steps_observed"] == 4
    assert s["mean_population_last_year"] == 25
    assert s["mean_food_respawn_rate_last_year"] == pytest.approx(0.02)
    assert s["mean_genetic_diversity_all_last_year"] == pytest.approx(0.2)
    assert s["total_birth_count_last_year"] == 10


def test_rates_are_ratio_of_sums_not_unweighted_mean_of_step_rates():
    s = calculate_last_year_metrics(fake_log(), steps_per_year=4)
    assert s["gene_exchange_event_per_birth_last_year"] == pytest.approx(2 / 10)
    assert s["gene_exchange_effective_per_event_last_year"] == pytest.approx(1 / 2)
    assert s["gene_exchange_effective_per_birth_last_year"] == pytest.approx(1 / 10)
    assert s["gene_exchange_changed_per_selected_locus_last_year"] == pytest.approx(1 / 4)


def test_partial_calendar_year_cannot_be_mislabelled_as_full_year():
    df = fake_log().iloc[:-1]
    s = calculate_last_year_metrics(df, steps_per_year=4)
    assert s["last_year_complete"] is False
    assert s["last_year_steps_observed"] == 3
    assert np.isnan(s["mean_population_last_year"])
    assert np.isnan(s["gene_exchange_event_per_birth_last_year"])


def test_zero_denominators_are_nan():
    df = fake_log()
    cols = ["birth_count", "gene_exchange_eligible_count", "gene_exchange_event_count", "gene_exchange_effective_count", "gene_exchange_selected_loci_count", "gene_exchange_changed_bit_count"]
    df.loc[4:, cols] = 0
    s = calculate_last_year_metrics(df, 4)
    assert np.isnan(s["gene_exchange_event_per_birth_last_year"])
    assert np.isnan(s["gene_exchange_effective_per_event_last_year"])
    assert np.isnan(s["gene_exchange_changed_per_selected_locus_last_year"])
    assert s["total_birth_count_last_year"] == 0


def test_missing_or_duplicate_step_prevents_bad_stats():
    d = fake_log()
    d.loc[7, "step"] = 6
    with pytest.raises(ValueError, match="unique"):
        calculate_last_year_metrics(d, 4)


def test_across_seeds_uses_seed_level_sample_std_and_counts_missing():
    summary = pd.DataFrame({
        "seed": [0, 1, 2],
        "mean_population_last_year": [10., 20., 30.],
        "gene_exchange_event_per_birth_last_year": [0.1, np.nan, 0.5],
    })
    out = across_seed_summary(summary).set_index("metric")
    assert out.at["mean_population_last_year", "n_valid_seeds"] == 3
    assert out.at["mean_population_last_year", "mean"] == pytest.approx(20)
    assert out.at["mean_population_last_year", "std"] == pytest.approx(10)
    assert out.at["gene_exchange_event_per_birth_last_year", "n_valid_seeds"] == 2
    assert out.at["gene_exchange_event_per_birth_last_year", "mean"] == pytest.approx(0.3)


def test_backfill_is_idempotent_and_preserves_prior_summary(tmp_path):
    exp = tmp_path / "exp"
    for seed in (0, 1):
        seed_dir = exp / f"seed_{seed}"
        seed_dir.mkdir(parents=True)
        fake_log().to_csv(seed_dir / "log.csv", index=False)
    original = pd.DataFrame({"seed": [0, 1], "final_population": [40, 40], "other_col": ["a", "b"]})
    original.to_csv(exp / "summary.csv", index=False)
    before = (exp / "summary.csv").read_bytes()
    output1, output2 = backfill_experiment(exp, 4)
    got = pd.read_csv(output1)
    assert output2.exists()
    assert got["mean_population_last_year"].tolist() == [25, 25]
    assert got["other_col"].tolist() == ["a", "b"]
    assert (exp / "summary_before_last_year.csv").read_bytes() == before
    backfill_experiment(exp, 4)
    again = pd.read_csv(output1)
    assert "mean_population_last_year_x" not in again.columns
    assert again["mean_population_last_year"].tolist() == [25, 25]
    assert (exp / "summary_before_last_year.csv").read_bytes() == before
