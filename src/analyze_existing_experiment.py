"""
analyze_existing_experiment.py

既存の複数seed実験結果から、
seedごとの遺伝子交換関連指標を集計・可視化する。

シミュレーション自体は再実行しない。
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def parse_args():
    parser = argparse.ArgumentParser(
        description="既存の実験結果から遺伝子交換関連指標を解析します。"
    )

    parser.add_argument(
        "--experiment-dir",
        type=str,
        required=True,
        help="summary.csv等が保存されている実験ディレクトリ",
    )

    return parser.parse_args()


def calculate_final_gene_exchange_traits(
    lineage_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    lineage_strategy_all_seeds.csv から、
    seedごとの最終 Gene Exchange Probability / Fraction を復元する。

    各Founder系譜の最終平均値を、
    final_alive_count で重み付けして集団平均を求める。
    """

    rows = []

    for seed, seed_df in lineage_df.groupby("seed"):

        alive_df = seed_df[
            seed_df["final_alive_count"] > 0
        ].copy()

        total_alive = alive_df["final_alive_count"].sum()

        if total_alive == 0:
            probability = float("nan")
            fraction = float("nan")

        else:
            probability = (
                alive_df["final_mean_gene_exchange_probability"]
                * alive_df["final_alive_count"]
            ).sum() / total_alive

            fraction = (
                alive_df["final_mean_gene_exchange_fraction"]
                * alive_df["final_alive_count"]
            ).sum() / total_alive

        rows.append(
            {
                "seed": seed,
                "final_gene_exchange_probability": probability,
                "final_gene_exchange_fraction": fraction,
            }
        )

    return pd.DataFrame(rows)


def plot_seed_values(
    df: pd.DataFrame,
    column: str,
    ylabel: str,
    output_path: Path,
):
    """
    seedごとの値を散布図として表示する。
    """

    plt.figure(figsize=(8, 5))

    plt.scatter(
        df["seed"],
        df[column],
        s=60,
    )

    mean_value = df[column].mean()

    plt.axhline(
        mean_value,
        linestyle="--",
        label=f"Mean = {mean_value:.3f}",
    )

    plt.xlabel("Seed")
    plt.ylabel(ylabel)
    plt.xticks(df["seed"])
    plt.grid(alpha=0.3)
    plt.legend()

    plt.tight_layout()
    plt.savefig(
        output_path,
        dpi=150,
    )
    plt.close()


def main():

    args = parse_args()

    experiment_dir = Path(args.experiment_dir)

    summary_path = experiment_dir / "summary.csv"
    lineage_path = (
        experiment_dir
        / "lineage_strategy_all_seeds.csv"
    )

    if not summary_path.exists():
        raise FileNotFoundError(
            f"summary.csv が見つかりません: {summary_path}"
        )

    if not lineage_path.exists():
        raise FileNotFoundError(
            "lineage_strategy_all_seeds.csv "
            f"が見つかりません: {lineage_path}"
        )

    summary_df = pd.read_csv(summary_path)
    lineage_df = pd.read_csv(lineage_path)

    # 過去データから最終交換形質を復元
    exchange_traits_df = (
        calculate_final_gene_exchange_traits(
            lineage_df
        )
    )

    # 既存summaryと結合
    analysis_df = summary_df.merge(
        exchange_traits_df,
        on="seed",
        how="left",
    )

    # 新しいsummaryを保存
    analysis_df.to_csv(
        experiment_dir
        / "gene_exchange_seed_summary.csv",
        index=False,
    )

    # -----------------------------
    # Seedごとの交換形質
    # -----------------------------

    plot_seed_values(
        analysis_df,
        "final_gene_exchange_probability",
        "Final Gene Exchange Probability",
        experiment_dir
        / "seed_final_gene_exchange_probability.png",
    )

    plot_seed_values(
        analysis_df,
        "final_gene_exchange_fraction",
        "Final Gene Exchange Fraction",
        experiment_dir
        / "seed_final_gene_exchange_fraction.png",
    )

    # -----------------------------
    # Seedごとの交換機会・交換発生
    # -----------------------------

    plot_seed_values(
        analysis_df,
        "mean_gene_exchange_eligible_rate_last_100",
        "Gene Exchange Eligible Rate",
        experiment_dir
        / "seed_gene_exchange_eligible_rate.png",
    )

    plot_seed_values(
        analysis_df,
        "mean_gene_exchange_event_rate_last_100",
        "Gene Exchange Event Rate",
        experiment_dir
        / "seed_gene_exchange_event_rate.png",
    )

    plot_seed_values(
        analysis_df,
        "mean_gene_exchange_birth_rate_last_100",
        "Gene Exchange Birth Rate",
        experiment_dir
        / "seed_gene_exchange_birth_rate.png",
    )

    print("\n=== Gene Exchange Analysis ===")

    print(
        analysis_df[
            [
                "seed",
                "final_gene_exchange_probability",
                "final_gene_exchange_fraction",
                "mean_gene_exchange_eligible_rate_last_100",
                "mean_gene_exchange_event_rate_last_100",
                "mean_gene_exchange_birth_rate_last_100",
            ]
        ].to_string(index=False)
    )

    print(
        "\n結果を保存しました:"
        f"\n{experiment_dir}"
    )


if __name__ == "__main__":
    main()