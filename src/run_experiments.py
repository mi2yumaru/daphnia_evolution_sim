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

# STEP1_AUTO_OUTCOMES_V1: import
try:
    from src.analyze_offspring_outcomes import aggregate_experiment_outcomes
except ImportError:
    from analyze_offspring_outcomes import aggregate_experiment_outcomes

# STEP3_GENE_FLOW_V1: import
try:
    from src.analyze_gene_flow import aggregate_gene_flow_experiment
except ImportError:
    from analyze_gene_flow import aggregate_gene_flow_experiment

# STEP4_LAST_YEAR_V1: shared final-year statistics (no simulation changes)
try:
    from src.last_year_summary import calculate_last_year_metrics, across_seed_summary, META_COLUMNS, METRIC_COLUMNS
except ImportError:
    from last_year_summary import calculate_last_year_metrics, across_seed_summary, META_COLUMNS, METRIC_COLUMNS

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

    # STEP3_CONTROLLED_INITIAL_PLACEMENT_V1
    parser.add_argument(
        "--initial-placement",
        choices=("uniform", "inside", "near", "far"),
        default=None,
        help="Founder initial placement (overrides organism.initial_placement_mode)",
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

def create_summary(all_logs: list[pd.DataFrame], steps_per_year: int = 3650) -> pd.DataFrame:
    """
    seedごとの最終値と後半100step平均を作成する。
    """
    rows = []

    for df in all_logs:
        seed = int(df["seed"].iloc[0])
        tail_size = min(100, len(df))
        tail = df.tail(tail_size)

        # STEP2_GENETIC_DIVERSITY_V1: 最終の暦年を1単位として集計
        last_year = df.loc[df["simulation_year"] == df["simulation_year"].iloc[-1]]

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
        # STEP2_GENETIC_DIVERSITY_V1
            "final_genetic_diversity_all": df["genetic_diversity_all"].iloc[-1],
            "mean_genetic_diversity_all_last_100": tail["genetic_diversity_all"].mean(),
            "mean_genetic_diversity_all_last_year": last_year["genetic_diversity_all"].mean(),
            "final_genetic_diversity_behavior": df["genetic_diversity_behavior"].iloc[-1],
            "mean_genetic_diversity_behavior_last_100": tail["genetic_diversity_behavior"].mean(),
            "mean_genetic_diversity_behavior_last_year": last_year["genetic_diversity_behavior"].mean(),
            "final_genetic_diversity_exchange": df["genetic_diversity_exchange"].iloc[-1],
            "mean_genetic_diversity_exchange_last_100": tail["genetic_diversity_exchange"].mean(),
            "mean_genetic_diversity_exchange_last_year": last_year["genetic_diversity_exchange"].mean(),
            "final_genotype_diversity": df["genotype_diversity"].iloc[-1],
            "mean_genotype_diversity_last_100": tail["genotype_diversity"].mean(),
            "mean_genotype_diversity_last_year": last_year["genotype_diversity"].mean(),
            "final_unique_genotype_ratio": df["unique_genotype_ratio"].iloc[-1],
            "mean_unique_genotype_ratio_last_100": tail["unique_genotype_ratio"].mean(),
            "mean_unique_genotype_ratio_last_year": last_year["unique_genotype_ratio"].mean(),
            "final_gene_exchange_probability":
                df["average_gene_exchange_probability"].iloc[-1],
            "final_gene_exchange_fraction":
                df["average_gene_exchange_fraction"].iloc[-1],
            "mean_gene_exchange_probability_last_100":
                tail["average_gene_exchange_probability"].mean(),
            "mean_gene_exchange_fraction_last_100":
                tail["average_gene_exchange_fraction"].mean(),
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
            "mean_gene_exchange_effective_birth_rate_last_100":
                tail["gene_exchange_effective_birth_rate"].mean(),
            "total_gene_exchange_effective_count":
                df["gene_exchange_effective_count"].sum(),
            "overall_gene_exchange_effective_rate": (
                df["gene_exchange_effective_count"].sum()
                / df["gene_exchange_event_count"].sum()
                if df["gene_exchange_event_count"].sum() > 0
                else float("nan")
            ),
            "overall_gene_exchange_effective_birth_rate": (
                df["gene_exchange_effective_count"].sum()
                / df["birth_count"].sum()
                if df["birth_count"].sum() > 0
                else float("nan")
            ),
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

    # STEP4_LAST_YEAR_V1: final complete calendar year per seed.
    # Drop existing STEP2-only year columns before inserting consistently.
    final_year_rows = [
        {"seed": int(df["seed"].iloc[0]), **calculate_last_year_metrics(df, steps_per_year)}
        for df in all_logs
    ]
    new_year = pd.DataFrame(final_year_rows)
    duplicated_columns = [c for c in (*META_COLUMNS, *METRIC_COLUMNS) if c in summary_df.columns]
    summary_df = summary_df.drop(columns=duplicated_columns).merge(new_year, on="seed", how="left", validate="one_to_one")

    return summary_df

def main() -> None:
    args = parse_args()

    project_root = Path(__file__).parent.parent
    config_path = project_root / "configs" / "default.yaml"

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if args.initial_placement is not None:
        config["organism"]["initial_placement_mode"] = args.initial_placement

    experiment_dir = (
        project_root
        / "results"
        / "experiments"
        / args.experiment_name
    )
    experiment_dir.mkdir(parents=True, exist_ok=True)

    # Preserve the exact config for spatial classification later.
    config_snapshot_path = experiment_dir / "config_used.yaml"
    if config_snapshot_path.exists():
        with config_snapshot_path.open(encoding="utf-8") as f:
            previous_config = yaml.safe_load(f)
        if previous_config != config:
            raise ValueError("Experiment directory contains a different config_used.yaml; choose a new --experiment-name")
    else:
        with config_snapshot_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False)

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

    # STEP4_LAST_YEAR_V1: use the configured year length.
    sim_config = config["simulation"]
    steps_per_year = int(sim_config["days_per_year"]) * int(sim_config["steps_per_day"])
    summary_df = create_summary(all_logs, steps_per_year=steps_per_year)
    summary_df.to_csv(
        experiment_dir / "summary.csv",
        index=False
    )
    across_seed_summary(summary_df).to_csv(
        experiment_dir / "summary_last_year_across_seeds.csv",
        index=False,
    )

    # --------------------------------
    # STEP1_AUTO_OUTCOMES_V1: seed間の追加集計
    analysis_settings = config.get("analysis", {}).get("offspring_outcomes", {})
    if analysis_settings.get("enabled", True):
        aggregate_experiment_outcomes(
            experiment_dir=experiment_dir,
            seeds=args.seeds,
            horizon_steps=int(analysis_settings.get("horizon_steps", 200)),
        )
        print("生存・繁殖成績のseed間集計完了")

    # STEP3_GENE_FLOW_V1: seed間の提供関係・交差Founder遺伝子移動を集計
    flow_settings = config.get("analysis", {}).get("gene_flow", {})
    if flow_settings.get("enabled", True):
        aggregate_gene_flow_experiment(experiment_dir, args.seeds)
        print("遺伝子提供・Founder系譜間のseed間集計完了")

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