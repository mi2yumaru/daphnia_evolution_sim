"""遺伝子交換による出生区分と、その後の生存・繁殖成績の観察的解析。

既存の lineage DataFrame を使うため、本体の進化・繁殖ロジックは変更しない。
因果関係は立証しない。比較・推測は基本的に seed ごとの値で行う。
"""
from __future__ import annotations

from pathlib import Path
import warnings

import pandas as pd


GROUPS = ("no_exchange", "exchange_no_change", "effective_exchange")
REQUIRED = {
    "organism_id", "parent_id", "birth_step", "death_step",
    "gene_exchange_occurred", "gene_exchange_changed_bit_count",
}
METRICS = ("survival_rate", "reproduction_rate", "mean_offspring")


def _event_flags(values: pd.Series) -> pd.Series:
    # CSV読み込み後の bool, 文字列, 数値のいずれも扱えるようにする。
    vals = values.fillna(False).astype(str).str.strip().str.lower()
    valid = {"true", "false", "1", "0", "yes", "no"}
    if not vals.isin(valid).all():
        raise ValueError("gene_exchange_occurred に未対応の値が含まれます")
    return vals.isin(("true", "1", "yes"))


def analyze_lineage_dataframe(
    lineage: pd.DataFrame,
    last_logged_step: int,
    horizon_steps: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """個体別とグループ別の生存・直接出生成績を返す。

    判定例: H=200なら出生時から200ステップ後に生存しているか。
    終了時までHステップ観察できない個体・Founderは対象外。
    """
    horizon_steps = int(horizon_steps)
    if horizon_steps <= 0:
        raise ValueError("horizon_steps は1以上で指定してください")
    missing = REQUIRED - set(lineage.columns)
    if missing:
        raise ValueError(f"lineage に必須列がありません: {sorted(missing)}")

    data = lineage.copy()
    if data["organism_id"].isna().any() or data["organism_id"].duplicated().any():
        raise ValueError("organism_id の欠損または重複があります")

    for c in ("organism_id", "parent_id", "birth_step", "death_step",
              "gene_exchange_changed_bit_count"):
        data[c] = pd.to_numeric(data[c], errors="raise")

    exchange = _event_flags(data["gene_exchange_occurred"])
    changed = data["gene_exchange_changed_bit_count"].fillna(0)
    if (changed < 0).any() or ((changed > 0) & ~exchange).any():
        raise ValueError("遺伝子交換イベントと変化bit数に矛盾があります")

    data["birth_exchange_group"] = "no_exchange"
    data.loc[exchange, "birth_exchange_group"] = "exchange_no_change"
    data.loc[changed > 0, "birth_exchange_group"] = "effective_exchange"

    observed = data.loc[
        data["parent_id"].notna()
        & (data["birth_step"] + horizon_steps <= int(last_logged_step)),
        ["organism_id", "parent_id", "birth_step", "death_step", "birth_exchange_group"],
    ].copy()
    cutoff = observed["birth_step"] + horizon_steps
    observed["survived_horizon"] = (
        observed["death_step"].isna() | (observed["death_step"] > cutoff)
    )

    # 子の parent_id と出生時刻から、対象個体がHステップ以内に産んだ子を数える。
    # 出生数に孫以降は含まない。
    births = data.loc[data["parent_id"].notna(), ["parent_id", "birth_step"]].rename(
        columns={"parent_id": "organism_id", "birth_step": "child_birth_step"}
    )
    parent_births = observed[["organism_id", "birth_step"]].rename(
        columns={"birth_step": "parent_birth_step"}
    )
    matched = births.merge(parent_births, on="organism_id", how="inner")
    elapsed = matched["child_birth_step"] - matched["parent_birth_step"]
    valid = matched.loc[(elapsed > 0) & (elapsed <= horizon_steps)]
    counts = valid.groupby("organism_id").size()
    observed["offspring_count_horizon"] = (
        observed["organism_id"].map(counts).fillna(0).astype(int)
    )
    observed["reproduced_horizon"] = observed["offspring_count_horizon"] > 0
    observed["horizon_steps"] = horizon_steps

    rows = []
    for group in GROUPS:
        selected = observed.loc[observed["birth_exchange_group"] == group]
        n = len(selected)
        rows.append({
            "birth_exchange_group": group,
            "horizon_steps": horizon_steps,
            "n_observed": n,
            # 標本がないグループは0%ではなく欠損とする。
            "survival_rate": float(selected["survived_horizon"].mean()) if n else float("nan"),
            "reproduction_rate": float(selected["reproduced_horizon"].mean()) if n else float("nan"),
            "mean_offspring": float(selected["offspring_count_horizon"].mean()) if n else float("nan"),
        })
    summary = pd.DataFrame(rows)
    return observed, summary


def aggregate_experiment_outcomes(
    experiment_dir: str | Path,
    seeds: list[int],
    horizon_steps: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """指定seedのみ集計し、以前実行したseedを混入させない。"""
    experiment_dir = Path(experiment_dir)
    if not seeds or len(seeds) != len(set(seeds)):
        raise ValueError("seeds は重複なしの1個以上の整数を指定してください")

    summaries = []
    for seed in seeds:
        path = experiment_dir / f"seed_{seed}" / "offspring_outcomes_by_group.csv"
        if not path.is_file():
            raise FileNotFoundError(f"seed={seed} の集計CSVがありません: {path}")
        summary = pd.read_csv(path)
        if not set(GROUPS).issubset(set(summary["birth_exchange_group"])):
            raise ValueError(f"出生区分が不足しています: {path}")
        if not (summary["horizon_steps"] == horizon_steps).all():
            raise ValueError(f"horizon_steps が一致しません: {path}")
        summary.insert(0, "seed", seed)
        summaries.append(summary)

    by_seed = pd.concat(summaries, ignore_index=True)
    # N=0のカテゴリは seed間の平均・標準偏差の計算から除外する。
    observed = by_seed[by_seed["n_observed"] > 0]
    rows = []
    for group in GROUPS:
        frame = observed[observed["birth_exchange_group"] == group]
        row = {
            "birth_exchange_group": group,
            "horizon_steps": horizon_steps,
            "n_total_seeds": len(seeds),
            "n_seeds_with_observations": len(frame),
            "total_observed_individuals": int(frame["n_observed"].sum()),
        }
        for metric in METRICS:
            row[f"{metric}_mean"] = frame[metric].mean()
            row[f"{metric}_std"] = frame[metric].std(ddof=1)
        rows.append(row)

    across = pd.DataFrame(rows)
    by_seed.to_csv(experiment_dir / "offspring_outcomes_by_seed.csv", index=False)
    across.to_csv(experiment_dir / "offspring_outcomes_across_seeds.csv", index=False)
    for row in rows:
        if row["n_seeds_with_observations"] < len(seeds):
            warnings.warn(
                f"{row['birth_exchange_group']}: 有効出生があるseedは"
                f"{row['n_seeds_with_observations']}/{len(seeds)}個です。"
                "欠損グループを0とみなさずに集計しています。",
                stacklevel=2,
            )
    return by_seed, across
