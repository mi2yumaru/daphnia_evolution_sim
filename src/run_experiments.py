"""
run_experiments.py - 複数seedでの独立反復実験
"""

import argparse
from pathlib import Path

import pandas as pd
import yaml

try:
    from src.runner import run_single_simulation
    from src.visualizer import plot_aggregate_mean_std
except ImportError:
    from runner import run_single_simulation
    from visualizer import plot_aggregate_mean_std

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="複数seedでシミュレーションを反復実行します。"
    )

    parser.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        default=list(range(10)),
        help="実行するseed一覧。例: --seeds 0 1 2 3 4"
    )

    parser.add_argument(
        "--save-run-plots",
        action="store_true",
        help="各seedの個別グラフも保存します。"
    )

    parser.add_argument(
        "--experiment-name",
        type=str,
        default="multi_seed",
        help="実験結果ディレクトリ名"
    )

    return parser.parse_args()

def aggregate_runs(all_logs: list[pd.DataFrame]) -> pd.DataFrame:
    """
    各seedのログをstep単位で集約し、平均とseed間標準偏差を求める。
    """
    combined = pd.concat(all_logs, ignore_index=True)

    numeric_columns = [
        column
        for column in combined.select_dtypes(include="number").columns
        if column not in {"seed", "step"}
    ]

    aggregate = (
        combined
        .groupby("step")[numeric_columns]
        .agg(["mean", "std"])
    )

    aggregate.columns = [
        f"{metric}_{stat}"
        for metric, stat in aggregate.columns
    ]

    aggregate = aggregate.reset_index()

    return aggregate

def create_summary(all_logs: list[pd.DataFrame]) -> pd.DataFrame:
    """
    seedごとの最終値と後半100step平均を作成する。
    """
    rows = []

    for df in all_logs:
        seed = int(df["seed"].iloc[0])
        tail_size = min(100, len(df))
        tail = df.tail(tail_size)

        rows.append({
            "seed": seed,
            "final_population": df["population_size"].iloc[-1],
            "mean_population_last_100": tail["population_size"].mean(),
            "mean_move_rate_last_100": tail["move_rate"].mean(),
            "mean_total_eat_rate_last_100": (
                tail["total_eat_rate"].mean()
                if "total_eat_rate" in tail.columns
                else tail["eat_rate"].mean()
            ),
            "mean_eat_after_move_rate_last_100": tail["eat_after_move_rate"].mean(),
            "mean_eat_without_move_rate_last_100": tail["eat_without_move_rate"].mean(),
            "mean_move_count_last_100": tail["move_count"].mean(),
            "mean_non_move_count_last_100": tail["non_move_count"].mean(),
            "mean_shared_food_cell_count_last_100": (
                tail["shared_food_cell_count"].mean()
                if "shared_food_cell_count" in tail.columns
                else 0.0
            ),
            "mean_shared_food_consumer_count_last_100": (
                tail["shared_food_consumer_count"].mean()
                if "shared_food_consumer_count" in tail.columns
                else 0.0
            ),
            "mean_consumers_per_shared_food_last_100": (
                tail["mean_consumers_per_shared_food"].mean()
                if "mean_consumers_per_shared_food" in tail.columns
                else 0.0
            ),
            "mean_birth_rate_last_100": tail["birth_rate"].mean(),
            "mean_death_rate_last_100": tail["death_rate"].mean(),
            "final_exploration_tendency":
                df["average_exploration_tendency"].iloc[-1],
            "final_site_fidelity":
                df["average_site_fidelity"].iloc[-1],
            "final_risk_tolerance":
                df["average_risk_tolerance"].iloc[-1],
            "final_reproduction_timing":
                df["average_reproduction_timing"].iloc[-1],
        })

    return pd.DataFrame(rows)

