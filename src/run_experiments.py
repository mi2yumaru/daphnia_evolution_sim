"""
run_experiments.py - 複数seedでの独立反復実験
"""

import argparse
from pathlib import Path

import pandas as pd
import yaml

try:
    from src.runner import run_single_simulation
    from src.visualizer import (
        COMMON_PLOT_SPECS,
        add_derived_metrics,
        plot_aggregate_mean_std,
        plot_food_dynamics,
        plot_food_respawn_rate,
    )
except ImportError:
    from runner import run_single_simulation
    from visualizer import (
        COMMON_PLOT_SPECS,
        add_derived_metrics,
        plot_aggregate_mean_std,
        plot_food_dynamics,
        plot_food_respawn_rate,
    )

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
            "mean_shared_food_cell_ratio_last_100": (
                tail["shared_food_cell_ratio"].mean()
            ),
            "mean_shared_food_consumer_ratio_last_100": (
                tail["shared_food_consumer_ratio"].mean()
            ),
            "mean_birth_rate_last_100": tail["birth_rate"].mean(),
            "mean_death_rate_last_100": tail["death_rate"].mean(),
            "mean_age_death_rate_last_100": tail["age_death_rate"].mean(),
            "mean_energy_death_rate_last_100": tail["energy_death_rate"].mean(),
            "mean_age_death_count_last_100": tail["age_death_count"].mean(),
            "mean_energy_death_count_last_100": tail["energy_death_count"].mean(),
            "final_exploration_tendency":
                df["average_exploration_tendency"].iloc[-1],
            "final_site_fidelity":
                df["average_site_fidelity"].iloc[-1],
            "final_risk_tolerance":
                df["average_risk_tolerance"].iloc[-1],
            "final_reproduction_timing":
                df["average_reproduction_timing"].iloc[-1],
            "mean_gene_exchange_eligible_rate_last_100":
                tail["gene_exchange_eligible_rate"].mean(),
            "mean_gene_exchange_event_rate_last_100":
                tail["gene_exchange_event_rate_plot"].mean(),
            "mean_gene_exchange_birth_rate_last_100":
                tail["gene_exchange_birth_rate"].mean(),
            "mean_gene_exchange_event_count_last_100":
                tail["gene_exchange_event_count"].mean(),
            "mean_gene_exchange_selected_loci_count_last_100":
                tail["gene_exchange_selected_loci_count"].mean(),
            "mean_gene_exchange_changed_bit_count_last_100":
                tail["gene_exchange_changed_bit_count"].mean(),
            "total_gene_exchange_events":
                df["gene_exchange_event_count"].sum(),
            "total_gene_exchange_selected_loci":
                df["gene_exchange_selected_loci_count"].sum(),
            "total_gene_exchange_changed_bits":
                df["gene_exchange_changed_bit_count"].sum(),
        })

    summary_df = pd.DataFrame(rows)

    lineage_rows = []

    for df in all_logs:
        seed = int(df["seed"].iloc[0])

        tail_size = min(100,len(df),)

        tail = df.tail(tail_size)

        lineage_rows.append({
            "seed": seed,
            "final_active_lineage_count": df["active_lineage_count"].iloc[-1],
            "mean_active_lineage_count_last_100": tail["active_lineage_count"].mean(),
            "final_largest_lineage_share": df["largest_lineage_share"].iloc[-1],
            "mean_largest_lineage_share_last_100": tail["largest_lineage_share"].mean(),
            "final_average_generation": df["average_generation"].iloc[-1],
            "final_max_generation": df["max_generation"].iloc[-1],
        })

    lineage_summary_df = pd.DataFrame(lineage_rows)

    summary_df = summary_df.merge(
        lineage_summary_df,
        on="seed",
        how="left",
    )

    return summary_df

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
    all_lineage_summaries: list[pd.DataFrame] = []

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

        # グラフ・集計用の派生指標を追加
        df = add_derived_metrics(df)
        
        df["seed"] = seed
        all_logs.append(df)

        # --------------------------------
        # Founder系統×行動戦略summaryを取得
        # --------------------------------
        lineage_summary_path = (
            seed_dir
            / "lineage_strategy_summary.csv"
        )

        if not lineage_summary_path.exists():
            raise FileNotFoundError(
                "lineage_strategy_summary.csv "
                f"が見つかりません: "
                f"{lineage_summary_path}"
            )

        lineage_summary_df = pd.read_csv(lineage_summary_path)

        # seed列を先頭に追加
        lineage_summary_df.insert(
            0,
            "seed",
            seed,
        )

        all_lineage_summaries.append(lineage_summary_df)

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

    # --------------------------------
    # 全seedのFounder系統summaryを結合
    # --------------------------------
    if not all_lineage_summaries:raise RuntimeError("系譜summaryがありません。")

    lineage_strategy_all_seeds_df = (
        pd.concat(
            all_lineage_summaries,
            ignore_index=True,
        )
        .sort_values(["seed","founder_id",])
        .reset_index(drop=True)
    )


    # extinction_stepを
    # 欠損可能な整数型に変換
    if (
        "extinction_step"
        in lineage_strategy_all_seeds_df.columns
    ):
        lineage_strategy_all_seeds_df[
            "extinction_step"
        ] = (
            lineage_strategy_all_seeds_df[
                "extinction_step"
            ]
            .astype("Int64")
        )


    lineage_strategy_all_seeds_df.to_csv(
        experiment_dir
        / "lineage_strategy_all_seeds.csv",
        index=False,
    )

    # -------------------------
    # 共通グラフ / 単一seed専用グラフ
    # -------------------------
    plot_food_respawn_rate(
        all_logs[0],
        experiment_dir / "food_respawn_rate.png",
    )

    plot_food_dynamics(
        aggregate_df,
        experiment_dir / "food_dynamics_mean_std.png",
    )

    for spec in COMMON_PLOT_SPECS:
        if spec["name"] == "food_respawn_rate":
            continue
        if spec["name"] == "food_dynamics":
            continue

        output_path = experiment_dir / spec["aggregate_output_name"]
        plot_aggregate_mean_std(
            aggregate_df,
            output_path,
            metrics=spec["metrics"],
            title=f"{spec['title']} Across Seeds",
            ylabel=spec["ylabel"],
            fixed_ylim=spec.get("fixed_ylim"),
        )

    if "largest_lineage_share_mean" in aggregate_df.columns:
        largest_lineage_upper = (
            aggregate_df["largest_lineage_share_mean"]
            + aggregate_df["largest_lineage_share_std"].fillna(0.0)
        ).max()
        largest_lineage_ymax = max(largest_lineage_upper * 1.1, 0.1)
        largest_lineage_ymax = min(largest_lineage_ymax, 1.0)

        plot_aggregate_mean_std(
            aggregate_df,
            experiment_dir / "largest_lineage_share_mean_std.png",
            metrics=[("largest_lineage_share", "Largest Lineage Share")],
            title="Largest Lineage Share Across Seeds",
            ylabel="Share",
            fixed_ylim=(0.0, largest_lineage_ymax),
        )

    print("\n=== 複数seed実験完了 ===")
    print(f"実行seed: {args.seeds}")
    print(f"出力先: {experiment_dir}")


if __name__ == "__main__":
    main()