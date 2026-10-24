"""STEP1自動集計を既存のrunnerとrun_experimentsへ追加する、一度だけ実行する導入スクリプト。

既存の進化・繁殖アルゴリズムは変更しない。マーカーによって二重挿入を防ぐ。
読み込み対象: src/runner.py, src/run_experiments.py, configs/default.yaml
"""
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent
MARKER = "# STEP1_AUTO_OUTCOMES_V1"
RUNNER = ROOT / "src" / "runner.py"
MULTI = ROOT / "src" / "run_experiments.py"
CONFIG = ROOT / "configs" / "default.yaml"
ANALYZER = ROOT / "src" / "analyze_offspring_outcomes.py"

RUNNER_IMPORT = '''# STEP1_AUTO_OUTCOMES_V1: import
try:
    from src.analyze_offspring_outcomes import analyze_lineage_dataframe
except ImportError:
    from analyze_offspring_outcomes import analyze_lineage_dataframe

'''

RUNNER_HOOK = '''        # STEP1_AUTO_OUTCOMES_V1: 出生時の遺伝子交換別の生存・繁殖成績
        analysis_settings = run_config.get("analysis", {}).get("offspring_outcomes", {})
        if analysis_settings.get("enabled", True):
            outcome_horizon = int(analysis_settings.get("horizon_steps", 200))
            outcome_individual, outcome_summary = analyze_lineage_dataframe(
                lineage_df,
                last_logged_step=int(df["step"].iloc[-1]),
                horizon_steps=outcome_horizon,
            )
            outcome_summary.to_csv(
                output_dir / "offspring_outcomes_by_group.csv", index=False
            )
            if analysis_settings.get("save_individual", False):
                outcome_individual.to_csv(
                    output_dir / "offspring_outcomes_individual.csv", index=False
                )
            print(f"生存・繁殖成績の自動集計完了: {output_dir}")

'''

MULTI_IMPORT = '''# STEP1_AUTO_OUTCOMES_V1: import
try:
    from src.analyze_offspring_outcomes import aggregate_experiment_outcomes
except ImportError:
    from analyze_offspring_outcomes import aggregate_experiment_outcomes

'''

MULTI_HOOK = '''    # STEP1_AUTO_OUTCOMES_V1: seed間の追加集計
    analysis_settings = config.get("analysis", {}).get("offspring_outcomes", {})
    if analysis_settings.get("enabled", True):
        aggregate_experiment_outcomes(
            experiment_dir=experiment_dir,
            seeds=args.seeds,
            horizon_steps=int(analysis_settings.get("horizon_steps", 200)),
        )
        print("生存・繁殖成績のseed間集計完了")

'''

CONFIG_ADD = '''\n# STEP1_AUTO_OUTCOMES_V1: 生存・繁殖成績の自動集計\nanalysis:\n  offspring_outcomes:\n    enabled: true\n    horizon_steps: 200  # 比較前に固定する観察期間（ステップ）\n    save_individual: false  # trueなら個体別の大きなCSVも保存\n'''


def insert_once(contents: str, anchor: str, new_text: str, file_name: str) -> str:
    if contents.count(anchor) != 1:
        raise ValueError(f"{file_name}: 挿入位置が見つからないか複数あります。元コードが変更されている可能性があります。")
    return contents.replace(anchor, new_text + anchor, 1)


def main() -> None:
    for path in (RUNNER, MULTI, CONFIG, ANALYZER):
        if not path.is_file():
            raise FileNotFoundError(f"必要なファイルがありません: {path}")

    runner = RUNNER.read_text(encoding="utf-8")
    multi = MULTI.read_text(encoding="utf-8")
    cfg = CONFIG.read_text(encoding="utf-8")

    state = [MARKER in content for content in (runner, multi, cfg)]
    if all(state):
        print("STEP1の自動集計は導入済みです。重複変更しません。")
        return
    if any(state):
        raise RuntimeError("STEP1の導入が一部だけ済んでいます。手動で状態を確認してください。")

    import re
    if re.search(r"(?m)^analysis\s*:", cfg):
        raise RuntimeError("default.yamlに既存のanalysis:があります。重複を避けるため導入を中止しました。")

    # 既存の記述を置き換えるのではなく、正確に照合できる位置に追加する。
    runner2 = insert_once(runner, "def resolve_total_steps(", RUNNER_IMPORT, str(RUNNER))
    runner2 = insert_once(runner2, "        # Founder系統×行動戦略summary\n", RUNNER_HOOK, str(RUNNER))
    multi2 = insert_once(multi, "def parse_args()", MULTI_IMPORT, str(MULTI))
    multi2 = insert_once(multi2, "    # 全seedのFounder系統summaryを結合\n", MULTI_HOOK, str(MULTI))
    # 必ず全ての変更点をチェックしてから書き出す。
    cfg2 = cfg.rstrip("\n") + "\n" + CONFIG_ADD.lstrip("\n")

    backup = ROOT / "step1_auto_backup"
    backup.mkdir(exist_ok=True)
    for path in (RUNNER, MULTI, CONFIG):
        target = backup / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copy2(path, target)

    for path, contents in ((RUNNER, runner2), (MULTI, multi2), (CONFIG, cfg2)):
        path.write_text(contents, encoding="utf-8")
    print("STEP1の自動集計を組み込みました。")
    print("元ファイルのバックアップ: step1_auto_backup/")
    print("実行例: python src/run_experiments.py --seeds 0 1 2 --experiment-name outcome_smoke_test")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"導入を中止しました: {exc}", file=sys.stderr)
        sys.exit(1)
