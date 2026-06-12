"""
main.py - 単一seedシミュレーションの実行エントリーポイント

指定した乱数seedでシミュレーションを1回実行する。
ライブ可視化、CSV保存、静的グラフ保存をオプションで切り替えられる。
"""

import argparse
from pathlib import Path

import yaml

try:
    # プロジェクトルートからモジュールとして実行する場合
    from src.runner import run_single_simulation
except ImportError:
    # python src/main.py として直接実行する場合
    from runner import run_single_simulation


def parse_args() -> argparse.Namespace:
    """
    コマンドライン引数を解析する。

    Returns:
        argparse.Namespace: 解析済みの引数
    """
    parser = argparse.ArgumentParser(
        description="ミジンコ進化シミュレーションを単一seedで実行します。"
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help=(
            "使用する乱数seed。"
            "省略した場合は configs/default.yaml の random_seed を使用します。"
        ),
    )

    parser.add_argument(
        "--live",
        action="store_true",
        help="リアルタイム可視化を有効にします。",
    )

    parser.add_argument(
        "--no-plots",
        action="store_true",
        help="実行後の静的グラフを保存しません。",
    )

    parser.add_argument(
        "--no-csv",
        action="store_true",
        help="各ステップの詳細ログCSVを保存しません。",
    )

    return parser.parse_args()


def main() -> None:
    """
    単一seedのシミュレーションを実行する。
    """
    args = parse_args()

    # プロジェクトルートと設定ファイルのパス
    project_root = Path(__file__).resolve().parent.parent
    config_path = project_root / "configs" / "default.yaml"

    print(f"設定ファイルを読み込んでいます: {config_path}")

    with open(config_path, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    # --seed が指定されていれば優先し、
    # 指定されていなければ default.yaml の値を使う
    if args.seed is not None:
        seed = args.seed
    else:
        seed = int(config["simulation"]["random_seed"])

    # seedごとに出力ディレクトリを分ける
    output_dir = (
        project_root
        / "results"
        / "single_runs"
        / f"seed_{seed}"
    )

    print("\n=== 単一seedシミュレーション ===")
    print(f"seed: {seed}")
    print(f"ライブ可視化: {'あり' if args.live else 'なし'}")
    print(f"CSV保存: {'なし' if args.no_csv else 'あり'}")
    print(f"グラフ保存: {'なし' if args.no_plots else 'あり'}")
    print(f"出力先: {output_dir}")
    print()

    df = run_single_simulation(
        config=config,
        seed=seed,
        output_dir=output_dir,
        live=args.live,
        save_csv=not args.no_csv,
        save_plots=not args.no_plots,
    )

    if df.empty:
        print("シミュレーションログが空です。")
        return

    print("\n=== シミュレーション完了 ===")
    print(f"記録ステップ数: {len(df)}")
    print(f"最終個体数: {int(df['population_size'].iloc[-1])}")
    print(f"最終食料数: {int(df['food_count'].iloc[-1])}")
    print(f"最終平均エネルギー: {df['average_energy'].iloc[-1]:.2f}")
    print(f"結果保存先: {output_dir}")


if __name__ == "__main__":
    main()