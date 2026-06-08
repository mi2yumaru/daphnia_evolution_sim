"""environment.py - Grid environment for the simulation

Supports food placement and respawn in either random mode or
patch-based modes: 'random', 'radial', 'spread'.
"""

from typing import Set, Tuple, List, Optional
import math
import numpy as np


class Environment:
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
    ) -> None:
        self.width = int(width)
        self.height = int(height)
        self.food: Set[Tuple[int, int]] = set()

        self.respawn_mode = str(respawn_mode)
        self.patch_count = max(1, int(patch_count))
        self.patch_radius = max(0, int(patch_radius))
        self.patch_density = float(patch_density)
        self.outside_respawn_fraction = float(outside_respawn_fraction)
        self.patch_layout = str(patch_layout)
        self.patch_radial_fraction = float(patch_radial_fraction)
        self.patch_spread_use_corners = bool(patch_spread_use_corners)
        self.patch_spread_step = int(patch_spread_step)

        # optional explicit centers
        self._explicit_patch_centers: Optional[List[Tuple[int, int]]] = None
        if patch_centers_config:
            self._explicit_patch_centers = [(int(x), int(y)) for x, y in patch_centers_config]

        self.patch_centers: List[Tuple[int, int]] = []

    def init_food(self, initial_count: int) -> None:
        if initial_count <= 0:
            return

        if self.respawn_mode == "patch":
            self._init_patch_regions()
            patch_cells = self._get_patch_cells()
            empty_patch = [p for p in patch_cells if p not in self.food]
            if empty_patch:
                place = min(initial_count, len(empty_patch))
                chosen = np.random.choice(len(empty_patch), size=place, replace=False)
                for i in chosen:
                    self.food.add(empty_patch[int(i)])
                if place < initial_count:
                    self._add_random_food(initial_count - place)
                return

        self._add_random_food(initial_count)

    def _add_random_food(self, count: int) -> None:
        if count <= 0:
            return
        empty = [(x, y) for x in range(self.width) for y in range(self.height) if (x, y) not in self.food]
        if not empty:
            return
        k = min(count, len(empty))
        idx = np.random.choice(len(empty), size=k, replace=False)
        for i in idx:
            self.food.add(empty[int(i)])

    def _init_patch_regions(self) -> None:
        if self.patch_centers:
            return

        # explicit centers override
        if self._explicit_patch_centers:
            centers = []
            for x, y in self._explicit_patch_centers:
                cx = max(0, min(self.width - 1, int(x)))
                cy = max(0, min(self.height - 1, int(y)))
                centers.append((cx, cy))
            self.patch_centers = centers[: self.patch_count]
            return

        layout = self.patch_layout
        n = max(1, self.patch_count)

        if layout == "radial":
            midx = (self.width - 1) / 2.0
            midy = (self.height - 1) / 2.0
            base_radius = max(1, int(round(min(self.width, self.height) * self.patch_radial_fraction)))
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

        if layout == "spread":
            step = self.patch_spread_step if self.patch_spread_step > 0 else max(1, min(self.width, self.height) // 40)
            candidates = [(x, y) for x in range(0, self.width, step) for y in range(0, self.height, step)]
            existing: List[Tuple[int, int]] = []
            if self.patch_spread_use_corners:
                existing.extend([(0, 0), (0, self.height - 1), (self.width - 1, 0), (self.width - 1, self.height - 1)])

            centers: List[Tuple[int, int]] = []

            def min_dist2(pt, pts):
                if not pts:
                    return float("inf")
                x0, y0 = pt
                return min((x0 - x1) ** 2 + (y0 - y1) ** 2 for x1, y1 in pts)

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

            if not centers:
                # fallback to random
                centers = [(np.random.randint(0, self.width), np.random.randint(0, self.height)) for _ in range(n)]

            self.patch_centers = centers[:n]
            return

        # default: random layout
        self.patch_centers = [(np.random.randint(0, self.width), np.random.randint(0, self.height)) for _ in range(n)]

    def _get_patch_cells(self) -> List[Tuple[int, int]]:
        cells: List[Tuple[int, int]] = []
        if not self.patch_centers:
            return cells
        r_adj = self.patch_radius + 0.5
        r2 = r_adj * r_adj
        for cx, cy in self.patch_centers:
            x0 = max(0, int(cx - self.patch_radius))
            x1 = min(self.width - 1, int(cx + self.patch_radius))
            y0 = max(0, int(cy - self.patch_radius))
            y1 = min(self.height - 1, int(cy + self.patch_radius))
            for x in range(x0, x1 + 1):
                dx2 = (x - cx) * (x - cx)
                for y in range(y0, y1 + 1):
                    dy2 = (y - cy) * (y - cy)
                    if dx2 + dy2 <= r2:
                        cells.append((x, y))
        # deduplicate
        return list(set(cells))

    def has_food(self, x: int, y: int) -> bool:
        return (x, y) in self.food

    def remove_food(self, x: int, y: int) -> None:
        self.food.discard((x, y))

    def respawn_food(self, rate: float) -> None:
        if rate <= 0.0:
            return
        total = self.width * self.height
        to_add = int(total * rate)
        if to_add <= 0:
            return

        if self.respawn_mode == "patch":
            self._init_patch_regions()
            patch_cells = self._get_patch_cells()
            empty_patch = [p for p in patch_cells if p not in self.food]

            outside_frac = max(0.0, min(1.0, self.outside_respawn_fraction))
            patch_target = int(to_add * (1.0 - outside_frac))
            outside_target = to_add - patch_target

            added = 0
            if empty_patch and patch_target > 0:
                max_patch = max(1, int(len(empty_patch) * self.patch_density))
                add_patch = min(patch_target, max_patch, len(empty_patch))
                chosen = np.random.choice(len(empty_patch), size=add_patch, replace=False)
                for i in chosen:
                    self.food.add(empty_patch[int(i)])
                added += add_patch

            if outside_target > 0:
                empty_outside = [
                    (x, y)
                    for x in range(self.width)
                    for y in range(self.height)
                    if (x, y) not in self.food and (x, y) not in patch_cells
                ]
                if empty_outside:
                    add_out = min(outside_target, len(empty_outside))
                    chosen_out = np.random.choice(len(empty_outside), size=add_out, replace=False)
                    for i in chosen_out:
                        self.food.add(empty_outside[int(i)])
                    added += add_out

            if added < to_add:
                self._add_random_food(to_add - added)
            return

        # random mode
        self._add_random_food(to_add)

    def food_count(self) -> int:
        return len(self.food)
