"""
piece.py — Tetromino definition, 7-bag randomiser, and CW/CCW rotation.

Piece.shape stores the live grid (color IDs, 0=empty).
Piece.rot_state tracks rotation for SRS kick-table lookups (0=spawn, 1=CW, 2=180, 3=CCW).
"""
import random
from constants import SHAPES, COLS

# ── 7-bag randomiser ──────────────────────────────────────────────────────────
# Each bag contains exactly one of every piece type, shuffled.
# This guarantees no piece type is skipped for more than 12 consecutive pieces,
# eliminating the brutal droughts that pure random spawning can produce.
_bag: list[str] = []

def _next_type() -> str:
    global _bag
    if not _bag:
        _bag = list(SHAPES.keys())
        random.shuffle(_bag)
    return _bag.pop()


class Piece:
    def __init__(self, shape_name: str | None = None):
        self.type      = shape_name if shape_name is not None else _next_type()
        self.shape     = [row[:] for row in SHAPES[self.type]]
        self.x         = COLS // 2 - len(self.shape[0]) // 2
        self.y         = 0
        self.rot_state = 0   # 0=spawn, 1=CW, 2=180, 3=CCW

    def rotated_cw(self) -> tuple[list[list[int]], int]:
        """Return (new_shape, new_rot_state) for a clockwise rotation."""
        shape = [list(row) for row in zip(*self.shape[::-1])]
        return shape, (self.rot_state + 1) % 4

    def rotated_ccw(self) -> tuple[list[list[int]], int]:
        """Return (new_shape, new_rot_state) for a counter-clockwise rotation."""
        shape = [list(row) for row in zip(*self.shape)][::-1]
        return shape, (self.rot_state - 1) % 4

    @property
    def color_id(self) -> int:
        for row in self.shape:
            for v in row:
                if v:
                    return v
        return 0
