"""STEP2: 遺伝的多様性を既存の daphnia_evolution_sim に組み込む。

使い方（プロジェクト直下）:
    python apply_step2_genetic_diversity.py

1. 最初に全ファイルの挿入箇所を検証
2. 現状を step2_genetic_diversity_backup/ にバックアップ
3. 新しいログ・単一/複数seedグラフ・summary の最小変更を追加
既存のシミュレーションの個体行動、繁殖・交換処理は変更しません。
"""

from __future__ import annotations

import ast
from datetime import datetime
from pathlib import Path
import shutil
import sys

MARKER = "STEP2_GENETIC_DIVERSITY_V1"
PROJECT = Path(__file__).resolve().parent
TARGETS = (
    Path("src/simulation.py"),
    Path("src/logger.py"),
    Path("src/visualizer.py"),
    Path("src/run_experiments.py"),
)
NEW_SOURCE = Path("src/genetic_diversity.py")
NEW_TEST = Path("tests/test_genetic_diversity.py")
METRICS = (
    "genetic_diversity_all",
    "genetic_diversity_behavior",
    "genetic_diversity_exchange",
    "genotype_diversity",
    "unique_genotype_ratio",
)


def insert_before(s: str, needle: str, addition: str, file_name: str) -> str:
    count = s.count(needle)
    if count != 1:
        raise ValueError(f"{file_name}: 一致する挿入箇所が {count} 件（期待: 1）。変更を停止します: {needle!r}")
    return s.replace(needle, addition + needle, 1)


def build_patches(originals: dict[Path, str]) -> dict[Path, str]:
    changed = {}

    path = TARGETS[0]
    src = originals[path]
    src = insert_before(src, "import numpy as np\n", "# " + MARKER + "\n", path.as_posix())
    src = insert_before(
        src,
        "        # 系譜統計を計算\n",
        "        # " + MARKER + ": 遺伝的多様性はstep末の生存集団を対象に計算\n"
        "        diversity_metrics = calculate_genetic_diversity(self.organisms)\n\n",
        path.as_posix(),
    )
    src = insert_before(src, "        self.logger.record(\n", "", path.as_posix())
    src = insert_before(src, "            active_lineage_count=active_lineage_count,\n", "            **diversity_metrics,\n", path.as_posix())
    # Import は既存の二通りの import と同様にモジュール/直接起動に対応
    src = insert_before(
        src,
        "import numpy as np\n",
        "", path.as_posix(),
    )
    src = src.replace(
        "# " + MARKER + "\nimport numpy as np\n",
        "import numpy as np\n\n"
        "# " + MARKER + ": 遺伝的多様性の算出\n"
        "try:\n    from .genetic_diversity import calculate_genetic_diversity\n"
        "except ImportError:\n    from genetic_diversity import calculate_genetic_diversity\n",
        1,
    )
    changed[path] = src

    path = TARGETS[1]
    src = originals[path]
    signature = "".join(f"        {key}: float,\n" for key in METRICS)
    src = insert_before(src, "        active_lineage_count: int,\n", "        # " + MARKER + "\n" + signature, path.as_posix())
    src = insert_before(
        src, '            "active_lineage_count": active_lineage_count,\n',
        "            # " + MARKER + "\n" +
        "".join(f'            "{key}": {key},\n' for key in METRICS),
        path.as_posix(),
    )
    changed[path] = src

    path = TARGETS[2]
    src = originals[path]
    specs = (
        "    # " + MARKER + "\n"
        "    {\n"
        '        "name": "genetic_diversity",\n'
        '        "metrics": [\n'
        '            ("genetic_diversity_all", "All 120 loci"),\n'
        '            ("genetic_diversity_behavior", "Behavior 80 loci"),\n'
        '            ("genetic_diversity_exchange", "Exchange 40 loci"),\n'
        '        ],\n'
        '        "title": "Within-Population Genetic Diversity (2p(1-p))",\n'
        '        "ylabel": "Mean locus diversity",\n'
        '        "output_name": "genetic_diversity.png",\n'
        '        "aggregate_output_name": "genetic_diversity_mean_std.png",\n'
        '        "fixed_ylim": (0.0, 0.5),\n'
        "    },\n"
        "    {\n"
        '        "name": "genotype_diversity",\n'
        '        "metrics": [\n'
        '            ("genotype_diversity", "Genotype Simpson diversity"),\n'
        '            ("unique_genotype_ratio", "Unique genotype ratio"),\n'
        '        ],\n'
        '        "title": "Whole-Genome Genotype Diversity",\n'
        '        "ylabel": "Diversity / Ratio",\n'
        '        "output_name": "genotype_diversity.png",\n'
        '        "aggregate_output_name": "genotype_diversity_mean_std.png",\n'
        '        "fixed_ylim": (0.0, 1.0),\n'
        "    },\n"
    )
    src = insert_before(src, "]\n\n\ndef add_derived_metrics(", specs, path.as_posix())
    changed[path] = src

    path = TARGETS[3]
    src = originals[path]
    src = insert_before(
        src, "        rows.append({\n",
        "        # " + MARKER + ": 最終の暦年を1単位として集計\n"
        "        last_year = df.loc[df[\"simulation_year\"] == df[\"simulation_year\"].iloc[-1]]\n\n",
        path.as_posix(),
    )
    summary_extra = "        # " + MARKER + "\n"
    for name in METRICS:
        summary_extra += f'            "final_{name}": df["{name}"].iloc[-1],\n'
        summary_extra += f'            "mean_{name}_last_100": tail["{name}"].mean(),\n'
        summary_extra += f'            "mean_{name}_last_year": last_year["{name}"].mean(),\n'
    src = insert_before(src, '            "final_gene_exchange_probability":\n', summary_extra, path.as_posix())
    changed[path] = src

    for path, code in changed.items():
        try:
            ast.parse(code, filename=path.as_posix())
        except SyntaxError as exc:
            raise ValueError(f"{path}: 変更後に構文エラー: {exc}") from exc
    return changed


