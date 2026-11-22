"""9-case energy pilot: offspring energy x food energy (3, 5, 7).

Both 4-patch and random seasonal food environments; one year, seed 0.
The base 4 energy-related organism parameters are fixed to L=.30 M=1.00
T=20 C=10, matching one of the already tested 20 configurations.

From the repository root:
    python src/run_grid_energy9.py --list
    python src/run_grid_energy9.py --limit 2
    python src/run_grid_energy9.py
    python src/run_grid_energy9.py --only-f4 --list # O5/F4 only, no run
    python src/run_grid_energy9.py --only-f4        # 2 extra runs

All original result directories and configs/default.yaml remain untouched.
Only complete output is skipped on restart. For each run, raw log.csv and
lineage.csv are retained, and summary tables are updated immediately.
"""
from __future__ import annotations

import argparse
import csv
import itertools
import math
import subprocess
import sys
import time
from pathlib import Path

import yaml

try:
    from src.analyze_lineage_life_history import METRICS as LIFE_METRICS
    from src.analyze_lineage_life_history import analyze as analyze_lineage
    from src.run_grid_search import FIELDNAMES as GRID_FIELDS
    from src.run_grid_search import case_name, compute_metrics, make_config
except ImportError:
    from analyze_lineage_life_history import METRICS as LIFE_METRICS
    from analyze_lineage_life_history import analyze as analyze_lineage
    from run_grid_search import FIELDNAMES as GRID_FIELDS
    from run_grid_search import case_name, compute_metrics, make_config

EXPERIMENT = "grid_energy9_1y_seed0"
BASE_PARAMS = (0.30, 1.00, 20, 10)
ENERGIES = (3, 5, 7)
EXTRA_CONDITION = (5, 4)  # optional targeted follow-up, not part of original 3x3
ENVIRONMENTS = ("patch", "random")
SEED = 0
EXPECTED_STEPS = 3650

SUMMARY_FIELDS = [
    "case", "environment", "offspring_energy", "food_energy",
    *[name for name in GRID_FIELDS if name != "case"],
    *LIFE_METRICS,
]

PAIR_METRICS = (
    "final_population", "mean_population", "min_population_winter",
    "total_births", "total_deaths", "energy_death_share",
    "final_average_generation", "elapsed_sec",
    "distinct_reproductive_parents",
    "first_reproduction_median_days",
    "first_reproduction_mean_days",
    "first_reproduction_before_6d_frac",
    "first_reproduction_6_to_12d_frac",
    "first_reproduction_over_12d_frac",
)
PAIRED_FIELDS = [
    "case", "offspring_energy", "food_energy",
    *(f"{env}_{metric}" for metric in PAIR_METRICS for env in ENVIRONMENTS),
]


def case_name_energy(offspring: int, food: int) -> str:
    return f"O{offspring}_F{food}"


def conditions() -> list[tuple[int, int]]:
    # Begin with the unchanged 5/5 setting, so --limit 2 checks both modes.
    pairs = list(itertools.product(ENERGIES, repeat=2))
    return [(5, 5), *(pair for pair in pairs if pair != (5, 5))]


def tasks(only_f4: bool = False) -> list[tuple[int, int, str]]:
    pairs = [EXTRA_CONDITION] if only_f4 else conditions()
    return [(o, f, env) for o, f in pairs for env in ENVIRONMENTS]


def output_conditions() -> list[tuple[int, int]]:
    """Always preserve any optional O5/F4 results in shared CSV summaries."""
    return [*conditions(), EXTRA_CONDITION]


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def make_energy_config(base: dict, offspring: int, food: int, env: str) -> dict:
    if offspring not in ENERGIES or (
        food not in ENERGIES and (offspring, food) != EXTRA_CONDITION
    ):
        raise ValueError("Only the 3x3 grid and O5/F4 follow-up are supported")
    if env not in ENVIRONMENTS:
        raise ValueError("Unsupported environment")
    # Keep the same settings used for the two historical one-year grids.
    cfg = make_config(base, BASE_PARAMS)
    cfg["organism"]["offspring_energy"] = offspring
    cfg["environment"]["food_energy"] = food
    cfg["environment"]["mode"] = env
    if (cfg["simulation"]["days_per_year"] * cfg["simulation"]["steps_per_day"]
            != EXPECTED_STEPS):
        raise RuntimeError("Expected a 3650-step year (365 days x 10 steps)")
    return cfg


