"""
main.py - シミュレーション実行エントリーポイント

設定ファイルを読み込み、シミュレーションを実行し、結果を出力
"""

from pathlib import Path
import yaml
from simulation import Simulation
from logger import SimulationLogger
from visualizer import plot_population, plot_average_energy


def main() -> None:
    """
    メイン実行関数
    
    1. configs/default.yaml を読み込む
    2. Simulation を作成して run() する
    3. ログをCSVに保存する
    4. グラフを生成して保存する
    5. 出力ファイルのパスを表示する
    """
    # プロジェクトルート（main.py の親親ディレクトリ）を取得
    project_root = Path(__file__).parent.parent
    config_path = project_root / "configs" / "default.yaml"
    
    # 設定ファイルを読み込む
    print(f"設定ファイルを読み込んでいます: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    # 出力ディレクトリを作成（存在しなければ）
    results_dir = project_root / "results"
    results_dir.mkdir(exist_ok=True)
    
    # シミュレーションを実行
    print("シミュレーションを実行中...")
    sim = Simulation(config)
    sim.run()
    print(f"シミュレーション完了。{sim.current_step} ステップ実行しました。")
    
    # ログをCSVに保存
    csv_path = project_root / config["simulation"]["output_csv"]
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    sim.logger.save_csv(str(csv_path))
    print(f"ログをCSVに保存しました: {csv_path}")
    
    # グラフを生成して保存
    df = sim.logger.to_dataframe()
    
    population_plot_path = project_root / config["simulation"]["population_plot"]
    plot_population(df, str(population_plot_path))
    print(f"個体数グラフを保存しました: {population_plot_path}")
    
    energy_plot_path = project_root / config["simulation"]["energy_plot"]
    plot_average_energy(df, str(energy_plot_path))
    print(f"平均エネルギーグラフを保存しました: {energy_plot_path}")
    
    # 最終統計情報を表示
    print("\n=== シミュレーション完了 ===")
    print(f"最終個体数: {len(sim.organisms)}")
    print(f"最終食料数: {sim.environment.food_count()}")
    if len(sim.organisms) > 0:
        final_avg_energy = sum(org.energy for org in sim.organisms) / len(sim.organisms)
        print(f"最終平均エネルギー: {final_avg_energy:.2f}")


if __name__ == "__main__":
    main()
