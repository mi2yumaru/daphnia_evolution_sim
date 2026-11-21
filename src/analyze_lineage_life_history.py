"""Extract comparable reproductive life-history metrics from existing lineage.csv.

Does not change or rerun simulations. One row per condition/environment/seed;
a second file pairs the 20 random-environment runs with patch counterparts.

Usage from the repository root:
    python src/analyze_lineage_life_history.py --limit 2
    python src/analyze_lineage_life_history.py  # aggregates 6-12d first reproduction
    python src/analyze_lineage_life_history.py --include-long
"""
from __future__ import annotations

import argparse
import csv
import math
import statistics
from pathlib import Path

import yaml

SOURCE_EXPERIMENTS = (
    ("patch256", "grid_patch4_1y_seed0"),
    ("random20", "grid_random20_1y_seed0"),
)
LONG_EXPERIMENT = ("long", "grid5_5y_10seeds")

METRICS = [
    "lineage_individuals",
    "founder_count",
    "offspring_count",
    "distinct_reproductive_parents",
    "founder_reproductive_parents",
    "nonfounder_reproductive_parents",
    "first_reproduction_mean_days",
    "first_reproduction_std_days",
    "first_reproduction_median_days",
    "first_reproduction_p10_days",
    "first_reproduction_p90_days",
    "first_reproduction_before_6d_frac",
    "first_reproduction_6_to_12d_frac",
    "first_reproduction_over_12d_frac",
    "first_reproduction_under_7d_frac",
    "first_reproduction_under_10d_frac",
    "first_reproduction_10_to_20d_frac",
    "founder_first_reproduction_median_days",
    "nonfounder_first_reproduction_median_days",
    "parent_age_at_birth_mean_days",
    "parent_age_at_birth_std_days",
    "parent_age_at_birth_median_days",
    "parent_age_at_birth_p10_days",
    "parent_age_at_birth_p90_days",
    "unresolved_parent_rows",
]
FIELDS = [
    "dataset", "case", "environment", "seed", "duration_years",
    "steps_per_day", "source_path", "source_bytes", "source_mtime_ns",
    "status", *METRICS,
]


class OnlineMoments:
    def __init__(self) -> None:
        self.n = 0
        self.mean = 0.0
        self.m2 = 0.0

    def add(self, x: float) -> None:
        self.n += 1
        delta = x - self.mean
        self.mean += delta / self.n
        self.m2 += delta * (x - self.mean)

    def sample_std(self) -> float:
        return math.sqrt(self.m2 / (self.n - 1)) if self.n > 1 else math.nan


def percentile(sorted_values: list[float], percent: float) -> float:
    """Linear interpolation, matching numpy's default percentile rule."""
    if not sorted_values:
        return math.nan
    position = (len(sorted_values) - 1) * percent / 100.0
    low = int(math.floor(position))
    high = int(math.ceil(position))
    weight = position - low
    return sorted_values[low] * (1.0 - weight) + sorted_values[high] * weight


def number(x: float) -> float | str:
    return round(x, 5) if math.isfinite(x) else ""


def identifier(value: str) -> int | None:
    value = value.strip()
    if not value or value.lower() in {"nan", "none", "null"}:
        return None
    # Pandas exports nullable parent IDs as 2.0 when mixed with missing values.
    parsed = float(value)
    if not parsed.is_integer() or parsed < 0:
        raise ValueError(f"Invalid individual/parent id: {value!r}")
    return int(parsed)


