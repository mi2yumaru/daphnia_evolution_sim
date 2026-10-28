"""STEP3: parent lineage と donor lineage の遺伝子交換関係を集計する。

重要: donor->offspring の結びつきは「選択座位を提供し、親ゲノムの値と
異なるビットが生成された」ことの記録であり、遺伝子座別の祖先追跡ではない。
Founder系譜は親系譜(parent_id)を継ぐラベル。提供系譜とは区別する。
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

NEEDED = (
    "organism_id", "parent_id", "founder_id", "birth_step",
    "gene_exchange_occurred", "gene_exchange_donor_id",
    "gene_exchange_donor_founder_id", "gene_exchange_selected_loci_count",
    "gene_exchange_changed_bit_count",
)
METRICS = (
    "total_births", "exchange_events", "effective_exchanges",
    "cross_founder_events", "cross_founder_effective_exchanges",
    "selected_loci_total", "changed_bits_total", "distinct_donors",
    "donor_founder_edges", "exchange_per_birth", "effective_per_birth",
    "cross_founder_effective_per_birth", "cross_founder_share_of_effective",
)
WINDOW_METRICS = (
    "births", "exchange_events", "effective_exchanges",
    "cross_founder_events", "cross_founder_effective_exchanges",
    "selected_loci_total", "changed_bits_total", "exchange_per_birth",
    "effective_per_birth", "cross_founder_effective_per_birth", "cross_founder_share_of_effective",
)


def _ratio(numerator: int | float, denominator: int | float) -> float:
    return float(numerator / denominator) if denominator else float("nan")


def _events_to_bool(series: pd.Series) -> pd.Series:
    lowered = series.fillna(False).astype(str).str.strip().str.lower()
    if not lowered.isin({"true", "false", "1", "0", "yes", "no"}).all():
        raise ValueError("gene_exchange_occurred の値が不正です")
    return lowered.isin(("true", "1", "yes"))


def _validate_and_prepare(lineage: pd.DataFrame, last_step: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    missing = set(NEEDED) - set(lineage.columns)
    if missing:
        raise ValueError(f"lineage.csv の必須列が不足: {sorted(missing)}")

    d = lineage.loc[:, NEEDED].copy()
    numbers = (
        "organism_id", "parent_id", "founder_id", "birth_step",
        "gene_exchange_donor_id", "gene_exchange_donor_founder_id",
        "gene_exchange_selected_loci_count", "gene_exchange_changed_bit_count",
    )
    for name in numbers:
        d[name] = pd.to_numeric(d[name], errors="raise")
    if d["organism_id"].isna().any() or d["organism_id"].duplicated().any():
        raise ValueError("organism_id に欠損・重複があります")
    if (d["birth_step"] < 0).any() or (d["birth_step"] > last_step).any():
        raise ValueError("birth_step の範囲が不正です")
    if d[["founder_id", "birth_step", "gene_exchange_selected_loci_count", "gene_exchange_changed_bit_count"]].isna().any().any():
        raise ValueError("必須の整数値が欠損しています")
    if (d[["gene_exchange_selected_loci_count", "gene_exchange_changed_bit_count"]] < 0).any().any():
        raise ValueError("交換bit数が負です")
    if (d["gene_exchange_changed_bit_count"] > d["gene_exchange_selected_loci_count"]).any():
        raise ValueError("変化bit数が選択座位数を超えています")

    d["exchange_event"] = _events_to_bool(d["gene_exchange_occurred"])
    d["effective_event"] = d["gene_exchange_changed_bit_count"] > 0
    d["has_parent"] = d["parent_id"].notna()
    d["cross_founder"] = d["exchange_event"] & (
        d["founder_id"] != d["gene_exchange_donor_founder_id"]
    )
    d["cross_founder_effective"] = d["cross_founder"] & d["effective_event"]
    if ((~d["exchange_event"]) & (
        d["gene_exchange_donor_id"].notna() |
        d["gene_exchange_donor_founder_id"].notna() |
        (d["gene_exchange_selected_loci_count"] != 0) |
        d["effective_event"]
    )).any():
        raise ValueError("交換イベントなしなのに提供者や交換bitが記録されています")
    if (d["exchange_event"] & (
        ~d["has_parent"] | d["gene_exchange_donor_id"].isna() |
        d["gene_exchange_donor_founder_id"].isna()
    )).any():
        raise ValueError("交換イベントの提供者IDまたは親IDが欠損しています")

    index = d.set_index("organism_id", verify_integrity=True)
    births = d.loc[d["has_parent"]].copy()
    parents = births["parent_id"].map(index["founder_id"])
    if parents.isna().any():
        raise ValueError("lineage内に存在しない親IDがあります")
    if (parents.to_numpy() != births["founder_id"].to_numpy()).any():
        raise ValueError("子が引き継いだFounder系譜と親のFounder系譜が一致しません")
    donors = births.loc[births["exchange_event"]]
    donor_founders = donors["gene_exchange_donor_id"].map(index["founder_id"])
    if donor_founders.isna().any() or (
        donor_founders.to_numpy() != donors["gene_exchange_donor_founder_id"].to_numpy()
    ).any():
        raise ValueError("提供個体IDと提供元Founder系譜が一致しません")
    parent_birth_steps = births["parent_id"].map(index["birth_step"])
    if (parent_birth_steps > births["birth_step"]).any():
        raise ValueError("子が親より先に生まれています")
    donor_birth_steps = donors["gene_exchange_donor_id"].map(index["birth_step"])
    if (donor_birth_steps > donors["birth_step"]).any():
        raise ValueError("子が遺伝子提供個体より先に生まれています")
    return d, births


def _summarize_windows(births: pd.DataFrame, last_step: int, window_steps: int) -> pd.DataFrame:
    n_windows = last_step // window_steps + 1
    work = births.copy()
    work["window_index"] = (work["birth_step"] // window_steps).astype(int)
    rows = []
    for index in range(n_windows):
        subset = work.loc[work["window_index"] == index]
        n_births = len(subset)
        exchange_count = int(subset["exchange_event"].sum())
        effective_count = int(subset["effective_event"].sum())
        cross_count = int(subset["cross_founder"].sum())
        cross_effective = int(subset["cross_founder_effective"].sum())
        rows.append({
            "window_start": index * window_steps,
            "window_end": min((index + 1) * window_steps - 1, last_step),
            "births": n_births,
            "exchange_events": exchange_count,
            "effective_exchanges": effective_count,
            "cross_founder_events": cross_count,
            "cross_founder_effective_exchanges": cross_effective,
            "selected_loci_total": int(subset["gene_exchange_selected_loci_count"].sum()),
            "changed_bits_total": int(subset["gene_exchange_changed_bit_count"].sum()),
            "exchange_per_birth": _ratio(exchange_count, n_births),
            "effective_per_birth": _ratio(effective_count, n_births),
            "cross_founder_effective_per_birth": _ratio(cross_effective, n_births),
            "cross_founder_share_of_effective": _ratio(cross_effective, effective_count),
        })
    return pd.DataFrame(rows)


def analyze_gene_flow(
    lineage: pd.DataFrame,
    last_logged_step: int,
    window_steps: int = 100,
) -> dict[str, pd.DataFrame]:
    """STEP3 集計用データフレーム群。シミュレーション処理への副作用なし。"""
    last_step = int(last_logged_step)
    window_steps = int(window_steps)
    if last_step < 0 or window_steps < 1:
        raise ValueError("last_logged_step は0以上、window_steps は1以上で指定してください")
    d, births = _validate_and_prepare(lineage, last_step)
    exchanged = births.loc[births["exchange_event"]].copy()
    effective = exchanged.loc[exchanged["effective_event"]].copy()
    cross_effective = effective.loc[effective["cross_founder"]].copy()
    direct_birth_counts = births.groupby("parent_id").size()

    # Donorとして一度でも選ばれた個体。自分が産んだ子は別の列に記載。
    donor_rows = []
    for donor_id, group in exchanged.groupby("gene_exchange_donor_id", sort=True):
        donor_id = int(donor_id)
        eff = group.loc[group["effective_event"]]
        cross = eff.loc[eff["cross_founder"]]
        donor_rows.append({
            "donor_id": donor_id,
            "donor_founder_id": int(group["gene_exchange_donor_founder_id"].iloc[0]),
            "direct_offspring_count": int(direct_birth_counts.get(donor_id, 0)),
            "donor_event_count": len(group),
            "donor_effective_count": len(eff),
            "donor_cross_founder_effective_count": len(cross),
            "donor_selected_loci_total": int(group["gene_exchange_selected_loci_count"].sum()),
            "donor_changed_bits_total": int(group["gene_exchange_changed_bit_count"].sum()),
            "distinct_effective_recipient_founders": int(eff["founder_id"].nunique()),
            "distinct_cross_founder_recipients": int(cross["founder_id"].nunique()),
        })
    donor_cols = (
        "donor_id", "donor_founder_id", "direct_offspring_count", "donor_event_count",
        "donor_effective_count", "donor_cross_founder_effective_count",
        "donor_selected_loci_total", "donor_changed_bits_total",
        "distinct_effective_recipient_founders", "distinct_cross_founder_recipients",
    )
    donors = pd.DataFrame(donor_rows, columns=donor_cols)

    # donor Founder -> parent Founder 方向。自己Founder内の交換も行として残す。
    edge_rows = []
    for (from_id, to_id), group in exchanged.groupby(
        ["gene_exchange_donor_founder_id", "founder_id"], sort=True
    ):
        edge_rows.append({
            "donor_founder_id": int(from_id),
            "recipient_founder_id": int(to_id),
            "cross_founder": int(from_id) != int(to_id),
            "exchange_events": len(group),
            "effective_exchanges": int(group["effective_event"].sum()),
            "selected_loci_total": int(group["gene_exchange_selected_loci_count"].sum()),
            "changed_bits_total": int(group["gene_exchange_changed_bit_count"].sum()),
            "distinct_donor_individuals": int(group["gene_exchange_donor_id"].nunique()),
            "distinct_direct_parents": int(group["parent_id"].nunique()),
        })
    edge_cols = (
        "donor_founder_id", "recipient_founder_id", "cross_founder",
        "exchange_events", "effective_exchanges", "selected_loci_total",
        "changed_bits_total", "distinct_donor_individuals", "distinct_direct_parents",
    )
    edges = pd.DataFrame(edge_rows, columns=edge_cols)

    # 父系 (primary parent) に基づく founder_id 集計と、donor 起点の実績を併記。
    founder_ids = sorted(d.loc[~d["has_parent"], "founder_id"].astype(int).unique())
    founder_rows = []
    for founder_id in founder_ids:
        own = births.loc[births["founder_id"] == founder_id]
        outgoing = exchanged.loc[exchanged["gene_exchange_donor_founder_id"] == founder_id]
        incoming = exchanged.loc[exchanged["founder_id"] == founder_id]
        outgoing_effective = outgoing.loc[outgoing["effective_event"]]
        incoming_effective = incoming.loc[incoming["effective_event"]]
        cross_outgoing = outgoing_effective.loc[outgoing_effective["founder_id"] != founder_id]
        cross_incoming = incoming_effective.loc[
            incoming_effective["gene_exchange_donor_founder_id"] != founder_id
        ]
        founder_rows.append({
            "founder_id": founder_id,
            "lineage_births": len(own),
            "lineage_member_count_including_founder": int((d["founder_id"] == founder_id).sum()),
            "received_exchange_events": len(incoming),
            "received_effective_exchanges": len(incoming_effective),
            "received_cross_founder_effective": len(cross_incoming),
            "provided_exchange_events": len(outgoing),
            "provided_effective_exchanges": len(outgoing_effective),
            "provided_cross_founder_effective": len(cross_outgoing),
            "provided_changed_bits_total": int(outgoing["gene_exchange_changed_bit_count"].sum()),
            "individual_donors": int(outgoing["gene_exchange_donor_id"].nunique()),
            "distinct_other_recipient_lineages": int(cross_outgoing["founder_id"].nunique()),
        })
    founder_cols = (
        "founder_id", "lineage_births", "lineage_member_count_including_founder",
        "received_exchange_events", "received_effective_exchanges",
        "received_cross_founder_effective", "provided_exchange_events",
        "provided_effective_exchanges", "provided_cross_founder_effective",
        "provided_changed_bits_total", "individual_donors", "distinct_other_recipient_lineages",
    )
    founders = pd.DataFrame(founder_rows, columns=founder_cols)

    n_births = len(births)
    event_n = len(exchanged)
    effective_n = len(effective)
    cross_n = int(exchanged["cross_founder"].sum())
    cross_effective_n = len(cross_effective)
    summary = pd.DataFrame([{
        "total_births": n_births,
        "exchange_events": event_n,
        "effective_exchanges": effective_n,
        "cross_founder_events": cross_n,
        "cross_founder_effective_exchanges": cross_effective_n,
        "selected_loci_total": int(exchanged["gene_exchange_selected_loci_count"].sum()),
        "changed_bits_total": int(exchanged["gene_exchange_changed_bit_count"].sum()),
        "distinct_donors": int(exchanged["gene_exchange_donor_id"].nunique()),
        "donor_founder_edges": len(edges),
        "exchange_per_birth": _ratio(event_n, n_births),
        "effective_per_birth": _ratio(effective_n, n_births),
        "cross_founder_effective_per_birth": _ratio(cross_effective_n, n_births),
        "cross_founder_share_of_effective": _ratio(cross_effective_n, effective_n),
    }], columns=METRICS)
    windows = _summarize_windows(births, last_step, window_steps)
    return {"donors": donors, "edges": edges, "founders": founders,
            "windows": windows, "summary": summary}


OUTPUTS = {
    "donors": "gene_flow_donors.csv",
    "edges": "gene_flow_founder_edges.csv",
    "founders": "gene_flow_founders.csv",
    "windows": "gene_flow_by_window.csv",
    "summary": "gene_flow_summary.csv",
}


def _plot_rates(windows: pd.DataFrame, output_file: Path, aggregate: bool) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    step_col = "window_start"
    names = (
        ("effective_per_birth", "Effective exchange / births"),
        ("cross_founder_effective_per_birth", "Cross-founder effective / births"),
    )
    for key, label in names:
        col = f"{key}_mean" if aggregate else key
        ax.plot(windows[step_col], windows[col], label=label)
        if aggregate:
            std = windows[f"{key}_std"].fillna(0.0)
            mean = windows[col]
            ax.fill_between(windows[step_col], (mean - std).clip(lower=0),
                            (mean + std).clip(upper=1), alpha=0.17)
    ax.set(xlabel="Step (window start)", ylabel="Fraction of births",
           title="Gene-exchange contribution by time window")
    ax.set_ylim(bottom=0, top=1)
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_file, dpi=150)
    plt.close(fig)


def _plot_cross_share(windows: pd.DataFrame, output_file: Path, aggregate: bool) -> None:
    key = "cross_founder_share_of_effective"
    col = f"{key}_mean" if aggregate else key
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(windows["window_start"], windows[col], label="Cross-founder / effective exchanges")
    if aggregate:
        mean, std = windows[col], windows[f"{key}_std"].fillna(0.0)
        ax.fill_between(windows["window_start"], (mean - std).clip(lower=0),
                        (mean + std).clip(upper=1), alpha=0.2)
    ax.set(xlabel="Step (window start)", ylabel="Fraction of effective exchanges",
           title="Cross-founder share among effective exchanges")
    ax.set_ylim(0, 1)
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_file, dpi=150)
    plt.close(fig)


def save_gene_flow_seed(
    lineage: pd.DataFrame,
    output_dir: str | Path,
    last_logged_step: int,
    window_steps: int = 100,
    save_plots: bool = False,
) -> dict[str, pd.DataFrame]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    result = analyze_gene_flow(lineage, last_logged_step, window_steps)
    for key, name in OUTPUTS.items():
        result[key].to_csv(output_dir / name, index=False)
    if save_plots:
        _plot_rates(result["windows"], output_dir / "gene_flow_rates.png", False)
        _plot_cross_share(result["windows"], output_dir / "gene_flow_cross_share.png", False)
    return result


def aggregate_gene_flow_experiment(
    experiment_dir: str | Path,
    seeds: list[int],
    save_plots: bool = True,
) -> dict[str, pd.DataFrame]:
    experiment_dir = Path(experiment_dir)
    summaries, all_windows = [], []
    for seed in seeds:
        seed_dir = experiment_dir / f"seed_{seed}"
        for name in ("gene_flow_summary.csv", "gene_flow_by_window.csv"):
            if not (seed_dir / name).is_file():
                raise FileNotFoundError(f"STEP3ファイルがありません: {seed_dir / name}")
        s = pd.read_csv(seed_dir / "gene_flow_summary.csv")
        w = pd.read_csv(seed_dir / "gene_flow_by_window.csv")
        if len(s) != 1 or not set(METRICS).issubset(s.columns) or not set(WINDOW_METRICS).issubset(w.columns):
            raise ValueError(f"STEP3のseed出力が不正です: {seed_dir}")
        s.insert(0, "seed", seed)
        w.insert(0, "seed", seed)
        summaries.append(s)
        all_windows.append(w)
    if not summaries:
        raise ValueError("少なくとも1つのseedが必要です")
    merged_s = pd.concat(summaries, ignore_index=True)
    merged_w = pd.concat(all_windows, ignore_index=True)
    n_seeds = len(seeds)
    counts = merged_w.groupby("window_start")["seed"].nunique()
    if not (counts == n_seeds).all() or len(merged_w) != len(counts) * n_seeds:
        raise ValueError("windowごとのseed数が一致しません（実行ステップ数を確認）")
    ends = merged_w.groupby("window_start")["window_end"].nunique()
    if not (ends == 1).all():
        raise ValueError("seedごとに観察終了ステップが一致しません")
    numeric = [k for k in WINDOW_METRICS if k in merged_w.columns]
    mean_std = merged_w.groupby("window_start")[numeric].agg(["mean", "std"])
    mean_std.columns = [f"{name}_{stat}" for name, stat in mean_std.columns]
    mean_std = mean_std.reset_index()
    mean_std.insert(1, "window_end", merged_w.groupby("window_start")["window_end"].first().to_numpy())
    by_seed = merged_s.sort_values("seed").reset_index(drop=True)
    across = pd.DataFrame([{
        "metric": k,
        "n_valid_seeds": int(merged_s[k].count()),
        "mean": float(merged_s[k].mean()),
        "std": float(merged_s[k].std()) if merged_s[k].count() > 1 else float("nan"),
    } for k in METRICS])
    by_seed.to_csv(experiment_dir / "gene_flow_metrics_by_seed.csv", index=False)
    across.to_csv(experiment_dir / "gene_flow_metrics_across_seeds.csv", index=False)
    mean_std.to_csv(experiment_dir / "gene_flow_windows_across_seeds.csv", index=False)
    if save_plots:
        _plot_rates(mean_std, experiment_dir / "gene_flow_rates_mean_std.png", True)
        _plot_cross_share(mean_std, experiment_dir / "gene_flow_cross_share_mean_std.png", True)
    return {"by_seed": by_seed, "across_seeds": across, "windows": mean_std}


def cli() -> None:
    parser = argparse.ArgumentParser(description="既存のlineage.csvからSTEP3ログを再生成")
    parser.add_argument("--experiment-dir", required=True, type=Path)
    parser.add_argument("--seeds", nargs="+", type=int, default=None)
    parser.add_argument("--window-steps", type=int, default=100)
    parser.add_argument("--save-run-plots", action="store_true")
    args = parser.parse_args()
    if args.window_steps < 1:
        parser.error("--window-steps は1以上")
    if args.seeds is None:
        args.seeds = sorted(int(p.name.removeprefix("seed_")) for p in args.experiment_dir.glob("seed_*")
                            if p.is_dir() and p.name.removeprefix("seed_").isdigit())
    if not args.seeds:
        parser.error("seedフォルダが見つかりません")
    for seed in args.seeds:
        folder = args.experiment_dir / f"seed_{seed}"
        lineage = pd.read_csv(folder / "lineage.csv")
        log_path = folder / "log.csv"
        if not log_path.is_file():
            raise FileNotFoundError(f"最終ステップ確認用の log.csv がありません: {log_path}")
        last_step = int(pd.read_csv(log_path, usecols=["step"])["step"].iloc[-1])
        save_gene_flow_seed(lineage, folder, last_step, args.window_steps, args.save_run_plots)
        print(f"STEP3 解析済み: seed={seed}")
    aggregate_gene_flow_experiment(args.experiment_dir, args.seeds)
    print("STEP3 10seed統合ログとグラフの生成完了")


if __name__ == "__main__":
    cli()
