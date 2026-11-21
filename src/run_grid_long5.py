"""Run 5 selected energy parameter sets in two environments, 5 years x 10 seeds.

Run from the repository root:
    python src/run_grid_long5.py --list
    python src/run_grid_long5.py --limit 2
    python src/run_grid_long5.py

Each (parameter set, environment, seed) is a separate run so completed
runs are skipped on restart. The original 1-year sweep folders stay intact.
"""
from __future__ import annotations

import argparse
import csv
import math
import statistics
import subprocess
import sys
import time
from collections import deque
from pathlib import Path

import yaml

from run_grid_search import case_name, make_config

EXPERIMENT = "grid5_5y_10seeds"
SELECTION = (
    (0.30, 0.50, 20, 10),  # Baseline
    (0.15, 0.50, 20, 10),  # Lower living cost
    (0.60, 0.50, 20, 10),  # Higher living cost
    (0.30, 1.00, 20, 10),  # Higher moving cost
    (0.30, 0.50, 30, 10),  # Higher reproduction threshold
)
ENVIRONMENTS = ("patch", "random")
SEEDS = tuple(range(10))
YEARS = 5
STEPS_PER_YEAR = 365 * 10
TOTAL_STEPS = YEARS * STEPS_PER_YEAR
METRICS = (
    "final_population", "min_population", "max_population",
    "mean_population", "mean_population_last_year", "total_births",
    "total_deaths", "energy_deaths", "age_deaths", "energy_death_share",
    "mean_energy", "mean_move_rate", "mean_eat_rate",
    "final_average_generation", "final_max_generation",
    "last_year_gene_exchange_probability",
    "last_year_gene_exchange_fraction",
    "last_year_gene_exchange_birth_rate",
    "last_year_gene_exchange_effective_birth_rate",
    *(f"year_{year}_mean_population" for year in range(1, YEARS + 1)),
)
FIELDS = [
    "case", "environment", "seed",
    "living_cost", "move_cost", "reproduction_threshold", "reproduction_cost",
    "status", "elapsed_sec", "steps_logged", "survived_5y",
    "first_extinction_step", *METRICS,
]
OPTIONAL_LAST_YEAR = (
    "average_gene_exchange_probability",
    "average_gene_exchange_fraction",
    "gene_exchange_birth_rate",
    "gene_exchange_effective_birth_rate",
)


def read_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def make_run_config(base: dict, values: tuple, mode: str, seed: int) -> dict:
    cfg = make_config(base, values)  # keeps 1-year grid behavior and analyses
    cfg["environment"]["mode"] = mode
    cfg["simulation"]["duration_mode"] = "years"
    cfg["simulation"]["duration_years"] = YEARS
    cfg["simulation"]["random_seed"] = seed
    if cfg["simulation"]["days_per_year"] * cfg["simulation"]["steps_per_day"] != STEPS_PER_YEAR:
        raise ValueError("Expected 365 days/year x 10 steps/day")
    return cfg


def check_older_snapshot(
    repo: Path, values: tuple, mode: str, cfg: dict
) -> None:
    old_name = (
        "grid_patch4_1y_seed0" if mode == "patch" else "grid_random20_1y_seed0"
    )
    old = (
        repo / "results" / "experiments" / old_name
        / case_name(values) / "config_used.yaml"
    )
    if not old.is_file():
        return
    previous = read_yaml(old)
    previous["simulation"]["duration_years"] = YEARS
    previous["simulation"]["random_seed"] = cfg["simulation"]["random_seed"]
    if previous != cfg:
        raise RuntimeError(
            f"Settings differ from the 1-year experiment: {old}. "
            "Do not mix experiments with different settings."
        )


