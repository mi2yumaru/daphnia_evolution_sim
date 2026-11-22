"""Run 12 calibrated ecological conditions in two environments for 5 years x 10 seeds.

From the repository root (Windows PowerShell or shell):
    python src/run_grid_long12.py --list
    python src/run_grid_long12.py --limit 2
    python src/run_grid_long12.py

Every (condition, environment, seed) runs independently so completed
simulations can be skipped after interruption. Old 1-year grid outputs,
configs/default.yaml, and prior 5-year experiment directories are untouched.

Gene exchange remains enabled/evolvable as in the base calibration config.
CSV logs, per-seed lineage, life-history and across-seed mean/std are retained.
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

try:
    from src.run_grid_search import case_name, make_config
    from src.analyze_lineage_life_history import METRICS as LIFE_METRICS
    from src.analyze_lineage_life_history import analyze as analyze_lineage
except ImportError:
    from run_grid_search import case_name, make_config
    from analyze_lineage_life_history import METRICS as LIFE_METRICS
    from analyze_lineage_life_history import analyze as analyze_lineage

EXPERIMENT = "grid12_5y_10seeds"
SELECTION = (
    (0.30, 0.50, 20, 10),  # 01 original baseline
    (0.30, 0.75, 20, 10),  # 02 moderate movement cost
    (0.30, 1.00, 20, 10),  # 03 strongest balanced 1-year candidate
    (0.45, 0.50, 20, 10),  # 04 raised living cost
    (0.45, 0.75, 20, 10),  # 05 intermediate ecological costs
    (0.45, 1.00, 20, 10),  # 06 both ecological costs raised
    (0.60, 0.75, 20, 10),  # 07 high energy pressure
    (0.60, 1.00, 20, 10),  # 08 harsh ecological stress control
    (0.15, 1.00, 20, 10),  # 09 low living cost
    (0.15, 1.00, 15, 10),  # 10 low living cost + low threshold
    (0.30, 1.00, 15, 10),  # 11 lower reproduction threshold
    (0.30, 1.00, 25, 10),  # 12 higher reproduction threshold
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
    *(f"year_{year}_min_population" for year in range(1, YEARS + 1)),
    *(f"year_{year}_winter_min_population" for year in range(1, YEARS + 1)),
    *LIFE_METRICS,
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
    year_min_population = [math.inf] * YEARS
    year_winter_min_population = [math.inf] * YEARS
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
            year_min_population[year] = min(year_min_population[year], pop)
            if "month" in row and int(float(row["month"])) in (12, 1, 2):
                year_winter_min_population[year] = min(
                    year_winter_min_population[year], pop
                )
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
        **{
            f"year_{i + 1}_min_population": val
            for i, val in enumerate(year_min_population)
        },
        **{
            f"year_{i + 1}_winter_min_population":
                ("" if math.isinf(val) else val)
            for i, val in enumerate(year_winter_min_population)
        },
    }


def summarize_run(
    log: Path, lineage: Path, values: tuple, mode: str, seed: int,
    elapsed: float
) -> dict:
    if not lineage.is_file():
        raise FileNotFoundError(f"Missing lineage.csv for {mode}, seed={seed}: {lineage}")
    row = summarize_log(log, values, mode, seed, elapsed)
    life = analyze_lineage(lineage, steps_per_day=10)
    if life["unresolved_parent_rows"] != 0:
        raise ValueError(f"Unresolved parent IDs in {lineage}")
    return {**row, **life}


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


def build_tasks(seeds: tuple[int, ...] = SEEDS) -> list[tuple[tuple, str, int]]:
    # Seed-first ordering: --limit 2 checks both environments for first case.
    return [
        (values, mode, seed)
        for seed in seeds for values in SELECTION for mode in ENVIRONMENTS
    ]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="12 conditions x 2 environments x 10 seeds x 5 years"
    )
    parser.add_argument("--list", action="store_true", help="Show planned runs")
    parser.add_argument("--limit", type=int, help="Run at most N new single-seed jobs")
    parser.add_argument(
        "--seeds", nargs="+", type=int, default=list(SEEDS),
        help="Optional selected seed IDs (0-9); defaults to all 10",
    )
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    if not args.seeds or len(set(args.seeds)) != len(args.seeds):
        parser.error("--seeds must be a nonempty unique set")
    if any(seed not in SEEDS for seed in args.seeds):
        parser.error("--seeds must be in 0 through 9")
    if len(SELECTION) != 12 or len({case_name(v) for v in SELECTION}) != 12:
        raise RuntimeError("Expected twelve unique parameter sets")
    if any(v[3] != 10 for v in SELECTION):
        raise RuntimeError("Reproduction cost must remain 10 for all cases")

    seeds = tuple(args.seeds)
    tasks = build_tasks(seeds)
    total = len(tasks)
    if total != len(SELECTION) * len(ENVIRONMENTS) * len(seeds):
        raise RuntimeError("Unexpected duplicate or missing tasks")
    if args.list:
        for values in SELECTION:
            print(case_name(values))
        print(f"Environments: {ENVIRONMENTS}, seeds: {seeds}, years: {YEARS}")
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
        if snapshot.is_file():
            if read_yaml(snapshot) != cfg:
                raise RuntimeError(
                    f"Config mismatch; experiment settings differ: {snapshot}"
                )
        elif any((output / f"seed_{seed}" / name).is_file()
                 for name in ("log.csv", "lineage.csv")):
            raise RuntimeError(
                f"Untracked output found without config snapshot: {output}"
            )

    new = 0
    skipped = 0
    for i, (values, mode, seed) in enumerate(tasks, start=1):
        case = case_name(values)
        key = f"{case}/{mode}/seed_{seed}"
        output = root / case / mode / f"rep_{seed}"
        log = output / f"seed_{seed}" / "log.csv"
        lineage = output / f"seed_{seed}" / "lineage.csv"
        per_seed_summary = output / "summary.csv"
        finished = (
            log.is_file() and lineage.is_file() and per_seed_summary.is_file()
        )
        old = records.get(key, {})
        # An extinct population may have zero reproductive parents, in which
        # case age-fraction fields are legitimately blank; the parent-resolution
        # counter is populated for every successfully analyzed lineage.
        has_life_metrics = old.get("unresolved_parent_rows", "") != ""
        if (finished and old.get("status") == "complete"
                and int(old.get("steps_logged", "0")) == TOTAL_STEPS
                and has_life_metrics):
            skipped += 1
            continue
        if finished:
            # Crash after run complete but before summary save: recalculate.
            records[key] = summarize_run(
                log, lineage, values, mode, seed, float("nan")
            )
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
        print(f"[{i:03d}/{total}] RUN {key}", flush=True)
        start = time.monotonic()
        with job_log.open("w", encoding="utf-8") as out:
            proc = subprocess.run(
                cmd, cwd=repo, stdout=out, stderr=subprocess.STDOUT, check=False
            )
        elapsed = time.monotonic() - start
        if proc.returncode != 0:
            raise RuntimeError(f"Simulation failed: {key}. See {job_log}")
        if not (log.is_file() and lineage.is_file() and per_seed_summary.is_file()):
            raise RuntimeError(f"Missing output: {key}. See {job_log}")
        records[key] = summarize_run(
            log, lineage, values, mode, seed, elapsed
        )
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
    print(f"Completed: {done}/{total} | New: {new} | Skipped: {skipped}")
    print(f"Per-seed summary: {summaries}")
    print(f"Across-seed summary: {root / 'summary_across_seeds.csv'}")
    print("Repeat the same command to resume unfinished jobs.")
    print("All per-seed logs/lineages are preserved under each rep_N/seed_N folder.")


if __name__ == "__main__":
    main()
