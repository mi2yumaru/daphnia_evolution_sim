"""
visualizer.py - シミュレーション結果の可視化

グラフ出力用の関数群
"""
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

COMMON_PLOT_SPECS = [
    {
        "name": "population",
        "metrics": [("population_size", "Population")],
        "title": "Population Over Time",
        "ylabel": "Population Size",
        "output_name": "population.png",
        "aggregate_output_name": "population_mean_std.png",
    },
    {
        "name": "average_energy",
        "metrics": [("average_energy", "Average Energy")],
        "title": "Average Energy Over Time",
        "ylabel": "Average Energy",
        "output_name": "average_energy.png",
        "aggregate_output_name": "average_energy_mean_std.png",
    },
    {
        "name": "average_age",
        "metrics": [("average_age", "Average Age")],
        "title": "Average Age Over Time",
        "ylabel": "Average Age",
        "output_name": "average_age.png",
        "aggregate_output_name": "average_age_mean_std.png",
    },
    {
        "name": "movement_eating",
        "metrics": [("move_rate", "Move Rate"), ("total_eat_rate", "Total Eat Rate")],
        "title": "Movement and Total Eating Rates Over Time",
        "ylabel": "Rate",
        "output_name": "movement_and_eating_rates.png",
        "aggregate_output_name": "movement_eating_mean_std.png",
    },
    {
        "name": "eating_breakdown",
        "metrics": [("eat_after_move_rate", "Eat Success After Move"), ("eat_without_move_rate", "Eat Success Without Move")],
        "title": "Eating Success Rates by Movement State",
        "ylabel": "Rate",
        "output_name": "eating_breakdown_rates.png",
        "aggregate_output_name": "eating_breakdown_rates_mean_std.png",
    },
    {
        "name": "behavior_traits",
        "metrics": [
            ("average_exploration_tendency", "Exploration Tendency"),
            ("average_site_fidelity", "Site Fidelity"),
            ("average_risk_tolerance", "Risk Tolerance"),
            ("average_reproduction_timing", "Reproduction Timing"),
        ],
        "title": "Average Behavior Traits Over Time",
        "ylabel": "Trait Value",
        "output_name": "behavior_traits.png",
        "aggregate_output_name": "behavior_traits_mean_std.png",
        "fixed_ylim": (0.0, 1.0),
    },
    {
        "name": "birth_death_components",
        "metrics": [("birth_rate", "Birth Rate"), ("age_death_rate", "Age Death Rate"), ("energy_death_rate", "Energy Death Rate")],
        "title": "Birth and Death Rates Over Time",
        "ylabel": "Rate",
        "output_name": "birth_death_rates.png",
        "aggregate_output_name": "birth_death_mean_std.png",
    },
    {
        "name": "birth_death_counts",
        "metrics": [("birth_count", "Birth Count"), ("age_death_count", "Age Death Count"), ("energy_death_count", "Energy Death Count")],
        "title": "Birth and Death Counts Over Time",
        "ylabel": "Count",
        "output_name": "birth_count.png",
        "aggregate_output_name": "birth_death_counts_mean_std.png",
    },
    {
        "name": "food_sharing_ratios",
        "metrics": [("shared_food_cell_ratio", "Shared Food Cell Ratio"), ("shared_food_consumer_ratio", "Shared Food Consumer Ratio")],
        "title": "Food Sharing Ratios Over Time",
        "ylabel": "Ratio",
        "output_name": "food_sharing_ratios.png",
        "aggregate_output_name": "food_sharing_ratios_mean_std.png",
        "fixed_ylim": (0.0, 1.0),
    },
    {
        "name": "consumers_per_shared_food",
        "metrics": [("mean_consumers_per_shared_food_plot", "Mean Consumers per Shared Food")],
        "title": "Mean Consumers per Shared Food Over Time",
        "ylabel": "Consumers per Shared Food",
        "output_name": "consumers_per_shared_food.png",
        "aggregate_output_name": "consumers_per_shared_food_mean_std.png",
    },
    {
        "name": "active_lineage_count",
        "metrics": [("active_lineage_count", "Active Lineage Count")],
        "title": "Active Lineages Over Time",
        "ylabel": "Lineage Count",
        "output_name": "active_lineage_count.png",
        "aggregate_output_name": "active_lineage_count_mean_std.png",
    },
    {
        "name": "largest_lineage_share",
        "metrics": [("largest_lineage_share", "Largest Lineage Share")],
        "title": "Largest Lineage Share Over Time",
        "ylabel": "Share",
        "output_name": "largest_lineage_share.png",
        "aggregate_output_name": "largest_lineage_share_mean_std.png",
    },
    {
        "name": "generation_progress",
        "metrics": [("average_generation", "Average Generation"), ("max_generation", "Max Generation")],
        "title": "Generation Progress Over Time",
        "ylabel": "Generation",
        "output_name": "generation.png",
        "aggregate_output_name": "generation_mean_std.png",
    },
    {
        "name": "food_respawn_rate",
        "metrics": [("food_respawn_rate", "Food Respawn Rate")],
        "title": "Food Respawn Rate Over Time",
        "ylabel": "Food Respawn Rate",
        "output_name": "food_respawn_rate.png",
        "aggregate_output_name": "food_respawn_rate_mean_std.png",
    },
    {
        "name": "food_dynamics",
        "metrics": [("food_respawn_count", "Food Respawned"), ("food_consumed_count", "Food Consumed"), ("food_count", "Food Count")],
        "title": "Food Dynamics Over Time",
        "ylabel": "Food Cells",
        "output_name": "food_dynamics.png",
        "aggregate_output_name": "food_dynamics_mean_std.png",
    },
]