def read_records(path: Path) -> dict[str, dict]:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        return {row["run_id"]: row for row in csv.DictReader(f)}


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def summarize_log(
    path: Path, values: tuple, mode: str, seed: int, elapsed: float
) -> dict:
    totals = {
        "birth_count": 0.0, "death_count": 0.0,
        "energy_death_count": 0.0, "age_death_count": 0.0,
        "population_size": 0.0, "average_energy": 0.0,
        "move_rate": 0.0, "total_eat_rate": 0.0,
    }
    year_population = [0.0] * YEARS
    last_year_optional = {name: 0.0 for name in OPTIONAL_LAST_YEAR}
    min_pop = math.inf
    max_pop = 0
    extinct_step = ""
    last_100 = deque(maxlen=100)
    last = None
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = set(totals) | {"step", "average_generation", "max_generation"}
        missing = required - set(reader.fieldnames or ())
        if missing:
            raise RuntimeError(f"Missing columns in {path}: {sorted(missing)}")
        available_optional = set(reader.fieldnames or ()) & set(OPTIONAL_LAST_YEAR)
        count = 0
        for count, row in enumerate(reader, start=1):
            if count > TOTAL_STEPS:
                raise RuntimeError(f"Too many steps in {path}")
            year = (count - 1) // STEPS_PER_YEAR
            pop = int(float(row["population_size"]))
            min_pop = min(min_pop, pop)
            max_pop = max(max_pop, pop)
            year_population[year] += pop
            last_100.append(pop)
            if pop == 0 and extinct_step == "":
                extinct_step = int(float(row["step"]))
            for key in totals:
                totals[key] += float(row[key])
            if year == YEARS - 1:
                for key in available_optional:
                    last_year_optional[key] += float(row[key])
            last = row

    if count != TOTAL_STEPS or last is None:
        raise RuntimeError(f"Expected {TOTAL_STEPS} steps, found {count}: {path}")
    deaths = totals["energy_death_count"] + totals["age_death_count"]
    L, M, T, C = values
    return {
        "run_id": f"{case_name(values)}/{mode}/seed_{seed}",
        "case": case_name(values), "environment": mode, "seed": seed,
        "living_cost": L, "move_cost": M,
        "reproduction_threshold": T, "reproduction_cost": C,
        "status": "complete",
        "elapsed_sec": "" if math.isnan(elapsed) else round(elapsed, 2),
        "steps_logged": count,
        "survived_5y": int(extinct_step == "" and int(float(last["population_size"])) > 0),
        "first_extinction_step": extinct_step,
        "final_population": int(float(last["population_size"])),
        "min_population": int(min_pop), "max_population": int(max_pop),
        "mean_population": round(totals["population_size"] / count, 5),
        "mean_population_last_year": round(year_population[-1] / STEPS_PER_YEAR, 5),
        "total_births": int(totals["birth_count"]),
        "total_deaths": int(totals["death_count"]),
        "energy_deaths": int(totals["energy_death_count"]),
        "age_deaths": int(totals["age_death_count"]),
        "energy_death_share": (
            round(totals["energy_death_count"] / deaths, 6)
            if deaths else ""
        ),
        "mean_energy": round(totals["average_energy"] / count, 6),
        "mean_move_rate": round(totals["move_rate"] / count, 6),
        "mean_eat_rate": round(totals["total_eat_rate"] / count, 6),
        "final_average_generation": float(last["average_generation"]),
        "final_max_generation": int(float(last["max_generation"])),
        "last_year_gene_exchange_probability": (
            round(last_year_optional["average_gene_exchange_probability"] / STEPS_PER_YEAR, 6)
            if "average_gene_exchange_probability" in available_optional else ""
        ),
        "last_year_gene_exchange_fraction": (
            round(last_year_optional["average_gene_exchange_fraction"] / STEPS_PER_YEAR, 6)
            if "average_gene_exchange_fraction" in available_optional else ""
        ),
        "last_year_gene_exchange_birth_rate": (
            round(last_year_optional["gene_exchange_birth_rate"] / STEPS_PER_YEAR, 6)
            if "gene_exchange_birth_rate" in available_optional else ""
        ),
        "last_year_gene_exchange_effective_birth_rate": (
            round(last_year_optional["gene_exchange_effective_birth_rate"] / STEPS_PER_YEAR, 6)
            if "gene_exchange_effective_birth_rate" in available_optional else ""
        ),
        **{
            f"year_{i + 1}_mean_population": round(total / STEPS_PER_YEAR, 5)
            for i, total in enumerate(year_population)
        },
    }


def aggregate_records(records: dict[str, dict]) -> tuple[list[dict], list[str]]:
    fields = [
        "case", "environment", "completed_seeds", "survived_seeds",
        "extinct_seeds", *(
            f"{name}_{stat}" for name in METRICS for stat in ("mean", "std")
        ),
    ]
    aggregated = []
    for values in SELECTION:
        for mode in ENVIRONMENTS:
            prefix = f"{case_name(values)}/{mode}/"
            group = [
                row for key, row in records.items()
                if key.startswith(prefix) and row.get("status") == "complete"
            ]
            result = {
                "case": case_name(values), "environment": mode,
                "completed_seeds": len(group),
                "survived_seeds": sum(int(r["survived_5y"]) for r in group),
                "extinct_seeds": sum(1 - int(r["survived_5y"]) for r in group),
            }
            for key in METRICS:
                values_present = [
                    float(row[key]) for row in group
                    if row.get(key, "") not in ("", None)
                ]
                result[f"{key}_mean"] = (
                    round(statistics.mean(values_present), 6)
                    if values_present else ""
                )
                result[f"{key}_std"] = (
                    round(statistics.stdev(values_present), 6)
                    if len(values_present) >= 2 else ""
                )
            aggregated.append(result)
    return aggregated, fields


