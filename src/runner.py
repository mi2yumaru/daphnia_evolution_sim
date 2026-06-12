"""
runner.py - 単一シミュレーション実行の共通処理
"""

from copy import deepcopy
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from src.simulation import Simulation
    from src.live_visualizer import run_live_visualization
    from src.visualizer import save_all_single_run_plots
except ImportError:
    from simulation import Simulation
    from live_visualizer import run_live_visualization
    from visualizer import save_all_single_run_plots


def run_single_simulation(
    config: dict[str, Any],
    seed: int,
    output_dir: str | Path,
    live: bool = False,
    save_csv: bool = True,
    save_plots: bool = True,
) -> pd.DataFrame:
    """
    指定seedでシミュレーションを1回実行する。

    Args:
        config: YAMLから読み込んだ設定辞書
        seed: 使用する乱数seed
        output_dir: CSV・グラフの保存先
        live: リアルタイム可視化を行うか
        save_csv: 詳細ログCSVを保存するか
        save_plots: 静的グラフを保存するか

    Returns:
        1回分のログDataFrame
    """
    run_config = deepcopy(config)
    run_config["simulation"]["random_seed"] = seed

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    sim = Simulation(run_config)

    if live:
        run_live_visualization(sim)
    else:
        sim.run()

    df = sim.logger.to_dataframe()

    if save_csv:
        csv_path = output_dir / "log.csv"
        sim.logger.save_csv(str(csv_path))

    if save_plots:
        save_all_single_run_plots(df, output_dir)

    return df