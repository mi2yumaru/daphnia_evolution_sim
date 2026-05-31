"""
organism.py - 個体の定義

各個体は x, y 座標、エネルギー、年齢、ゲノムを持ち、
移動、摂食、繁殖、死亡判定などのメソッドを提供します。
"""

from typing import List, Optional, Tuple
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
    
    def move(self, width: int, height: int, move_type: str = "moore") -> None:
        """
        個体を移動させる
        
        Args:
            width: グリッドの幅
            height: グリッドの高さ
            move_type: "moore" (8方向) または "von_neumann" (4方向)
        """
        if move_type == "moore":
            # 周囲8方向
            directions = [
                (-1, -1), (-1, 0), (-1, 1),
                (0, -1),           (0, 1),
                (1, -1),  (1, 0),  (1, 1)
            ]
        elif move_type == "von_neumann":
            # 上下左右4方向
            directions = [
                (-1, 0),
                (0, -1), (0, 1),
                (1, 0)
            ]
        else:
            raise ValueError(f"Unknown move_type: {move_type}")
        
        # ランダムに1方向を選択
        dy, dx = directions[np.random.randint(len(directions))]
        new_x = self.x + dx
        new_y = self.y + dy
        
        # グリッド境界内に留まる
        self.x = max(0, min(new_x, width - 1))
        self.y = max(0, min(new_y, height - 1))
    
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
    
    def can_reproduce(self, threshold: float) -> bool:
        """
        繁殖可能な状態か判定
        
        Args:
            threshold: 繁殖に必要なエネルギー値
        
        Returns:
            bool: 繁殖可能ならTrue
        """
        return self.energy >= threshold
    
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
