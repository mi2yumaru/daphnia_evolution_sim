"""Final complete calendar-year summary for Daphnia multi-seed experiments.

STEP4: No changes to simulation, genome, births, deaths or logging.
Time-averaged states are distinct from event-weighted ratios.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil

import numpy as np
import pandas as pd

# Raw logged state => output summary column.  ``mean`` averages snapshots/steps,
# whereas event probabilities are computed below from summed integer counts.
MEAN_METRICS = {
    "population_size": "mean_population_last_year",
    "food_count": "mean_food_count_last_year",
    "food_respawn_rate": "mean_food_respawn_rate_last_year",
    "food_respawn_count": "mean_food_respawn_count_last_year",
    "food_consumed_count": "mean_food_consumed_count_last_year",
    # FOOD_FLOW_LOGGING_V1: region-specific states and per-step flows.
    "patch_area": "mean_patch_area_last_year",
    "outside_area": "mean_outside_area_last_year",
    "food_in": "mean_food_in_last_year",
    "food_out": "mean_food_out_last_year",
    "food_respawn_in": "mean_food_respawn_in_last_year",
    "food_respawn_out": "mean_food_respawn_out_last_year",
    "food_consumed_in": "mean_food_consumed_in_last_year",
    "food_consumed_out": "mean_food_consumed_out_last_year",
    "density_in": "mean_density_in_last_year",
    "density_out": "mean_density_out_last_year",
    "density_ratio": "mean_density_ratio_last_year",
    "density_pre_in": "mean_density_pre_in_last_year",
    "density_pre_out": "mean_density_pre_out_last_year",
    "birth_count": "mean_birth_count_last_year",
    "death_count": "mean_death_count_last_year",
    "age_death_count": "mean_age_death_count_last_year",
    "energy_death_count": "mean_energy_death_count_last_year",
    "birth_rate": "mean_birth_rate_last_year",
    "death_rate": "mean_death_rate_last_year",
    "age_death_rate": "mean_age_death_rate_last_year",
    "energy_death_rate": "mean_energy_death_rate_last_year",
    "move_rate": "mean_move_rate_last_year",
    "move_count": "mean_move_count_last_year",
    "non_move_count": "mean_non_move_count_last_year",
    "total_eat_rate": "mean_total_eat_rate_last_year",
    "eat_after_move_rate": "mean_eat_after_move_rate_last_year",
    "eat_without_move_rate": "mean_eat_without_move_rate_last_year",
    "mean_consumers_per_shared_food": "mean_consumers_per_shared_food_last_year",
    "shared_food_cell_ratio": "mean_shared_food_cell_ratio_last_year",
    "shared_food_consumer_ratio": "mean_shared_food_consumer_ratio_last_year",
    "average_exploration_tendency": "mean_exploration_tendency_last_year",
    "average_site_fidelity": "mean_site_fidelity_last_year",
    "average_risk_tolerance": "mean_risk_tolerance_last_year",
    "average_reproduction_timing": "mean_reproduction_timing_last_year",
    "average_gene_exchange_probability": "mean_gene_exchange_probability_last_year",
    "average_gene_exchange_fraction": "mean_gene_exchange_fraction_last_year",
    "gene_exchange_eligible_count": "mean_gene_exchange_eligible_count_last_year",
    "gene_exchange_event_count": "mean_gene_exchange_event_count_last_year",
    "gene_exchange_effective_count": "mean_gene_exchange_effective_count_last_year",
    "gene_exchange_selected_loci_count": "mean_gene_exchange_selected_loci_count_last_year",
    "gene_exchange_changed_bit_count": "mean_gene_exchange_changed_bit_count_last_year",
    "genetic_diversity_all": "mean_genetic_diversity_all_last_year",
    "genetic_diversity_behavior": "mean_genetic_diversity_behavior_last_year",
    "genetic_diversity_exchange": "mean_genetic_diversity_exchange_last_year",
    "genotype_diversity": "mean_genotype_diversity_last_year",
    "unique_genotype_ratio": "mean_unique_genotype_ratio_last_year",
    "active_lineage_count": "mean_active_lineage_count_last_year",
    "largest_lineage_share": "mean_largest_lineage_share_last_year",
    "average_generation": "mean_average_generation_last_year",
    "max_generation": "mean_max_generation_last_year",
}

TOTAL_METRICS = {
    "birth_count": "total_birth_count_last_year",
    "death_count": "total_death_count_last_year",
    "food_respawn_count": "total_food_respawn_count_last_year",
    "food_consumed_count": "total_food_consumed_count_last_year",
    "food_respawn_in": "total_food_respawn_in_last_year",
    "food_respawn_out": "total_food_respawn_out_last_year",
    "food_consumed_in": "total_food_consumed_in_last_year",
    "food_consumed_out": "total_food_consumed_out_last_year",
    "gene_exchange_eligible_count": "total_gene_exchange_eligible_count_last_year",
    "gene_exchange_event_count": "total_gene_exchange_event_count_last_year",
    "gene_exchange_effective_count": "total_gene_exchange_effective_count_last_year",
    "gene_exchange_selected_loci_count": "total_gene_exchange_selected_loci_count_last_year",
    "gene_exchange_changed_bit_count": "total_gene_exchange_changed_bit_count_last_year",
}

# Numerator / denominator computed over THE SAME whole year. Zero denom -> NaN.
RATIO_METRICS = {
    "food_respawn_in_fraction_last_year": ("food_respawn_in", "food_respawn_count"),
    "food_consumed_in_fraction_last_year": ("food_consumed_in", "food_consumed_count"),
    "gene_exchange_eligible_per_birth_last_year": ("gene_exchange_eligible_count", "birth_count"),
    "gene_exchange_event_per_eligible_last_year": ("gene_exchange_event_count", "gene_exchange_eligible_count"),
    "gene_exchange_event_per_birth_last_year": ("gene_exchange_event_count", "birth_count"),
    "gene_exchange_effective_per_event_last_year": ("gene_exchange_effective_count", "gene_exchange_event_count"),
    "gene_exchange_effective_per_birth_last_year": ("gene_exchange_effective_count", "birth_count"),
    "gene_exchange_changed_per_selected_locus_last_year": ("gene_exchange_changed_bit_count", "gene_exchange_selected_loci_count"),
}

METRIC_COLUMNS = tuple(dict.fromkeys([*MEAN_METRICS.values(), *TOTAL_METRICS.values(), *RATIO_METRICS]))
META_COLUMNS = ("last_year_calendar_year", "last_year_start_step", "last_year_end_step", "last_year_steps_observed", "last_year_complete")


def calculate_last_year_metrics(df: pd.DataFrame, steps_per_year: int = 3650) -> dict[str, float | int | bool]:
    """Describe the final calendar year, excluding partial final years.

    The source log is required to be ordered by step and contain a step-0 based
    complete year. A partial year yields NaN for all year metrics (not fake 0s).
    """
    if not isinstance(steps_per_year, int) or steps_per_year <= 0:
        raise ValueError("steps_per_year must be a positive integer")
    if df.empty or not {"step", "simulation_year"}.issubset(df.columns):
        raise ValueError("A non-empty step log with step and simulation_year is required")
    steps = pd.to_numeric(df["step"], errors="raise")
    years = pd.to_numeric(df["simulation_year"], errors="raise")
    if steps.isna().any() or years.isna().any() or not steps.is_monotonic_increasing or steps.duplicated().any():
        raise ValueError("step must be unique, non-missing, and in increasing order")
    year = int(years.iloc[-1])
    if year < 1 or (years.iloc[-1] != year):
        raise ValueError("simulation_year must end with a positive integer")
    last = df.loc[years == year]
    start = (year - 1) * steps_per_year
    end = year * steps_per_year - 1
    year_steps = pd.to_numeric(last["step"], errors="raise")
    complete = (len(last) == steps_per_year and
                year_steps.iloc[0] == start and year_steps.iloc[-1] == end and
                bool((year_steps.diff().iloc[1:] == 1).all()))
    out: dict[str, float | int | bool] = {
        "last_year_calendar_year": year,
        "last_year_start_step": start,
        "last_year_end_step": end,
        "last_year_steps_observed": len(last),
        "last_year_complete": bool(complete),
    }
    if not complete:
        out.update({key: float("nan") for key in METRIC_COLUMNS})
        return out

    for col, key in MEAN_METRICS.items():
        out[key] = float(pd.to_numeric(last[col], errors="raise").mean()) if col in last.columns else float("nan")
    for col, key in TOTAL_METRICS.items():
        out[key] = float(pd.to_numeric(last[col], errors="raise").sum(min_count=1)) if col in last.columns else float("nan")
    for key, (numer, denom) in RATIO_METRICS.items():
        n, d = TOTAL_METRICS[numer], TOTAL_METRICS[denom]
        denominator = out[d]
        numerator = out[n]
        out[key] = float(numerator / denominator) if pd.notna(denominator) and denominator > 0 and pd.notna(numerator) else float("nan")
    return out


def across_seed_summary(summary: pd.DataFrame) -> pd.DataFrame:
    """One row per year metric: mean/std across seeds (sample std, ddof=1)."""
    if "seed" not in summary.columns or summary["seed"].isna().any() or summary["seed"].duplicated().any():
        raise ValueError("summary.csv requires distinct, nonmissing seed values")
    rows = []
    for name in METRIC_COLUMNS:
        vals = pd.to_numeric(summary[name], errors="coerce") if name in summary.columns else pd.Series(dtype=float)
        vals = vals.replace([np.inf, -np.inf], np.nan).dropna()
        rows.append({
            "metric": name,
            "n_valid_seeds": int(len(vals)),
            "mean": float(vals.mean()) if len(vals) else float("nan"),
            "std": float(vals.std(ddof=1)) if len(vals) >= 2 else float("nan"),
        })
    return pd.DataFrame(rows)


def backfill_experiment(experiment_dir: Path, steps_per_year: int = 3650) -> tuple[Path, Path]:
    """Update existing per-seed summary from logs only; no simulation rerun.

    Writes a one-time backup of the old summary.csv. Does not touch lineage,
    per-step log, graphs, experimental configs, or simulation logic.
    """
    experiment_dir = Path(experiment_dir)
    summary_path = experiment_dir / "summary.csv"
    if not summary_path.is_file():
        raise FileNotFoundError(f"No existing summary.csv: {summary_path}")
    summary = pd.read_csv(summary_path)
    if "seed" not in summary.columns or summary["seed"].isna().any() or summary["seed"].duplicated().any():
        raise ValueError("summary.csv must contain unique seeds")
    updates = {}
    # Validate every seed and its log BEFORE writing any files.
    for seed in summary["seed"].astype(int):
        path = experiment_dir / f"seed_{seed}" / "log.csv"
        if not path.is_file():
            raise FileNotFoundError(f"No log.csv for seed {seed}: {path}")
        log = pd.read_csv(path)
        # The two food-sharing ratios are normally added by visualizer.py
        # during an experiment. Reconstruct them from raw log.csv here.
        if "shared_food_cell_ratio" not in log and {
            "shared_food_cell_count", "food_consumed_count"
        }.issubset(log.columns):
            denom = log["food_consumed_count"].where(log["food_consumed_count"] > 0)
            log["shared_food_cell_ratio"] = log["shared_food_cell_count"] / denom
        if "shared_food_consumer_ratio" not in log and {
            "shared_food_consumer_count", "eat_count"
        }.issubset(log.columns):
            denom = log["eat_count"].where(log["eat_count"] > 0)
            log["shared_food_consumer_ratio"] = log["shared_food_consumer_count"] / denom
        updates[seed] = calculate_last_year_metrics(log, steps_per_year)
    for key in (*META_COLUMNS, *METRIC_COLUMNS):
        summary[key] = summary["seed"].astype(int).map({s: values[key] for s, values in updates.items()})
    backup = experiment_dir / "summary_before_last_year.csv"
    if not backup.exists():
        shutil.copy2(summary_path, backup)
    summary.to_csv(summary_path, index=False)
    across_path = experiment_dir / "summary_last_year_across_seeds.csv"
    across_seed_summary(summary).to_csv(across_path, index=False)
    return summary_path, across_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Add final complete-year metrics using saved seed logs")
    parser.add_argument("--experiment-dir", type=Path, required=True)
    parser.add_argument("--steps-per-year", type=int, default=3650, help="365 days * 10 steps/day by default")
    args = parser.parse_args()
    summary, across = backfill_experiment(args.experiment_dir, args.steps_per_year)
    print(f"Updated per-seed summary: {summary}")
    print(f"New seed-mean/std summary: {across}")
    print("Original summary backed up once as summary_before_last_year.csv")


if __name__ == "__main__":
    main()