def main() -> None:
    files = {p: PROJECT / p for p in TARGETS}
    for path, absolute in files.items():
        if not absolute.is_file():
            raise FileNotFoundError(f"対象ファイルがありません: {absolute}")
    if not (PROJECT / NEW_SOURCE).is_file():
        raise FileNotFoundError("先に ZIP の src/genetic_diversity.py を配置してください")
    if not (PROJECT / NEW_TEST).is_file():
        raise FileNotFoundError("先に ZIP の tests/test_genetic_diversity.py を配置してください")

    originals = {p: f.read_text(encoding="utf-8") for p, f in files.items()}
    has_marker = [MARKER in s for s in originals.values()]
    if all(has_marker):
        print("STEP2 は適用済みです。変更はありません。")
        return
    if any(has_marker):
        raise ValueError("STEP2 が一部だけ適用されています。ファイルを確認してください（変更は行いません）。")

    changes = build_patches(originals)  # 全対象ファイルを事前検証（ここでは書き換えない）

    backup_dir = PROJECT / "step2_genetic_diversity_backup" / datetime.now().strftime("%Y%m%d_%H%M%S")
    for rel, path in files.items():
        dest = backup_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)

    try:
        for rel, contents in changes.items():
            files[rel].write_text(contents, encoding="utf-8")
    except Exception:
        # 途中でエラーがあっても全ファイルを元の状態に戻す
        for rel, contents in originals.items():
            files[rel].write_text(contents, encoding="utf-8")
        raise

    print("STEP2: 遺伝的多様性の自動ログ集計を組み込みました。")
    print("バックアップ:", backup_dir)
    print("変更したファイル:")
    for rel in changes:
        print("  ", rel.as_posix())
    print("次に python -m pytest tests/test_genetic_diversity.py -q を実行してください。")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)