def main() -> None:
    args = parse_args()

    project_root = Path(__file__).parent.parent
    config_path = project_root / "configs" / "default.yaml"

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    experiment_dir = (
        project_root
        / "results"
        / "experiments"
        / args.experiment_name
    )
    experiment_dir.mkdir(parents=True, exist_ok=True)

    all_logs: list[pd.DataFrame] = []

    for seed in args.seeds:
        print(f"seed={seed} を実行中...")

        seed_dir = experiment_dir / f"seed_{seed}"

        df = run_single_simulation(
            config=config,
            seed=seed,
            output_dir=seed_dir,
            live=False,
            save_csv=True,
            save_plots=args.save_run_plots,
        )

        df = df.copy()
        df["seed"] = seed
        all_logs.append(df)

    if not all_logs:
        raise RuntimeError("実行結果がありません。")

    aggregate_df = aggregate_runs(all_logs)
    aggregate_df.to_csv(
        experiment_dir / "aggregate.csv",
        index=False
    )

    summary_df = create_summary(all_logs)
    summary_df.to_csv(
        experiment_dir / "summary.csv",
        index=False
    )

    plot_aggregate_mean_std(
        aggregate_df,
        experiment_dir / "population_mean_std.png",
        metrics=[
            ("population_size", "Population")
        ],
        title="Population Across Seeds",
        ylabel="Population Size"
    )

    plot_aggregate_mean_std(
        aggregate_df,
        experiment_dir / "movement_eating_mean_std.png",
        metrics=[
            ("move_rate", "Move Rate"),
            ("total_eat_rate", "Total Eat Rate"),
        ],
        title="Movement and Total Eating Rates Across Seeds",
        ylabel="Rate"
    )

    plot_aggregate_mean_std(
        aggregate_df,
        experiment_dir / "eating_breakdown_rates_mean_std.png",
        metrics=[
            ("eat_after_move_rate", "Eat Success After Move"),
            ("eat_without_move_rate", "Eat Success Without Move"),
        ],
        title="Eating Success Rates by Movement State Across Seeds",
        ylabel="Rate"
    )

    plot_aggregate_mean_std(
        aggregate_df,
        experiment_dir / "birth_death_mean_std.png",
        metrics=[
            ("birth_rate", "Birth Rate"),
            ("death_rate", "Death Rate"),
        ],
        title="Birth and Death Rates Across Seeds",
        ylabel="Rate"
    )

    plot_aggregate_mean_std(
        aggregate_df,
        experiment_dir / "behavior_traits_mean_std.png",
        metrics=[
            (
                "average_exploration_tendency",
                "Exploration Tendency"
            ),
            (
                "average_site_fidelity",
                "Site Fidelity"
            ),
            (
                "average_risk_tolerance",
                "Risk Tolerance"
            ),
            (
                "average_reproduction_timing",
                "Reproduction Timing"
            ),
        ],
        title="Behavior Traits Across Seeds",
        ylabel="Trait Value",
        fixed_ylim=(0.0, 1.0)
    )

    plot_aggregate_mean_std(
        aggregate_df,
        experiment_dir / "average_energy_mean_std.png",
        metrics=[
            ("average_energy", "Average Energy")
        ],
        title="Average Energy Across Seeds",
        ylabel="Average Energy"
    )

    plot_aggregate_mean_std(
        aggregate_df,
        experiment_dir / "average_age_mean_std.png",
        metrics=[
            ("average_age", "Average Age")
        ],
        title="Average Age Across Seeds",
        ylabel="Average Age"
    )

    plot_aggregate_mean_std(
        aggregate_df,
        experiment_dir / "birth_death_counts_mean_std.png",
        metrics=[
            ("birth_count", "Birth Count"),
            ("death_count", "Death Count"),
        ],
        title="Birth and Death Counts Across Seeds",
        ylabel="Count"
    )

    print("\n=== 複数seed実験完了 ===")
    print(f"実行seed: {args.seeds}")
    print(f"出力先: {experiment_dir}")


if __name__ == "__main__":
    main()