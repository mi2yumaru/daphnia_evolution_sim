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

def resolve_total_steps(config: dict[str, Any]) -> int:
    """
    simulation設定から総実行ステップ数を決定する。

    duration_mode == "steps":
        simulation.stepsをそのまま使用する。

    duration_mode == "years":
        duration_years × days_per_year × steps_per_day
        により総実行ステップ数を計算する。

    計算した値はsimulation.stepsへ格納する。
    """
    if "simulation" not in config:
        raise KeyError(
            "設定に 'simulation' セクションがありません。"
        )

    sim_config = config["simulation"]

    # 古い設定ファイルとの互換性を保つため、
    # duration_modeがない場合はstepsモードとして扱う
    duration_mode = str(
        sim_config.get("duration_mode", "steps")
    ).strip().lower()

    if duration_mode == "steps":
        if "steps" not in sim_config:
            raise KeyError(
                "duration_modeが'steps'ですが、"
                "simulation.stepsが設定されていません。"
            )

        try:
            total_steps = int(sim_config["steps"])
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "simulation.stepsには整数を指定してください。"
            ) from exc

        if total_steps <= 0:
            raise ValueError(
                "simulation.stepsは1以上にしてください。"
            )

    elif duration_mode == "years":
        required_keys = (
            "duration_years",
            "days_per_year",
            "steps_per_day",
        )

        missing_keys = [
            key
            for key in required_keys
            if key not in sim_config
        ]

        if missing_keys:
            raise KeyError(
                "duration_modeが'years'ですが、"
                f"次の設定がありません: {missing_keys}"
            )

        try:
            duration_years = int(
                sim_config["duration_years"]
            )
            days_per_year = int(
                sim_config["days_per_year"]
            )
            steps_per_day = int(
                sim_config["steps_per_day"]
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "duration_years、days_per_year、"
                "steps_per_dayには整数を指定してください。"
            ) from exc

        if duration_years <= 0:
            raise ValueError(
                "simulation.duration_yearsは1以上にしてください。"
            )

        if days_per_year <= 0:
            raise ValueError(
                "simulation.days_per_yearは1以上にしてください。"
            )

        if steps_per_day <= 0:
            raise ValueError(
                "simulation.steps_per_dayは1以上にしてください。"
            )

        total_steps = (
            duration_years
            * days_per_year
            * steps_per_day
        )

    else:
        raise ValueError(
            "simulation.duration_modeには"
            "'steps'または'years'を指定してください。"
        )

    # Simulation.run()はsimulation.stepsを参照するため、
    # 決定した総ステップ数を実行用設定へ格納する
    sim_config["steps"] = total_steps

    return total_steps

