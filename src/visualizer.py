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
