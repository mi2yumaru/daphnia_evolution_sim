"""Offline plotting and log-only CLI regressions (fast, no simulation runs)."""
from pathlib import Path
import sys

import pandas as pd
import pytest

from src import plot_from_logs, run_experiments, visualizer


def test_log_only_multi_seed_cli_is_accepted(monkeypatch):
    monkeypatch.setattr(
        sys, "argv",
        ["run_experiments.py", "--no-plots", "--seeds", "0", "1"],
    )
    args = run_experiments.parse_args()
    assert args.no_plots is True
    assert args.save_run_plots is False


def test_log_only_and_run_plots_are_mutually_exclusive(monkeypatch):
    monkeypatch.setattr(
        sys, "argv",
        ["run_experiments.py", "--no-plots", "--save-run-plots"],
    )
    with pytest.raises(SystemExit):
        run_experiments.parse_args()


def test_offline_single_reads_csv_and_calls_shared_plotters(tmp_path, monkeypatch):
    run_dir = tmp_path / "seed_42"
    run_dir.mkdir()
    pd.DataFrame({"step": [0], "population_size": [4]}).to_csv(
        run_dir / "log.csv", index=False
    )
    called = []
    monkeypatch.setattr(plot_from_logs, "save_all_single_run_plots",
                        lambda df, output: called.append(("single", len(df), Path(output))))
    monkeypatch.setattr(plot_from_logs, "saved_gene_flow_plots",
                        lambda path, aggregate: called.append(("flow", aggregate)))
    plot_from_logs.plot_saved_single_run(run_dir)
    assert called == [("single", 1, run_dir), ("flow", False)]


def test_offline_experiment_uses_saved_aggregate_and_seed_csv(tmp_path, monkeypatch):
    experiment_dir = tmp_path / "experiment"
    experiment_dir.mkdir()
    pd.DataFrame({"step": [0], "population_size_mean": [10]}).to_csv(
        experiment_dir / "aggregate.csv", index=False
    )
    for seed in (10, 2):
        folder = experiment_dir / f"seed_{seed}"
        folder.mkdir()
        pd.DataFrame({"step": [0], "food_respawn_rate": [seed]}).to_csv(
            folder / "log.csv", index=False
        )

    calls = []
    monkeypatch.setattr(plot_from_logs, "save_all_aggregate_plots",
                        lambda agg, seed, dest: calls.append(
                            ("aggregate", agg["population_size_mean"].iloc[0],
                             seed["food_respawn_rate"].iloc[0], Path(dest))
                        ))
    monkeypatch.setattr(plot_from_logs, "saved_gene_flow_plots",
                        lambda path, aggregate: calls.append(("flow", aggregate)))
    monkeypatch.setattr(plot_from_logs, "plot_saved_single_run",
                        lambda directory: calls.append(("seed", Path(directory).name)))
    plot_from_logs.plot_saved_experiment(experiment_dir, save_run_plots=True)
    assert calls == [
        ("aggregate", 10, 2, experiment_dir),
        ("flow", True),
        ("seed", "seed_2"),
        ("seed", "seed_10"),
    ]


def test_missing_aggregate_fails_without_running_simulation(tmp_path):
    with pytest.raises(FileNotFoundError, match="aggregate.csv"):
        plot_from_logs.plot_saved_experiment(tmp_path)


def test_shared_aggregate_plot_function_reuses_current_names(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(visualizer, "plot_food_respawn_rate",
                        lambda df, path: calls.append(Path(path).name))
    monkeypatch.setattr(visualizer, "plot_food_dynamics",
                        lambda df, path: calls.append(Path(path).name))
    monkeypatch.setattr(visualizer, "plot_aggregate_mean_std",
                        lambda df, path, **kw: calls.append(Path(path).name))
    sample = pd.DataFrame({
        "step": [0], "largest_lineage_share_mean": [0.2],
        "largest_lineage_share_std": [0.1],
    })
    visualizer.save_all_aggregate_plots(sample, sample, tmp_path)
    assert "food_respawn_rate.png" in calls
    assert "food_dynamics_mean_std.png" in calls
    assert "population_mean_std.png" in calls
    assert "largest_lineage_share_mean_std.png" in calls
