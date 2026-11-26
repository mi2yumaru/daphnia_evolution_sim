"""Main experiment: 2 food layouts x 2 seasonal modes x 5 exchange modes x 10 seeds.

Run:
  python src/run_main_experiment.py --list
  python src/run_main_experiment.py --limit 2
  python src/run_main_experiment.py

Each run uses its own configuration snapshot and output directory.
Repeated execution skips verified, completed runs. Incomplete runs are
rerun in their own directory; historical experiments are not modified.
"""
from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = "main_experiment_20"
SPATIAL = ("random", "patch4")
SEASONAL = (False, True)
EXCHANGE = (
    "none",
    "fixed_100_50",
    "fixed_50_25",
    "evolvable_zero",
    "evolvable_random",
)
SEEDS = tuple(range(10))
YEARS = 5
EXPECTED_STEPS = YEARS * 365 * 10


def build_config(base: dict, spatial: str, seasonal: bool, exchange: str, seed: int) -> dict:
    if spatial not in SPATIAL or seasonal not in SEASONAL or exchange not in EXCHANGE:
        raise ValueError("Unsupported main-experiment condition")
    if seed not in SEEDS:
        raise ValueError("Seed must be 0..9")
    cfg = deepcopy(base)
    cfg["simulation"]["duration_mode"] = "years"
    cfg["simulation"]["duration_years"] = YEARS
    cfg["simulation"]["random_seed"] = seed
    cfg["environment"]["mode"] = "random" if spatial == "random" else "patch"
    cfg["environment"]["periodic_boundary"] = True
    cfg["environment"]["food_respawn_rate"] = 0.02
    cfg["seasonal_food"]["enabled"] = seasonal
    cfg["seasonal_food"]["csv_path"] = "data/kasumigaura_sta9_food_respawn_365_mean002.csv"
    cfg["organism"]["initial_placement_mode"] = "uniform"
    cfg["organism"]["paired_initialization"] = True
    cfg["gene_exchange"]["initial_trait_mode"] = "zero" if exchange == "evolvable_zero" else "random"
    if exchange == "none":
        cfg["gene_exchange"].update(enabled=False, mode="fixed", probability=0.0, fraction=0.0)
    elif exchange == "fixed_100_50":
        cfg["gene_exchange"].update(enabled=True, mode="fixed", probability=1.0, fraction=0.5)
    elif exchange == "fixed_50_25":
        cfg["gene_exchange"].update(enabled=True, mode="fixed", probability=0.5, fraction=0.25)
    else:
        cfg["gene_exchange"].update(enabled=True, mode="evolvable")
    cfg.setdefault("analysis", {}).setdefault("offspring_outcomes", {})["enabled"] = True
    cfg.setdefault("analysis", {}).setdefault("gene_flow", {})["enabled"] = True
    if cfg["simulation"]["steps_per_day"] != 10 or cfg["simulation"]["days_per_year"] != 365:
        raise ValueError("Expected 10 steps/day and 365 days/year")
    return cfg


def conditions():
    return [
        (spatial, seasonal, exchange)
        for spatial in SPATIAL for seasonal in SEASONAL for exchange in EXCHANGE
    ]


def run_name(spatial: str, seasonal: bool, exchange: str) -> str:
    return f"{spatial}/{'seasonal' if seasonal else 'constant'}/{exchange}"


def csv_rows(path: Path) -> int:
    with path.open(encoding="utf-8-sig", newline="") as fp:
        return sum(1 for _ in csv.DictReader(fp))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run 20 main-experiment conditions, 10 seeds, 5 years")
    parser.add_argument("--list", action="store_true", help="Print conditions without running")
    parser.add_argument("--limit", type=int, default=None, help="Run at most N new jobs")
    parser.add_argument("--seeds", nargs="+", type=int, default=list(SEEDS))
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    if len(set(args.seeds)) != len(args.seeds) or not args.seeds or any(s not in SEEDS for s in args.seeds):
        parser.error("Seeds must be unique integers between 0 and 9")
    tasks = [(sp, season, ex, seed) for sp, season, ex in conditions() for seed in args.seeds]
    if args.list:
        for sp, season, ex in conditions():
            print(run_name(sp, season, ex))
        print(f"Total: {len(conditions())} conditions x {len(args.seeds)} seeds = {len(tasks)} runs")
        return

    with (ROOT / "configs/default.yaml").open(encoding="utf-8") as fp:
        base = yaml.safe_load(fp)
    result_root = ROOT / "results/experiments" / EXPERIMENT

    # Validate every saved config before launching any new simulation.
    for sp, season, ex, seed in tasks:
        cfg = build_config(base, sp, season, ex, seed)
        folder = result_root / run_name(sp, season, ex) / f"seed_{seed}"
        snapshot = folder / "config_used.yaml"
        if snapshot.exists():
            with snapshot.open(encoding="utf-8") as fp:
                old = yaml.safe_load(fp)
            if old != cfg:
                raise RuntimeError(f"Config mismatch: {snapshot}")
        elif (folder / f"seed_{seed}/log.csv").exists():
            raise RuntimeError(f"Output without config snapshot: {folder}")

    started = 0
    skipped = 0
    for sp, season, ex, seed in tasks:
        cfg = build_config(base, sp, season, ex, seed)
        name = run_name(sp, season, ex)
        folder = result_root / name / f"seed_{seed}"
        log = folder / f"seed_{seed}" / "log.csv"
        lineage = folder / f"seed_{seed}" / "lineage.csv"
        summary = folder / "summary.csv"
        final_year = folder / "summary_last_year_across_seeds.csv"
        if all(f.is_file() for f in (log, lineage, summary, final_year)) and csv_rows(log) == EXPECTED_STEPS:
            skipped += 1
            continue
        if args.limit is not None and started >= args.limit:
            break
        folder.mkdir(parents=True, exist_ok=True)
        snapshot = folder / "config_used.yaml"
        with snapshot.open("w", encoding="utf-8") as fp:
            yaml.safe_dump(cfg, fp, allow_unicode=True, sort_keys=False)
        config_path = folder / "run_config.yaml"
        with config_path.open("w", encoding="utf-8") as fp:
            yaml.safe_dump(cfg, fp, allow_unicode=True, sort_keys=False)
        command = [
            sys.executable, str(ROOT / "src/run_experiments.py"),
            "--config", str(config_path),
            "--seeds", str(seed),
            "--experiment-name", f"{EXPERIMENT}/{name}/seed_{seed}",
            "--no-plots",
        ]
        print(f"RUN {name}, seed={seed}", flush=True)
        with (folder / "run_output.txt").open("w", encoding="utf-8") as fp:
            process = subprocess.run(command, cwd=ROOT, stdout=fp, stderr=subprocess.STDOUT, check=False)
        if process.returncode:
            raise RuntimeError(f"Run failed ({name}, seed={seed}); see {folder / 'run_output.txt'}")
        if not all(f.is_file() for f in (log, lineage, summary, final_year)) or csv_rows(log) != EXPECTED_STEPS:
            raise RuntimeError(f"Incomplete output: {folder}")
        started += 1
    print(f"New runs: {started}; skipped completed: {skipped}; total selected: {len(tasks)}")


if __name__ == "__main__":
    main()
