"""
environment.py - 環境（グリッド）の定義

2Dグリッド上の食料管理と、将来的な環境属性（温度、光、環境段階など）の拡張を想定
"""

from typing import Set, Tuple, List, Optional
import numpy as np


class Environment:
    """
    2Dグリッド環境を表現するクラス

    食料の配置・削除・再生成などを管理します
    """

    def __init__(
        self,
        width: int,
        height: int,
        respawn_mode: str = "random",
        patch_count: int = 4,
        patch_radius: int = 5,
        patch_density: float = 0.8,
        outside_respawn_fraction: float = 0.05,
        patch_layout: str = "random",
        patch_centers_config: Optional[List[Tuple[int, int]]] = None,
        patch_radial_fraction: float = 0.25,
        patch_spread_use_corners: bool = True,
        patch_spread_step: int = 0,
    ):
        self.width = int(width)
        self.height = int(height)
        self.food: Set[Tuple[int, int]] = set()

        self.respawn_mode = respawn_mode
        self.patch_count = int(patch_count)
        self.patch_radius = int(patch_radius)
        self.patch_density = float(patch_density)
        self.outside_respawn_fraction = float(outside_respawn_fraction)
        self.patch_layout = str(patch_layout)
        self.patch_radial_fraction = float(patch_radial_fraction)
        self.patch_spread_use_corners = bool(patch_spread_use_corners)
        self.patch_spread_step = int(patch_spread_step)

        # explicit centers (optional)
        self._explicit_patch_centers: Optional[List[Tuple[int, int]]] = None
        if patch_centers_config:
            self._explicit_patch_centers = [(int(x), int(y)) for x, y in patch_centers_config]

        self.patch_centers: List[Tuple[int, int]] = []

    def init_food(self, initial_count: int) -> None:
        if self.respawn_mode == "patch":
            self._init_patch_regions()
            patch_cells = self._get_patch_cells()
            empty_patch_cells = [pos for pos in patch_cells if pos not in self.food]
            if empty_patch_cells:
                count = min(initial_count, len(empty_patch_cells))
                chosen = np.random.choice(len(empty_patch_cells), size=count, replace=False)
                for idx in chosen:
                    self.food.add(empty_patch_cells[idx])

                if count < initial_count:
                    remaining = initial_count - count
                    self._add_random_food(remaining)
                return

        self._add_random_food(initial_count)

    def _add_random_food(self, count: int) -> None:
        empty_cells = [(x, y) for x in range(self.width) for y in range(self.height) if (x, y) not in self.food]
        if not empty_cells or count <= 0:
            return
        count = min(count, len(empty_cells))
        chosen_positions = np.random.choice(len(empty_cells), size=count, replace=False)
        for idx in chosen_positions:
            self.food.add(empty_cells[idx])

    def _init_patch_regions(self) -> None:
        # already initialized
        if self.patch_centers:
            return

        # explicit centers provided?
        if self._explicit_patch_centers:
            centers: List[Tuple[int, int]] = []
            for x, y in self._explicit_patch_centers:
                cx = max(0, min(self.width - 1, int(x)))
                cy = max(0, min(self.height - 1, int(y)))
                centers.append((cx, cy))
            self.patch_centers = centers[: self.patch_count]
            return

        # radial layout
        if self.patch_layout == "radial":
            import math

            n = max(1, self.patch_count)
            midx = int(round(self.width * 0.5))
            midy = int(round(self.height * 0.5))
            base_radius = int(round(min(self.width, self.height) * float(self.patch_radial_fraction)))
            if base_radius <= 0:
                base_radius = max(1, min(self.width, self.height) // 4)
            centers: List[Tuple[int, int]] = []
            for i in range(n):
                theta = 2.0 * math.pi * i / n
                x = int(round(midx + base_radius * math.cos(theta)))
                y = int(round(midy + base_radius * math.sin(theta)))
                x = max(0, min(self.width - 1, x))
                y = max(0, min(self.height - 1, y))
                centers.append((x, y))
            self.patch_centers = centers
            return

        # spread layout (farthest-point sampling), optional corner seeding
        if self.patch_layout == "spread":
            n = max(1, self.patch_count)
            step = self.patch_spread_step if self.patch_spread_step > 0 else max(1, min(self.width, self.height) // 40)
            candidates = [(x, y) for x in range(0, self.width, step) for y in range(0, self.height, step)]

            existing: List[Tuple[int, int]] = []
            if self.patch_spread_use_corners:
                existing.extend([(0, 0), (0, self.height - 1), (self.width - 1, 0), (self.width - 1, self.height - 1)])

            centers: List[Tuple[int, int]] = []

            def min_dist2(pt, points):
                if not points:
                    return float("inf")
                x, y = pt
                return min((x - px) ** 2 + (y - py) ** 2 for px, py in points)

            for _ in range(n):
                best = None
                bestd = -1.0
                for c in candidates:
                    if c in centers:
                        continue
                    d = min_dist2(c, existing + centers)
                    if d > bestd:
                        bestd = d
                        best = c
                if best is None:
                    break
                centers.append(best)

            self.patch_centers = centers[:n]
            return

        # default random
        centers: List[Tuple[int, int]] = []
        for _ in range(self.patch_count):
            x = np.random.randint(0, self.width)
            y = np.random.randint(0, self.height)
            centers.append((x, y))
        self.patch_centers = centers

    def _get_patch_cells(self) -> List[Tuple[int, int]]:
        cells: List[Tuple[int, int]] = []
        # use radius + 0.5 to smooth edges
        r_adj = self.patch_radius + 0.5
        r2 = r_adj * r_adj
        for center_x, center_y in self.patch_centers:
            x0 = max(0, int(center_x - self.patch_radius))
            x1 = min(self.width - 1, int(center_x + self.patch_radius))
            y0 = max(0, int(center_y - self.patch_radius))
            y1 = min(self.height - 1, int(center_y + self.patch_radius))
            for x in range(x0, x1 + 1):
                dx2 = (x - center_x) * (x - center_x)
                for y in range(y0, y1 + 1):
                    dy2 = (y - center_y) * (y - center_y)
                    if dx2 + dy2 <= r2:
                        cells.append((x, y))
        return list(set(cells))

    def has_food(self, x: int, y: int) -> bool:
        return (x, y) in self.food

    def remove_food(self, x: int, y: int) -> None:
        self.food.discard((x, y))

    def respawn_food(self, rate: float) -> None:
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

            outside_frac = max(0.0, min(1.0, self.outside_respawn_fraction))
            patch_target = int(num_to_add * (1.0 - outside_frac))
            outside_target = num_to_add - patch_target

            added = 0
            if empty_patch_cells and patch_target > 0:
                max_patch_additions = int(len(empty_patch_cells) * self.patch_density)
                max_patch_additions = max(1, max_patch_additions)
                patch_to_add = min(patch_target, max_patch_additions, len(empty_patch_cells))
                chosen = np.random.choice(len(empty_patch_cells), size=patch_to_add, replace=False)
                for idx in chosen:
                    self.food.add(empty_patch_cells[idx])
                added += patch_to_add

            if outside_target > 0:
                empty_outside = [
                    (x, y)
                    for x in range(self.width)
                    for y in range(self.height)
                    if (x, y) not in self.food and (x, y) not in patch_cells
                ]
                if empty_outside:
                    outside_to_add = min(outside_target, len(empty_outside))
                    chosen_out = np.random.choice(len(empty_outside), size=outside_to_add, replace=False)
                    for idx in chosen_out:
                        self.food.add(empty_outside[idx])
                    added += outside_to_add

            if added < num_to_add:
                remaining = num_to_add - added
                self._add_random_food(remaining)
            return

        # random mode
        self._add_random_food(num_to_add)

    def food_count(self) -> int:
        return len(self.food)