def check_old_baseline(repo: Path, configs: dict[str, dict]) -> None:
    """If previous baseline snapshots exist, compare the whole YAML tree."""
    baseline = case_name(BASE_PARAMS)
    historical = {
        "patch": "grid_patch4_1y_seed0",
        "random": "grid_random20_1y_seed0",
    }
    for env, folder in historical.items():
        snapshot = (
            repo / "results" / "experiments" / folder
            / baseline / "config_used.yaml"
        )
        if not snapshot.is_file():
            print(f"NOTE: historical snapshot not found: {snapshot}", flush=True)
            continue
        if load_yaml(snapshot) != configs[env]:
            raise RuntimeError(
                f"Existing {env} experiment differs from new 5/5 config: "
                f"{snapshot}. Do not mix results with changed settings."
            )


def read_summary(path: Path) -> dict[tuple[str, str], dict]:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        return {
            (row["case"], row["environment"]): row
            for row in csv.DictReader(f)
        }


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def save_comparisons(root: Path, records: dict[tuple[str, str], dict]) -> None:
    # Includes O5/F4 whenever present, even after a later normal 3x3 rerun.
    rows = [
        records[(case_name_energy(o, f), env)]
        for o, f in output_conditions() for env in ENVIRONMENTS
        if (case_name_energy(o, f), env) in records
    ]
    write_csv(root / "grid_summary.csv", rows, SUMMARY_FIELDS)

    paired = []
    for o, f in output_conditions():
        case = case_name_energy(o, f)
        if not all((case, mode) in records for mode in ENVIRONMENTS):
            continue
        pair = {"case": case, "offspring_energy": o, "food_energy": f}
        for metric in PAIR_METRICS:
            for env in ENVIRONMENTS:
                pair[f"{env}_{metric}"] = records[(case, env)].get(metric, "")
        paired.append(pair)
    write_csv(root / "grid_paired_comparison.csv", paired, PAIRED_FIELDS)


def summarize(
    log: Path, lineage: Path, case: str,
    offspring: int, food: int, env: str, elapsed: float
) -> dict:
    if not lineage.is_file():
        raise FileNotFoundError(f"Missing lineage.csv: {lineage}")
    # Existing one-year summary computes population, generations, mortality.
    grid = compute_metrics(log, case, BASE_PARAMS, elapsed)
    if math.isnan(elapsed):
        grid["elapsed_sec"] = ""  # unavailable for reconstructed old jobs
    # Independently compute first reproduction age from parent/offspring IDs.
    life = analyze_lineage(lineage, steps_per_day=10)
    if life["unresolved_parent_rows"] != 0:
        raise RuntimeError("Unresolved parent IDs; cannot compare life histories")
    return {
        "case": case, "environment": env,
        "offspring_energy": offspring, "food_energy": food,
        **grid, **life,
    }


