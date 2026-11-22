"""Tests for 12-condition long grid selection, configuration and aggregation."""
import csv
import math
import tempfile
import unittest
from pathlib import Path

import yaml

from src.run_grid_long12 import (
    ENVIRONMENTS,
    EXPERIMENT,
    METRICS,
    SEEDS,
    SELECTION,
    TOTAL_STEPS,
    YEARS,
    aggregate_records,
    build_tasks,
    make_run_config,
    summarize_log,
)
from src.run_grid_search import case_name


class TestLongGrid12(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        repo = Path(__file__).resolve().parents[1]
        with (repo / "configs" / "default.yaml").open(encoding="utf-8") as f:
            cls.base = yaml.safe_load(f)

    def test_exact_twelve_conditions_and_240_runs(self):
        self.assertEqual(EXPERIMENT, "grid12_5y_10seeds")
        self.assertEqual(
            SELECTION,
            (
                (0.30, 0.50, 20, 10),
                (0.30, 0.75, 20, 10),
                (0.30, 1.00, 20, 10),
                (0.45, 0.50, 20, 10),
                (0.45, 0.75, 20, 10),
                (0.45, 1.00, 20, 10),
                (0.60, 0.75, 20, 10),
                (0.60, 1.00, 20, 10),
                (0.15, 1.00, 20, 10),
                (0.15, 1.00, 15, 10),
                (0.30, 1.00, 15, 10),
                (0.30, 1.00, 25, 10),
            ),
        )
        self.assertEqual(len({case_name(v) for v in SELECTION}), 12)
        runs = build_tasks()
        self.assertEqual(len(runs), 240)
        self.assertEqual(len(set(runs)), 240)
        self.assertEqual(
            runs[:2],
            [
                ((0.30, 0.50, 20, 10), "patch", 0),
                ((0.30, 0.50, 20, 10), "random", 0),
            ],
        )
        self.assertEqual(len(build_tasks((0,))), 24)
        self.assertEqual(TOTAL_STEPS, 18250)

    def test_config_preserves_initial_energy_and_exchange_settings(self):
        for values in SELECTION:
            for env in ENVIRONMENTS:
                for seed in (0, 9):
                    cfg = make_run_config(self.base, values, env, seed)
                    self.assertEqual(cfg["organism"]["living_cost"], values[0])
                    self.assertEqual(cfg["organism"]["move_cost"], values[1])
                    self.assertEqual(cfg["organism"]["reproduction_threshold"], values[2])
                    self.assertEqual(cfg["organism"]["reproduction_cost"], values[3])
                    self.assertEqual(cfg["organism"]["offspring_energy"], 5)
                    self.assertEqual(cfg["environment"]["food_energy"], 5)
                    self.assertEqual(cfg["environment"]["mode"], env)
                    self.assertEqual(cfg["simulation"]["duration_years"], YEARS)
                    self.assertEqual(cfg["simulation"]["random_seed"], seed)
                    self.assertEqual(cfg["gene_exchange"], self.base["gene_exchange"])
                    self.assertEqual(cfg["seasonal_food"], self.base["seasonal_food"])
                    self.assertEqual(cfg["organism"]["initial_energy"], 10)
                    self.assertFalse(cfg["analysis"]["offspring_outcomes"]["enabled"])
                    self.assertFalse(cfg["analysis"]["gene_flow"]["enabled"])

    def test_five_year_log_summarization(self):
        headers = [
            "step", "month", "birth_count", "death_count",
            "energy_death_count", "age_death_count", "population_size",
            "average_energy", "move_rate", "total_eat_rate",
            "average_generation", "max_generation",
            "average_gene_exchange_probability",
            "average_gene_exchange_fraction",
            "gene_exchange_birth_rate", "gene_exchange_effective_birth_rate",
        ]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "log.csv"
            with path.open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                for i in range(TOTAL_STEPS):
                    year_idx = i // 3650
                    writer.writerow({
                        "step": i,
                        "month": 1,
                        "birth_count": 2, "death_count": 2,
                        "energy_death_count": 1, "age_death_count": 1,
                        "population_size": 100 + 10 * year_idx,
                        "average_energy": 10.0, "move_rate": 0.4,
                        "total_eat_rate": 0.5, "average_generation": year_idx,
                        "max_generation": year_idx + 1,
                        "average_gene_exchange_probability": 0.2,
                        "average_gene_exchange_fraction": 0.1,
                        "gene_exchange_birth_rate": 0.05,
                        "gene_exchange_effective_birth_rate": 0.04,
                    })
            row = summarize_log(path, SELECTION[0], "patch", 0, 2.0)
        self.assertEqual(row["steps_logged"], TOTAL_STEPS)
        self.assertEqual(row["survived_5y"], 1)
        self.assertEqual(row["final_population"], 140)
        self.assertEqual(row["mean_population"], 120)
        self.assertEqual(row["mean_population_last_year"], 140)
        self.assertEqual(row["year_1_mean_population"], 100)
        self.assertEqual(row["year_5_mean_population"], 140)
        self.assertEqual(row["year_5_min_population"], 140)
        self.assertEqual(row["year_5_winter_min_population"], 140)
        self.assertEqual(row["last_year_gene_exchange_probability"], 0.2)
        self.assertEqual(row["last_year_gene_exchange_fraction"], 0.1)
        self.assertEqual(row["last_year_gene_exchange_effective_birth_rate"], 0.04)
        self.assertEqual(row["total_births"], TOTAL_STEPS * 2)
        self.assertEqual(row["total_deaths"], TOTAL_STEPS * 2)

    def test_aggregation_mean_and_std_across_seeds(self):
        case = case_name(SELECTION[0])
        def row(seed, final_pop, age, survived):
            return {
                "run_id": f"{case}/patch/seed_{seed}",
                "case": case, "environment": "patch", "seed": seed,
                "status": "complete", "survived_5y": survived,
                "final_population": final_pop,
                "first_reproduction_median_days": age,
                "first_reproduction_6_to_12d_frac": 0.30 + 0.20 * seed,
            }
        records = {
            f"{case}/patch/seed_0": row(0, 100, 9, 1),
            f"{case}/patch/seed_1": row(1, 140, 11, 0),
        }
        agg, fields = aggregate_records(records)
        first = next(x for x in agg if x["case"] == case and x["environment"] == "patch")
        self.assertEqual(first["completed_seeds"], 2)
        self.assertEqual(first["survived_seeds"], 1)
        self.assertEqual(first["extinct_seeds"], 1)
        self.assertEqual(first["final_population_mean"], 120)
        self.assertAlmostEqual(first["final_population_std"], 28.284271, places=4)
        self.assertEqual(first["first_reproduction_median_days_mean"], 10)
        self.assertAlmostEqual(first["first_reproduction_6_to_12d_frac_mean"], 0.40)
        self.assertIn("first_reproduction_median_days_std", fields)
        self.assertEqual(len(agg), 24)


if __name__ == "__main__":
    unittest.main()
