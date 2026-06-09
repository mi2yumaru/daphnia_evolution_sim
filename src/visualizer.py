"""
visualizer.py - シミュレーション結果の可視化

グラフ出力用の関数群
"""

import pandas as pd
import matplotlib.pyplot as plt


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

def plot_move_rate(df: pd.DataFrame, output_path: str) -> None:
    """
    移動率の時系列グラフを生成して保存する。

    Args:
        df: ログデータを持つDataFrame
        output_path: 保存先のファイルパス
    """
    plt.figure(figsize=(10, 6))
    plt.plot(df["step"], df["move_rate"], linewidth=2)
    plt.title("Move Rate Over Time")
    plt.xlabel("Step")
    plt.ylabel("Move Rate")
    plt.ylim(0, 1.0)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
    
def plot_eat_rate(df: pd.DataFrame, output_path: str) -> None:
    """
    摂食率の時系列グラフを生成して保存する。

    Args:
        df: ログデータを持つDataFrame
        output_path: 保存先のファイルパス
    """
    plt.figure(figsize=(10, 6))
    plt.plot(df["step"], df["eat_rate"], linewidth=2)
    plt.title("Eat Rate Over Time")
    plt.xlabel("Step")
    plt.ylabel("Eat Rate")
    plt.ylim(0, 1.0)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()