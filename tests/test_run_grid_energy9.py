"""Unit tests for energy pilot configuration and comparison layout."""
import unittest
from pathlib import Path

import yaml

from src.run_grid_energy9 import (
    BASE_PARAMS, ENERGIES, ENVIRONMENTS,
    case_name_energy, conditions, make_energy_config, tasks,
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
