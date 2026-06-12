"""
visualizer.py - シミュレーション結果の可視化

グラフ出力用の関数群
"""
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

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

def plot_population(df: pd.DataFrame, output_path: str) -> None:
    """
    個体数の時系列グラフを生成して保存
    
    Args:
        df: ログデータを持つDataFrame
        output_path: 保存先のファイルパス
    """
    plt.figure(figsize=(10, 6))
    plt.plot(df["step"], df["population_size"], linewidth=2, color="blue")
    plt.title("Population Over Time")
    plt.xlabel("Step")
    plt.ylabel("Population Size")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def plot_average_energy(df: pd.DataFrame, output_path: str) -> None:
    """
    平均エネルギーの時系列グラフを生成して保存
    
    Args:
        df: ログデータを持つDataFrame
        output_path: 保存先のファイルパス
    """
    plt.figure(figsize=(10, 6))
    plt.plot(df["step"], df["average_energy"], linewidth=2, color="green")
    plt.title("Average Energy Over Time")
    plt.xlabel("Step")
    plt.ylabel("Average Energy")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def plot_average_age(df: pd.DataFrame, output_path: str) -> None:
    """
    平均年齢の時系列グラフを生成して保存
    
    Args:
        df: ログデータを持つDataFrame
        output_path: 保存先のファイルパス
    """
    plt.figure(figsize=(10, 6))
    plt.plot(df["step"], df["average_age"], linewidth=2, color="orange")
    plt.title("Average Age Over Time")
    plt.xlabel("Step")
    plt.ylabel("Average Age")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


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
    """
    行動戦略 phenotype の平均値推移を1枚にまとめて保存
    
    Args:
        df: ログデータを持つDataFrame
        output_path: 保存先のファイルパス
    """
    plt.figure(figsize=(10, 6))
    plt.plot(
        df["step"],
        df["average_exploration_tendency"],
        label="Exploration Tendency",
        linewidth=2
    )

    plt.plot(
        df["step"],
        df["average_site_fidelity"],
        label="Site Fidelity",
        linewidth=2
    )

    plt.plot(
        df["step"],
        df["average_risk_tolerance"],
        label="Risk Tolerance",
        linewidth=2
    )

    plt.plot(
        df["step"],
        df["average_reproduction_timing"],
        label="Reproduction Timing",
        linewidth=2
    )

    plt.title("Average Behavior Traits Over Time")
    plt.xlabel("Step")
    plt.ylabel("Trait Value")
    plt.ylim(0, 1.0)
    plt.legend(loc="upper right")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()

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
    """
    移動率と摂食率の推移を1枚にまとめて保存する。

    Args:
        df: ログデータを持つDataFrame
        output_path: 保存先のファイルパス
    """
    plt.figure(figsize=(10, 6))

    plt.plot(
        df["step"],
        df["move_rate"],
        linewidth=2,
        label="Move Rate"
    )

    plt.plot(
        df["step"],
        df["eat_rate"],
        linewidth=2,
        label="Eat Rate"
    )

    plt.title("Movement and Eating Rates Over Time")
    plt.xlabel("Step")
    plt.ylabel("Rate")

    y_upper = get_dynamic_ylim_upper(
        [df["move_rate"], df["eat_rate"]],
        margin_ratio=0.1,
        min_upper=0.05
    )
    plt.ylim(0, y_upper)

    plt.legend(loc="upper right")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()

def plot_eat_per_move(df: pd.DataFrame, output_path: str) -> None:
    """
    移動1回あたりの摂食成功数の推移を保存する。

    Args:
        df: ログデータを持つDataFrame
        output_path: 保存先のファイルパス
    """
    plt.figure(figsize=(10, 6))

    plt.plot(
        df["step"],
        df["eat_per_move"],
        linewidth=2,
        label="Eat per Move"
    )

    plt.title("Eat per Move Over Time")
    plt.xlabel("Step")
    plt.ylabel("Eat per Move")

    y_upper = get_dynamic_ylim_upper(
        [df["eat_per_move"]],
        margin_ratio=0.1,
        min_upper=0.1
    )
    plt.ylim(0, y_upper)

    plt.legend(loc="upper right")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()

def plot_birth_death_rates(df: pd.DataFrame, output_path: str) -> None:
    """
    出生率と死亡率の推移を1枚にまとめて保存する。

    Args:
        df: ログデータを持つDataFrame
        output_path: 保存先のファイルパス
    """
    plt.figure(figsize=(10, 6))

    plt.plot(
        df["step"],
        df["birth_rate"],
        linewidth=2,
        label="Birth Rate"
    )

    plt.plot(
        df["step"],
        df["death_rate"],
        linewidth=2,
        label="Death Rate"
    )

    plt.title("Birth and Death Rates Over Time")
    plt.xlabel("Step")
    plt.ylabel("Rate")

    y_upper = get_dynamic_ylim_upper(
        [df["birth_rate"], df["death_rate"]],
        margin_ratio=0.1,
        min_upper=0.05
    )
    plt.ylim(0, y_upper)

    plt.legend(loc="upper right")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()

def save_all_single_run_plots(
    df: pd.DataFrame,
    output_dir: str | Path
) -> None:
    """
    単一seed実行用のグラフをまとめて保存する。

    Args:
        df: 1回分のシミュレーションログ
        output_dir: 出力先ディレクトリ
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    plot_population(
        df,
        str(output_dir / "population.png")
    )

    plot_average_energy(
        df,
        str(output_dir / "average_energy.png")
    )

    plot_average_age(
        df,
        str(output_dir / "average_age.png")
    )

    plot_birth_count(
        df,
        str(output_dir / "birth_count.png")
    )

    plot_death_count(
        df,
        str(output_dir / "death_count.png")
    )

    plot_behavior_traits(
        df,
        str(output_dir / "behavior_traits.png")
    )

    plot_behavior_trait_std(
        df,
        str(output_dir / "behavior_trait_std.png")
    )

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

    plot_movement_and_eating_rates(
        df,
        str(output_dir / "movement_and_eating_rates.png")
    )

    plot_eat_per_move(
        df,
        str(output_dir / "eat_per_move.png")
    )

    plot_birth_death_rates(
        df,
        str(output_dir / "birth_death_rates.png")
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