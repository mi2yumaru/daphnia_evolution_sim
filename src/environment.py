"""
environment.py - 環境（グリッド）の定義

2Dグリッド上の食料管理と、将来的な環境属性（温度、光、環境段階など）の拡張を想定
"""

from typing import Set, Tuple
import numpy as np


class Environment:
    """
    2Dグリッド環境を表現するクラス
    
    食料の配置・削除・再生成などを管理します
    
    属性:
        width: グリッドの幅
        height: グリッドの高さ
        food: 食料の位置を管理するセット（座標のタプルで管理）
    """
    
    def __init__(self, width: int, height: int):
        """
        環境を初期化
        
        Args:
            width: グリッドの幅
            height: グリッドの高さ
        """
        self.width: int = width
        self.height: int = height
        self.food: Set[Tuple[int, int]] = set()
        
        # 将来的な環境属性の拡張用
        # self.temperature: float = 20.0  # 温度
        # self.daylight: float = 1.0       # 光の強度
        # self.environmental_phase: str = "normal"  # 環境段階
    
    def init_food(self, initial_count: int) -> None:
        """
        初期食料をランダムに配置
        
        Args:
            initial_count: 配置する食料の数
        """
        positions = np.random.randint(0, self.width, size=(initial_count, 2))
        for x, y in positions:
            self.food.add((int(x), int(y)))
    
    def has_food(self, x: int, y: int) -> bool:
        """
        指定座標に食料があるか確認
        
        Args:
            x: x座標
            y: y座標
        
        Returns:
            bool: 食料があればTrue
        """
        return (x, y) in self.food
    
    def remove_food(self, x: int, y: int) -> None:
        """
        指定座標の食料を削除
        
        Args:
            x: x座標
            y: y座標
        """
        self.food.discard((x, y))
    
    def respawn_food(self, rate: float) -> None:
        """
        毎ステップ食料を再生成
        
        グリッド全体（width * height）に対して rate の割合で新しい食料を追加
        既に食料がある場所には重複追加しない
        
        Args:
            rate: 食料再生成率（0.0～1.0）
        """
        # 再生成する食料数を計算
        num_to_add = int(self.width * self.height * rate)
        
        for _ in range(num_to_add):
            # 既に食料がない場所にランダムに配置
            while True:
                x = np.random.randint(0, self.width)
                y = np.random.randint(0, self.height)
                if (x, y) not in self.food:
                    self.food.add((x, y))
                    break
    
    def food_count(self) -> int:
        """
        現在の食料数を返す
        
        Returns:
            int: 食料の数
        """
        return len(self.food)