def output_paths(root: Path, case: str, env: str) -> tuple[Path, Path, Path, Path]:
    directory = root / case / env
    return (
        directory / "config_used.yaml",
        directory / "seed_0" / "log.csv",
        directory / "seed_0" / "lineage.csv",
        directory / "summary.csv",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Offspring (3,5,7) x food (3,5,7) x patch/random x 1y seed0"
    )
    parser.add_argument("--list", action="store_true", help="Print runs, no simulation")
    parser.add_argument("--limit", type=int, help="Run at most N new simulations")
    parser.add_argument(
        "--only-f4", action="store_true",
        help="Run only O5/F4 (two environments), append to existing 18 results",
    )
    args = parser.parse_args()
    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be positive")

    jobs = tasks(only_f4=args.only_f4)
    expected_jobs = 2 if args.only_f4 else 18
    if len(jobs) != expected_jobs or len(set(jobs)) != expected_jobs:
        raise RuntimeError(f"Expected {expected_jobs} distinct runs")

    if args.list:
        for index, (offspring, food, env) in enumerate(jobs, 1):
            print(
                f"{index:02d}/{expected_jobs}: {case_name_energy(offspring, food)} "
                f"{env} | offspring={offspring}, food={food}, seed=0, 1 year"
            )
        return

    repo = Path(__file__).resolve().parent.parent
    run_script = repo / "src" / "run_experiments.py"
    if not run_script.is_file():
        raise FileNotFoundError(run_script)
    base = load_yaml(repo / "configs" / "default.yaml")
    baseline_by_env = {
        env: make_energy_config(base, 5, 5, env)
        for env in ENVIRONMENTS
    }
    check_old_baseline(repo, baseline_by_env)
    root = repo / "results" / "experiments" / EXPERIMENT
    configs_dir = root / "_configs"
    logs_dir = root / "_run_logs"
    configs_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    summary_path = root / "grid_summary.csv"
    records = read_summary(summary_path)

    # Preflight all snapshots before running anything.
    for offspring, food, env in jobs:
        case = case_name_energy(offspring, food)
        snapshot, log, lineage, existing_summary = output_paths(root, case, env)
        cfg = make_energy_config(base, offspring, food, env)
        if snapshot.is_file():
            if load_yaml(snapshot) != cfg:
                raise RuntimeError(
                    f"Config mismatch: {snapshot}; refusing to mix experiments"
                )
        elif log.is_file() or lineage.is_file() or existing_summary.is_file():
            raise RuntimeError(
                f"Outputs exist without config snapshot at {snapshot}. "
                "Move the incomplete folder aside and inspect before retrying."
            )

    new_runs = 0
    skipped = 0
    for index, (offspring, food, env) in enumerate(jobs, 1):
        case = case_name_energy(offspring, food)
        key = case, env
        snapshot, log, lineage, per_case_summary = output_paths(root, case, env)
        existing = records.get(key)
        finished_files = log.is_file() and lineage.is_file() and per_case_summary.is_file()
        if (finished_files and existing is not None
                and existing.get("status") == "complete"
                and existing.get("first_reproduction_6_to_12d_frac", "") != ""
                and int(existing.get("steps_logged", "0")) == EXPECTED_STEPS):
            skipped += 1
            continue

        if finished_files:
            # This covers interruption after the subprocess finished but
            # before the combined summary CSV was written.
            old_elapsed = (
                float(existing["elapsed_sec"])
                if existing and existing.get("elapsed_sec") not in ("", "nan", None)
                else math.nan
            )
            records[key] = summarize(
                log, lineage, case, offspring, food, env, old_elapsed
            )
            save_comparisons(root, records)
            skipped += 1
            print(f"[{index:02d}/{expected_jobs}] Rebuilt summary: {case}/{env}", flush=True)
            continue

        if args.limit is not None and new_runs >= args.limit:
            break

        config = make_energy_config(base, offspring, food, env)
        cfg_path = configs_dir / f"{case}_{env}.yaml"
        with cfg_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False)
        cmd = [
            sys.executable, str(run_script), "--config", str(cfg_path),
            "--seeds", str(SEED),
            "--experiment-name", f"{EXPERIMENT}/{case}/{env}",
            "--no-plots",
        ]
        job_log = logs_dir / f"{case}_{env}.txt"
        print(f"[{index:02d}/{expected_jobs}] RUN {case}/{env}", flush=True)
        began = time.monotonic()
        with job_log.open("w", encoding="utf-8") as handle:
            proc = subprocess.run(
                cmd, cwd=repo, stdout=handle, stderr=subprocess.STDOUT,
                check=False,
            )
        elapsed = time.monotonic() - began
        if proc.returncode != 0:
            raise RuntimeError(
                f"Simulation failed: {case}/{env}. Check {job_log}"
            )
        if not (log.is_file() and lineage.is_file() and per_case_summary.is_file()):
            raise RuntimeError(
                f"Expected CSV outputs missing: {case}/{env}. Check {job_log}"
            )
        records[key] = summarize(
            log, lineage, case, offspring, food, env, elapsed
        )
        save_comparisons(root, records)
        new_runs += 1
        rec = records[key]
        ratio = rec["first_reproduction_6_to_12d_frac"]
        ratio_label = f"{float(ratio)*100:.1f}%" if ratio != "" else "N/A"
        print(
            f"  DONE {elapsed:.1f}s | population={rec['final_population']} | "
            f"first-repro median={rec['first_reproduction_median_days']}d | "
            f"6-12d={ratio_label}",
            flush=True,
        )

    done = sum(
        (case_name_energy(o, f), env) in records
        and records[(case_name_energy(o, f), env)].get("status") == "complete"
        for o, f, env in jobs
    )
    print(
        f"Completed {done}/{expected_jobs} for requested task set | "
        f"New simulations: {new_runs} | Skipped: {skipped}"
    )
    print(f"Summary: {root / 'grid_summary.csv'}")
    print(f"Paired comparison: {root / 'grid_paired_comparison.csv'}")
    print("Re-run the command to resume unfinished cases.")


if __name__ == "__main__":
    main()