def add_derived_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Add shared derived columns used by single- and multi-seed plots."""
    result = df.copy()

    if "food_consumed_count" in result.columns:
        result["consumed_food_cell_count"] = result["food_consumed_count"]
    elif "eat_count" in result.columns:
        non_shared_food_cell_count = (
            result["eat_count"] - result.get("shared_food_consumer_count", 0)
        ).clip(lower=0)
        result["consumed_food_cell_count"] = (
            result.get("shared_food_cell_count", 0) + non_shared_food_cell_count
        )
    else:
        result["consumed_food_cell_count"] = 0

    if "consumed_food_cell_count" in result.columns:
        food_cell_denominator = result["consumed_food_cell_count"].where(
            result["consumed_food_cell_count"] > 0
        )
        result["shared_food_cell_ratio"] = result.get("shared_food_cell_count", 0) / food_cell_denominator

        consumer_denominator = result.get("eat_count", 0).where(result.get("eat_count", 0) > 0)
        result["shared_food_consumer_ratio"] = result.get("shared_food_consumer_count", 0) / consumer_denominator
    else:
        result["shared_food_cell_ratio"] = 0.0
        result["shared_food_consumer_ratio"] = 0.0

    if "mean_consumers_per_shared_food" in result.columns:
        result["mean_consumers_per_shared_food_plot"] = result["mean_consumers_per_shared_food"].where(
            result.get("shared_food_cell_count", 0) > 0
        )
    else:
        result["mean_consumers_per_shared_food_plot"] = pd.NA

    return result


def get_dynamic_ylim_upper(values_list, margin_ratio: float = 0.1, min_upper: float = 0.05) -> float:
    """
    複数の系列データから、見やすいy軸上限を自動計算する。

    Args:
        values_list: pandas Series や list の配列
        margin_ratio: 最大値に対してどれくらい余白を足すか
        min_upper: 上限が小さすぎる場合の最低値

    Returns:
        float: y軸上限
    """
    max_value = 0.0

    for values in values_list:
        current_max = float(values.max()) if len(values) > 0 else 0.0
        if current_max > max_value:
            max_value = current_max

    if max_value <= 0.0:
        return min_upper

    upper = max_value * (1.0 + margin_ratio)
    return max(upper, min_upper)

def plot_single_metrics(
    df: pd.DataFrame,
    output_path: str | Path,
    metrics: list[tuple[str, str]],
    title: str,
    ylabel: str,
    fixed_ylim: tuple[float, float] | None = None,
) -> None:
    """Plot step-wise values for a single seed without mean/std bands."""
    plt.figure(figsize=(10, 6))

    for metric, label in metrics:
        if metric not in df.columns:
            continue
        plt.plot(df["step"], df[metric], linewidth=2, label=label)

    plt.title(title)
    plt.xlabel("Step")
    plt.ylabel(ylabel)

    if fixed_ylim is not None:
        plt.ylim(*fixed_ylim)

    plt.legend(loc="upper right")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def plot_population(df: pd.DataFrame, output_path: str) -> None:
    """Compatibility wrapper for the population plot."""
    plot_single_metrics(
        df,
        output_path,
        [("population_size", "Population")],
        "Population Over Time",
        "Population Size",
    )


def plot_average_energy(df: pd.DataFrame, output_path: str) -> None:
    """Compatibility wrapper for the average energy plot."""
    plot_single_metrics(
        df,
        output_path,
        [("average_energy", "Average Energy")],
        "Average Energy Over Time",
        "Average Energy",
    )


def plot_average_age(df: pd.DataFrame, output_path: str) -> None:
    """Compatibility wrapper for the average age plot."""
    plot_single_metrics(
        df,
        output_path,
        [("average_age", "Average Age")],
        "Average Age Over Time",
        "Average Age",
    )


def plot_birth_count(df: pd.DataFrame, output_path: str) -> None:
    """
    誕生個体数の時系列グラフを生成して保存
    
    Args:
        df: ログデータを持つDataFrame
        output_path: 保存先のファイルパス
    """
    plt.figure(figsize=(10, 6))
    plt.plot(df["step"], df["birth_count"], linewidth=2, color="red")
    plt.title("Birth Count Over Time")
    plt.xlabel("Step")
    plt.ylabel("Number of Births")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def plot_death_count(df: pd.DataFrame, output_path: str) -> None:
    """
    死亡個体数の時系列グラフを生成して保存
    
    Args:
        df: ログデータを持つDataFrame
        output_path: 保存先のファイルパス
    """
    plt.figure(figsize=(10, 6))
    plt.plot(df["step"], df["death_count"], linewidth=2, color="black")
    plt.title("Death Count Over Time")
    plt.xlabel("Step")
    plt.ylabel("Number of Deaths")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def plot_behavior_traits(df: pd.DataFrame, output_path: str) -> None:
    """Compatibility wrapper for the behavior-traits average plot."""
    plot_single_metrics(
        df,
        output_path,
        [
            ("average_exploration_tendency", "Exploration Tendency"),
            ("average_site_fidelity", "Site Fidelity"),
            ("average_risk_tolerance", "Risk Tolerance"),
            ("average_reproduction_timing", "Reproduction Timing"),
        ],
        "Average Behavior Traits Over Time",
        "Trait Value",
        fixed_ylim=(0.0, 1.0),
    )

def plot_trait_range(
    df: pd.DataFrame,
    output_path: str,
    average_col: str,
    min_col: str,
    max_col: str,
    title: str,
    ylabel: str = "Trait Value"
) -> None:
    """
    1つの行動特性について、平均値と最小値〜最大値の範囲を描画して保存する。

    Args:
        df: ログデータを持つDataFrame
        output_path: 保存先のファイルパス
        average_col: 平均値の列名
        min_col: 最小値の列名
        max_col: 最大値の列名
        title: グラフタイトル
        ylabel: y軸ラベル
    """
    plt.figure(figsize=(10, 6))

    line, = plt.plot(
        df["step"],
        df[average_col],
        linewidth=2,
        label="Average"
    )

    plt.fill_between(
        df["step"],
        df[min_col],
        df[max_col],
        alpha=0.2,
        color=line.get_color(),
        label="Min-Max Range"
    )

    plt.title(title)
    plt.xlabel("Step")
    plt.ylabel(ylabel)
    plt.ylim(0, 1.0)
    plt.legend(loc="upper right")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()

def plot_behavior_trait_std(df: pd.DataFrame, output_path: str) -> None:
    """
    行動戦略 phenotype の標準偏差の推移を1枚にまとめて保存する。

    Args:
        df: ログデータを持つDataFrame
        output_path: 保存先のファイルパス
    """
    plt.figure(figsize=(10, 6))

    plt.plot(
        df["step"],
        df["std_exploration_tendency"],
        linewidth=2,
        label="Exploration Tendency"
    )

    plt.plot(
        df["step"],
        df["std_site_fidelity"],
        linewidth=2,
        label="Site Fidelity"
    )

    plt.plot(
        df["step"],
        df["std_risk_tolerance"],
        linewidth=2,
        label="Risk Tolerance"
    )

    plt.plot(
        df["step"],
        df["std_reproduction_timing"],
        linewidth=2,
        label="Reproduction Timing"
    )

    plt.title("Standard Deviation of Behavior Traits Over Time")
    plt.xlabel("Step")
    plt.ylabel("Standard Deviation")
    plt.ylim(0, 0.5)
    plt.legend(loc="upper right")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()

def plot_movement_and_eating_rates(df: pd.DataFrame, output_path: str) -> None:
    """Compatibility wrapper for the movement/eating plot."""
    total_eat_col = "total_eat_rate" if "total_eat_rate" in df.columns else "eat_rate"
    metrics = [("move_rate", "Move Rate"), (total_eat_col, "Total Eat Rate")]
    plot_single_metrics(df, output_path, metrics, "Movement and Eating Rates Over Time", "Rate")

def plot_eating_breakdown_rates(df: pd.DataFrame, output_path: str) -> None:
    """Compatibility wrapper for the eating-breakdown plot."""
    plot_single_metrics(
        df,
        output_path,
        [("eat_after_move_rate", "Eat Success After Move"), ("eat_without_move_rate", "Eat Success Without Move")],
        "Eating Success Rates by Movement State",
        "Rate",
    )

def plot_birth_death_rates(df: pd.DataFrame, output_path: str) -> None:
    """Compatibility wrapper for the birth/death components plot."""
    metrics = [("birth_rate", "Birth Rate"), ("age_death_rate", "Age Death Rate"), ("energy_death_rate", "Energy Death Rate")]
    plot_single_metrics(df, output_path, metrics, "Birth and Death Rates Over Time", "Rate")

def plot_food_dynamics(
    df: pd.DataFrame,
    output_path: str | Path,
) -> None:
    """
    ステップ単位で餌の増減を1枚にまとめて保存する。

    単一seedログまたは複数seed集計データのどちらでも描画できるようにする。
    """
    plt.figure(figsize=(10, 6))

    def _plot_series(mean_values: pd.Series, std_values: pd.Series | None, label: str, color: str) -> None:
        line, = plt.plot(
            df["step"],
            mean_values,
            linewidth=2,
            label=label,
            color=color,
        )
        if std_values is not None:
            lower = (mean_values - std_values).clip(lower=0.0)
            upper = mean_values + std_values
            plt.fill_between(
                df["step"],
                lower,
                upper,
                alpha=0.2,
                color=line.get_color(),
            )

    if all(col in df.columns for col in ["food_respawn_count_mean", "food_respawn_count_std"]):
        _plot_series(
            df["food_respawn_count_mean"],
            df["food_respawn_count_std"].fillna(0.0),
            "Food Respawned",
            "green",
        )
        _plot_series(
            df["food_consumed_count_mean"],
            df["food_consumed_count_std"].fillna(0.0),
            "Food Consumed",
            "red",
        )
        _plot_series(
            df["food_count_mean"],
            df["food_count_std"].fillna(0.0),
            "Food Count",
            "blue",
        )
    else:
        required_columns = {
            "step",
            "food_respawn_count",
            "food_consumed_count",
            "food_count",
        }

        missing_columns = required_columns - set(df.columns)

        if missing_columns:
            raise ValueError(
                "Missing columns for food dynamics plot: "
                f"{sorted(missing_columns)}"
            )

        _plot_series(df["food_respawn_count"], None, "Food Respawned", "green")
        _plot_series(df["food_consumed_count"], None, "Food Consumed", "red")
        _plot_series(df["food_count"], None, "Food Count", "blue")

    plt.title("Food Dynamics Over Time")
    plt.xlabel("Step")
    plt.ylabel("Food Cells")

    if all(col in df.columns for col in ["food_respawn_count_mean", "food_consumed_count_mean", "food_count_mean"]):
        y_upper = get_dynamic_ylim_upper(
            [
                df["food_respawn_count_mean"],
                df["food_consumed_count_mean"],
                df["food_count_mean"],
            ],
            margin_ratio=0.1,
            min_upper=0.05,
        )
    else:
        y_upper = get_dynamic_ylim_upper(
            [
                df["food_respawn_count"],
                df["food_consumed_count"],
                df["food_count"],
            ],
            margin_ratio=0.1,
            min_upper=0.05,
        )

    plt.ylim(0, y_upper)

    plt.legend(loc="upper right")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def plot_food_respawn_rate(
    df: pd.DataFrame,
    output_path: str | Path,
) -> None:
    """
    餌再生成率の時系列グラフを生成して保存する。

    1日につき1点だけ描画することで、
    1日の中で同じ値が複数step続くことによる
    階段状の見た目を避ける。

    Args:
        df:
            food_respawn_rate 列を含むシミュレーションログ
        output_path:
            保存先のファイルパス
    """

    required_columns = {
        "step",
        "simulation_year",
        "day_of_year",
        "food_respawn_rate",
    }

    missing_columns = (
        required_columns - set(df.columns)
    )

    if missing_columns:
        raise ValueError(
            "Missing columns for food respawn plot: "
            f"{sorted(missing_columns)}"
        )

    # -------------------------
    # 1日につき1行だけ取得
    # -------------------------
    daily_df = (
        df
        .drop_duplicates(
            subset=[
                "simulation_year",
                "day_of_year",
            ],
            keep="first",
        )
        .copy()
    )

    plt.figure(figsize=(10, 6))

    plt.plot(
        daily_df["step"],
        daily_df["food_respawn_rate"],
        linewidth=2,
        label="Food Respawn Rate",
    )

    # -------------------------
    # 複数年の場合は年境界を表示
    # -------------------------
    year_changed = (
        daily_df["simulation_year"]
        .ne(
            daily_df["simulation_year"].shift()
        )
    )

    year_start_steps = (
        daily_df.loc[
            year_changed,
            "step",
        ]
        .iloc[1:]
    )

    for step in year_start_steps:
        plt.axvline(
            x=step,
            linestyle="--",
            alpha=0.35,
        )

    plt.title(
        "Food Respawn Rate Over Time"
    )
    plt.xlabel("Step")
    plt.ylabel(
        "Food Respawn Rate"
    )

    y_max = float(
        daily_df[
            "food_respawn_rate"
        ].max()
    )

    plt.ylim(
        0.0,
        max(
            0.05,
            y_max * 1.1,
        ),
    )

    plt.legend(
        loc="upper right"
    )
    plt.grid(
        True,
        alpha=0.3,
    )

    plt.tight_layout()

    plt.savefig(
        output_path,
        dpi=150,
    )

    plt.close()

def save_all_single_run_plots(
    df: pd.DataFrame,
    output_dir: str | Path
) -> None:
    """Save common plots plus single-only plots for a single simulation run."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = add_derived_metrics(df)

    for spec in COMMON_PLOT_SPECS:
        output_path = output_dir / spec["output_name"]
        if spec["name"] == "food_respawn_rate":
            plot_food_respawn_rate(df, output_path)
        elif spec["name"] == "food_dynamics":
            plot_food_dynamics(df, output_path)
        else:
            plot_single_metrics(
                df,
                output_path,
                spec["metrics"],
                spec["title"],
                spec["ylabel"],
                fixed_ylim=spec.get("fixed_ylim"),
            )

    plot_birth_count(df, str(output_dir / "birth_count.png"))
    plot_death_count(df, str(output_dir / "death_count.png"))
    plot_behavior_trait_std(df, str(output_dir / "behavior_trait_std.png"))

    plot_trait_range(
        df,
        str(output_dir / "exploration_tendency_range.png"),
        average_col="average_exploration_tendency",
        min_col="min_exploration_tendency",
        max_col="max_exploration_tendency",
        title="Exploration Tendency Range Over Time"
    )

    plot_trait_range(
        df,
        str(output_dir / "site_fidelity_range.png"),
        average_col="average_site_fidelity",
        min_col="min_site_fidelity",
        max_col="max_site_fidelity",
        title="Site Fidelity Range Over Time"
    )

    plot_trait_range(
        df,
        str(output_dir / "risk_tolerance_range.png"),
        average_col="average_risk_tolerance",
        min_col="min_risk_tolerance",
        max_col="max_risk_tolerance",
        title="Risk Tolerance Range Over Time"
    )

    plot_trait_range(
        df,
        str(output_dir / "reproduction_timing_range.png"),
        average_col="average_reproduction_timing",
        min_col="min_reproduction_timing",
        max_col="max_reproduction_timing",
        title="Reproduction Timing Range Over Time"
    )