def build_lineage_strategy_summary(
    lineage_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    全個体の系譜記録から、
    Founder系統ごとの戦略・存続状況を集計する。

    1行 = 1 Founder系統。
    """

    summary_rows = []

    # Founder ID順に処理
    founder_ids = sorted(
        lineage_df["founder_id"]
        .dropna()
        .astype(int)
        .unique()
    )

    for founder_id in founder_ids:
        # このFounderに属する全個体
        lineage_group = lineage_df[lineage_df["founder_id"] == founder_id].copy()

        # Founder本人
        founder_rows = lineage_group[lineage_group["organism_id"] == founder_id]

        if founder_rows.empty:
            raise ValueError(
                f"Founder record not found: founder_id={founder_id}"
            )

        founder = founder_rows.iloc[0]

        # シミュレーション終了時点で生存している個体
        alive_group = lineage_group[lineage_group["death_step"].isna()].copy()

        final_alive_count = len(alive_group)

        is_extinct = final_alive_count == 0

        # 系統絶滅step
        if is_extinct:
            death_steps = lineage_group["death_step"].dropna()

            extinction_step = (
                int(death_steps.max())
                if not death_steps.empty
                else pd.NA
            )
        else:
            extinction_step = pd.NA

        summary_rows.append({
            "founder_id": founder_id,
            "is_extinct": is_extinct,
            "extinction_step": extinction_step,
            "total_individuals_ever_born": len(lineage_group),

            "final_alive_count": final_alive_count,

            # あとで総個体数が分かってから計算
            "final_lineage_share": 0.0,

            # Founderの初期戦略
            "founder_exploration_tendency": founder["birth_exploration_tendency"],
            "founder_site_fidelity": founder["birth_site_fidelity"],
            "founder_risk_tolerance": founder["birth_risk_tolerance"],
            "founder_reproduction_timing": founder["birth_reproduction_timing"],
            "founder_gene_exchange_probability": founder["birth_gene_exchange_probability"],
            "founder_gene_exchange_fraction": founder["birth_gene_exchange_fraction"],

            # 最終生存個体の戦略
            "final_mean_exploration_tendency": (
                alive_group[
                    "birth_exploration_tendency"
                ].mean()
                if final_alive_count > 0
                else pd.NA
            ),

            "final_std_exploration_tendency": (
                alive_group[
                    "birth_exploration_tendency"
                ].std(ddof=0)
                if final_alive_count > 0
                else pd.NA
            ),

            "final_mean_site_fidelity": (
                alive_group[
                    "birth_site_fidelity"
                ].mean()
                if final_alive_count > 0
                else pd.NA
            ),

            "final_std_site_fidelity": (
                alive_group[
                    "birth_site_fidelity"
                ].std(ddof=0)
                if final_alive_count > 0
                else pd.NA
            ),

            "final_mean_risk_tolerance": (
                alive_group[
                    "birth_risk_tolerance"
                ].mean()
                if final_alive_count > 0
                else pd.NA
            ),

            "final_std_risk_tolerance": (
                alive_group[
                    "birth_risk_tolerance"
                ].std(ddof=0)
                if final_alive_count > 0
                else pd.NA
            ),

            "final_mean_reproduction_timing": (
                alive_group[
                    "birth_reproduction_timing"
                ].mean()
                if final_alive_count > 0
                else pd.NA
            ),

            "final_std_reproduction_timing": (
                alive_group[
                    "birth_reproduction_timing"
                ].std(ddof=0)
                if final_alive_count > 0
                else pd.NA
            ),

            "final_mean_gene_exchange_probability": (
                alive_group[
                        "birth_gene_exchange_probability"
                ].mean()
                if final_alive_count > 0
                else pd.NA
            ),

            "final_std_gene_exchange_probability": (
                alive_group[
                    "birth_gene_exchange_probability"
                ].std(ddof=0)
                if final_alive_count > 0
                else pd.NA
            ),

            "final_mean_gene_exchange_fraction": (
                alive_group[
                    "birth_gene_exchange_fraction"
                ].mean()
                if final_alive_count > 0
                else pd.NA
            ),

            "final_std_gene_exchange_fraction": (
                alive_group[
                    "birth_gene_exchange_fraction"
                ].std(ddof=0)
                if final_alive_count > 0
                else pd.NA
            ),

            # 最終生存個体の世代
            "final_mean_generation": (
                alive_group["generation"].mean()
                if final_alive_count > 0
                else pd.NA
            ),

            "final_max_generation": (
                int(
                    alive_group["generation"].max()
                )
                if final_alive_count > 0
                else pd.NA
            ),
        })

    summary_df = pd.DataFrame(summary_rows)

    # 最終生存個体総数
    total_final_alive = summary_df["final_alive_count"].sum()

    if total_final_alive > 0:
        summary_df["final_lineage_share"] = (
            summary_df["final_alive_count"]
            / total_final_alive
        )

    return summary_df

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

    # ステップ直接指定または年数指定から、
    # 実際に実行する総ステップ数を決定する
    total_steps = resolve_total_steps(run_config)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    duration_mode = run_config["simulation"].get(
        "duration_mode",
        "steps",
    )

    if duration_mode == "years":
        duration_years = run_config["simulation"][
            "duration_years"
        ]
        print(
            f"実行期間: {duration_years}年 "
            f"({total_steps:,}ステップ)"
        )
    else:
        print(
            f"実行期間: {total_steps:,}ステップ"
        )

    sim = Simulation(run_config)

    if live:
        run_live_visualization(sim)
    else:
        sim.run()

    df = sim.logger.to_dataframe()

    if save_csv:
        # 通常のstep単位ログ
        csv_path = output_dir / "log.csv"
        sim.logger.save_csv(str(csv_path))

        # 全個体の系譜情報を保存
        lineage_df = pd.DataFrame(list(sim.lineage_records.values()))

        if not lineage_df.empty:
            lineage_df = (
                lineage_df
                .sort_values("organism_id")
                .reset_index(drop=True)
            )

        lineage_df.to_csv(
            output_dir / "lineage.csv",
            index=False,
        )

        # Founder系統×行動戦略summary
        if not lineage_df.empty:
            lineage_strategy_summary_df = (
                build_lineage_strategy_summary(
                    lineage_df
                )
            )

            lineage_strategy_summary_df.to_csv(
                output_dir
                / "lineage_strategy_summary.csv",
                index=False,
            )

    if save_plots:
        save_all_single_run_plots(df, output_dir)

    return df