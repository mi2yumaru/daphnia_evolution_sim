"""Regression checks for adoption of calibrated No.10 energy parameters.

Do not change historical step4_* configurations or grid selection definitions.
"""
import unittest
from pathlib import Path

import yaml

from src.run_grid_search import make_config
from src.run_grid_energy9 import BASE_PARAMS as ENERGY_PILOT_BASE_PARAMS
from src.run_grid_long12 import SELECTION as LONG_GRID_SELECTION


ROOT = Path(__file__).resolve().parents[1] / "configs"

NO10 = {
    "living_cost": 0.15,
    "move_cost": 1.0,
    "reproduction_threshold": 15,
    "reproduction_cost": 10,
    "offspring_energy": 5,
}
ACTIVE_CONFIGS = {
    "default.yaml": "patch",
    "random_periodic.yaml": "random",
    "patch16.yaml": "patch",
}
HISTORICAL_CONFIGS = (
    "step4_random.yaml",
    "step4_patch9.yaml",
    "step4_patch25.yaml",
)


def read_config(filename):
    with (ROOT / filename).open(encoding="utf-8") as f:
        return yaml.safe_load(f)


class TestNo10Calibration(unittest.TestCase):
    def test_active_configs_use_no10(self):
        for filename, mode in ACTIVE_CONFIGS.items():
            with self.subTest(filename=filename):
                config = read_config(filename)
                self.assertEqual(config["environment"]["mode"], mode)
                for key, expected in NO10.items():
                    self.assertEqual(config["organism"][key], expected)
                self.assertEqual(config["environment"]["food_energy"], 5)
                self.assertTrue(config["seasonal_food"]["enabled"])
                self.assertTrue(config["environment"]["periodic_boundary"])
                self.assertEqual(config["gene_exchange"]["mode"], "evolvable")
                self.assertTrue(config["gene_exchange"]["enabled"])

    def test_four_patch_and_random_energies_identical(self):
        patch = read_config("default.yaml")
        random = read_config("random_periodic.yaml")
        for key in NO10:
            self.assertEqual(patch["organism"][key], random["organism"][key])
        self.assertEqual(
            patch["seasonal_food"]["csv_path"],
            random["seasonal_food"]["csv_path"],
        )
        self.assertEqual(patch["environment"]["food_energy"], random["environment"]["food_energy"])

    def test_historical_step4_configs_are_not_recalibrated(self):
        for filename in HISTORICAL_CONFIGS:
            with self.subTest(filename=filename):
                cfg = read_config(filename)
                self.assertEqual(cfg["organism"]["living_cost"], 0.3)
                self.assertEqual(cfg["organism"]["move_cost"], 0.5)
                self.assertEqual(cfg["organism"]["reproduction_threshold"], 20)

    def test_existing_grid_runner_overrides_no10_values_for_old_cases(self):
        cfg = read_config("default.yaml")
        old_base = (0.30, 0.50, 20, 10)
        historical = make_config(cfg, old_base)
        self.assertEqual(historical["organism"]["living_cost"], 0.30)
        self.assertEqual(historical["organism"]["move_cost"], 0.50)
        self.assertEqual(historical["organism"]["reproduction_threshold"], 20)
        self.assertEqual(historical["organism"]["reproduction_cost"], 10)
        self.assertEqual(cfg["organism"]["living_cost"], NO10["living_cost"])
        self.assertEqual(cfg["organism"]["move_cost"], NO10["move_cost"])

    def test_grid_condition_definitions_do_not_change(self):
        self.assertIn((0.15, 1.0, 15, 10), LONG_GRID_SELECTION)
        self.assertEqual(len(LONG_GRID_SELECTION), 12)
        self.assertEqual(ENERGY_PILOT_BASE_PARAMS, (0.30, 1.00, 20, 10))


if __name__ == "__main__":
    unittest.main()
