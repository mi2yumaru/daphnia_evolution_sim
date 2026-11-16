"""Coordinate and distance helpers shared by periodic and finite grids.

Coordinates are integer cell indices. When periodic=True, opposite edges
are adjacent, and distances use the shortest wrapped displacement.
"""


def wrap_coordinate(value: int, size: int, periodic: bool) -> int:
    """Wrap into [0, size) only for periodic boundaries."""
    if size <= 0:
        raise ValueError("Grid dimension must be positive")
    return int(value) % size if periodic else int(value)


def axis_distance(a: int, b: int, size: int, periodic: bool) -> int:
    """Minimum cell distance along a grid axis."""
    delta = abs(int(a) - int(b))
    if not periodic:
        return delta
    if size <= 0:
        raise ValueError("Grid dimension must be positive")
    delta %= size
    return min(delta, size - delta)


def manhattan_distance(
    a: tuple[int, int],
    b: tuple[int, int],
    width: int,
    height: int,
    periodic: bool,
) -> int:
    """Four-connected shortest-distance heuristic (L1)."""
    return (
        axis_distance(a[0], b[0], width, periodic)
        + axis_distance(a[1], b[1], height, periodic)
    )


def squared_euclidean_distance(
    a: tuple[int, int],
    b: tuple[int, int],
    width: int,
    height: int,
    periodic: bool,
) -> int:
    """Squared Euclidean distance with shortest cyclic axis differences."""
    dx = axis_distance(a[0], b[0], width, periodic)
    dy = axis_distance(a[1], b[1], height, periodic)
    return dx * dx + dy * dy
