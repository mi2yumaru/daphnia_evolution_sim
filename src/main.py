"""
main.py - シミュレーション実行エントリーポイント

設定ファイルを読み込み、シミュレーションを実行し、結果を出力
"""

import sys
from pathlib import Path
import yaml
try:
    from src.simulation import Simulation
    from src.visualizer import (
        plot_population,
        plot_average_energy,
        plot_average_age,
        plot_birth_count,
        plot_death_count,
        plot_behavior_traits,
        plot_trait_range,
        plot_behavior_trait_std,
        plot_movement_and_eating_rates,
        plot_eat_per_move,
        plot_birth_death_rates,
    )
    from src.live_visualizer import run_live_visualization
except Exception:
    # running as a script (python src/main.py) — fall back to top-level imports
    from simulation import Simulation
    from visualizer import (
        plot_population,
        plot_average_energy,
        plot_average_age,
        plot_birth_count,
        plot_death_count,
        plot_behavior_traits,
        plot_trait_range,
        plot_behavior_trait_std,
        plot_movement_and_eating_rates,
        plot_eat_per_move,
        plot_birth_death_rates,
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
    
    behavior_traits_plot_path = project_root / config["simulation"].get("behavior_traits_plot", "results/behavior_traits.png")
    plot_behavior_traits(df, str(behavior_traits_plot_path))
    print(f"行動戦略グラフを保存しました: {behavior_traits_plot_path}")

    behavior_trait_std_plot_path = project_root / config["simulation"].get("behavior_trait_std_plot", "results/behavior_trait_std.png")
    plot_behavior_trait_std(df, str(behavior_trait_std_plot_path))
    print(f"行動戦略の標準偏差グラフを保存しました: {behavior_trait_std_plot_path}")

    exploration_range_plot_path = project_root / "results/exploration_tendency_range.png"
    plot_trait_range(
        df,
        str(exploration_range_plot_path),
        average_col="average_exploration_tendency",
        min_col="min_exploration_tendency",
        max_col="max_exploration_tendency",
        title="Exploration Tendency Range Over Time"
    )
    print(f"探索傾向の範囲グラフを保存しました: {exploration_range_plot_path}")

    site_fidelity_range_plot_path = project_root / "results/site_fidelity_range.png"
    plot_trait_range(
        df,
        str(site_fidelity_range_plot_path),
        average_col="average_site_fidelity",
        min_col="min_site_fidelity",
        max_col="max_site_fidelity",
        title="Site Fidelity Range Over Time"
    )
    print(f"餌場定着傾向の範囲グラフを保存しました: {site_fidelity_range_plot_path}")

    risk_tolerance_range_plot_path = project_root / "results/risk_tolerance_range.png"
    plot_trait_range(
        df,
        str(risk_tolerance_range_plot_path),
        average_col="average_risk_tolerance",
        min_col="min_risk_tolerance",
        max_col="max_risk_tolerance",
        title="Risk Tolerance Range Over Time"
    )
    print(f"リスク許容度の範囲グラフを保存しました: {risk_tolerance_range_plot_path}")

    reproduction_timing_range_plot_path = project_root / "results/reproduction_timing_range.png"
    plot_trait_range(
        df,
        str(reproduction_timing_range_plot_path),
        average_col="average_reproduction_timing",
        min_col="min_reproduction_timing",
        max_col="max_reproduction_timing",
        title="Reproduction Timing Range Over Time"
    )
    print(f"繁殖タイミングの範囲グラフを保存しました: {reproduction_timing_range_plot_path}")

    movement_and_eating_rates_plot_path = project_root / config["simulation"].get(
        "movement_and_eating_rates_plot",
        "results/movement_and_eating_rates.png"
    )
    plot_movement_and_eating_rates(df, str(movement_and_eating_rates_plot_path))
    print(f"移動率・摂食率グラフを保存しました: {movement_and_eating_rates_plot_path}")

    eat_per_move_plot_path = project_root / config["simulation"].get(
        "eat_per_move_plot",
        "results/eat_per_move.png"
    )
    plot_eat_per_move(df, str(eat_per_move_plot_path))
    print(f"移動あたり摂食成功率グラフを保存しました: {eat_per_move_plot_path}")

    birth_death_rates_plot_path = project_root / config["simulation"].get(
        "birth_death_rates_plot",
        "results/birth_death_rates.png"
    )
    plot_birth_death_rates(df, str(birth_death_rates_plot_path))
    print(f"出生率・死亡率グラフを保存しました: {birth_death_rates_plot_path}")

    # 最終統計情報を表示
    print("\n=== シミュレーション完了 ===")
    print(f"最終個体数: {len(sim.organisms)}")
    print(f"最終食料数: {sim.environment.food_count()}")
    if len(sim.organisms) > 0:
        final_avg_energy = sum(org.energy for org in sim.organisms) / len(sim.organisms)
        print(f"最終平均エネルギー: {final_avg_energy:.2f}")


if __name__ == "__main__":
    main()
