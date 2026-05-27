"""
Procedural Tron-style board background.
Pre-generates a Surface once; call get() anywhere after pygame.init().
"""
import pygame
from constants import BOARD_WIDTH, BOARD_HEIGHT, CELL_SIZE

_surf: pygame.Surface | None = None


def _build() -> pygame.Surface:
    s = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT))
    s.fill((4, 4, 18))   # very dark base

    # Major grid lines (every CELL_SIZE) — dark cyan
    grid_col   = (0, 28, 52)
    # Accent lines (every 3 cells) — slightly brighter
    accent_col = (0, 55, 95)
    # Bright nodes at accent intersections
    node_col   = (0, 95, 160)

    for x in range(0, BOARD_WIDTH + 1, CELL_SIZE):
        bright = (x % (CELL_SIZE * 3) == 0)
        pygame.draw.line(s, accent_col if bright else grid_col,
                         (x, 0), (x, BOARD_HEIGHT))
    for y in range(0, BOARD_HEIGHT + 1, CELL_SIZE):
        bright = (y % (CELL_SIZE * 3) == 0)
        pygame.draw.line(s, accent_col if bright else grid_col,
                         (0, y), (BOARD_WIDTH, y))

    # Small glowing nodes at accent-line intersections
    for x in range(0, BOARD_WIDTH + 1, CELL_SIZE * 3):
        for y in range(0, BOARD_HEIGHT + 1, CELL_SIZE * 3):
            pygame.draw.circle(s, node_col, (x, y), 2)

    # Subtle vertical gradient: slightly brighter at bottom (Tron floor perspective)
    grad = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT), pygame.SRCALPHA)
    for y in range(BOARD_HEIGHT):
        # Alpha darkens toward top (far), lightens toward bottom (near)
        alpha = int(30 * (1.0 - y / BOARD_HEIGHT))
        pygame.draw.line(grad, (0, 0, 0, alpha), (0, y), (BOARD_WIDTH, y))
    s.blit(grad, (0, 0))

    return s


def get() -> pygame.Surface:
    global _surf
    if _surf is None:
        _surf = _build()
    return _surf
