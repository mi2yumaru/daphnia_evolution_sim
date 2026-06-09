"""
simulation.py - シミュレーション主制御

Simulation クラスが各ステップでの環境、個体群、食料の更新を管理
"""

from typing import List, Dict, Any
import numpy as np
try:
    from .organism import Organism
    from .environment import Environment
    from .logger import SimulationLogger
except Exception:
    # when running as a script (python src/main.py) the package-relative imports
    # fail; fall back to top-level module imports
    from organism import Organism
    from environment import Environment
    from logger import SimulationLogger


class Simulation:
    """
    シミュレーション全体を制御するクラス
    
    設定に基づいて初期化し、各ステップの環境更新、個体の行動、ログ記録を行う
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        シミュレーションを初期化
        
        Args:
            config: 設定辞書（YAMLから読み込まれたもの）
        """
        self.config = config
        
        # 設定の取得
        sim_config = config["simulation"]
        env_config = config["environment"]
        org_config = config["organism"]
        gen_config = config["genetics"]
        
        # 乱数シードの設定
        np.random.seed(sim_config["random_seed"])
        
        # 環境の初期化
        self.environment = Environment(
            env_config["width"],
            env_config["height"],
            respawn_mode=env_config.get("mode", "random"),
            patch_count=env_config.get("patch_count", 4),
            patch_radius=env_config.get("patch_radius", 5),
            patch_density=env_config.get("patch_density", 0.8),
            outside_respawn_fraction=env_config.get("outside_respawn_fraction", 0.05),
            patch_layout=env_config.get("patch_layout", "random"),
            patch_centers_config=env_config.get("patch_centers", None),
            patch_radial_fraction=env_config.get("patch_radial_fraction", 0.25),
            patch_spread_use_corners=env_config.get("patch_spread_use_corners", True),
            patch_spread_step=env_config.get("patch_spread_step", 0)
        )
        self.environment.init_food(env_config["initial_food_count"])
        
        # 個体群の初期化
        self.organisms: List[Organism] = []
        for _ in range(org_config["initial_population"]):
            x = np.random.randint(0, env_config["width"])
            y = np.random.randint(0, env_config["height"])
            organism = Organism(
                x=x,
                y=y,
                initial_energy=org_config["initial_energy"],
                genome_length=gen_config["genome_length"]
            )
            self.organisms.append(organism)
        
        # ロガーの初期化
        self.logger = SimulationLogger()
        
        # 行動設定
        self.behavior_config = config.get("behavior", {})
        
        # ステップ数
        self.current_step = 0
        
        # 前ステップの生死情報（リアルタイム可視化用）
        self.last_birth_count = 0
        self.last_death_count = 0
    
    def step(self) -> None:
        """
        シミュレーションを1ステップ進める
        
        以下の順序で処理を実行：
        1. 各個体の age を増やす
        2. 個体を移動させる
        3. 移動先に餌があれば食べる
        4. エネルギーを消費する
        5. 繁殖可能なら子個体を作る
        6. 死亡個体を除く
        7. 新しい子個体を追加する
        8. 餌を再生成する
        9. 統計情報をログに記録する
        """
        org_config = self.config["organism"]
        env_config = self.config["environment"]
        gen_config = self.config["genetics"]
        
        # ステップ前の個体数（死亡数を計算するため）
        population_before = len(self.organisms)
        
        # 1. 各個体の age を増やす
        for organism in self.organisms:
            organism.age_one_step()
        
        # 2-5. 個体の行動を処理
        new_offspring: List[Organism] = []
        move_count = 0
        
        behavior_settings = {
            "low_energy_threshold_ratio": self.behavior_config.get("low_energy_threshold_ratio", 0.5),
            "site_memory_steps": self.behavior_config.get("site_memory_steps", 20),
            "current_step": self.current_step
        }

        for organism in self.organisms:
            low_energy_threshold = org_config["reproduction_threshold"] * behavior_settings["low_energy_threshold_ratio"]
            low_energy = organism.energy < low_energy_threshold

            # 2. 移動させる
            moved = organism.move(
                env_config["width"],
                env_config["height"],
                org_config["move_type"],
                self.environment,
                low_energy,
                behavior_settings
            )
            if moved:
                move_count += 1

            # 3. 移動先に餌があれば食べる
            if self.environment.has_food(organism.x, organism.y):
                organism.eat(env_config["food_energy"])
                self.environment.remove_food(organism.x, organism.y)
                organism.last_food_position = (organism.x, organism.y)
                organism.last_food_step = self.current_step
            
            # 4. エネルギーを消費する
            # living_cost は毎ステップ必ず消費し、move_cost は実際に移動した場合のみ消費する
            move_cost = org_config["move_cost"] if moved else 0.0
            
            organism.consume_energy(
                move_cost,
                org_config["living_cost"]
            )
            
            # 5. 繁殖可能なら子個体を作る
            if organism.can_reproduce(org_config["reproduction_threshold"]):
                child = organism.reproduce(
                    width=env_config["width"],
                    height=env_config["height"],
                    offspring_energy=org_config["offspring_energy"],
                    reproduction_cost=org_config["reproduction_cost"],
                    mutation_rate=gen_config["mutation_rate"],
                    genome_length=gen_config["genome_length"]
                )
                new_offspring.append(child)
        
        # 6. 死亡個体を除く
        self.organisms = [
            org for org in self.organisms
            if not org.is_dead(org_config["max_age"])
        ]
        
        # 死亡数を計算
        death_count = population_before - len(self.organisms)
        birth_count = len(new_offspring)
        
        # 7. 新しい子個体を追加する
        self.organisms.extend(new_offspring)
        
        # 8. 餌を再生成する
        self.environment.respawn_food(env_config["food_respawn_rate"])
        
        # 9. 統計情報をログに記録する
        population_size = len(self.organisms)
        food_count = self.environment.food_count()

        move_rate = move_count / population_before if population_before > 0 else 0.0
        
        if population_size > 0:
            average_energy = sum(org.energy for org in self.organisms) / population_size
            average_age = sum(org.age for org in self.organisms) / population_size
            average_exploration_tendency = sum(org.phenotype["exploration_tendency"] for org in self.organisms) / population_size
            average_site_fidelity = sum(org.phenotype["site_fidelity"] for org in self.organisms) / population_size
            average_risk_tolerance = sum(org.phenotype["risk_tolerance"] for org in self.organisms) / population_size
            average_reproduction_timing = sum(org.phenotype["reproduction_timing"] for org in self.organisms) / population_size
        else:
            average_energy = 0.0
            average_age = 0.0
            average_exploration_tendency = 0.0
            average_site_fidelity = 0.0
            average_risk_tolerance = 0.0
            average_reproduction_timing = 0.0
        
        self.logger.record(
            step=self.current_step,
            population_size=population_size,
            food_count=food_count,
            average_energy=average_energy,
            average_age=average_age,
            birth_count=birth_count,
            death_count=death_count,
            move_count=move_count,
            move_rate=move_rate,
            average_exploration_tendency=average_exploration_tendency,
            average_site_fidelity=average_site_fidelity,
            average_risk_tolerance=average_risk_tolerance,
            average_reproduction_timing=average_reproduction_timing
        )
        
        # 前ステップの生死情報を更新
        self.last_birth_count = birth_count
        self.last_death_count = death_count
        
        self.current_step += 1
    
    def run(self) -> None:
        """
        シミュレーションを最後まで実行
        
        設定された steps の数だけ step() を呼び出す
        """
        total_steps = self.config["simulation"]["steps"]
        
        for _ in range(total_steps):
            self.step()
            
            # 個体数が0になってもエラーにならないようにする
            if len(self.organisms) == 0:
                # 個体がいない場合でも処理は続ける
                pass
    
    def get_state(self) -> Dict[str, Any]:
        """
        現在のシミュレーション状態を返す
        
        Returns:
            dict: 現在の状態を含む辞書
                - step: 現在のステップ数
                - organism_positions: 個体の座標リスト [(x, y), ...]
                - organism_energies: 個体のエネルギーリスト
                - organism_states: 個体の状態（"normal" or "can_reproduce"）
                - food_positions: 食料の座標リスト
                - population_size: 個体数
                - food_count: 食料数
                - average_energy: 平均エネルギー
        """
        org_config = self.config["organism"]
        
        organism_positions = [(org.x, org.y) for org in self.organisms]
        organism_energies = [org.energy for org in self.organisms]
        
        # 個体の状態を判定
        organism_states = []
        for org in self.organisms:
            if org.can_reproduce(org_config["reproduction_threshold"]):
                organism_states.append("can_reproduce")
            else:
                organism_states.append("normal")
        
        food_positions = list(self.environment.food)
        population_size = len(self.organisms)
        food_count = self.environment.food_count()
        
        if population_size > 0:
            average_energy = sum(organism_energies) / population_size
            average_age = sum(org.age for org in self.organisms) / population_size
        else:
            average_energy = 0.0
            average_age = 0.0
        
        return {
            "step": self.current_step,
            "organism_positions": organism_positions,
            "organism_energies": organism_energies,
            "organism_states": organism_states,
            "organism_phenotypes": [org.phenotype for org in self.organisms],
            "food_positions": food_positions,
            "population_size": population_size,
            "food_count": food_count,
            "average_energy": average_energy,
            "average_age": average_age,
            "birth_count": self.last_birth_count,
            "death_count": self.last_death_count
        }
