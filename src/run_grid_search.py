"""4-patch / one-year / seed-0, 4^4 parameter sweep for daphnia_evolution_sim.

Copy this file to <repo>/src/run_grid_search.py.
Run from the repository root:
  python src/run_grid_search.py --limit 2   # smoke test; existing cases resume automatically
  python src/run_grid_search.py             # run the rest

Does not change the base configs/default.yaml or simulation implementation.
"""
from __future__ import annotations

import argparse
import copy
import csv
import itertools
import math
import subprocess
import sys
import time
from pathlib import Path

import yaml


GRID = {
    "living_cost": [0.15, 0.30, 0.45, 0.60],
    "move_cost": [0.25, 0.50, 0.75, 1.00],
    "reproduction_threshold": [15, 20, 25, 30],
    "reproduction_cost": [6, 8, 10, 12],
}
BASELINE = (0.30, 0.50, 20, 10)
EXPERIMENT = "grid_patch4_1y_seed0"
PARAM_KEYS = tuple(GRID)
FIELDNAMES = [
    "case", *PARAM_KEYS, "seed", "status", "elapsed_sec", "steps_logged",
    "survived_year", "first_extinction_step", "final_population",
    "min_population", "max_population", "mean_population",
    "mean_population_last_100", "min_population_winter", "total_births",
    "total_deaths", "energy_deaths", "age_deaths", "energy_death_share",
    "age_death_share", "mean_energy", "mean_move_rate",
    "mean_eat_rate", "final_average_generation", "final_max_generation",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="1年×seed 0×4パッチの256条件グリッドサーチ")
    p.add_argument("--limit", type=int, default=None, help="今回新しく実行する条件数の上限（例: 2）")
    p.add_argument("--list", action="store_true", help="条件を一覧表示して終了（実行しない）")
    return p.parse_args()


def cases():
    values = list(itertools.product(*(GRID[k] for k in PARAM_KEYS)))
    # Inspect configurations near today's baseline first; every one of 256 remains included.
    values.sort(key=lambda v: (
        sum(((float(x) - float(b)) / (GRID[k][1] - GRID[k][0])) ** 2
            for k, x, b in zip(PARAM_KEYS, v, BASELINE)), v
    ))
    return values


def case_name(vals) -> str:
    a, b, c, d = vals
    fmt = lambda x: f"{x:.2f}".replace(".", "p")
    return f"L{fmt(a)}_M{fmt(b)}_T{int(c)}_C{int(d)}"


def make_config(original: dict, vals: tuple) -> dict:
    conf = copy.deepcopy(original)
    assert conf["environment"]["mode"] == "patch", "base config must use patch mode"
    assert conf["environment"]["patch_count"] == 4, "base config must use four patches"
    assert conf["seasonal_food"]["enabled"] is True, "seasonal food must be enabled"
    conf["simulation"]["duration_mode"] = "years"
    conf["simulation"]["duration_years"] = 1
    conf["simulation"]["random_seed"] = 0
    for key, value in zip(PARAM_KEYS, vals):
        conf["organism"][key] = value
    # Omit optional post-run analyses. Step logs, core simulation, and lineage data
    # are still produced. Gene exchange behavior itself is NOT changed.
    conf.setdefault("analysis", {}).setdefault("offspring_outcomes", {})["enabled"] = False
    conf.setdefault("analysis", {}).setdefault("gene_flow", {})["enabled"] = False
    return conf


def load_summary(path: Path) -> dict[str, dict]:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        return {row["case"]: row for row in csv.DictReader(f)}


def save_summary(path: Path, records: dict[str, dict]) -> None:
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        for row in records.values():
            writer.writerow(row)
    tmp.replace(path)


