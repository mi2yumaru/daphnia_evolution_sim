"""Redraw existing plots from saved CSVs; never rerun the simulation.

Examples:
  python src/plot_from_logs.py --single-run-dir results/single_runs/seed_42
  python src/plot_from_logs.py --experiment-dir results/experiments/baseline_10seeds
  python src/plot_from_logs.py --experiment-dir results/experiments/baseline_10seeds --save-run-plots
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # Safe for headless, log-only postprocessing.

import pandas as pd

try:
    from src.visualizer import save_all_aggregate_plots, save_all_single_run_plots
    from src.analyze_gene_flow import _plot_rates, _plot_cross_share
except ImportError:
    from visualizer import save_all_aggregate_plots, save_all_single_run_plots
    from analyze_gene_flow import _plot_rates, _plot_cross_share


def read_csv_required(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"保存済みCSVが見つかりません: {path}")
    return pd.read_csv(path)


def saved_gene_flow_plots(directory: Path, *, aggregate: bool) -> None:
    """Recreate gene-flow images if their original input CSV is available."""
    filename = "gene_flow_windows_across_seeds.csv" if aggregate else "gene_flow_by_window.csv"
    path = directory / filename
    if not path.is_file():
        return  # These files do not exist when gene-flow analysis was disabled.
    windows = pd.read_csv(path)
    suffix = "_mean_std" if aggregate else ""
    _plot_rates(windows, directory / f"gene_flow_rates{suffix}.png", aggregate)
    _plot_cross_share(windows, directory / f"gene_flow_cross_share{suffix}.png", aggregate)


def plot_saved_single_run(directory: str | Path) -> None:
    """Reproduce single-seed PNGs from its log.csv without changing CSVs."""
    directory = Path(directory)
    log = read_csv_required(directory / "log.csv")
    save_all_single_run_plots(log, directory)
    saved_gene_flow_plots(directory, aggregate=False)


def _seed_directories(experiment_dir: Path) -> list[tuple[int, Path]]:
    result = []
    for folder in experiment_dir.glob("seed_*"):
        if folder.is_dir() and folder.name[5:].isdigit() and (folder / "log.csv").is_file():
            result.append((int(folder.name[5:]), folder))
    return sorted(result)


def plot_saved_experiment(
    experiment_dir: str | Path,
    *,
    save_run_plots: bool = False,
    reference_seed: int | None = None,
) -> None:
    """Reproduce multi-seed PNGs from aggregate.csv and one saved seed log."""
    experiment_dir = Path(experiment_dir)
    aggregate = read_csv_required(experiment_dir / "aggregate.csv")
    seed_dirs = _seed_directories(experiment_dir)
    if not seed_dirs:
        raise FileNotFoundError(
            f"描画用の seed_*/log.csv が見つかりません: {experiment_dir}"
        )

    # Do not mix older seed folders left in a reused experiment directory.
    # summary.csv preserves the actual seed list/order used for aggregate.csv.
    summary_path = experiment_dir / "summary.csv"
    if summary_path.is_file():
        summary = pd.read_csv(summary_path, usecols=["seed"])
        seeds = summary["seed"].astype(int).tolist()
        if not seeds or len(set(seeds)) != len(seeds):
            raise ValueError(f"summary.csv のseed一覧が不正です: {summary_path}")
        lookup = dict(seed_dirs)
        missing = [seed for seed in seeds if seed not in lookup]
        if missing:
            raise FileNotFoundError(f"集約対象のseedログが見つかりません: {missing}")
        seed_dirs = [(seed, lookup[seed]) for seed in seeds]

    if reference_seed is None:
        selected = seed_dirs[0][1]
    else:
        matches = [p for seed, p in seed_dirs if seed == reference_seed]
        if not matches:
            raise FileNotFoundError(
                f"指定したseedの log.csv が見つかりません: seed_{reference_seed}"
            )
        selected = matches[0]

    reference_log = read_csv_required(selected / "log.csv")
    save_all_aggregate_plots(aggregate, reference_log, experiment_dir)
    saved_gene_flow_plots(experiment_dir, aggregate=True)

    if save_run_plots:
        for _seed, directory in seed_dirs:
            plot_saved_single_run(directory)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="既存ログからグラフだけを再作成します（シミュレーションは実行しません）。"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--single-run-dir", type=Path,
        help="単一seedの出力フォルダ（log.csvのある場所）",
    )
    mode.add_argument(
        "--experiment-dir", type=Path,
        help="複数seed実験フォルダ（aggregate.csvとseed_*/log.csvのある場所）",
    )
    parser.add_argument(
        "--save-run-plots", action="store_true",
        help="複数seedの集約グラフに加えて、各seedの個別グラフも描画する",
    )
    parser.add_argument(
        "--reference-seed", type=int, default=None,
        help="餌リポップ率描画に使う代表seed（指定なしは最小のseed番号）",
    )
    args = parser.parse_args()
    if args.single_run_dir is not None:
        if args.save_run_plots or args.reference_seed is not None:
            parser.error("--save-run-plots / --reference-seed は --experiment-dir 専用です")
        plot_saved_single_run(args.single_run_dir)
        print(f"グラフ再描画完了（単一seed）: {args.single_run_dir}")
    else:
        plot_saved_experiment(
            args.experiment_dir,
            save_run_plots=args.save_run_plots,
            reference_seed=args.reference_seed,
        )
        print(f"グラフ再描画完了（複数seed）: {args.experiment_dir}")


if __name__ == "__main__":
    main()