def main() -> None:
    parser = argparse.ArgumentParser(
        description="5 parameter sets x 2 environments x 10 seeds x 5 years"
    )
    parser.add_argument("--list", action="store_true", help="Show planned runs")
    parser.add_argument("--limit", type=int, help="Run this many new single-seed jobs")
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    if len(SELECTION) != 5 or len({case_name(v) for v in SELECTION}) != 5:
        raise RuntimeError("Expected five unique parameter sets")

    tasks = [
        (values, mode, seed)
        for seed in SEEDS
        for values in SELECTION
        for mode in ENVIRONMENTS
    ]
    if len(tasks) != 100:
        raise RuntimeError(f"Expected 100 runs, got {len(tasks)}")
    if args.list:
        for values in SELECTION:
            print(case_name(values))
        print(f"Environments: {ENVIRONMENTS}, seeds: {SEEDS}, years: {YEARS}")
        print(f"Total: {len(tasks)} independent runs")
        return

    repo = Path(__file__).resolve().parent.parent
    root = repo / "results" / "experiments" / EXPERIMENT
    configs_dir = root / "_configs"
    logs_dir = root / "_run_logs"
    configs_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    runner = repo / "src" / "run_experiments.py"
    if not runner.is_file():
        raise RuntimeError(f"Cannot find experiment runner: {runner}")
    base = read_yaml(repo / "configs" / "default.yaml")
    summaries = root / "summary_per_seed.csv"
    records = read_records(summaries)

    # Fail early if earlier output uses settings other than those selected now.
    for values, mode, seed in tasks:
        cfg = make_run_config(base, values, mode, seed)
        check_older_snapshot(repo, values, mode, cfg)
        output = root / case_name(values) / mode / f"rep_{seed}"
        snapshot = output / "config_used.yaml"
        if snapshot.is_file() and read_yaml(snapshot) != cfg:
            raise RuntimeError(f"Config mismatch; existing experiment would be mixed: {snapshot}")

    new = 0
    skipped = 0
    for i, (values, mode, seed) in enumerate(tasks, start=1):
        case = case_name(values)
        key = f"{case}/{mode}/seed_{seed}"
        output = root / case / mode / f"rep_{seed}"
        log = output / f"seed_{seed}" / "log.csv"
        per_seed_summary = output / "summary.csv"
        if log.is_file() and per_seed_summary.is_file() and records.get(key, {}).get("status") == "complete":
            skipped += 1
            continue
        if log.is_file() and per_seed_summary.is_file():
            records[key] = summarize_log(log, values, mode, seed, float("nan"))
            write_csv(summaries, list(records.values()), ["run_id", *FIELDS])
            agg, fields = aggregate_records(records)
            write_csv(root / "summary_across_seeds.csv", agg, fields)
            skipped += 1
            continue
        if args.limit is not None and new >= args.limit:
            break

        cfg = make_run_config(base, values, mode, seed)
        cfg_path = configs_dir / f"{case}_{mode}_seed{seed}.yaml"
        with cfg_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)
        cmd = [
            sys.executable, str(runner), "--config", str(cfg_path),
            "--seeds", str(seed), "--experiment-name",
            f"{EXPERIMENT}/{case}/{mode}/rep_{seed}", "--no-plots",
        ]
        job_log = logs_dir / f"{case}_{mode}_seed{seed}.txt"
        print(f"[{i:03d}/100] RUN {key}", flush=True)
        start = time.monotonic()
        with job_log.open("w", encoding="utf-8") as out:
            proc = subprocess.run(
                cmd, cwd=repo, stdout=out, stderr=subprocess.STDOUT, check=False
            )
        elapsed = time.monotonic() - start
        if proc.returncode != 0:
            raise RuntimeError(f"Simulation failed: {key}. See {job_log}")
        if not log.is_file() or not per_seed_summary.is_file():
            raise RuntimeError(f"Missing output: {key}. See {job_log}")
        records[key] = summarize_log(log, values, mode, seed, elapsed)
        write_csv(summaries, list(records.values()), ["run_id", *FIELDS])
        agg, fields = aggregate_records(records)
        write_csv(root / "summary_across_seeds.csv", agg, fields)
        new += 1
        print(
            f"  DONE {elapsed:.1f}s | final_population={records[key]['final_population']} "
            f"| survived={records[key]['survived_5y']}",
            flush=True,
        )

    done = sum(
        records.get(f"{case_name(v)}/{m}/seed_{s}", {}).get("status") == "complete"
        for v, m, s in tasks
    )
    print(f"Completed: {done}/100 | New: {new} | Skipped: {skipped}")
    print(f"Per-seed summary: {summaries}")
    print(f"Across-seed summary: {root / 'summary_across_seeds.csv'}")
    print("Repeat the same command to resume unfinished jobs.")


if __name__ == "__main__":
    main()