def compute_metrics(path: Path, case: str, vals, elapsed_sec: float) -> dict:
    """Aggregate *counts*, not a mean of per-step death proportions."""
    sums = {"birth_count": 0, "death_count": 0, "energy_death_count": 0,
            "age_death_count": 0, "population_size": 0.0, "average_energy": 0.0,
            "move_rate": 0.0, "total_eat_rate": 0.0}
    steps = 0
    first_extinct = ""
    min_pop = math.inf
    max_pop = -math.inf
    winter_min = math.inf
    last100 = []
    last = None

    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = set(sums) | {"step", "month", "average_generation", "max_generation"}
        if not required.issubset(reader.fieldnames or []):
            raise RuntimeError(f"Missing log columns: {sorted(required - set(reader.fieldnames or []))}")
        for row in reader:
            steps += 1
            last = row
            for name in sums:
                sums[name] += float(row[name])
            pop = int(float(row["population_size"]))
            min_pop = min(min_pop, pop)
            max_pop = max(max_pop, pop)
            if pop == 0 and first_extinct == "":
                first_extinct = int(float(row["step"]))
            if int(float(row["month"])) in (12, 1, 2):
                winter_min = min(winter_min, pop)
            last100.append(pop)
            if len(last100) > 100:
                last100.pop(0)

    if steps == 0 or last is None:
        raise RuntimeError(f"Empty simulation log: {path}")
    if steps != 3650:
        raise RuntimeError(f"Expected 3650 steps, got {steps} ({path})")
    deaths = sums["energy_death_count"] + sums["age_death_count"]
    a, b, c, d = vals
    return {
        "case": case,
        "living_cost": a, "move_cost": b,
        "reproduction_threshold": c, "reproduction_cost": d,
        "seed": 0, "status": "complete", "elapsed_sec": round(elapsed_sec, 2),
        "steps_logged": steps,
        "survived_year": int(first_extinct == "" and int(float(last["population_size"])) > 0),
        "first_extinction_step": first_extinct,
        "final_population": int(float(last["population_size"])),
        "min_population": int(min_pop), "max_population": int(max_pop),
        "mean_population": round(sums["population_size"] / steps, 5),
        "mean_population_last_100": round(sum(last100) / len(last100), 5),
        "min_population_winter": "" if math.isinf(winter_min) else int(winter_min),
        "total_births": int(sums["birth_count"]),
        "total_deaths": int(sums["death_count"]),
        "energy_deaths": int(sums["energy_death_count"]),
        "age_deaths": int(sums["age_death_count"]),
        "energy_death_share": "" if deaths == 0 else round(sums["energy_death_count"] / deaths, 6),
        "age_death_share": "" if deaths == 0 else round(sums["age_death_count"] / deaths, 6),
        "mean_energy": round(sums["average_energy"] / steps, 6),
        "mean_move_rate": round(sums["move_rate"] / steps, 6),
        "mean_eat_rate": round(sums["total_eat_rate"] / steps, 6),
        "final_average_generation": float(last["average_generation"]),
        "final_max_generation": int(float(last["max_generation"])),
    }


def main() -> None:
    args = parse_args()
    if args.limit is not None and args.limit <= 0:
        raise SystemExit("--limit must be a positive integer")
    repo_root = Path(__file__).resolve().parent.parent
    runner = repo_root / "src" / "run_experiments.py"
    base_path = repo_root / "configs" / "default.yaml"
    if not runner.is_file() or not base_path.is_file():
        raise SystemExit("Place run_grid_search.py in the repository's src/ directory")
    with base_path.open(encoding="utf-8") as f:
        base = yaml.safe_load(f)
    root = repo_root / "results" / "experiments" / EXPERIMENT
    configs_dir = root / "_configs"
    logs_dir = root / "_run_logs"
    root.mkdir(parents=True, exist_ok=True)
    configs_dir.mkdir(exist_ok=True)
    logs_dir.mkdir(exist_ok=True)
    summary_file = root / "grid_summary.csv"
    records = load_summary(summary_file)

    all_cases = cases()
    print(f"{len(all_cases)} conditions; 4 patches, seasonal food, 1 year, seed 0", flush=True)
    count_new = 0
    count_skipped = 0
    for idx, vals in enumerate(all_cases, start=1):
        name = case_name(vals)
        if args.list:
            print(f"{idx:03d}: {name}")
            continue
        cfg = make_config(base, vals)
        exp_dir = root / name
        exp_config_path = exp_dir / "config_used.yaml"
        if exp_config_path.exists():
            with exp_config_path.open(encoding="utf-8") as f:
                previous = yaml.safe_load(f)
            if previous != cfg:
                raise RuntimeError(f"Config mismatch for {name}; do not mix changed baselines in one sweep")
        log_path = exp_dir / "seed_0" / "log.csv"
        summary_path = exp_dir / "summary.csv"
        if log_path.exists() and summary_path.exists():
            if name not in records or records[name].get("status") != "complete":
                records[name] = compute_metrics(log_path, name, vals, float("nan"))
                save_summary(summary_file, records)
            count_skipped += 1
            continue
        if args.limit is not None and count_new >= args.limit:
            break
        cfg_path = configs_dir / f"{name}.yaml"
        with cfg_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)
        cmd = [sys.executable, str(runner), "--config", str(cfg_path),
               "--seeds", "0", "--experiment-name", f"{EXPERIMENT}/{name}", "--no-plots"]
        print(f"[{idx:03d}/{len(all_cases)}] RUN {name}", flush=True)
        start = time.monotonic()
        with (logs_dir / f"{name}.txt").open("w", encoding="utf-8") as out:
            result = subprocess.run(cmd, cwd=repo_root, stdout=out, stderr=subprocess.STDOUT, check=False)
        elapsed = time.monotonic() - start
        if result.returncode != 0:
            raise RuntimeError(f"Simulation failed: {name}. Check {logs_dir / (name + '.txt')}")
        if not log_path.exists() or not summary_path.exists():
            raise RuntimeError(f"Missing expected outputs for {name}; see {logs_dir}")
        records[name] = compute_metrics(log_path, name, vals, elapsed)
        save_summary(summary_file, records)
        count_new += 1
        print(f"  DONE in {elapsed:.1f}s, population={records[name]['final_population']}, survived={records[name]['survived_year']}", flush=True)

    if not args.list:
        done = sum(row.get("status") == "complete" for row in records.values())
        print(f"Completed: {done}/256  |  New: {count_new}  |  Skipped: {count_skipped}")
        print(f"Summary: {summary_file}")
        print("Re-run the same command to continue remaining conditions.")


if __name__ == "__main__":
    main()
