"""STEP3の自動集計を既存のrunnerと10seed実験へ組み込む（一度だけ）。

実行場所: daphnia_evolution_sim のルート。
処理: アンカー検証 -> 文法検証 -> 退避 -> 3ファイル修正。
個体の繁殖、遺伝子交換、STEP1/STEP2の計算処理は変更しない。
"""
from __future__ import annotations

import ast
from datetime import datetime
import os
from pathlib import Path
import shutil
import sys

MARKER = "STEP3_GENE_FLOW_V1"
ROOT = Path(__file__).resolve().parent
TARGETS = (
    Path("src/runner.py"),
    Path("src/run_experiments.py"),
    Path("configs/default.yaml"),
)
REQUIRED = (Path("src/analyze_gene_flow.py"), Path("tests/test_gene_flow.py"))


def replace_once(text: str, anchor: str, replacement: str, filename: str) -> str:
    count = text.count(anchor)
    if count != 1:
        raise ValueError(f"{filename}: 挿入箇所が{count}個（期待は1個）: {anchor!r}")
    return text.replace(anchor, replacement, 1)


def patch_content(orig: dict[Path, str]) -> dict[Path, str]:
    runner = TARGETS[0]
    r = orig[runner]
    if "STEP1_AUTO_OUTCOMES_V1" not in r:
        raise ValueError("runner.py にSTEP1実装が見つかりません。現在のコードを確認してください")
    r = replace_once(
        r,
        "    from analyze_offspring_outcomes import analyze_lineage_dataframe\n",
        "    from analyze_offspring_outcomes import analyze_lineage_dataframe\n\n"
        f"# {MARKER}: import\n"
        "try:\n    from src.analyze_gene_flow import save_gene_flow_seed\n"
        "except ImportError:\n    from analyze_gene_flow import save_gene_flow_seed\n",
        str(runner),
    )
    r = replace_once(
        r,
        "        # STEP1_AUTO_OUTCOMES_V1: 出生時の遺伝子交換別の生存・繁殖成績\n",
        f"        # {MARKER}: 既存lineageから提供者・Founder系譜間の遺伝子移動を集計\n"
        "        flow_settings = run_config.get(\"analysis\", {}).get(\"gene_flow\", {})\n"
        "        if flow_settings.get(\"enabled\", True):\n"
        "            save_gene_flow_seed(\n"
        "                lineage_df, output_dir,\n"
        "                last_logged_step=int(df[\"step\"].iloc[-1]),\n"
        "                window_steps=int(flow_settings.get(\"window_steps\", 100)),\n"
        "                save_plots=save_plots,\n"
        "            )\n"
        "            print(f\"遺伝子提供・Founder系譜間の集計完了: {output_dir}\")\n\n"
        "        # STEP1_AUTO_OUTCOMES_V1: 出生時の遺伝子交換別の生存・繁殖成績\n",
        str(runner),
    )

    exp = TARGETS[1]
    e = orig[exp]
    if "STEP1_AUTO_OUTCOMES_V1" not in e or "def main()" not in e:
        raise ValueError("run_experiments.py の既存構成を確認できません")
    e = replace_once(
        e,
        "    from analyze_offspring_outcomes import aggregate_experiment_outcomes\n",
        "    from analyze_offspring_outcomes import aggregate_experiment_outcomes\n\n"
        f"# {MARKER}: import\n"
        "try:\n    from src.analyze_gene_flow import aggregate_gene_flow_experiment\n"
        "except ImportError:\n    from analyze_gene_flow import aggregate_gene_flow_experiment\n",
        str(exp),
    )
    e = replace_once(
        e,
        "    # 全seedのFounder系統summaryを結合\n",
        f"    # {MARKER}: seed間の提供関係・交差Founder遺伝子移動を集計\n"
        "    flow_settings = config.get(\"analysis\", {}).get(\"gene_flow\", {})\n"
        "    if flow_settings.get(\"enabled\", True):\n"
        "        aggregate_gene_flow_experiment(experiment_dir, args.seeds)\n"
        "        print(\"遺伝子提供・Founder系譜間のseed間集計完了\")\n\n"
        "    # 全seedのFounder系統summaryを結合\n",
        str(exp),
    )
    cfg = TARGETS[2]
    c = orig[cfg]
    c = replace_once(
        c,
        "    save_individual: false  # trueなら個体別の大きなCSVも保存\n",
        "    save_individual: false  # trueなら個体別の大きなCSVも保存\n"
        f"  # {MARKER}: 系譜・遺伝子提供関係の集計\n"
        "  gene_flow:\n"
        "    enabled: true\n"
        "    window_steps: 100  # 一定期間ごとの遺伝子交換・提供関係の推移\n",
        str(cfg),
    )
    ast.parse(r, filename=str(runner))
    ast.parse(e, filename=str(exp))
    return {runner: r, exp: e, cfg: c}


def install(root: Path = ROOT) -> str:
    for name in (*TARGETS, *REQUIRED):
        if not (root / name).is_file():
            raise FileNotFoundError(f"必要なファイルがありません: {root / name}")
    originals = {path: (root / path).read_text(encoding="utf-8") for path in TARGETS}
    installed = {path: MARKER in value for path, value in originals.items()}
    if all(installed.values()):
        return "すでにSTEP3が導入済みです。ファイルの変更はありません。"
    if any(installed.values()):
        raise RuntimeError("STEP3の一部だけが導入されています。安全のため停止しました。バックアップ等を確認してください")
    patched = patch_content(originals)
    # 設定をロードして階層を検証（設定変更はこの場ではしない）
    try:
        import yaml
        parsed = yaml.safe_load(patched[TARGETS[2]])
        assert parsed["analysis"]["gene_flow"]["window_steps"] == 100
    except Exception as exc:
        raise ValueError(f"default.yaml の検証に失敗: {exc}") from exc
    backup = root / "step3_gene_flow_backup" / datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = 1
    while backup.exists():
        backup = root / "step3_gene_flow_backup" / (datetime.now().strftime("%Y%m%d_%H%M%S") + f"_{suffix}")
        suffix += 1
    for path in TARGETS:
        dest = backup / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / path, dest)
    written: list[Path] = []
    try:
        for path in TARGETS:
            dst = root / path
            temp = dst.with_name(dst.name + ".step3_temp")
            try:
                temp.write_text(patched[path], encoding="utf-8", newline="\n")
                os.replace(temp, dst)
            finally:
                if temp.exists():
                    temp.unlink()
            written.append(path)
    except Exception:
        for path in written:
            shutil.copy2(backup / path, root / path)
        raise
    return f"STEP3の自動集計を追加しました。変更前のバックアップ: {backup}"


if __name__ == "__main__":
    try:
        print(install())
        print("次は python -m pytest tests/test_gene_flow.py -q を実行してください")
    except Exception as error:
        print(f"STEP3導入に失敗（可能な限り既存ファイルは維持）: {error}", file=sys.stderr)
        sys.exit(1)
