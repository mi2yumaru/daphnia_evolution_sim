"""Tests for retrospective lineage age calculations."""
import csv
import tempfile
import unittest
from pathlib import Path

from src.analyze_lineage_life_history import analyze, percentile


class TestLifeHistory(unittest.TestCase):
    def test_first_reproduction_and_event_weighting(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "lineage.csv"
            with p.open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(
                    f, fieldnames=("organism_id", "parent_id", "generation", "birth_step")
                )
                writer.writeheader()
                writer.writerows([
                    {"organism_id": 0, "parent_id": "", "generation": 0, "birth_step": 0},
                    {"organism_id": 1, "parent_id": "", "generation": 0, "birth_step": 0},
                    {"organism_id": 2, "parent_id": "0.0", "generation": 1, "birth_step": 10},
                    {"organism_id": 3, "parent_id": "0.0", "generation": 1, "birth_step": 30},
                    {"organism_id": 4, "parent_id": "2.0", "generation": 2, "birth_step": 40},
                ])
            res = analyze(p, 10)
            self.assertEqual(res["lineage_individuals"], 5)
            self.assertEqual(res["offspring_count"], 3)
            self.assertEqual(res["distinct_reproductive_parents"], 2)
            self.assertEqual(res["founder_reproductive_parents"], 1)
            self.assertEqual(res["nonfounder_reproductive_parents"], 1)
            self.assertAlmostEqual(res["first_reproduction_mean_days"], 2.05)
            self.assertAlmostEqual(res["first_reproduction_median_days"], 2.05)
            self.assertAlmostEqual(res["founder_first_reproduction_median_days"], 1.1)
            self.assertAlmostEqual(res["nonfounder_first_reproduction_median_days"], 3.0)
            self.assertAlmostEqual(res["parent_age_at_birth_mean_days"], 7.2 / 3, places=4)
            self.assertEqual(res["first_reproduction_under_10d_frac"], 1.0)

    def test_first_reproduction_6_to_12_day_interval_inclusive(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "lineage.csv"
            with p.open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(
                    f, fieldnames=("organism_id", "parent_id", "generation", "birth_step")
                )
                writer.writeheader()
                for i in range(4):
                    writer.writerow({
                        "organism_id": i, "parent_id": "",
                        "generation": 0, "birth_step": 0,
                    })
                for child_id, parent_id, birth_step in (
                    (4, 0, 49),   # age 5.0 days
                    (5, 1, 59),   # age 6.0 days
                    (6, 2, 119),  # age 12.0 days
                    (7, 3, 129),  # age 13.0 days
                ):
                    writer.writerow({
                        "organism_id": child_id, "parent_id": parent_id,
                        "generation": 1, "birth_step": birth_step,
                    })
            res = analyze(p, 10)
            self.assertEqual(res["first_reproduction_before_6d_frac"], 0.25)
            self.assertEqual(res["first_reproduction_6_to_12d_frac"], 0.50)
            self.assertEqual(res["first_reproduction_over_12d_frac"], 0.25)

    def test_empty_distribution(self):
        self.assertTrue(str(percentile([], 50)).lower() == "nan")


if __name__ == "__main__":
    unittest.main()
