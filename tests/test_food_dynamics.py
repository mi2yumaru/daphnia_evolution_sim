from src.environment import Environment
from src.logger import SimulationLogger


def test_respawn_food_returns_actual_added_count() -> None:
    env = Environment(width=10, height=10, respawn_mode="random")
    initial_food = 0
    env.init_food(initial_food)

    before_count = len(env.food)
    added = env.respawn_food(0.02)

    assert added >= 0
    assert added == len(env.food) - before_count
    assert len(env.food) >= before_count


def test_logger_records_food_dynamics_columns() -> None:
    logger = SimulationLogger()

    logger.record(
        step=0,
        simulation_year=1,
        day_of_year=1,
        month=1,
        day_of_month=1,
        food_respawn_rate=0.0,
        population_size=1,
        food_count=5,
        average_energy=1.0,
        average_age=2.0,
        birth_count=0,
        death_count=0,
        age_death_count=0,
        energy_death_count=0,
        move_count=0,
        move_rate=0.0,
        non_move_count=1,
        eat_count=0,
        eat_rate=0.0,
        eat_per_move=0.0,
        eat_after_move_count=0,
        eat_without_move_count=0,
        eat_after_move_rate=0.0,
        eat_without_move_rate=0.0,
        total_eat_rate=0.0,
        shared_food_cell_count=0,
        shared_food_consumer_count=0,
        mean_consumers_per_shared_food=0.0,
        birth_rate=0.0,
        death_rate=0.0,
        age_death_rate=0.0,
        energy_death_rate=0.0,
        average_exploration_tendency=0.0,
        std_exploration_tendency=0.0,
        min_exploration_tendency=0.0,
        max_exploration_tendency=0.0,
        average_site_fidelity=0.0,
        std_site_fidelity=0.0,
        min_site_fidelity=0.0,
        max_site_fidelity=0.0,
        average_risk_tolerance=0.0,
        std_risk_tolerance=0.0,
        min_risk_tolerance=0.0,
        max_risk_tolerance=0.0,
        average_reproduction_timing=0.0,
        std_reproduction_timing=0.0,
        min_reproduction_timing=0.0,
        max_reproduction_timing=0.0,
        active_lineage_count=0,
        largest_lineage_share=0.0,
        average_generation=0.0,
        max_generation=0,
        food_respawn_count=0,
        food_consumed_count=0,
    )

    df = logger.to_dataframe()
    assert "food_respawn_count" in df.columns
    assert "food_consumed_count" in df.columns
