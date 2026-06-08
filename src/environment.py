"""
environment.py - 環境（グリッド）の定義

2Dグリッド上の食料管理と、将来的な環境属性（温度、光、環境段階など）の拡張を想定
"""

from typing import Set, Tuple, List
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
    
    def __init__(
        self,
        width: int,
        height: int,
        respawn_mode: str = "random",
        patch_count: int = 3,
        patch_radius: int = 5,
        patch_density: float = 0.8
    ):
        """
        環境を初期化
        
        Args:
            width: グリッドの幅
            height: グリッドの高さ
            respawn_mode: 食料再生成モード（random または patch）
            patch_count: パッチ領域の数
            patch_radius: パッチの半径
            patch_density: パッチ領域に再生成される割合
        """
        self.width: int = width
        self.height: int = height
        self.food: Set[Tuple[int, int]] = set()
        self.respawn_mode = respawn_mode
        self.patch_count = patch_count
        self.patch_radius = patch_radius
        self.patch_density = patch_density
        self.patch_centers: List[Tuple[int, int]] = []
        
        # 将来的な環境属性の拡張用
        # self.temperature: float = 20.0  # 温度
        # self.daylight: float = 1.0       # 光の強度
        # self.environmental_phase: str = "normal"  # 環境段階
    
    def init_food(self, initial_count: int) -> None:
        """
        初期食料を配置
        
        Args:
            initial_count: 配置する食料の数
        """
        if self.respawn_mode == "patch":
            self._init_patch_regions()
            patch_cells = self._get_patch_cells()
            empty_patch_cells = [pos for pos in patch_cells if pos not in self.food]
            if empty_patch_cells:
                patch_count = min(initial_count, len(empty_patch_cells))
                chosen = np.random.choice(len(empty_patch_cells), size=patch_count, replace=False)
                for idx in chosen:
                    self.food.add(empty_patch_cells[idx])

                if patch_count < initial_count:
                    remaining = initial_count - patch_count
                    self._add_random_food(remaining)
                return

        self._add_random_food(initial_count)

    def _add_random_food(self, count: int) -> None:
        """
        グリッド上の空きセルにランダムに食料を追加する
        """
        empty_cells = [
            (x, y)
            for x in range(self.width)
            for y in range(self.height)
            if (x, y) not in self.food
        ]

        if not empty_cells or count <= 0:
            return

        count = min(count, len(empty_cells))
        chosen_positions = np.random.choice(len(empty_cells), size=count, replace=False)
        for idx in chosen_positions:
            self.food.add(empty_cells[idx])

    def _init_patch_regions(self) -> None:
        """
        パッチ領域の中心を初期化する
        """
        if self.patch_centers:
            return

        self.patch_centers = []
        for _ in range(self.patch_count):
            x = np.random.randint(0, self.width)
            y = np.random.randint(0, self.height)
            self.patch_centers.append((x, y))

    def _get_patch_cells(self) -> List[Tuple[int, int]]:
        """
        パッチ領域内のセルを返す
        """
        cells: List[Tuple[int, int]] = []
        for center_x, center_y in self.patch_centers:
            for x in range(center_x - self.patch_radius, center_x + self.patch_radius + 1):
                for y in range(center_y - self.patch_radius, center_y + self.patch_radius + 1):
                    if 0 <= x < self.width and 0 <= y < self.height:
                        cells.append((x, y))
        return list(set(cells))
    
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
        
        Args:
            rate: 食料再生成率（0.0～1.0）
        """
        if rate <= 0.0:
            return

        total_cells = self.width * self.height
        num_to_add = int(total_cells * rate)
        if num_to_add <= 0:
            return

        if self.respawn_mode == "patch":
            self._init_patch_regions()
            patch_cells = self._get_patch_cells()
            empty_patch_cells = [pos for pos in patch_cells if pos not in self.food]
            if not empty_patch_cells:
                return

            # パッチ内で再生成する個数は patch_density で調整
            max_patch_additions = int(len(empty_patch_cells) * self.patch_density)
            max_patch_additions = max(1, max_patch_additions)
            num_to_add = min(num_to_add, max_patch_additions, len(empty_patch_cells))
            chosen = np.random.choice(len(empty_patch_cells), size=num_to_add, replace=False)
            for idx in chosen:
                self.food.add(empty_patch_cells[idx])
            return

        # ランダムモード
        self._add_random_food(num_to_add)
    
    def food_count(self) -> int:
        """
        現在の食料数を返す
        
        Returns:
            int: 食料の数
        """
        return len(self.food)
