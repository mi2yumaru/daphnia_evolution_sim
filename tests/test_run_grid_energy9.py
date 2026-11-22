"""Unit tests for energy pilot configuration and comparison layout."""
import unittest
from pathlib import Path

import yaml

from src.run_grid_energy9 import (
    BASE_PARAMS, ENERGIES, EXTRA_CONDITION, ENVIRONMENTS,
    case_name_energy, conditions, make_energy_config, output_conditions, tasks,
    save_comparisons,
)


class TestEnergyGrid(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with (Path(__file__).resolve().parents[1] / "configs/default.yaml").open(
            encoding="utf-8"
        ) as f:
            cls.base = yaml.safe_load(f)

    def test_unique_eighteen_runs_and_baseline_first(self):
        all_tasks = tasks()
        self.assertEqual(len(all_tasks), 18)
        self.assertEqual(len(set(all_tasks)), 18)
        self.assertEqual(all_tasks[:2], [(5, 5, "patch"), (5, 5, "random")])
        self.assertEqual(case_name_energy(3, 7), "O3_F7")
        self.assertEqual(tasks(only_f4=True), [(5, 4, "patch"), (5, 4, "random")])
        self.assertEqual(EXTRA_CONDITION, (5, 4))
        self.assertEqual(len(output_conditions()), 10)

    def test_f4_changes_only_food_energy(self):
        for env in ENVIRONMENTS:
            baseline = make_energy_config(self.base, 5, 5, env)
            f4 = make_energy_config(self.base, 5, 4, env)
            self.assertEqual(f4["environment"]["food_energy"], 4)
            self.assertEqual(f4["organism"]["offspring_energy"], 5)
            baseline["environment"]["food_energy"] = 4
            self.assertEqual(f4, baseline)

    def test_existing_3x3_rows_survive_f4_summary(self):
        import csv
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            records = {
                ("O5_F5", env): {
                    "case": "O5_F5", "environment": env,
                    "offspring_energy": 5, "food_energy": 5,
                    "status": "complete",
                }
                for env in ENVIRONMENTS
            }
            records[("O5_F4", "patch")] = {
                "case": "O5_F4", "environment": "patch",
                "offspring_energy": 5, "food_energy": 4,
                "status": "complete",
            }
            save_comparisons(root, records)
            with (root / "grid_summary.csv").open(encoding="utf-8-sig") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 3)
            self.assertEqual(
                {(r["case"], r["environment"]) for r in rows},
                {("O5_F5", "patch"), ("O5_F5", "random"), ("O5_F4", "patch")},
            )
            records[("O5_F4", "random")] = {
                "case": "O5_F4", "environment": "random",
                "offspring_energy": 5, "food_energy": 4,
                "status": "complete",
            }
            save_comparisons(root, records)
            with (root / "grid_paired_comparison.csv").open(encoding="utf-8-sig") as f:
                paired = list(csv.DictReader(f))
            self.assertEqual({x["case"] for x in paired}, {"O5_F5", "O5_F4"})

    def test_configs_preserve_other_settings(self):
        baseline = make_energy_config(self.base, 5, 5, "patch")
        for offspring, food, env in tasks():
            cfg = make_energy_config(self.base, offspring, food, env)
            self.assertEqual(cfg["environment"]["food_energy"], food)
            self.assertEqual(cfg["organism"]["offspring_energy"], offspring)
            self.assertEqual(cfg["environment"]["mode"], env)
            self.assertEqual(cfg["simulation"]["duration_years"], 1)
            self.assertEqual(cfg["simulation"]["random_seed"], 0)
            self.assertEqual(cfg["organism"]["living_cost"], BASE_PARAMS[0])
            self.assertEqual(cfg["organism"]["move_cost"], BASE_PARAMS[1])
            self.assertEqual(cfg["organism"]["reproduction_threshold"], BASE_PARAMS[2])
            self.assertEqual(cfg["organism"]["reproduction_cost"], BASE_PARAMS[3])
            self.assertEqual(cfg["seasonal_food"], baseline["seasonal_food"])
            self.assertEqual(cfg["gene_exchange"], baseline["gene_exchange"])
            self.assertFalse(cfg["analysis"]["gene_flow"]["enabled"])
            self.assertFalse(cfg["analysis"]["offspring_outcomes"]["enabled"])


if __name__ == "__main__":
    unittest.main()
