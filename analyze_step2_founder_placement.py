"""STEP2: existing lineage.csv files -> founder initial placement comparison.

Run from the project root:
  python analyze_step2_founder_placement.py --experiment-dir results/experiments/EXPERIMENT_NAME --config configs/default.yaml

Does not alter the simulation or existing CSVs. Requires the exact patch-center
configuration that was used to generate the experiment (not just similar area).
Outputs results/experiments/EXPERIMENT_NAME/step2_founder_placement/.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

REQUIRED = {
    "organism_id", "parent_id", "founder_id", "birth_step",
    "birth_x", "birth_y", "death_step",
}
METRICS = [
    "survival_50", "survival_100", "survival_200", "ever_reproduced",
    "reproduced_by_100", "first_birth_step", "direct_births_by_200",
    "direct_births_total", "lineage_alive_final",
    "final_alive_lineage_count", "descendants_ever_born", "total_lineage_born",
]


def build_patch_cells(env: dict) -> set[tuple[int, int]]:
    """Reproduce the explicit-center disk geometry in Environment._get_patch_cells."""
    if env.get("mode") != "patch":
        raise ValueError('This STEP2 analysis requires environment.mode: "patch".')
    centers = env.get("patch_centers")
    if not centers:
        raise ValueError("Explicit patch_centers absent. Supply the EXACT run configuration;")
    n = int(env.get("patch_count", len(centers)))
    if len(centers) < n:
        raise ValueError("patch_centers has fewer centers than patch_count")
    width, height, radius = int(env["width"]), int(env["height"]), int(env["patch_radius"])
    r2 = (radius + 0.5) ** 2
    result = set()
    for raw_cx, raw_cy in centers[:n]:
        cx, cy = int(raw_cx), int(raw_cy)
        if not (0 <= cx < width and 0 <= cy < height):
            raise ValueError(f"Invalid center {(cx, cy)}")
        for x in range(max(0, cx-radius), min(width-1, cx+radius)+1):
            for y in range(max(0, cy-radius), min(height-1, cy+radius)+1):
                if (x-cx)**2 + (y-cy)**2 <= r2:
                    result.add((x, y))
    if len(result) in (0, width*height):
        raise ValueError("No patch/outside cells available")
    return result


def summarize_seed(lineage_path: Path, patch_cells: set, seed: int,
                   expected_n: int, end_step: int) -> pd.DataFrame:
    frame = pd.read_csv(lineage_path, usecols=lambda c: c in REQUIRED, low_memory=False)
    missing = REQUIRED - set(frame.columns)
    if missing:
        raise ValueError(f"{lineage_path}: missing columns {sorted(missing)}")
    if frame["organism_id"].duplicated().any():
        raise ValueError(f"{lineage_path}: organism_id is duplicated")
    founders = frame.loc[
        frame["parent_id"].isna() &
        frame["birth_step"].eq(0) &
        frame["organism_id"].eq(frame["founder_id"]),
        ["organism_id", "birth_x", "birth_y", "death_step"],
    ].copy()
    if len(founders) != expected_n:
        raise ValueError(f"{lineage_path}: {len(founders)} founders (expected {expected_n})")
    founders = founders.rename(columns={"organism_id": "founder_id", "birth_x": "initial_x", "birth_y": "initial_y", "death_step": "founder_death_step"})
    if founders[["initial_x", "initial_y"]].isna().any().any():
        raise ValueError(f"{lineage_path}: missing initial positions")
    founders["placement"] = [
        "inside" if (int(x), int(y)) in patch_cells else "outside"
        for x, y in zip(founders["initial_x"], founders["initial_y"])
    ]
    founders["seed"] = int(seed)

    death = founders["founder_death_step"]
    for t in (50, 100, 200):
        founders[f"survival_{t}"] = (death.isna() | (death > t)).astype(float)

    # A direct child has parent_id == founder_id. Other descendants are NOT direct children.
    direct = frame.loc[frame["parent_id"].notna(), ["parent_id", "birth_step"]]
    direct_counts = direct.groupby("parent_id", sort=False).size()
    first_birth = direct.groupby("parent_id", sort=False)["birth_step"].min()
    direct_200 = direct.loc[direct["birth_step"].le(200)].groupby("parent_id", sort=False).size()

    founders["direct_births_total"] = founders["founder_id"].map(direct_counts).fillna(0).astype(int)
    founders["direct_births_by_200"] = founders["founder_id"].map(direct_200).fillna(0).astype(int)
    founders["first_birth_step"] = founders["founder_id"].map(first_birth).astype(float)
    founders["ever_reproduced"] = founders["direct_births_total"].gt(0).astype(float)
    founders["reproduced_by_100"] = founders["first_birth_step"].le(100).fillna(False).astype(float)

    sizes = frame.groupby("founder_id", sort=False).size()
    alive_sizes = frame.loc[frame["death_step"].isna()].groupby("founder_id", sort=False).size()
    founders["total_lineage_born"] = founders["founder_id"].map(sizes).fillna(0).astype(int)
    founders["final_alive_lineage_count"] = founders["founder_id"].map(alive_sizes).fillna(0).astype(int)
    founders["descendants_ever_born"] = founders["total_lineage_born"] - 1
    founders["lineage_alive_final"] = founders["final_alive_lineage_count"].gt(0).astype(float)

    if frame["birth_step"].max() > end_step:
        raise ValueError(f"{lineage_path}: birth_step extends past experimental end step {end_step}")
    if frame["death_step"].notna().any() and frame["death_step"].max() > end_step:
        raise ValueError(f"{lineage_path}: death_step extends past experimental end step {end_step}")
    return founders


def group_results(founders: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (seed, placement), g in founders.groupby(["seed", "placement"], sort=True):
        row = {"seed": int(seed), "placement": placement, "n_founders": len(g)}
        for name in METRICS:
            row[name] = float(g[name].mean())
        rows.append(row)
    return pd.DataFrame(rows)


def across_seed_results(per_seed: pd.DataFrame) -> pd.DataFrame:
    rows = []
    # seed = the independent replicate; differences are paired within the same seed.
    for metric in METRICS:
        panel = per_seed.pivot(index="seed", columns="placement", values=metric)
        for label in ("inside", "outside"):
            vals = panel[label].dropna() if label in panel else pd.Series(dtype=float)
            rows.append({"metric": metric, "comparison": label, "n_valid_seeds": len(vals),
                         "mean": float(vals.mean()) if len(vals) else np.nan,
                         "std_between_seeds": float(vals.std(ddof=1)) if len(vals)>1 else np.nan})
        if "inside" in panel and "outside" in panel:
            diff = (panel["inside"] - panel["outside"]).dropna()
        else:
            diff = pd.Series(dtype=float)
        rows.append({"metric": metric, "comparison": "inside_minus_outside",
                     "n_valid_seeds": len(diff), "mean": float(diff.mean()) if len(diff) else np.nan,
                     "std_between_seeds": float(diff.std(ddof=1)) if len(diff)>1 else np.nan})
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser(description="STEP2 founder initial-placement retrospective analysis")
    ap.add_argument("--experiment-dir", type=Path, required=True)
    ap.add_argument("--config", type=Path, default=Path("configs/default.yaml"),
                    help="YAML config that EXACTLY matches the original experiment")
    args = ap.parse_args()
    with args.config.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    env = cfg["environment"]
    cells = build_patch_cells(env)
    total_cells = int(env["width"]) * int(env["height"])
    seed_paths = sorted(args.experiment_dir.glob("seed_*/lineage.csv"),
                        key=lambda p: int(p.parent.name.split("_",1)[1]))
    if not seed_paths:
        raise FileNotFoundError(f"No seed_*/lineage.csv files found under {args.experiment_dir}")
    n_founders = int(cfg["organism"]["initial_population"])
    end_step = int(cfg["simulation"].get("duration_years",3) *
                   cfg["simulation"].get("days_per_year",365) *
                   cfg["simulation"].get("steps_per_day",10)) - 1 if cfg["simulation"].get("duration_mode") == "years" else int(cfg["simulation"]["steps"])-1
    print(f"Config: {args.config} | patch area={len(cells)}/{total_cells} ({len(cells)/total_cells:.2%}), founder count={n_founders}")
    print("CAUTION: verify that centers and radius MATCH the historical run configuration.")
    frames = []
    for lineage in seed_paths:
        seed = int(lineage.parent.name.split("_", 1)[1])
        found = summarize_seed(lineage, cells, seed, n_founders, end_step)
        frames.append(found)
        print(f"seed={seed}: founder inside={sum(found.placement=='inside')}, outside={sum(found.placement=='outside')}, "
              f"final living lineages={int(found.lineage_alive_final.sum())}")
    founders = pd.concat(frames, ignore_index=True)
    per_seed = group_results(founders)
    across = across_seed_results(per_seed)

    # Validate against the experiment's usual summary where present.
    summary_file = args.experiment_dir / "summary.csv"
    if summary_file.exists():
        summary = pd.read_csv(summary_file)
        if {"seed", "final_active_lineage_count"}.issubset(summary.columns):
            calculated = founders.groupby("seed")["lineage_alive_final"].sum().astype(int)
            expected = summary.set_index("seed")["final_active_lineage_count"].astype(int)
            overlap = calculated.index.intersection(expected.index)
            if not calculated.loc[overlap].eq(expected.loc[overlap]).all():
                raise AssertionError("Final surviving founder lineages do not match summary.csv; check input runs")
            print("Validation: final active lineages match summary.csv")
        if {"seed"}.issubset(summary.columns) and set(founders["seed"].unique()) != set(summary["seed"].unique()):
            print("WARNING: some summary.csv seeds have no lineage.csv available; only loaded seeds analyzed.")

    out = args.experiment_dir / "step2_founder_placement"
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "founder_placement_individual.csv": founders,
        "founder_placement_by_seed.csv": per_seed,
        "founder_placement_across_seeds.csv": across,
    }
    for name, data in paths.items():
        path = out / name
        data.to_csv(path, index=False, encoding="utf-8-sig")
        print("Saved:", path)
    print("\nPaired inside-minus-outside differences (positive means higher inside):")
    display = across.loc[across["comparison"].eq("inside_minus_outside"), ["metric","mean","n_valid_seeds"]]
    print(display.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    print("\nNOTE: observational association, not a causal estimate; placements were not experimentally controlled.")


if __name__ == "__main__":
    main()
