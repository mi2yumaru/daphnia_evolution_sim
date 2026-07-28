import pandas as pd

from src.visualizer import COMMON_PLOT_SPECS, add_derived_metrics


def test_add_derived_metrics_adds_shared_food_columns() -> None:
    df = pd.DataFrame(
        {
            "step": [0, 1],
            "eat_count": [4, 0],
            "shared_food_consumer_count": [2, 0],
            "shared_food_cell_count": [1, 0],
            "mean_consumers_per_shared_food": [2.0, 0.0],
        }
    )

    result = add_derived_metrics(df)

    assert "consumed_food_cell_count" in result.columns
    assert "shared_food_cell_ratio" in result.columns
    assert "shared_food_consumer_ratio" in result.columns
    assert "mean_consumers_per_shared_food_plot" in result.columns
    assert result.loc[0, "consumed_food_cell_count"] == 3
    assert result.loc[0, "shared_food_cell_ratio"] == 1.0 / 3.0
    assert result.loc[0, "shared_food_consumer_ratio"] == 0.5
    assert pd.isna(result.loc[1, "mean_consumers_per_shared_food_plot"])


def test_common_plot_specs_include_expected_common_graphs() -> None:
    names = {spec["name"] for spec in COMMON_PLOT_SPECS}

    expected = {
        "population",
        "average_energy",
        "average_age",
        "movement_eating",
        "eating_breakdown",
        "behavior_traits",
        "birth_death_components",
        "birth_death_counts",
        "food_sharing_ratios",
        "consumers_per_shared_food",
        "active_lineage_count",
        "largest_lineage_share",
        "generation_progress",
        "food_respawn_rate",
        "food_dynamics",
    }

    assert expected.issubset(names)
