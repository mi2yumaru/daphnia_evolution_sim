"""
main.py - シミュレーション実行エントリーポイント

設定ファイルを読み込み、シミュレーションを実行し、結果を出力
"""

import sys
from pathlib import Path
import yaml
from simulation import Simulation
from visualizer import (
    plot_population,
    plot_average_energy,
    plot_average_age,
    plot_birth_count,
    plot_death_count
)
from live_visualizer import run_live_visualization


def print_usage():
    """使用方法を表示"""
    print("使用方法:")
    print("  通常モード (CSV と静的グラフを出力):")
    print("    python src/main.py")
    print()
    print("  リアルタイム可視化モード:")
    print("    python src/main.py --live")
    print()
    print("  ヘルプ表示:")
    print("    python src/main.py --help")


def main() -> None:
    """
    メイン実行関数
    
    1. configs/default.yaml を読み込む
    2. コマンドラインオプションを処理
    3. 通常モードまたはリアルタイム可視化モードでシミュレーションを実行
    4. ログをCSVに保存する
    5. グラフを生成して保存する
    6. 出力ファイルのパスを表示する
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
    
    # コマンドラインオプションを処理
    live_mode = False
    if len(sys.argv) > 1:
        if sys.argv[1] == "--live":
            live_mode = True
        elif sys.argv[1] in ["--help", "-h"]:
            print_usage()
            return
        else:
            print(f"不明なオプション: {sys.argv[1]}")
            print_usage()
            return
    
    # シミュレーションを実行
    print("シミュレーションを作成中...")
    sim = Simulation(config)
    
    if live_mode:
        print("リアルタイム可視化モードで実行中...")
        run_live_visualization(sim)
    else:
        print("通常モードで実行中...")
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
    
    age_plot_path = project_root / config["simulation"].get("average_age_plot", "results/average_age.png")
    plot_average_age(df, str(age_plot_path))
    print(f"平均年齢グラフを保存しました: {age_plot_path}")
    
    birth_plot_path = project_root / config["simulation"].get("birth_count_plot", "results/birth_count.png")
    plot_birth_count(df, str(birth_plot_path))
    print(f"誕生数グラフを保存しました: {birth_plot_path}")
    
    death_plot_path = project_root / config["simulation"].get("death_count_plot", "results/death_count.png")
    plot_death_count(df, str(death_plot_path))
    print(f"死亡数グラフを保存しました: {death_plot_path}")
    
    # 最終統計情報を表示
    print("\n=== シミュレーション完了 ===")
    print(f"最終個体数: {len(sim.organisms)}")
    print(f"最終食料数: {sim.environment.food_count()}")
    if len(sim.organisms) > 0:
        final_avg_energy = sum(org.energy for org in sim.organisms) / len(sim.organisms)
        print(f"最終平均エネルギー: {final_avg_energy:.2f}")


if __name__ == "__main__":
    main()
