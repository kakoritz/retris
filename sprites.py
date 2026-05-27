"""
Procedurally generated NES-style block sprites — no image files needed.
All surfaces are cached on first use so they're only built once.
"""
import pygame
from constants import COLORS, CELL_SIZE

_blocks: dict[int, pygame.Surface] = {}
_ghosts: dict[int, pygame.Surface] = {}


def _build_block(color: tuple, size: int) -> pygame.Surface:
    surf = pygame.Surface((size, size))

    hi  = tuple(min(c + 90, 255) for c in color)   # bright highlight
    hi2 = tuple(min(c + 40, 255) for c in color)   # mid highlight
    sh  = tuple(max(c - 80, 0)   for c in color)   # shadow
    border = (8, 8, 20)

    # main fill
    surf.fill(color)

    # 1-px dark outer border
    pygame.draw.rect(surf, border, (0, 0, size, size), 1)

    # inner bevel  ─ top + left = highlight, bottom + right = shadow
    pygame.draw.line(surf, hi,  (1, 1),        (size - 2, 1))
    pygame.draw.line(surf, hi,  (1, 1),        (1, size - 2))
    pygame.draw.line(surf, sh,  (2, size - 2), (size - 2, size - 2))
    pygame.draw.line(surf, sh,  (size - 2, 2), (size - 2, size - 2))

    # small highlight square in top-left corner (NES pixel detail)
    sq = max(size // 7, 2)
    pygame.draw.rect(surf, hi,  (3, 3, sq + 2, sq + 2))
    pygame.draw.rect(surf, hi2, (3, 3, sq,     sq))

    return surf


def _build_ghost(color: tuple, size: int, opacity_pct: int) -> pygame.Surface:
    """Build a ghost (shadow) tile surface at the given opacity (0–100).

    0  % → completely invisible.
    25 % → default: faint fill with a visible outline — readable but unobtrusive.
    100% → near-solid: looks almost identical to a placed block.

    Alpha values are scaled linearly so both endpoints feel correct:
      fill    0 → 210  (body colour)
      outline 0 → 255  (edge colour)
    """
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    t = opacity_pct / 100.0
    fill_a    = int(t * 210)
    outline_a = int(t * 255)
    pygame.draw.rect(surf, (*color, fill_a),    (0, 0, size, size))
    pygame.draw.rect(surf, (*color, outline_a), (0, 0, size, size), 1)
    return surf


def _apply_palette(color: tuple, phase: int) -> tuple:
    """Darken a colour by 10 % per phase step (phase 0 = unchanged)."""
    if phase == 0:
        return color
    factor = max(0.0, 1.0 - phase * 0.10)
    return tuple(max(0, int(c * factor)) for c in color)


def get_block(color_id: int, size: int = CELL_SIZE,
              palette_phase: int = 0) -> pygame.Surface:
    key = (color_id, size, palette_phase)
    if key not in _blocks:
        _blocks[key] = _build_block(_apply_palette(COLORS[color_id], palette_phase), size)
    return _blocks[key]


def get_ghost(color_id: int, size: int = CELL_SIZE,
              opacity_pct: int = 25, palette_phase: int = 0) -> pygame.Surface:
    key = (color_id, size, opacity_pct, palette_phase)
    if key not in _ghosts:
        _ghosts[key] = _build_ghost(
            _apply_palette(COLORS[color_id], palette_phase), size, opacity_pct)
    return _ghosts[key]
