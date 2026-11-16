"""Frozen pre-optimization movement implementation.

Copied from src/organism.py in commit 894ea1933b10caa0210332b7d2438231a68ce678.
This is only imported by tests; do not replace its computations with optimized
helpers, otherwise the regression test would no longer be independent.
"""
from __future__ import annotations

from typing import Any, Dict
import numpy as np
from src.spatial import wrap_coordinate, manhattan_distance


def reference_move(
    self,
    width: int,
    height: int,
    move_type: str,
    environment: Any,
    low_energy: bool,
    behavior_config: Dict[str, Any],
    periodic_boundary: bool = False,
) -> bool:
    """
    個体を移動させる
    
    自分のいるマスも含めて餌を確認し、「移動しない」ことも候補の1つとして重み付き選択する。


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

    # 念のため 0.0〜1.0 に丸める
    base_move_prob = float(np.clip(base_move_prob, 0.0, 1.0))

     # 行動設定
    detection_range = int(behavior_config.get("food_detection_range", 1))
    current_cell_food_weight = float(behavior_config.get("current_cell_food_weight", 8.0))
    nearby_food_weight = float(behavior_config.get("nearby_food_weight", 4.0))
    site_memory_weight = float(behavior_config.get("site_memory_weight", 2.0))

    # 候補: (0, 0) は「移動しない」
    candidates = [(0, 0)]

    # 有限境界では範囲外の方向を除外する。
    # 周期境界では全方向を許可し、小さいグリッドで同じ
    # 移動先が複数の方向に現れる場合は重複計上しない。
    seen_targets = {(self.x, self.y)}
    for dx, dy in directions:
        target_x = wrap_coordinate(self.x + dx, width, periodic_boundary)
        target_y = wrap_coordinate(self.y + dy, height, periodic_boundary)
        if not (0 <= target_x < width and 0 <= target_y < height):
            continue
        if periodic_boundary and (target_x, target_y) in seen_targets:
            continue
        seen_targets.add((target_x, target_y))
        candidates.append((dx, dy))

    # もし動ける方向がない場合は移動しない
    if len(candidates) == 1:
        return False

    # 自分のいるマスに餌があるか
    current_cell_has_food = environment.has_food(self.x, self.y)

    # 周囲方向に餌が見つかるかどうかを判定
    # detection_range > 1 の場合は、その方向に何マス先まで見る
    food_directions = set()

    for dx, dy in candidates[1:]:
        for dist in range(1, detection_range + 1):
            target_x = wrap_coordinate(
                self.x + dx * dist, width, periodic_boundary
            )
            target_y = wrap_coordinate(
                self.y + dy * dist, height, periodic_boundary
            )

            if not (0 <= target_x < width and 0 <= target_y < height):
                break
            if (target_x, target_y) == (self.x, self.y):
                # A ray has wrapped back to its starting cell.
                break

            if environment.has_food(target_x, target_y):
                # 実際の移動は1マスなので、餌がある「方向」だけ記録する
                food_directions.add((dx, dy))
                break

    # last_food_position が有効かどうかを判定
    memory_steps = behavior_config.get("site_memory_steps", 20)

    use_site_memory = (
        self.last_food_position is not None
        and self.last_food_step is not None
        and self.last_food_step + memory_steps >= behavior_config.get("current_step", 0)
    )

    weights = []
    move_candidate_count = len(candidates) - 1

    for dx, dy in candidates:
        # stay: 移動しない
        if dx == 0 and dy == 0:
            # exploration_tendency が低いほど stay が強くなる
            weight = 1.0 - base_move_prob

            # 自分のマスに餌がある場合は、移動しない重みを強くする
            if current_cell_has_food:
                weight += current_cell_food_weight

        # move: 周囲へ移動
        else:
            # exploration_tendency が高いほど移動候補全体が強くなる
            weight = base_move_prob / move_candidate_count

            # その方向に餌がある場合は、その方向を強くする
            if (dx, dy) in food_directions:
                weight += nearby_food_weight

            # 最後に餌を食べた場所へ近づく方向を少し優遇
            if use_site_memory and self.last_food_position is not None:
                target_x = wrap_coordinate(
                    self.x + dx, width, periodic_boundary
                )
                target_y = wrap_coordinate(
                    self.y + dy, height, periodic_boundary
                )
                distance_before = manhattan_distance(
                    self.last_food_position, (self.x, self.y),
                    width, height, periodic_boundary,
                )
                distance_after = manhattan_distance(
                    self.last_food_position, (target_x, target_y),
                    width, height, periodic_boundary,
                )

                if distance_after < distance_before:
                    weight += site_memory_weight * self.phenotype["site_fidelity"]

        weights.append(max(weight, 0.0))

    weights = np.array(weights, dtype=float)

    if weights.sum() <= 0.0:
        dx, dy = 0, 0
    else:
        probabilities = weights / weights.sum()
        choice = np.random.choice(len(candidates), p=probabilities)
        dx, dy = candidates[choice]

    self.x = wrap_coordinate(self.x + dx, width, periodic_boundary)
    self.y = wrap_coordinate(self.y + dy, height, periodic_boundary)

    return (self.x != old_x) or (self.y != old_y)

