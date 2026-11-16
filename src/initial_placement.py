"""STEP3: Candidate initial cells by Euclidean distance to the nearest patch cell.

This module has no random draws and does not alter the simulation's dynamics.
The environment grid uses integer (x, y) coordinates.
"""

from __future__ import annotations

import math
from typing import Collection

try:
    from .spatial import squared_euclidean_distance
except ImportError:
    from spatial import squared_euclidean_distance


def nearest_patch_center_spacing(
    width: int,
    height: int,
    patch_centers: Collection[tuple[int, int]],
    periodic_boundary: bool = False,
) -> float:
    """Shortest center-to-center Euclidean distance, including torus wrapping.

    Requires at least two distinct centers in the map; a one-patch environment
    has no interpatch spacing by definition.
    """
    if width < 1 or height < 1:
        raise ValueError("Grid dimensions must be positive")
    centers = [tuple(map(int, center)) for center in patch_centers]
    if len(centers) < 2:
        raise ValueError("Relative placement requires at least two patch centers")
    if len(set(centers)) != len(centers):
        raise ValueError("Patch centers must be distinct")
    if any(not (0 <= x < width and 0 <= y < height) for x, y in centers):
        raise ValueError("Patch center outside environment grid")

    best_squared = min(
        squared_euclidean_distance(
            centers[i], centers[j], width, height, periodic_boundary
        )
        for i in range(len(centers))
        for j in range(i + 1, len(centers))
    )
    if best_squared <= 0:
        raise ValueError("Patch center spacing must be positive")
    return math.sqrt(best_squared)


def resolve_initial_placement_distances(
    width: int,
    height: int,
    patch_centers: Collection[tuple[int, int]],
    *,
    periodic_boundary: bool = False,
    distance_mode: str = "absolute",
    near_max_distance: float = 3.0,
    far_min_distance: float = 15.0,
    near_fraction: float = 0.2,
    far_fraction: float = 0.4,
) -> tuple[float, float]:
    """Return near/far thresholds in grid cells.

    'absolute' preserves older fixed-distance experiment configurations.
    'relative' scales both thresholds by L, the shortest center spacing
    measured using the configured boundary condition. Distances from a
    candidate founder cell are still measured to the nearest *patch cell*.
    """
    if distance_mode == "absolute":
        near, far = float(near_max_distance), float(far_min_distance)
    elif distance_mode == "relative":
        near_ratio, far_ratio = float(near_fraction), float(far_fraction)
        if not (
            math.isfinite(near_ratio)
            and math.isfinite(far_ratio)
            and 0 < near_ratio < far_ratio
        ):
            raise ValueError(
                "Relative placement requires 0 < near_fraction < far_fraction"
            )
        spacing = nearest_patch_center_spacing(
            width, height, patch_centers, periodic_boundary
        )
        near, far = spacing * near_ratio, spacing * far_ratio
    else:
        raise ValueError(
            "initial_placement_distance_mode must be 'absolute' or 'relative'"
        )

    if not (math.isfinite(near) and math.isfinite(far) and 0 < near < far):
        raise ValueError("Placement thresholds must satisfy 0 < near < far")
    return near, far


def initial_placement_candidates(
    width: int,
    height: int,
    patch_cells: Collection[tuple[int, int]],
    mode: str,
    near_max_distance: float = 3.0,
    far_min_distance: float = 15.0,
    periodic_boundary: bool = False,
) -> list[tuple[int, int]]:
    """Return eligible cells, sorted by x then y.

    inside:       member of patch region
    near:         outside patch, with 0 < distance <= near_max_distance
    far:          outside patch, with distance >= far_min_distance

    Distance is measured to the *nearest cell of the patch region*, not to
    the patch center. When periodic_boundary=True, distance is toroidal.
    Near/far thresholds are provided by the caller (absolute or scaled).
    Near and far are non-overlapping if far_min > near_max.
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
                squared_euclidean_distance(
                    (x, y), (px, py), width, height, periodic_boundary
                )
                for px, py in patch_locations
            )
            if mode == "near" and 0 < distance2 <= near2:
                result.append((x, y))
            elif mode == "far" and distance2 >= far2:
                result.append((x, y))
    return result
