"""
organism.py - 個体の定義

各個体は x, y 座標、エネルギー、年齢、ゲノムを持ち、
移動、摂食、繁殖、死亡判定などのメソッドを提供します。
"""

from typing import List, Optional, Tuple, Dict, Any
import numpy as np


class Organism:
    """
    個体を表現するクラス
    
    属性:
        x: グリッド上のx座標
        y: グリッド上のy座標
        energy: 現在のエネルギー値
        age: 個体の年齢（ステップ数）
        genome: 0/1 のゲノム配列
    """
    
    def __init__(
        self,
        x: int,
        y: int,
        initial_energy: float,
        genome_length: int,
        genome: Optional[np.ndarray] = None
    ):
        """
        個体を初期化
        
        Args:
            x: 初期x座標
            y: 初期y座標
            initial_energy: 初期エネルギー値
            genome_length: ゲノム長
            genome: ゲノム配列。Noneの場合は0/1ランダムで初期化
        """
        self.x: int = x
        self.y: int = y
        self.energy: float = initial_energy
        self.age: int = 0
        
        if genome is None:
            # ランダムな0/1配列で初期化
            self.genome: np.ndarray = np.random.randint(0, 2, size=genome_length)
        else:
            self.genome: np.ndarray = genome.copy()

        self.phenotype: Dict[str, float] = self.calculate_phenotype()
        self.last_food_position: Optional[Tuple[int, int]] = None
        self.last_food_step: Optional[int] = None
    
    def calculate_phenotype(self) -> Dict[str, float]:
        """ゲノムから phenotype を計算する"""
        phenotypes = {}
        labels = [
            "exploration_tendency",
            "site_fidelity",
            "risk_tolerance",
            "reproduction_timing"
        ]

        for idx, label in enumerate(labels):
            start = idx * 5
            segment = self.genome[start:start + 5].astype(int)
            value = 0
            for bit in segment:
                value = (value << 1) | int(bit)
            phenotypes[label] = value / 31.0

        return phenotypes

    def move(
        self,
        width: int,
        height: int,
        move_type: str,
        environment: Any,
        low_energy: bool,
        behavior_config: Dict[str, Any]
    ) -> bool:
        """
        個体を移動させる
        
        Returns:
        bool: 実際に座標が変化した場合は True、移動しなかった場合は False

        Args:
            width: グリッドの幅
            height: グリッドの高さ
            move_type: "moore" (8方向) または "von_neumann" (4方向)
        """

        old_x = self.x
        old_y = self.y

        if move_type == "moore":
            directions = [
                (-1, -1), (-1, 0), (-1, 1),
                (0, -1),           (0, 1),
                (1, -1),  (1, 0),  (1, 1)
            ]
        elif move_type == "von_neumann":
            directions = [
                (-1, 0),
                (0, -1), (0, 1),
                (1, 0)
            ]
        else:
            raise ValueError(f"Unknown move_type: {move_type}")

        base_move_prob = self.phenotype["exploration_tendency"]
        if low_energy:
            risk = self.phenotype["risk_tolerance"]
            base_move_prob *= 0.4 + 0.6 * risk

        # 周囲に餌が見つかるかどうかを判定
        detection_range = behavior_config.get("food_detection_range", 1)
        food_neighbors = []
        for dx, dy in directions:
            for dist in range(1, detection_range + 1):
                target_x = self.x + dx * dist
                target_y = self.y + dy * dist
                if 0 <= target_x < width and 0 <= target_y < height:
                    if environment.has_food(target_x, target_y):
                        food_neighbors.append((dx, dy))
                        break
                else:
                    break

        # last_food_position が有効かどうかを判定
        memory_steps = behavior_config.get("site_memory_steps", 20)
        use_site_memory = (
            self.last_food_position is not None
            and self.last_food_step is not None
            and self.last_food_step + memory_steps >= behavior_config.get("current_step", 0)
        )

        stay_probability = 1.0 - base_move_prob
        if stay_probability < 0.0:
            stay_probability = 0.0

        if food_neighbors:
            # 餌が存在する場合は餌方向にバイアスをかける
            candidates = directions.copy()
            weights = []
            for dx, dy in candidates:
                weight = 1.0
                if (dx, dy) in food_neighbors:
                    weight += 4.0
                if use_site_memory and self.last_food_position is not None:
                    target_x = self.x + dx
                    target_y = self.y + dy
                    distance_before = abs(self.last_food_position[0] - self.x) + abs(self.last_food_position[1] - self.y)
                    distance_after = abs(self.last_food_position[0] - target_x) + abs(self.last_food_position[1] - target_y)
                    if distance_after < distance_before:
                        weight += 2.0 * self.phenotype["site_fidelity"]
                weights.append(weight)
            chosen = np.random.choice(len(candidates), p=np.array(weights) / np.sum(weights))
            dx, dy = candidates[chosen]
        else:
            if np.random.random() >= base_move_prob:
                dx, dy = 0, 0
            else:
                candidates = directions.copy()
                weights = [1.0] * len(candidates)
                if use_site_memory and self.last_food_position is not None:
                    for i, (dx, dy) in enumerate(candidates):
                        target_x = self.x + dx
                        target_y = self.y + dy
                        if 0 <= target_x < width and 0 <= target_y < height:
                            distance_before = abs(self.last_food_position[0] - self.x) + abs(self.last_food_position[1] - self.y)
                            distance_after = abs(self.last_food_position[0] - target_x) + abs(self.last_food_position[1] - target_y)
                            if distance_after < distance_before:
                                weights[i] += self.phenotype["site_fidelity"] * 2.0
                weights = np.array(weights)
                if weights.sum() == 0:
                    choice = np.random.randint(len(candidates))
                else:
                    weights = weights / weights.sum()
                    choice = np.random.choice(len(candidates), p=weights)
                dx, dy = candidates[choice]

        new_x = max(0, min(self.x + dx, width - 1))
        new_y = max(0, min(self.y + dy, height - 1))

        self.x = new_x
        self.y = new_y

        return(self.x != old_x) or (self.y != old_y)
    
    def consume_energy(self, move_cost: float, living_cost: float) -> None:
        """
        移動と生活のコストを消費
        
        Args:
            move_cost: 移動のエネルギーコスト
            living_cost: 生活維持のエネルギーコスト
        """
        self.energy -= move_cost + living_cost
    
    def eat(self, food_energy: float) -> None:
        """
        食料を摂食してエネルギーを得る
        
        Args:
            food_energy: 食料が持つエネルギー量
        """
        self.energy += food_energy
    
    def can_reproduce(self, base_threshold: float) -> bool:
        """
        繁殖可能な状態か判定
        
        Args:
            base_threshold: 基本の繁殖閾値
        
        Returns:
            bool: 繁殖可能ならTrue
        """
        effective_threshold = base_threshold * (1.0 + self.phenotype["reproduction_timing"])
        return self.energy >= effective_threshold

    def get_effective_reproduction_threshold(self, base_threshold: float) -> float:
        """実際に必要な繁殖エネルギー閾値を返す"""
        return base_threshold * (1.0 + self.phenotype["reproduction_timing"])
    
    def reproduce(
        self,
        width: int,
        height: int,
        offspring_energy: float,
        reproduction_cost: float,
        mutation_rate: float,
        genome_length: int
    ) -> "Organism":
        """
        子個体を生成
        
        親のエネルギーは reproduction_cost だけ減少し、
        子のゲノムは親をコピーしてから mutation_rate に応じてビット反転される
        
        Args:
            width: グリッドの幅
            height: グリッドの高さ
            offspring_energy: 子個体の初期エネルギー
            reproduction_cost: 繁殖コスト
            mutation_rate: ゲノムの各ビットについて、変異する確率
            genome_length: ゲノム長
        
        Returns:
            Organism: 生成された子個体
        """
        # 親のエネルギーを消費
        self.energy -= reproduction_cost
        
        # 子のゲノムは親のコピー
        child_genome = self.genome.copy()
        
        # 変異を適用
        for i in range(len(child_genome)):
            if np.random.random() < mutation_rate:
                child_genome[i] = 1 - child_genome[i]  # ビット反転
        
        # 子個体を親の近くにランダムに配置
        # 親の位置から±2以内の範囲にランダムに配置
        child_x = self.x + np.random.randint(-2, 3)
        child_y = self.y + np.random.randint(-2, 3)
        child_x = max(0, min(child_x, width - 1))
        child_y = max(0, min(child_y, height - 1))
        
        child = Organism(
            x=child_x,
            y=child_y,
            initial_energy=offspring_energy,
            genome_length=genome_length,
            genome=child_genome
        )
        
        return child
    
    def is_dead(self, max_age: int) -> bool:
        """
        個体が死亡しているか判定
        
        エネルギーが0以下、または最大年齢に達したら死亡
        
        Args:
            max_age: 個体の最大年齢
        
        Returns:
            bool: 死亡していればTrue
        """
        return self.energy <= 0 or self.age >= max_age
    
    def age_one_step(self) -> None:
        """年齢を1増やす"""
        self.age += 1
