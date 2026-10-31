"""STEP3: Candidate initial cells by Euclidean distance to the nearest patch cell.

This module has no random draws and does not alter the simulation's dynamics.
The environment grid uses integer (x, y) coordinates.
"""

from __future__ import annotations

import math
from typing import Collection


def initial_placement_candidates(
    width: int,
    height: int,
    patch_cells: Collection[tuple[int, int]],
    mode: str,
    near_max_distance: float = 3.0,
    far_min_distance: float = 15.0,
) -> list[tuple[int, int]]:
    """Return eligible cells, sorted by x then y.

    inside:       member of patch region
    near:         outside patch, with 0 < distance <= near_max_distance
    far:          outside patch, with distance >= far_min_distance

    Distance is measured to the *nearest cell of the patch region*, not to
    the patch center. Near and far are non-overlapping if far_min > near_max.
    """
    if mode not in {"inside", "near", "far"}:
        raise ValueError("initial placement mode must be inside, near or far")
    if width < 1 or height < 1:
        raise ValueError("Grid dimensions must be positive")
    if not (math.isfinite(near_max_distance) and near_max_distance > 0):
        raise ValueError("near_max_distance must be a finite positive value")
    if not (math.isfinite(far_min_distance) and far_min_distance > near_max_distance):
        raise ValueError("far_min_distance must be finite and > near_max_distance")

    patches = set(patch_cells)
    if not patches:
        raise ValueError("Patch mode requires at least one patch cell")
    if any(not (0 <= x < width and 0 <= y < height) for x, y in patches):
        raise ValueError("Patch cell outside environment grid")

    result: list[tuple[int, int]] = []
    if mode == "inside":
        return sorted(patches)

    near2 = near_max_distance * near_max_distance
    far2 = far_min_distance * far_min_distance
    patch_locations = sorted(patches)
    for x in range(width):
        for y in range(height):
            if (x, y) in patches:
                continue
            distance2 = min(
                (x - px) ** 2 + (y - py) ** 2
                for px, py in patch_locations
            )
            if mode == "near" and 0 < distance2 <= near2:
                result.append((x, y))
            elif mode == "far" and distance2 >= far2:
                result.append((x, y))
    return result