def analyze(path: Path, steps_per_day: int) -> dict:
    """One pass: lineage.csv is stored in ascending organism_id order."""
    if steps_per_day < 1:
        raise ValueError("steps_per_day must be positive")

    # ID -> (birth_step, generation)
    born: dict[int, tuple[int, int]] = {}
    # parent ID -> first observed age-at-childbirth in steps
    first: dict[int, int] = {}
    parent_birth_ages: list[float] = []
    event_ages = OnlineMoments()
    offspring = 0
    founders = 0
    unresolved = 0
    prev_id = -1

    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        needed = {"organism_id", "parent_id", "generation", "birth_step"}
        missing = needed - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path}: missing fields {sorted(missing)}")
        for row in reader:
            individual = identifier(row["organism_id"])
            if individual is None or individual <= prev_id:
                raise ValueError(f"{path}: organism_id not sorted/unique")
            prev_id = individual

            birth_step = int(float(row["birth_step"]))
            generation = int(float(row["generation"]))
            parent_id = identifier(row["parent_id"])
            if parent_id is None:
                founders += 1
                if generation != 0:
                    raise ValueError(f"{path}: missing parent for generation {generation}")
            else:
                offspring += 1
                parent_info = born.get(parent_id)
                if parent_info is None:
                    unresolved += 1
                else:
                    parent_birth_step, parent_generation = parent_info
                    if generation != parent_generation + 1:
                        raise ValueError(f"{path}: invalid generation for {individual}")
                    # Founders are aged at the start of step 0; individuals
                    # born later only begin aging on the following step.
                    age_steps = (
                        birth_step - parent_birth_step
                        + (1 if parent_generation == 0 else 0)
                    )
                    if age_steps < 0:
                        raise ValueError(f"{path}: child born before parent")
                    if parent_id not in first or age_steps < first[parent_id]:
                        first[parent_id] = age_steps
                    age_days = age_steps / steps_per_day
                    event_ages.add(age_days)
                    parent_birth_ages.append(age_days)
            born[individual] = birth_step, generation

    if unresolved:
        raise ValueError(
            f"{path}: {unresolved} parent IDs could not be resolved; "
            "source may not be ordered or complete"
        )

    all_first_days = sorted(v / steps_per_day for v in first.values())
    founder_first = sorted(
        age / steps_per_day
        for parent_id, age in first.items()
        if born[parent_id][1] == 0
    )
    nonfounder_first = sorted(
        age / steps_per_day
        for parent_id, age in first.items()
        if born[parent_id][1] > 0
    )
    event_sorted = sorted(parent_birth_ages)
    parent_birth_ages.clear()

    nparents = len(all_first_days)
    if nparents:
        first_mean = statistics.fmean(all_first_days)
        first_std = statistics.stdev(all_first_days) if nparents > 1 else math.nan
        before6 = sum(v < 6 for v in all_first_days) / nparents
        between6and12 = sum(6 <= v <= 12 for v in all_first_days) / nparents
        after12 = sum(v > 12 for v in all_first_days) / nparents
        under7 = sum(v < 7 for v in all_first_days) / nparents
        under10 = sum(v < 10 for v in all_first_days) / nparents
        between10and20 = sum(10 <= v <= 20 for v in all_first_days) / nparents
    else:
        first_mean = first_std = before6 = between6and12 = after12 = under7 = under10 = between10and20 = math.nan

    return {
        "lineage_individuals": len(born),
        "founder_count": founders,
        "offspring_count": offspring,
        "distinct_reproductive_parents": nparents,
        "founder_reproductive_parents": len(founder_first),
        "nonfounder_reproductive_parents": len(nonfounder_first),
        "first_reproduction_mean_days": number(first_mean),
        "first_reproduction_std_days": number(first_std),
        "first_reproduction_median_days": number(percentile(all_first_days, 50)),
        "first_reproduction_p10_days": number(percentile(all_first_days, 10)),
        "first_reproduction_p90_days": number(percentile(all_first_days, 90)),
        "first_reproduction_before_6d_frac": number(before6),
        "first_reproduction_6_to_12d_frac": number(between6and12),
        "first_reproduction_over_12d_frac": number(after12),
        "first_reproduction_under_7d_frac": number(under7),
        "first_reproduction_under_10d_frac": number(under10),
        "first_reproduction_10_to_20d_frac": number(between10and20),
        "founder_first_reproduction_median_days": number(percentile(founder_first, 50)),
        "nonfounder_first_reproduction_median_days": number(percentile(nonfounder_first, 50)),
        "parent_age_at_birth_mean_days": number(event_ages.mean) if event_ages.n else "",
        "parent_age_at_birth_std_days": number(event_ages.sample_std()),
        "parent_age_at_birth_median_days": number(percentile(event_sorted, 50)),
        "parent_age_at_birth_p10_days": number(percentile(event_sorted, 10)),
        "parent_age_at_birth_p90_days": number(percentile(event_sorted, 90)),
        "unresolved_parent_rows": unresolved,
    }


