"""Run 20 selected parameter conditions in random food environment, 1 year, seed 0.

Preserves the original 4-patch sweep and uses the same config except environment.mode.
Run from repository root:
    python src/run_grid_random20.py --list
    python src/run_grid_random20.py --limit 2
    python src/run_grid_random20.py
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

import yaml

from run_grid_search import (
    case_name,
    compute_metrics,
    load_summary,
    make_config,
    save_summary,
)

EXPERIMENT = "grid_random20_1y_seed0"
PATCH_EXPERIMENT = "grid_patch4_1y_seed0"
# (living_cost, move_cost, reproduction_threshold, reproduction_cost)
SELECTED = [
    (0.30, 0.50, 20, 10),  #  1: baseline
    (0.15, 0.50, 20, 10),  #  2: living cost
    (0.45, 0.50, 20, 10),  #  3
    (0.60, 0.50, 20, 10),  #  4
    (0.30, 0.25, 20, 10),  #  5: moving cost
    (0.30, 0.75, 20, 10),  #  6
    (0.30, 1.00, 20, 10),  #  7
    (0.30, 0.50, 15, 10),  #  8: reproduction threshold
    (0.30, 0.50, 25, 10),  #  9
    (0.30, 0.50, 30, 10),  # 10
    (0.30, 0.50, 20,  6),  # 11: reproduction cost
    (0.30, 0.50, 20,  8),  # 12
    (0.30, 0.50, 20, 12),  # 13
    (0.15, 0.25, 20, 10),  # 14: living × moving cost
    (0.15, 1.00, 20, 10),  # 15
    (0.60, 0.25, 20, 10),  # 16
    (0.60, 1.00, 20, 10),  # 17
    (0.30, 0.50, 15,  6),  # 18: threshold × reproduction cost
    (0.30, 0.50, 30, 12),  # 19
    (0.60, 1.00, 30, 12),  # 20: most costly corner
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="20 cases, random food, seasonal variation, 1 year, seed 0"
    )
    parser.add_argument("--list", action="store_true", help="List cases without running")
    parser.add_argument("--limit", type=int, help="Run at most this many new cases")
    args = parser.parse_args()
    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be positive")
    if len(SELECTED) != 20 or len({case_name(v) for v in SELECTED}) != 20:
        raise RuntimeError("The 20 selected cases are missing or duplicated")

    if args.list:
        for i, vals in enumerate(SELECTED, 1):
            print(f"{i:02d}: {case_name(vals)}")
        return

    repo = Path(__file__).resolve().parent.parent
    runner = repo / "src" / "run_experiments.py"
    base_path = repo / "configs" / "default.yaml"
    if not runner.is_file() or not base_path.is_file():
        raise SystemExit("Run from a checkout with src/run_experiments.py and configs/default.yaml")
    with base_path.open(encoding="utf-8") as f:
        base_config = yaml.safe_load(f)

    root = repo / "results" / "experiments" / EXPERIMENT
    config_dir = root / "_configs"
    logs_dir = root / "_run_logs"
    config_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    summary_path = root / "grid_summary.csv"
    records = load_summary(summary_path)

    print(f"{len(SELECTED)} conditions; random food, seasonal variation, 1 year, seed 0", flush=True)
    new_count = 0
    skipped_count = 0

    for i, vals in enumerate(SELECTED, 1):
        name = case_name(vals)
        # Reuse the exact parameter assignment and analysis settings from the
        # existing 4-patch grid search, changing ONLY the food spatial mode.
        cfg = make_config(base_config, vals)
        cfg["environment"]["mode"] = "random"

        # If the original 4-patch snapshot is available, fail rather than
        # silently compare experiments with additional changed settings.
        patch_snapshot = repo / "results" / "experiments" / PATCH_EXPERIMENT / name / "config_used.yaml"
        if patch_snapshot.is_file():
            with patch_snapshot.open(encoding="utf-8") as f:
                original = yaml.safe_load(f)
            original["environment"]["mode"] = "random"
            if original != cfg:
                raise RuntimeError(
                    f"Configuration differs from the old 4-patch experiment: {name}. "
                    "Restore the original baseline before comparing environments."
                )

        case_dir = root / name
        snapshot = case_dir / "config_used.yaml"
        if snapshot.is_file():
            with snapshot.open(encoding="utf-8") as f:
                previous = yaml.safe_load(f)
            if previous != cfg:
                raise RuntimeError(f"Config mismatch for {name}; refusing to mix results")

        log_path = case_dir / "seed_0" / "log.csv"
        per_case_summary = case_dir / "summary.csv"
        if log_path.is_file() and per_case_summary.is_file():
            if name not in records or records[name].get("status") != "complete":
                records[name] = compute_metrics(log_path, name, vals, float("nan"))
                save_summary(summary_path, records)
            skipped_count += 1
            continue

        if args.limit is not None and new_count >= args.limit:
            break

        cfg_path = config_dir / f"{name}.yaml"
        with cfg_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)
        command = [
            sys.executable, str(runner), "--config", str(cfg_path),
            "--seeds", "0", "--experiment-name", f"{EXPERIMENT}/{name}",
            "--no-plots",
        ]
        print(f"[{i:02d}/{len(SELECTED)}] RUN {name}", flush=True)
        start = time.monotonic()
        with (logs_dir / f"{name}.txt").open("w", encoding="utf-8") as output:
            proc = subprocess.run(
                command, cwd=repo, stdout=output,
                stderr=subprocess.STDOUT, check=False,
            )
        elapsed = time.monotonic() - start
        if proc.returncode != 0:
            raise RuntimeError(
                f"Simulation failed for {name}; see {logs_dir / (name + '.txt')}"
            )
        if not log_path.is_file() or not per_case_summary.is_file():
            raise RuntimeError(f"Missing output for {name}; see {logs_dir}")

        records[name] = compute_metrics(log_path, name, vals, elapsed)
        save_summary(summary_path, records)
        new_count += 1
        print(
            f"  DONE {elapsed:.1f}s: population={records[name]['final_population']}, "
            f"survived={records[name]['survived_year']}",
            flush=True,
        )

    done = sum(records.get(case_name(v), {}).get("status") == "complete" for v in SELECTED)
    print(f"Completed: {done}/20 | New: {new_count} | Skipped: {skipped_count}")
    print(f"Summary: {summary_path}")
    print("Re-run the same command to resume unfinished cases.")


if __name__ == "__main__":
    main()
