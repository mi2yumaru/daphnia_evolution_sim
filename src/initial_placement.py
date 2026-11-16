"""STEP3: Candidate initial cells by Euclidean distance to the nearest patch cell.

This module has no random draws and does not alter the simulation's dynamics.
The environment grid uses integer (x, y) coordinates.
"""

from __future__ import annotations

import math
from typing import Collection, Mapping, Sequence

try:
    from .spatial import squared_euclidean_distance
except ImportError:
    from spatial import squared_euclidean_distance



def minimum_patch_center_distance(
    centers: Sequence[tuple[int, int]],
    width: int,
    height: int,
    periodic_boundary: bool,
) -> float:
    """Shortest Euclidean center separation, accounting for wraparound.

    The center-to-center distance is a layout scale, not the distance used
    to classify each founder (which is still to the nearest *patch cell*).
    """
    if width <= 0 or height <= 0:
        raise ValueError("Grid dimensions must be positive")
    center_list = [tuple(map(int, center)) for center in centers]
    if len(center_list) < 2:
        raise ValueError("Relative placement requires at least two patch centers")
    if any(not (0 <= x < width and 0 <= y < height) for x, y in center_list):
        raise ValueError("Patch center outside environment grid")
    if len(set(center_list)) != len(center_list):
        raise ValueError("Patch centers must be distinct for relative placement")

    minimum_squared = min(
        squared_euclidean_distance(
            center_list[i], center_list[j],
            width, height, periodic_boundary,
        )
        for i in range(len(center_list))
        for j in range(i + 1, len(center_list))
    )
    if minimum_squared <= 0:
        raise ValueError("Minimum patch center separation must be positive")
    return math.sqrt(minimum_squared)


def resolve_initial_placement_distances(
    organism_config: Mapping[str, object],
    centers: Sequence[tuple[int, int]],
    width: int,
    height: int,
    periodic_boundary: bool,
) -> tuple[float, float]:
    """Resolve near/far thresholds for fixed or relative placement.

    fixed (default): preserve the historical absolute thresholds.
    relative: near = L * near_fraction (default 0.2),
              far = L * far_fraction (default 0.4), where L is the
              shortest distance between distinct patch centers.
    """
    mode = str(organism_config.get("initial_placement_distance_mode", "fixed"))
    if mode == "fixed":
        near = float(organism_config.get(
            "initial_placement_near_max_distance", 3.0
        ))
        far = float(organism_config.get(
            "initial_placement_far_min_distance", 15.0
        ))
    elif mode == "relative":
        near_fraction = float(organism_config.get(
            "initial_placement_near_fraction", 0.2
        ))
        far_fraction = float(organism_config.get(
            "initial_placement_far_fraction", 0.4
        ))
        if not (
            math.isfinite(near_fraction)
            and math.isfinite(far_fraction)
            and 0 < near_fraction < far_fraction
        ):
            raise ValueError(
                "Relative placement fractions must be finite and "
                "0 < near_fraction < far_fraction"
            )
        spacing = minimum_patch_center_distance(
            centers, width, height, periodic_boundary
        )
        near = spacing * near_fraction
        far = spacing * far_fraction
    else:
        raise ValueError(
            "initial_placement_distance_mode must be 'fixed' or 'relative'"
        )

    if not (
        math.isfinite(near) and math.isfinite(far)
        and 0 < near < far
    ):
        raise ValueError("Placement distances must satisfy 0 < near < far")
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
    Thresholds are passed by the caller, using either fixed distances or
    distances resolved from the minimum patch-center separation.
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