def discover(repo: Path, include_long: bool) -> list[dict]:
    experiments = list(SOURCE_EXPERIMENTS)
    if include_long:
        experiments.append(LONG_EXPERIMENT)
    result = []
    for kind, folder in experiments:
        root = repo / "results" / "experiments" / folder
        if kind == "long":
            files = sorted(root.glob("*/*/rep_*/seed_*/lineage.csv"))
        else:
            files = sorted(root.glob("*/seed_*/lineage.csv"))
        for path in files:
            if kind == "long":
                expdir = path.parent.parent
                environment = path.parent.parent.parent.name
                case = path.parent.parent.parent.parent.name
            else:
                expdir = path.parent.parent
                environment = "patch" if kind == "patch256" else "random"
                case = expdir.name
            config_path = expdir / "config_used.yaml"
            if not config_path.is_file():
                raise FileNotFoundError(f"Missing config_used.yaml: {config_path}")
            with config_path.open(encoding="utf-8") as f:
                config = yaml.safe_load(f)
            if config.get("organism", {}).get("randomize_initial_age", False):
                raise ValueError(
                    f"{config_path}: random initial founder ages require a "
                    "different estimator; initial age was not logged in lineage.csv"
                )
            seed = int(path.parent.name.removeprefix("seed_"))
            result.append({
                "dataset": kind,
                "case": case,
                "environment": environment,
                "seed": seed,
                "duration_years": int(config["simulation"]["duration_years"]),
                "steps_per_day": int(config["simulation"]["steps_per_day"]),
                "source_path": str(path.relative_to(repo)),
                "source_bytes": path.stat().st_size,
                "source_mtime_ns": path.stat().st_mtime_ns,
                "status": "complete",
                "path": path,
            })
    return result


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    temp = path.with_suffix(".tmp")
    with temp.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temp.replace(path)


def load_existing(path: Path) -> dict[tuple, dict]:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        return {
            (r["dataset"], r["case"], r["environment"], int(r["seed"])): r
            for r in csv.DictReader(f)
        }


def matched_comparison(records: dict[tuple, dict]) -> list[dict]:
    pairs = []
    for key, random_row in records.items():
        dataset, case, environment, seed = key
        if dataset != "random20" or environment != "random":
            continue
        patch = records.get(("patch256", case, "patch", seed))
        if not patch:
            continue
        row = {"case": case, "seed": seed}
        for k in METRICS:
            row[f"patch_{k}"] = patch.get(k, "")
            row[f"random_{k}"] = random_row.get(k, "")
        pairs.append(row)
    return sorted(pairs, key=lambda r: (r["case"], int(r["seed"])))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Summarize reproductive ages from existing lineage.csv files"
    )
    parser.add_argument("--limit", type=int, help="Analyze at most this many new files")
    parser.add_argument(
        "--include-long", action="store_true",
        help="Also scan completed 5-year simulations when present",
    )
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be a positive integer")

    repo = Path(__file__).resolve().parent.parent
    output = repo / "results" / "experiments" / "lineage_life_history"
    output.mkdir(parents=True, exist_ok=True)
    summary_file = output / "lineage_life_history_per_run.csv"
    comparison_file = output / "lineage_life_history_matched20.csv"
    records = load_existing(summary_file)
    files = discover(repo, args.include_long)
    print(f"Found {len(files)} lineage files, {len(records)} pre-existing summaries", flush=True)
    if not files:
        raise SystemExit("No lineage files found; check results/experiments folders")

    added = 0
    skipped = 0
    for f in files:
        key = (f["dataset"], f["case"], f["environment"], f["seed"])
        previous = records.get(key)
        if (
            previous
            and int(previous.get("source_bytes", "-1")) == f["source_bytes"]
            and int(previous.get("source_mtime_ns", "-1")) == f["source_mtime_ns"]
            and previous.get("status") == "complete"
            and previous.get("first_reproduction_6_to_12d_frac", "") not in ("", None)
        ):
            skipped += 1
            continue
        if args.limit is not None and added >= args.limit:
            break
        print(f"ANALYZE {f['dataset']}/{f['case']}/{f['environment']}/seed_{f['seed']}", flush=True)
        row = {k: v for k, v in f.items() if k != "path"}
        row.update(analyze(f["path"], f["steps_per_day"]))
        records[key] = row
        write_csv(
            summary_file,
            [records[k] for k in sorted(records)],
            FIELDS,
        )
        added += 1
        print(
            f"  first-reproduction median: {row['first_reproduction_median_days']} days; "
            f"parents: {row['distinct_reproductive_parents']}",
            flush=True,
        )

    pair = matched_comparison(records)
    comp_fields = ["case", "seed"] + [
        col
        for metric in METRICS
        for col in (f"patch_{metric}", f"random_{metric}")
    ]
    write_csv(comparison_file, pair, comp_fields)
    print(
        f"Processed: {added}; skipped unchanged: {skipped}; paired cases: {len(pair)}",
        flush=True,
    )
    print(f"Summary: {summary_file}")
    print(f"Comparison: {comparison_file}")
    print(
        "Important: averages are conditional on organisms that reproduced; "
        "nonreproducers and right-censoring are not included."
    )


if __name__ == "__main__":
    main()