def plot_aggregate_mean_std(
    aggregate_df: pd.DataFrame,
    output_path: str | Path,
    metrics: list[tuple[str, str]],
    title: str,
    ylabel: str,
    fixed_ylim: tuple[float, float] | None = None,
) -> None:
    """
    複数seedのstepごとの平均値とseed間標準偏差を描画する。

    Args:
        aggregate_df:
            <指標>_mean と <指標>_std を持つDataFrame
        output_path:
            グラフ保存先
        metrics:
            [(列名の基礎部分, 表示名), ...]
        title:
            グラフタイトル
        ylabel:
            y軸ラベル
        fixed_ylim:
            y軸を固定する場合の範囲
    """
    plt.figure(figsize=(10, 6))

    for metric, label in metrics:
        mean_col = f"{metric}_mean"
        std_col = f"{metric}_std"

        mean_values = aggregate_df[mean_col]
        std_values = aggregate_df[std_col].fillna(0.0)

        line, = plt.plot(
            aggregate_df["step"],
            mean_values,
            linewidth=2,
            label=label
        )

        lower = (mean_values - std_values).clip(lower=0.0)
        upper = mean_values + std_values

        plt.fill_between(
            aggregate_df["step"],
            lower,
            upper,
            alpha=0.2,
            color=line.get_color()
        )

    plt.title(title)
    plt.xlabel("Step")
    plt.ylabel(ylabel)

    if fixed_ylim is not None:
        plt.ylim(*fixed_ylim)

    plt.legend(loc="upper right")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()