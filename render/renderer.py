# renderer.py — all draw_* functions, extracted from main.py
import colorsys
import math
import random
import pygame

import config
from constants import (
    COLS, ROWS, CELL_SIZE,
    BOARD_WIDTH, BOARD_HEIGHT, SIDEBAR_WIDTH, SCREEN_WIDTH, SCREEN_HEIGHT,
    BG_COLOR, BORDER_COLOR, WHITE, YELLOW, COLORS, SHAPES, LEVEL_THEMES,
)
from board import Board
from piece import Piece
from sprites import get_block, get_ghost
from game_constants import (
    FLASH_COLOR_NORM, FLASH_COLOR_QUAD,
    WOW_POPUP_DURATION, POPUP_DURATION,
    POPUP_STYLES,
)

# ── rendering-only constants ──────────────────────────────────────────────────

# Pixel-font glyphs for the PAUSE overlay (5×5 grids)
_PAUSE_GLYPHS = {
    'P': [[1,1,1,1,0],
          [1,0,0,0,1],
          [1,1,1,1,0],
          [1,0,0,0,0],
          [1,0,0,0,0]],
    'A': [[0,1,1,0,0],
          [1,0,0,1,0],
          [1,1,1,1,0],
          [1,0,0,1,0],
          [1,0,0,1,0]],
    'U': [[1,0,0,0,1],
          [1,0,0,0,1],
          [1,0,0,0,1],
          [1,0,0,0,1],
          [0,1,1,1,0]],
    'S': [[0,1,1,1,0],
          [1,0,0,0,0],
          [0,1,1,0,0],
          [0,0,0,1,0],
          [1,1,1,0,0]],
    'E': [[1,1,1,1,0],
          [1,0,0,0,0],
          [1,1,1,0,0],
          [1,0,0,0,0],
          [1,1,1,1,0]],
}
_PAUSE_COLORS = [
    (0, 240, 240),
    (240, 240, 0),
    (160, 0, 240),
    (0, 240, 0),
    (240, 0, 0),
]
_PAUSE_BLOCK = 12   # px block size for PAUSE text
_PAUSE_CELL  = 14   # block + 2 px gap

_TIER_DESC = {
    1:  "whole-note bass pulse",
    2:  "quarter-note walking bass",
    3:  "8th-note Am groove",
    4:  "chord movement bass  (Am / F / G)",
    5:  "bass + Am arpeggio",
    6:  "bass + full chord arpeggio",
    7:  "bass + arp + melody layer 1",
    8:  "bass + arp + melody layers 1 & 2",
    9:  "syncopated bass + full arrangement",
    10: "full arrangement + sparkle highs",
}

_TITLE_COLORS = [
    (160,   0, 240),
    (  0, 240, 240),
    (240, 240,   0),
    (  0, 240,   0),
    (  0,  60, 240),
    (240,   0,   0),
]

# ── font cache ────────────────────────────────────────────────────────────────

_font_cache: dict = {}

def _font(size: int, bold: bool = True) -> pygame.font.Font:
    key = (size, bold)
    if key not in _font_cache:
        _font_cache[key] = pygame.font.SysFont("monospace", size, bold=bold)
    return _font_cache[key]


# ── UI button hitbox rects (logical 460×600 coords) ──────────────────────────
# Imported by input_handler.py for tap/click detection.

MENU_ABOUT_RECT    = pygame.Rect( 12,  12, 40, 40)
MENU_SETTINGS_RECT = pygame.Rect(408,  12, 40, 40)
MENU_START_RECT    = pygame.Rect( 60, 178, 340, 44)
MENU_LB_RECT       = pygame.Rect( 60, 226, 340, 44)
INGAME_GEAR_RECT   = pygame.Rect(432,   4, 26, 26)
PAUSE_CONTINUE_RECT = pygame.Rect(110, 308, 240, 50)
PAUSE_QUIT_RECT     = pygame.Rect(110, 372, 240, 50)
BACK_RECT          = pygame.Rect( 10, 556, 120, 34)
ABOUT_GITHUB_RECT  = pygame.Rect( 60, 440, 340, 30)


# ── shared UI helpers ─────────────────────────────────────────────────────────

def _draw_shadow_text(surf: pygame.Surface, text: str, font_size: int,
                      x: int, y: int, color=None, bold: bool = True,
                      center_x: bool = False) -> None:
    if color is None:
        color = WHITE
    f  = _font(font_size, bold=bold)
    sh = f.render(text, True, (15, 15, 15))
    t  = f.render(text, True, color)
    bx = x - t.get_width() // 2 if center_x else x
    surf.blit(sh, (bx + 2, y + 2))
    surf.blit(t,  (bx, y))


def _draw_btn(surf: pygame.Surface, text: str, rect: pygame.Rect,
              color: tuple) -> None:
    bg = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    bg.fill((0, 0, 0, 110))
    surf.blit(bg, (rect.x, rect.y))
    pygame.draw.rect(surf, color, rect, 2)
    hi = tuple(min(255, c + 70) for c in color)
    pygame.draw.line(surf, hi, (rect.x + 3, rect.y + 2),
                     (rect.right - 4, rect.y + 2))
    f  = _font(20)
    sh = f.render(text, True, (15, 15, 15))
    t  = f.render(text, True, color)
    tx = rect.centerx - t.get_width()  // 2
    ty = rect.centery - t.get_height() // 2
    surf.blit(sh, (tx + 2, ty + 2))
    surf.blit(t,  (tx, ty))


def _draw_icon_circle(surf: pygame.Surface, letter: str,
                      rect: pygame.Rect, color: tuple) -> None:
    bg = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    bg.fill((0, 0, 0, 110))
    surf.blit(bg, (rect.x, rect.y))
    r = min(rect.w, rect.h) // 2 - 1
    pygame.draw.circle(surf, color, rect.center, r, 2)
    f = _font(18)
    t = f.render(letter, True, color)
    surf.blit(t, (rect.centerx - t.get_width()  // 2,
                  rect.centery - t.get_height() // 2))


def _draw_back_btn(surf: pygame.Surface) -> None:
    _draw_btn(surf, "< BACK", BACK_RECT, BORDER_COLOR)


# ── RETRIS pixel-block logo ───────────────────────────────────────────────────

# 5-col × 6-row bitmaps; 1 = filled block
_LOGO_GLYPHS = {
    'R': [[1,1,1,1,0],[1,0,0,0,1],[1,1,1,1,0],[1,0,1,0,0],[1,0,0,1,0],[1,0,0,0,1]],
    'E': [[1,1,1,1,1],[1,0,0,0,0],[1,1,1,1,0],[1,0,0,0,0],[1,0,0,0,0],[1,1,1,1,1]],
    'T': [[1,1,1,1,1],[0,0,1,0,0],[0,0,1,0,0],[0,0,1,0,0],[0,0,1,0,0],[0,0,1,0,0]],
    'I': [[1,1,1,1,1],[0,0,1,0,0],[0,0,1,0,0],[0,0,1,0,0],[0,0,1,0,0],[1,1,1,1,1]],
    'S': [[0,1,1,1,1],[1,0,0,0,0],[0,1,1,1,0],[0,0,0,0,1],[0,0,0,0,1],[1,1,1,1,0]],
}
# color_ids per letter: R=purple(3)  E=cyan(1)  T=yellow(2)  R=green(4)  I=blue(6)  S=red(5)
_LOGO_COLORS = [3, 1, 2, 4, 6, 5]
_LOGO_CELL   = 9   # px per block in the logo


def draw_retris_logo(surf: pygame.Surface, top_y: int = 8) -> None:
    letters = list("RETRIS")
    letter_w = 5 * _LOGO_CELL
    gap      = 2 * _LOGO_CELL
    total_w  = len(letters) * letter_w + (len(letters) - 1) * gap
    x0       = (SCREEN_WIDTH - total_w) // 2

    for li, ch in enumerate(letters):
        glyph    = _LOGO_GLYPHS[ch]
        color_id = _LOGO_COLORS[li]
        lx       = x0 + li * (letter_w + gap)
        for gy, row in enumerate(glyph):
            for gx, val in enumerate(row):
                if val:
                    surf.blit(get_block(color_id, _LOGO_CELL),
                              (lx + gx * _LOGO_CELL, top_y + gy * _LOGO_CELL))


# ── animated tetromino background ─────────────────────────────────────────────

def _draw_animated_bg(surf: pygame.Surface) -> None:
    """Faint tiled tetromino shapes that cycle theme color every 15 s."""
    t      = pygame.time.get_ticks()
    idx    = (t // 15000) % len(LEVEL_THEMES)
    nxt    = (idx + 1)   % len(LEVEL_THEMES)
    frac   = (t % 15000) / 15000.0
    gc     = LEVEL_THEMES[idx][1]
    gc_n   = LEVEL_THEMES[nxt][1]
    tint   = tuple(int(gc[i] * (1 - frac) + gc_n[i] * frac) for i in range(3))

    cell   = 7
    ov     = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    rng    = random.Random(idx)

    piece_list = list(SHAPES.items())
    for pt, shape in piece_list:
        for _ in range(4):
            px = rng.randint(-1, SCREEN_WIDTH  // cell)
            py = rng.randint(-1, SCREEN_HEIGHT // cell)
            for ry, row in enumerate(shape):
                for rx, v in enumerate(row):
                    if v:
                        pygame.draw.rect(ov, (*tint, 28),
                            ((px + rx) * cell, (py + ry) * cell,
                             cell - 1, cell - 1))
    surf.blit(ov, (0, 0))


# ── board / piece drawing ─────────────────────────────────────────────────────

def draw_board(surf: pygame.Surface, board: Board,
               flash_rows: set | None = None,
               flash_on: bool = False,
               flash_quad: bool = False,
               wow_on: bool = False,
               palette_phase: int = 0) -> None:
    theme      = LEVEL_THEMES[palette_phase % len(LEVEL_THEMES)]
    board_cell = theme[0]
    grid_line  = theme[1]
    surf.fill(grid_line)   # 1-px grid gaps come from this fill + CELL_SIZE-1 cells

    if wow_on and flash_on:
        h = (pygame.time.get_ticks() / 90) % 1.0   # ~11 Hz hue cycle
        r, g, b = colorsys.hsv_to_rgb(h, 1.0, 1.0)
        fc = (int(r * 255), int(g * 255), int(b * 255))
    elif flash_quad:
        fc = FLASH_COLOR_QUAD
    else:
        fc = FLASH_COLOR_NORM

    for gy, row in enumerate(board.grid):
        for gx, val in enumerate(row):
            px, py = gx * CELL_SIZE, gy * CELL_SIZE
            if wow_on and flash_on:
                pygame.draw.rect(surf, fc, (px, py, CELL_SIZE - 1, CELL_SIZE - 1))
            elif flash_rows and gy in flash_rows and flash_on:
                pygame.draw.rect(surf, fc, (px, py, CELL_SIZE - 1, CELL_SIZE - 1))
            elif val:
                surf.blit(get_block(val, palette_phase=palette_phase), (px, py))
            else:
                pygame.draw.rect(surf, board_cell,
                                 (px, py, CELL_SIZE - 1, CELL_SIZE - 1))


def _draw_danger_line(surf: pygame.Surface) -> None:
    y = 10 * CELL_SIZE
    t = pygame.time.get_ticks()
    pulse = 0.5 + 0.5 * math.sin(t * 0.016)
    r     = 255
    gb    = int(20 + 30 * pulse)
    col   = (r, gb, gb)
    pygame.draw.line(surf, col, (0, y),     (BOARD_WIDTH - 1, y),     2)
    glow = (int(r * 0.28), int(gb * 0.28), int(gb * 0.28))
    pygame.draw.line(surf, glow, (0, y - 1), (BOARD_WIDTH - 1, y - 1), 1)
    pygame.draw.line(surf, glow, (0, y + 2), (BOARD_WIDTH - 1, y + 2), 1)


def draw_piece(surf: pygame.Surface, piece: Piece,
               palette_phase: int = 0) -> None:
    for row_i, row in enumerate(piece.shape):
        for col_i, val in enumerate(row):
            if val:
                surf.blit(get_block(val, palette_phase=palette_phase),
                          ((piece.x + col_i) * CELL_SIZE,
                           (piece.y + row_i) * CELL_SIZE))


def draw_ghost(surf: pygame.Surface, board: Board, piece: Piece,
               opacity_pct: int = 25, palette_phase: int = 0) -> None:
    if opacity_pct == 0:
        return
    gy = board.ghost_y(piece)
    if gy == piece.y:
        return
    for row_i, row in enumerate(piece.shape):
        for col_i, val in enumerate(row):
            if val:
                surf.blit(get_ghost(val, opacity_pct=opacity_pct,
                                    palette_phase=palette_phase),
                          ((piece.x + col_i) * CELL_SIZE,
                           (gy + row_i) * CELL_SIZE))


# ── odometer score display ────────────────────────────────────────────────────

def draw_odometer(surf: pygame.Surface, digits: list, anim_from: list,
                  anim_offs: list, x: int, y: int, faded: bool = False) -> None:
    """Draw an 8-digit pinball-style odometer at (x, y).

    Each digit lives in a small dark box and scrolls upward when the value
    changes.  anim_offs[i] is 1.0 the frame a digit changes and decays to
    0.0 over ~200 ms — the caller controls the decay rate.
    """
    dw, dh, gap = 16, 22, 1
    base_col = (255, 220, 50) if not faded else (100, 78, 18)
    dim_col  = (16, 16, 36)
    bdr_col  = (52, 52, 88) if not faded else (28, 28, 50)
    font     = _font(16)

    for i in range(8):
        dx       = x + i * (dw + gap)
        box_surf = pygame.Surface((dw, dh))
        box_surf.fill(dim_col)
        pygame.draw.rect(box_surf, bdr_col, (0, 0, dw, dh), 1)

        off   = anim_offs[i] if anim_offs else 0.0
        new_d = str(digits[i])

        if off > 0.0:
            scroll = int(off * dh)
            old_t  = font.render(str(anim_from[i]), True, base_col)
            new_t  = font.render(new_d,             True, base_col)
            cy_old = dh // 2 - old_t.get_height() // 2 - scroll
            cy_new = dh // 2 - new_t.get_height() // 2 + dh - scroll
            box_surf.blit(old_t, (dw // 2 - old_t.get_width() // 2, cy_old))
            box_surf.blit(new_t, (dw // 2 - new_t.get_width() // 2, cy_new))
        else:
            t = font.render(new_d, True, base_col)
            box_surf.blit(t, (dw // 2 - t.get_width() // 2,
                               dh // 2 - t.get_height() // 2))

        surf.blit(box_surf, (dx, y))


# ── level-up board overlay ────────────────────────────────────────────────────

def draw_level_up_overlay(surf: pygame.Surface, level_num: int,
                          timer: int, max_timer: int,
                          level_theme_idx: int) -> None:
    """Draw a centred 'LEVEL N' banner on the board surface."""
    if timer <= 0:
        return

    progress = timer / max_timer  # 1.0 = just appeared, 0.0 = about to vanish

    if progress > 0.85:                              # fade in
        alpha = 1.0 - (progress - 0.85) / 0.15
    elif progress > 0.18:                            # hold
        alpha = 1.0
    else:                                            # fade out
        alpha = progress / 0.18
    alpha = max(0.0, min(1.0, alpha))

    scale = (0.5 + 0.5 * (1.0 - (progress - 0.85) / 0.15)
             if progress > 0.85 else 1.0)

    theme  = LEVEL_THEMES[level_theme_idx % len(LEVEL_THEMES)]
    gc     = theme[1]   # grid-line colour — more saturated than board_cell
    bright = tuple(min(255, int(c * 3.8 + 50)) for c in gc)

    label   = f"LEVEL  {level_num}"
    fsize   = max(10, int(38 * scale))
    f       = _font(fsize)
    tw, th  = f.size(label)
    cx      = BOARD_WIDTH // 2
    cy      = BOARD_HEIGHT // 2 - 28
    pad_x, pad_y = 18, 10
    bw, bh  = tw + pad_x * 2, th + pad_y * 2

    bg = pygame.Surface((bw, bh), pygame.SRCALPHA)
    bg.fill((0, 0, 0, int(210 * alpha)))
    surf.blit(bg, (cx - bw // 2, cy - bh // 2))

    pulse = 0.6 + 0.4 * math.sin(pygame.time.get_ticks() * 0.014)
    bdr_a = int(255 * alpha * pulse)
    bdr   = pygame.Surface((bw + 6, bh + 6), pygame.SRCALPHA)
    pygame.draw.rect(bdr, (*bright, bdr_a), (0, 0, bw + 6, bh + 6), 3,
                     border_radius=6)
    surf.blit(bdr, (cx - bw // 2 - 3, cy - bh // 2 - 3))

    sh_col = tuple(max(0, int(c * 0.3 * alpha)) for c in bright)
    surf.blit(f.render(label, True, sh_col), (cx - tw // 2 + 2, cy - th // 2 + 2))

    text_col = tuple(int(c * alpha) for c in bright)
    surf.blit(f.render(label, True, text_col), (cx - tw // 2, cy - th // 2))


# ── demo overlay ──────────────────────────────────────────────────────────────

def draw_demo_overlay(surf: pygame.Surface, label: str) -> None:
    """Top banner shown during demo mode."""
    banner = pygame.Surface((BOARD_WIDTH, 38), pygame.SRCALPHA)
    banner.fill((0, 0, 0, 185))
    surf.blit(banner, (0, 3))

    t1 = _font(13).render("DEMO", True, (255, 70, 70))
    surf.blit(t1, (8, 11))

    if label:
        t2 = _font(12, bold=False).render(label, True, (220, 220, 220))
        surf.blit(t2, (BOARD_WIDTH // 2 - t2.get_width() // 2, 14))

    t3 = _font(10, bold=False).render("SPACE / ESC  to exit", True, (130, 130, 130))
    surf.blit(t3, (BOARD_WIDTH - t3.get_width() - 6, 21))


# ── popup ─────────────────────────────────────────────────────────────────────

def draw_popup(surf: pygame.Surface, count: int, timer: int) -> None:
    if timer <= 0 or count not in POPUP_STYLES:
        return
    text_str, base_color, base_size = POPUP_STYLES[count]

    is_wow   = (count in (0, 13, 15))
    duration = WOW_POPUP_DURATION if is_wow else POPUP_DURATION
    elapsed  = duration - timer

    if is_wow:
        y = BOARD_HEIGHT // 2 - 18 - int((elapsed / duration) * 40)
    else:
        start_y = int(BOARD_HEIGHT * 0.62)
        y = start_y - int((elapsed / POPUP_DURATION) * 60)

    alpha = 1.0 if timer > 600 else timer / 600
    size  = base_size + (5 if elapsed < 200 else 0)

    if base_color is None:
        speed = 200 if is_wow else 450
        h = (pygame.time.get_ticks() / speed) % 1.0
        r, g, b = colorsys.hsv_to_rgb(h, 1.0, 1.0)
        vivid = (int(r * 255), int(g * 255), int(b * 255))
    else:
        vivid = base_color

    color = tuple(int(c * alpha) for c in vivid)
    f     = _font(size)
    tw, th = f.size(text_str)

    pad_x = 14 if is_wow else 10
    pad_y = 7  if is_wow else 4
    bw, bh = tw + pad_x * 2, th + pad_y * 2
    bx = BOARD_WIDTH // 2 - bw // 2
    bg_alpha = 0.30 if is_wow else 0.22
    bg = tuple(int(c * bg_alpha * alpha) for c in vivid)
    pygame.draw.rect(surf, bg, (bx, y - pad_y, bw, bh), border_radius=6)
    shadow = tuple(int(c * 0.25 * alpha) for c in vivid)
    t = f.render(text_str, True, shadow)
    surf.blit(t, (BOARD_WIDTH // 2 - tw // 2 + 2, y + 2))
    t = f.render(text_str, True, color)
    surf.blit(t, (BOARD_WIDTH // 2 - tw // 2, y))


# ── touch controls overlay ───────────────────────────────────────────────────

def draw_touch_controls(surf: pygame.Surface) -> None:
    """Overlay semi-transparent virtual D-pad buttons at the screen bottom."""
    btn_h = 65
    btn_y = SCREEN_HEIGHT - btn_h
    btn_w = SCREEN_WIDTH // 6
    labels = ['◄', '↺', '▼', '▲', '↻', '□']

    bg = pygame.Surface((SCREEN_WIDTH, btn_h), pygame.SRCALPHA)
    bg.fill((0, 0, 0, 150))
    surf.blit(bg, (0, btn_y))

    for i, label in enumerate(labels):
        w = btn_w if i < 5 else SCREEN_WIDTH - btn_w * 5
        x = btn_w * i
        pygame.draw.rect(surf, (70, 70, 90), (x, btn_y, w, btn_h), 1)
        t = _font(20).render(label, True, (190, 190, 210))
        surf.blit(t, (x + (w - t.get_width()) // 2,
                      btn_y + (btn_h - t.get_height()) // 2))


# ── sidebar ───────────────────────────────────────────────────────────────────

def draw_sidebar(surf: pygame.Surface, score: int, lines: int,
                 level: int, piece_queue: list, best: int,
                 hold_piece=None, hold_used: bool = False,
                 speed_tier: int = 1, lines_to_next_level: int = 10,
                 palette_phase: int = 0,
                 popup_count: int = 0, popup_timer: int = 0,
                 next_flash_timer: int = 0, hold_has_piece: bool = False,
                 combo: int = 0, level_up_flash_timer: int = 0,
                 score_digits: list | None = None,
                 score_anim_from: list | None = None,
                 score_anim_offs: list | None = None,
                 cascading: bool = False,
                 cascade_freefall: bool = False) -> None:
    sx = BOARD_WIDTH + 12

    def lbl(text, y): surf.blit(_font(13).render(text, True, BORDER_COLOR), (sx, y))

    # ── score odometer ──────────────────────────────────────────────────────
    lbl("SCORE", 13)
    if score_digits is not None:
        draw_odometer(surf, score_digits,
                      score_anim_from or [0] * 8,
                      score_anim_offs or [0.0] * 8,
                      sx, 28)
    else:
        surf.blit(_font(19).render(str(score).zfill(7), True, YELLOW), (sx, 28))

    # ── best odometer (static, faded) ───────────────────────────────────────
    lbl("BEST", 55)
    best_digits = [int(d) for d in str(min(best, 99999999)).zfill(8)]
    draw_odometer(surf, best_digits, [0] * 8, [0.0] * 8, sx, 70, faded=True)

    # ── level + lines ───────────────────────────────────────────────────────
    surf.blit(_font(12).render("LVL",   True, BORDER_COLOR), (sx,      98))
    surf.blit(_font(12).render("LINES", True, BORDER_COLOR), (sx + 65, 98))
    level_col = WHITE if level_up_flash_timer > 0 else YELLOW
    surf.blit(_font(17).render(str(level), True, level_col), (sx,      112))
    surf.blit(_font(17).render(str(lines), True, YELLOW),    (sx + 65, 112))

    # ── combo ───────────────────────────────────────────────────────────────
    combo_col = (80, 220, 255) if combo >= 2 else tuple(max(c - 110, 0) for c in BORDER_COLOR)
    combo_str = f"COMBO  ×{combo}" if combo >= 2 else "COMBO"
    surf.blit(_font(11).render(combo_str, True, combo_col), (sx, 132))

    # ── speed tier ──────────────────────────────────────────────────────────
    surf.blit(_font(12).render("SPEED", True, BORDER_COLOR), (sx, 155))
    surf.blit(_font(17).render(f"T{speed_tier}", True, YELLOW), (sx, 169))

    # ── next level countdown ─────────────────────────────────────────────────
    surf.blit(_font(12).render("NEXT  LEVEL  IN", True, BORDER_COLOR), (sx, 193))
    nl = lines_to_next_level
    nl_col = ((100, 255, 100) if nl > 5 else
              (255, 200, 50)  if nl > 2 else
              (255, 80,  80))
    surf.blit(_font(14).render(f"{nl} line{'s' if nl != 1 else ''}", True, nl_col),
              (sx, 207))

    box_w  = SIDEBAR_WIDTH - 16
    box_x  = sx - 4
    mini   = CELL_SIZE - 8
    tiny   = 10

    NEXT_Y     = 228
    NEXT_BOX_Y = NEXT_Y + 20
    P1_H       = 72
    MINI_H     = 78
    NEXT_BOX_H = P1_H + 2 + MINI_H

    surf.blit(_font(13).render("NEXT", True, BORDER_COLOR), (sx, NEXT_Y))

    if next_flash_timer > 0:
        fa = min(1.0, next_flash_timer / 120)
        fc = tuple(int(c * fa) for c in (255, 255, 255))
        pygame.draw.rect(surf, fc,
                         (box_x - 1, NEXT_BOX_Y - 1, box_w + 2, NEXT_BOX_H + 2), 2,
                         border_radius=3)
    pygame.draw.rect(surf, BORDER_COLOR, (box_x, NEXT_BOX_Y, box_w, NEXT_BOX_H), 1)

    p1 = piece_queue[0] if piece_queue else None
    if p1 is not None:
        s1 = p1.shape
        pc = max(len(r) for r in s1);  pr = len(s1)
        ox = box_x + (box_w - pc * (mini + 1)) // 2
        oy = NEXT_BOX_Y + (P1_H - pr * (mini + 1)) // 2
        for ri, row in enumerate(s1):
            for ci, v in enumerate(row):
                if v:
                    surf.blit(get_block(v, mini, palette_phase=palette_phase),
                              (ox + ci * (mini + 1), oy + ri * (mini + 1)))

    div_y = NEXT_BOX_Y + P1_H + 1
    pygame.draw.line(surf, tuple(max(c - 60, 0) for c in BORDER_COLOR),
                     (box_x + 4, div_y), (box_x + box_w - 4, div_y))

    half_w   = box_w // 2
    grid_y   = div_y + 3
    slot_h   = (MINI_H - 4) // 2
    for idx in range(4):
        p = piece_queue[idx + 1] if (idx + 1) < len(piece_queue) else None
        col_i = idx % 2;  row_i = idx // 2
        slot_x = box_x + col_i * half_w
        slot_y = grid_y + row_i * slot_h
        if col_i == 0:
            pygame.draw.line(surf, tuple(max(c - 60, 0) for c in BORDER_COLOR),
                             (box_x + half_w, grid_y + 2),
                             (box_x + half_w, grid_y + MINI_H - 5))
        if p is not None:
            sp = p.shape
            pc2 = max(len(r) for r in sp);  pr2 = len(sp)
            ox2 = slot_x + (half_w - pc2 * (tiny + 1)) // 2
            oy2 = slot_y + (slot_h - pr2 * (tiny + 1)) // 2
            for ri, row in enumerate(sp):
                for ci, v in enumerate(row):
                    if v:
                        surf.blit(get_block(v, tiny, palette_phase=palette_phase),
                                  (ox2 + ci * (tiny + 1), oy2 + ri * (tiny + 1)))

    HOLD_Y     = NEXT_BOX_Y + NEXT_BOX_H + 12
    HOLD_BOX_Y = HOLD_Y + 20
    HOLD_BOX_H = 66

    surf.blit(_font(13).render("HOLD", True, BORDER_COLOR), (sx, HOLD_Y))
    if hold_has_piece:
        t_ms = pygame.time.get_ticks()
        glow = 0.45 + 0.45 * math.sin(t_ms / 285.0)
        gc   = tuple(int(c * glow) for c in (80, 220, 255))
        pygame.draw.rect(surf, gc,
                         (box_x - 1, HOLD_BOX_Y - 1, box_w + 2, HOLD_BOX_H + 2), 2,
                         border_radius=3)
    border_col = tuple(max(c - 80, 0) for c in BORDER_COLOR) if hold_used else BORDER_COLOR
    pygame.draw.rect(surf, border_col, (box_x, HOLD_BOX_Y, box_w, HOLD_BOX_H), 1)
    if hold_piece is not None:
        sh = hold_piece.shape
        pc = max(len(r) for r in sh);  pr = len(sh)
        ox = box_x + (box_w - pc * (mini + 1)) // 2
        oy = HOLD_BOX_Y + (HOLD_BOX_H - pr * (mini + 1)) // 2
        for ri, row in enumerate(sh):
            for ci, v in enumerate(row):
                if v:
                    blk = get_block(v, mini, palette_phase=palette_phase)
                    if hold_used:
                        blk = blk.copy(); blk.set_alpha(90)
                    surf.blit(blk, (ox + ci * (mini + 1), oy + ri * (mini + 1)))

    ctrl_y = HOLD_BOX_Y + HOLD_BOX_H + 10
    for i, h in enumerate(["<> move  ^ rot  Z ccw",
                            "v drop  SPC hard  C hold"]):
        surf.blit(_font(10).render(h, True, BORDER_COLOR), (sx, ctrl_y + i * 14))

    # ── cascade indicator ────────────────────────────────────────────────────
    if cascading:
        t_ms = pygame.time.get_ticks()
        if cascade_freefall:
            hue   = (t_ms / 1200.0) % 1.0
            r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
            cas_col = (int(r * 255), int(g * 255), int(b * 255))
        else:
            cas_col = (60, 160, 160)
        cas_y = ctrl_y + 32
        surf.blit(_font(10).render("Cascading...", True, cas_col), (sx, cas_y))

    draw_popup(surf, popup_count, popup_timer)


# ── game-over overlay ─────────────────────────────────────────────────────────

def draw_game_over_overlay(surf: pygame.Surface, score: int,
                           stat_pieces: int = 0, stat_tetrises: int = 0,
                           stat_tspins: int = 0, stat_combo: int = 0,
                           stat_time: float = 0.0) -> None:
    ov = pygame.Surface((BOARD_WIDTH, 220), pygame.SRCALPHA)
    ov.fill((0, 0, 0, 210))
    surf.blit(ov, (0, BOARD_HEIGHT // 2 - 50))
    cx = BOARD_WIDTH // 2

    t = _font(26).render("GAME OVER", True, (255, 60, 60))
    surf.blit(t, (cx - t.get_width() // 2, BOARD_HEIGHT // 2 - 44))

    t = _font(17).render(f"SCORE  {str(score).zfill(7)}", True, YELLOW)
    surf.blit(t, (cx - t.get_width() // 2, BOARD_HEIGHT // 2 - 8))

    mins, secs = divmod(int(stat_time), 60)
    time_str   = f"{mins}:{secs:02d}"
    stats = [
        ("TIME",     time_str),
        ("PIECES",   str(stat_pieces)),
        ("RETRIS!", str(stat_tetrises)),
        ("T-SPINS",  str(stat_tspins)),
        ("BEST COMBO", f"×{stat_combo}"),
    ]
    sy = BOARD_HEIGHT // 2 + 18
    for label, val in stats:
        tl = _font(11, bold=False).render(label, True, BORDER_COLOR)
        tv = _font(12).render(val, True, (200, 220, 255))
        surf.blit(tl, (cx - 70, sy))
        surf.blit(tv, (cx + 20, sy))
        sy += 16

    for i, hint in enumerate(["SPACE / ESC = menu",
                               "L = leaderboard"]):
        t = _font(12, bold=False).render(hint, True, BORDER_COLOR)
        surf.blit(t, (cx - t.get_width() // 2, sy + 6 + i * 15))


# ── settings ─────────────────────────────────────────────────────────────────

def draw_settings(surf: pygame.Surface, music_vol: int, sfx_vol: int,
                  settings_row: int, muted: bool, scale: float,
                  ghost_opacity: int = 25, das_preset: str = "normal") -> None:
    surf.fill(BG_COLOR)
    cx = SCREEN_WIDTH // 2

    t = _font(30).render("SETTINGS", True, YELLOW)
    surf.blit(t, (cx - t.get_width() // 2, 26))
    pygame.draw.line(surf, BORDER_COLOR, (40, 68), (SCREEN_WIDTH - 40, 68), 1)

    def _vol_row(label, pct, y, selected):
        col = YELLOW if selected else BORDER_COLOR
        surf.blit(_font(14, bold=False).render(label, True, col), (60, y))
        bx, by, bw, bh = 60, y + 22, 200, 13
        pygame.draw.rect(surf, BORDER_COLOR, (bx, by, bw, bh), 1)
        fill_w = int(bw * pct / 100)
        if fill_w > 2:
            pygame.draw.rect(surf, col, (bx + 1, by + 1, fill_w - 2, bh - 2))
        surf.blit(_font(14).render(f"{pct}%", True, col), (bx + bw + 10, by - 2))
        if selected:
            surf.blit(_font(11, bold=False).render("< / >  adjust", True, YELLOW),
                      (bx + bw + 10, by + 13))

    _vol_row("MUSIC VOLUME",  music_vol,    80, settings_row == 0)
    _vol_row("SFX VOLUME",    sfx_vol,      150, settings_row == 1)

    scale_col = YELLOW if settings_row == 2 else BORDER_COLOR
    surf.blit(_font(14, bold=False).render("DISPLAY SCALE", True, scale_col), (60, 222))
    for i, v in enumerate(config.VALID_SCALES):
        lbl    = f"{v:g}×"
        active = (v == scale)
        box_x  = 60 + i * 80
        box_col = YELLOW if (active and settings_row == 2) else (
                  BORDER_COLOR if not active else (210, 210, 80))
        pygame.draw.rect(surf, box_col, (box_x, 244, 68, 22), 0 if active else 1)
        tc = BG_COLOR if active else box_col
        surf.blit(_font(14).render(lbl, True, tc),
                  (box_x + 34 - _font(14).size(lbl)[0] // 2, 246))
    if settings_row == 2:
        surf.blit(_font(11, bold=False).render("< / >  change scale  (restarts window)",
                                               True, YELLOW), (60, 272))

    _vol_row("GHOST  OPACITY", ghost_opacity, 300, settings_row == 3)
    if settings_row == 3 and ghost_opacity == 0:
        surf.blit(_font(11, bold=False).render("shadow disabled", True, BORDER_COLOR),
                  (60, 336))
    elif settings_row == 3 and ghost_opacity == 100:
        surf.blit(_font(11, bold=False).render("full solid tile", True, BORDER_COLOR),
                  (60, 336))

    das_col = YELLOW if settings_row == 4 else BORDER_COLOR
    surf.blit(_font(14, bold=False).render("INPUT SPEED  (DAS / ARR)", True, das_col),
              (60, 348))
    das_labels = {"slow": "Slow", "normal": "Normal", "fast": "Fast", "instant": "Instant"}
    for i, key in enumerate(config.VALID_DAS_PRESETS):
        active  = (key == das_preset)
        box_col = YELLOW if (active and settings_row == 4) else (
                  BORDER_COLOR if not active else (210, 210, 80))
        bx = 60 + i * 98
        pygame.draw.rect(surf, box_col, (bx, 370, 86, 22), 0 if active else 1)
        tc  = BG_COLOR if active else box_col
        lbl = das_labels[key]
        surf.blit(_font(13).render(lbl, True, tc),
                  (bx + 43 - _font(13).size(lbl)[0] // 2, 372))
    if settings_row == 4:
        d, r = config.DAS_SETTINGS[das_preset]
        arr_str = "instant" if r == 0 else f"{r} ms"
        surf.blit(_font(11, bold=False).render(
            f"delay {d} ms  ·  repeat {arr_str}", True, YELLOW), (60, 398))

    mute_col = (255, 80, 80) if muted else (80, 220, 100)
    t = _font(15).render(f"M  —  MUSIC : {'MUTED' if muted else 'ON'}", True, mute_col)
    surf.blit(t, (cx - t.get_width() // 2, 424))

    ctrl_col = YELLOW if settings_row == 5 else BORDER_COLOR
    surf.blit(_font(14, bold=False).render("VIEW  CONTROLS", True, ctrl_col), (60, 450))
    if settings_row == 5:
        surf.blit(_font(11, bold=False).render("ENTER  —  open controls screen",
                                               True, YELLOW), (60, 470))

    pygame.draw.line(surf, BORDER_COLOR, (40, 492), (SCREEN_WIDTH - 40, 492), 1)
    for i, hint in enumerate(["UP / DOWN  :  select row",
                               "LEFT / RIGHT  :  adjust"]):
        t = _font(13, bold=False).render(hint, True, BORDER_COLOR)
        surf.blit(t, (cx - t.get_width() // 2, 504 + i * 18))

    _draw_back_btn(surf)
    pygame.draw.rect(surf, BORDER_COLOR, (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), 2)


# ── pause overlay ─────────────────────────────────────────────────────────────

def draw_pause(surf: pygame.Surface, blink_on: bool) -> None:
    ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    ov.fill((0, 0, 0, 175))
    surf.blit(ov, (0, 0))

    if blink_on:
        word   = "PAUSE"
        total  = len(word) * 5 * _PAUSE_CELL + (len(word) - 1) * 8
        start_x = (SCREEN_WIDTH - total) // 2
        top_y   = 240
        for li, ch in enumerate(word):
            lx   = start_x + li * (5 * _PAUSE_CELL + 8)
            col  = _PAUSE_COLORS[li]
            glyph = _PAUSE_GLYPHS[ch]
            for gy in range(5):
                for gx in range(5):
                    if glyph[gy][gx]:
                        x = lx + gx * _PAUSE_CELL
                        y = top_y + gy * _PAUSE_CELL
                        pygame.draw.rect(surf, col,
                                         (x, y, _PAUSE_BLOCK, _PAUSE_BLOCK))
                        bright = tuple(min(255, c + 90) for c in col)
                        pygame.draw.line(surf, bright,
                                         (x, y), (x + _PAUSE_BLOCK - 1, y))
                        pygame.draw.line(surf, bright,
                                         (x, y), (x, y + _PAUSE_BLOCK - 1))
                        dark = tuple(max(0, c - 60) for c in col)
                        pygame.draw.line(surf, dark,
                                         (x + _PAUSE_BLOCK - 1, y),
                                         (x + _PAUSE_BLOCK - 1, y + _PAUSE_BLOCK - 1))
                        pygame.draw.line(surf, dark,
                                         (x, y + _PAUSE_BLOCK - 1),
                                         (x + _PAUSE_BLOCK - 1, y + _PAUSE_BLOCK - 1))

    cx = SCREEN_WIDTH // 2
    _draw_btn(surf, "CONTINUE",     PAUSE_CONTINUE_RECT, (60, 220, 80))
    _draw_btn(surf, "QUIT  TO  MENU", PAUSE_QUIT_RECT,  (220, 60, 60))
    t = _font(11, bold=False).render("SPACE  —  resume    S  —  settings", True, BORDER_COLOR)
    surf.blit(t, (cx - t.get_width() // 2, 434))


# ── music preview ─────────────────────────────────────────────────────────────

def draw_music_test(surf: pygame.Surface, selected: int) -> None:
    surf.fill(BG_COLOR)
    cx = SCREEN_WIDTH // 2

    t = _font(22).render("MUSIC  PREVIEW", True, YELLOW)
    surf.blit(t, (cx - t.get_width() // 2, 20))
    pygame.draw.line(surf, BORDER_COLOR, (40, 54), (SCREEN_WIDTH - 40, 54), 1)

    hint = _font(11, bold=False).render(
        "UP / DOWN : select tier     ESC : back to menu", True, BORDER_COLOR)
    surf.blit(hint, (cx - hint.get_width() // 2, 60))
    pygame.draw.line(surf, BORDER_COLOR, (40, 78), (SCREEN_WIDTH - 40, 78), 1)

    ROW_H = 42
    for i in range(1, 11):
        y   = 86 + (i - 1) * ROW_H
        sel = (i == selected)
        col = YELLOW if sel else BORDER_COLOR
        if sel:
            pygame.draw.polygon(surf, YELLOW,
                                [(46, y + 8), (54, y + 13), (46, y + 18)])
        surf.blit(_font(16).render(f"TIER {i:>2}", True, col), (62, y + 4))
        desc_col = BORDER_COLOR if not sel else (220, 220, 100)
        surf.blit(_font(12, bold=False).render(_TIER_DESC[i], True, desc_col),
                  (158, y + 7))
        if sel:
            pygame.draw.line(surf, YELLOW,
                             (62, y + ROW_H - 4), (SCREEN_WIDTH - 40, y + ROW_H - 4), 1)

    pygame.draw.rect(surf, BORDER_COLOR, (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), 2)


# ── in-game pause gear icon ───────────────────────────────────────────────────

def draw_ingame_gear(surf: pygame.Surface) -> None:
    r = INGAME_GEAR_RECT
    bg = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
    bg.fill((0, 0, 0, 80))
    surf.blit(bg, (r.x, r.y))
    color = (160, 160, 160)
    pygame.draw.rect(surf, color, r, 1)
    f = _font(16)
    t = f.render("II", True, color)
    surf.blit(t, (r.centerx - t.get_width() // 2,
                  r.centery - t.get_height() // 2))


# ── controls screen ───────────────────────────────────────────────────────────

_CONTROLS_TABLE = [
    ("MOVE",         "LEFT / RIGHT"),
    ("ROTATE CW",    "UP  or  X"),
    ("ROTATE CCW",   "Z"),
    ("SOFT DROP",    "DOWN"),
    ("HARD DROP",    "SPACE"),
    ("HOLD PIECE",   "C"),
    ("PAUSE",        "ESC  or  Q"),
    ("SETTINGS",     "S"),
    ("MUTE",         "M"),
    ("ABOUT / INFO", "A  (at menu)"),
]

def draw_controls(surf: pygame.Surface) -> None:
    surf.fill(BG_COLOR)
    cx = SCREEN_WIDTH // 2

    _draw_shadow_text(surf, "CONTROLS", 28, cx, 22, YELLOW, center_x=True)
    pygame.draw.line(surf, BORDER_COLOR, (30, 62), (SCREEN_WIDTH - 30, 62), 1)

    col_label = 40
    col_key   = 250
    row_h     = 38
    y0        = 76

    for i, (action, keys) in enumerate(_CONTROLS_TABLE):
        y   = y0 + i * row_h
        col = WHITE if i % 2 == 0 else (200, 200, 200)
        _draw_shadow_text(surf, action, 13, col_label, y, col)
        _draw_shadow_text(surf, keys,   13, col_key,   y, (80, 200, 255))

    pygame.draw.line(surf, BORDER_COLOR,
                     (30, y0 + len(_CONTROLS_TABLE) * row_h + 4),
                     (SCREEN_WIDTH - 30, y0 + len(_CONTROLS_TABLE) * row_h + 4), 1)

    _draw_back_btn(surf)
    pygame.draw.rect(surf, BORDER_COLOR, (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), 2)


# ── menu ──────────────────────────────────────────────────────────────────────

def _draw_mini_piece(surf, shape, cx, cy, cell):
    cols = max(len(r) for r in shape)
    rows = len(shape)
    ox   = cx - cols * (cell + 1) // 2
    oy   = cy - rows * (cell + 1) // 2
    for ri, row in enumerate(shape):
        for ci, val in enumerate(row):
            if val:
                surf.blit(get_block(val, cell),
                          (ox + ci * (cell + 1), oy + ri * (cell + 1)))


def draw_menu(surf: pygame.Surface, blink_on: bool, updater=None,
              menu_row: int = 0) -> None:
    surf.fill(BG_COLOR)
    cx = SCREEN_WIDTH // 2

    # ── RETRIS pixel-block logo ───────────────────────────────────────────────
    draw_retris_logo(surf, top_y=10)

    # ── "by kakoritz" ─────────────────────────────────────────────────────────
    t = _font(11, bold=False).render("by kakoritz", True, BORDER_COLOR)
    surf.blit(t, (cx - t.get_width() // 2, 76))

    # ── Mini tetromino parade ─────────────────────────────────────────────────
    slot_w = SCREEN_WIDTH // len(SHAPES)
    for i, pt in enumerate(SHAPES):
        _draw_mini_piece(surf, SHAPES[pt], slot_w * i + slot_w // 2, 130, 16)

    # ── ⓘ / ⚙ icon buttons ────────────────────────────────────────────────────
    _draw_icon_circle(surf, "i", MENU_ABOUT_RECT,    (80, 200, 255))
    _draw_icon_circle(surf, "S", MENU_SETTINGS_RECT, (180, 180, 180))

    # ── NES-style selection cursor ────────────────────────────────────────────
    items = ["START  GAME", "LEADERBOARD"]
    item_y = [192, 240]

    for i, (label, y) in enumerate(zip(items, item_y)):
        selected = (i == menu_row)
        color    = WHITE if selected else (90, 90, 90)
        _draw_shadow_text(surf, label, 22, cx, y, color, center_x=True)
        if selected and blink_on:
            ax = cx - _font(22).size(label)[0] // 2 - 28
            _draw_shadow_text(surf, ">", 22, ax, y, (255, 220, 0))

    # ── Version + update badge ────────────────────────────────────────────────
    from game_constants import VERSION
    ver_color = BORDER_COLOR
    ver_label = f"v{VERSION}"
    if updater and updater.status == "available":
        ver_label = f"v{VERSION}  •  v{updater.latest_version} available!"
        ver_color = (255, 220, 0) if blink_on else (180, 155, 0)
    t = _font(11, bold=False).render(ver_label, True, ver_color)
    surf.blit(t, (cx - t.get_width() // 2, SCREEN_HEIGHT - 22))

    pygame.draw.rect(surf, BORDER_COLOR, (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), 2)


def draw_about(surf: pygame.Surface, updater) -> None:
    surf.fill(BG_COLOR)
    cx = SCREEN_WIDTH // 2

    draw_retris_logo(surf, top_y=10)
    t = _font(11, bold=False).render("by kakoritz", True, BORDER_COLOR)
    surf.blit(t, (cx - t.get_width() // 2, 76))
    pygame.draw.line(surf, BORDER_COLOR, (30, 92), (SCREEN_WIDTH - 30, 92), 1)

    from game_constants import VERSION
    _draw_shadow_text(surf, f"Version  v{VERSION}", 14, cx, 100,
                      WHITE, center_x=True)
    pygame.draw.line(surf, BORDER_COLOR, (30, 124), (SCREEN_WIDTH - 30, 124), 1)

    y = 134
    status = updater.status if updater else "checking"

    if status == "checking":
        t = _font(13, bold=False).render("Checking for updates...", True, (140, 140, 140))
        surf.blit(t, (cx - t.get_width() // 2, y))

    elif status == "up_to_date":
        _draw_shadow_text(surf, "Up to date", 14, cx, y, (60, 200, 80), center_x=True)

    elif status in ("offline", "error"):
        msg = "No internet connection" if status == "offline" else "Update check failed"
        t = _font(12, bold=False).render(msg, True, (160, 100, 100))
        surf.blit(t, (cx - t.get_width() // 2, y))

    elif status == "available":
        _draw_shadow_text(surf, f"v{updater.latest_version}  available!", 14,
                          cx, y, (255, 220, 0), center_x=True)
        y += 26

        lines_drawn = 0
        for ver, body in updater.release_notes:
            if lines_drawn >= 10:
                break
            t = _font(11).render(f"— v{ver} —", True, (80, 160, 220))
            surf.blit(t, (cx - t.get_width() // 2, y))
            y += 15; lines_drawn += 1
            for raw in body.splitlines():
                raw = raw.strip()
                if not raw or lines_drawn >= 10:
                    break
                while len(raw) > 52:
                    t = _font(10, bold=False).render(raw[:52], True, (190, 190, 190))
                    surf.blit(t, (32, y)); y += 13; lines_drawn += 1
                    raw = "  " + raw[52:]
                    if lines_drawn >= 10:
                        break
                if lines_drawn < 10:
                    t = _font(10, bold=False).render(raw, True, (190, 190, 190))
                    surf.blit(t, (32, y)); y += 13; lines_drawn += 1

        pygame.draw.line(surf, BORDER_COLOR, (30, min(y+4, 420)), (SCREEN_WIDTH-30, min(y+4, 420)), 1)
        _draw_shadow_text(surf, "ENTER  —  open download page", 12,
                          cx, min(y+12, 426), (0, 200, 160), center_x=True)

    # ── GitHub link ───────────────────────────────────────────────────────────
    pygame.draw.line(surf, BORDER_COLOR, (30, 454), (SCREEN_WIDTH - 30, 454), 1)
    _draw_shadow_text(surf, "github.com/kakoritz/retris", 12,
                      cx, 462, (80, 180, 255), center_x=True)
    pygame.draw.rect(surf, (80, 180, 255),
                     ABOUT_GITHUB_RECT, 1)

    # ── Demo tip ──────────────────────────────────────────────────────────────
    t = _font(10, bold=False).render("tip: press D at menu for a secret demo mode",
                                     True, BORDER_COLOR)
    surf.blit(t, (cx - t.get_width() // 2, 498))

    _draw_back_btn(surf)
    pygame.draw.rect(surf, BORDER_COLOR, (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), 2)


# ── name entry ────────────────────────────────────────────────────────────────

def draw_name_entry(surf: pygame.Surface, initials: list, cursor: int,
                    blink_on: bool, score: int, lines: int, level: int) -> None:
    surf.fill(BG_COLOR)
    cx = SCREEN_WIDTH // 2

    t = _font(30).render("NEW HIGH SCORE!", True, YELLOW)
    surf.blit(t, (cx - t.get_width() // 2, 70))

    t = _font(19).render(f"SCORE  {str(score).zfill(7)}", True, WHITE)
    surf.blit(t, (cx - t.get_width() // 2, 118))

    t = _font(14, bold=False).render(f"LINES {lines}    LEVEL {level}", True, BORDER_COLOR)
    surf.blit(t, (cx - t.get_width() // 2, 148))

    pygame.draw.line(surf, BORDER_COLOR, (cx - 140, 174), (cx + 140, 174), 1)

    t = _font(14, bold=False).render("ENTER YOUR INITIALS", True, BORDER_COLOR)
    surf.blit(t, (cx - t.get_width() // 2, 188))

    slot, gap = 58, 18
    sx = cx - (3 * slot + 2 * gap) // 2
    for i, ch in enumerate(initials):
        x      = sx + i * (slot + gap)
        active = (i == cursor)
        pygame.draw.rect(surf, YELLOW if active else BORDER_COLOR,
                         (x, 218, slot, slot), 2)
        if (not active) or blink_on:
            t = _font(40).render(ch, True, YELLOW if active else WHITE)
            surf.blit(t, (x + slot // 2 - t.get_width() // 2,
                          218 + slot // 2 - t.get_height() // 2))

    if blink_on:
        ax = sx + cursor * (slot + gap) + slot // 2
        t  = _font(14, bold=False).render("^", True, YELLOW)
        surf.blit(t, (ax - t.get_width() // 2, 284))

    for i, hint in enumerate(["UP / DOWN : change letter",
                               "LEFT / RIGHT : move cursor",
                               "ENTER : confirm"]):
        t = _font(14, bold=False).render(hint, True, BORDER_COLOR)
        surf.blit(t, (cx - t.get_width() // 2, 322 + i * 20))

    pygame.draw.rect(surf, BORDER_COLOR, (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), 2)


# ── leaderboard ───────────────────────────────────────────────────────────────

_LB_RANK_COLORS = [
    (255, 215,   0),   # 1 — gold
    (192, 192, 192),   # 2 — silver
    (205, 127,  50),   # 3 — bronze
]

def draw_leaderboard(surf: pygame.Surface, scores: list,
                     hi_name: str | None, hi_score: int | None) -> None:
    surf.fill(BG_COLOR)
    _draw_animated_bg(surf)
    cx = SCREEN_WIDTH // 2

    # ── Title ─────────────────────────────────────────────────────────────────
    _draw_shadow_text(surf, "HIGH  SCORES", 26, cx, 12, YELLOW, center_x=True)

    pygame.draw.line(surf, BORDER_COLOR, (12, 50), (SCREEN_WIDTH - 12, 50), 1)

    # ── Column header ─────────────────────────────────────────────────────────
    X_RANK  = 14
    X_NAME  = 50
    X_SCORE = 110
    X_LINES = 314
    X_LVL   = 390
    Y_HDR   = 56
    ROW_H   = 44

    for label, x in [("#", X_RANK), ("NAME", X_NAME), ("SCORE", X_SCORE),
                     ("LINES", X_LINES), ("LVL", X_LVL)]:
        t = _font(11, bold=False).render(label, True, BORDER_COLOR)
        surf.blit(t, (x, Y_HDR))

    pygame.draw.line(surf, BORDER_COLOR, (12, Y_HDR + 18), (SCREEN_WIDTH - 12, Y_HDR + 18), 1)

    # ── Entries ───────────────────────────────────────────────────────────────
    for i, e in enumerate(scores):
        y       = Y_HDR + 22 + i * ROW_H
        is_new  = (e["name"] == hi_name and e["score"] == hi_score)
        rank_c  = _LB_RANK_COLORS[i] if i < 3 else (WHITE if is_new else (200, 200, 200))

        # Row tint for new entry
        if is_new:
            hl = pygame.Surface((SCREEN_WIDTH - 24, ROW_H - 2), pygame.SRCALPHA)
            hl.fill((255, 220, 0, 28))
            surf.blit(hl, (12, y))

        # Rank
        _draw_shadow_text(surf, f"{i+1}", 14, X_RANK, y + 2, rank_c)

        # Name
        _draw_shadow_text(surf, e["name"], 16, X_NAME, y, rank_c)

        # Score — odometer style (static)
        digits = [int(d) for d in str(min(e["score"], 99999999)).zfill(8)]
        draw_odometer(surf, digits, [0]*8, [0.0]*8, X_SCORE, y + 2)

        # Lines
        _draw_shadow_text(surf, str(e["lines"]), 14, X_LINES, y + 2,
                          (180, 220, 255) if is_new else (160, 160, 160))

        # Level
        _draw_shadow_text(surf, str(e["level"]), 14, X_LVL, y + 2,
                          (100, 255, 100) if is_new else (140, 140, 140))

        # Thin separator
        if i < len(scores) - 1:
            pygame.draw.line(surf, (40, 40, 40),
                             (12, y + ROW_H - 2), (SCREEN_WIDTH - 12, y + ROW_H - 2), 1)

    pygame.draw.line(surf, BORDER_COLOR,
                     (12, SCREEN_HEIGHT - 48), (SCREEN_WIDTH - 12, SCREEN_HEIGHT - 48), 1)

    _draw_back_btn(surf)
    t = _font(12, bold=False).render("R  —  play again", True, BORDER_COLOR)
    surf.blit(t, (cx - t.get_width() // 2, SCREEN_HEIGHT - 38))

    pygame.draw.rect(surf, BORDER_COLOR, (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), 2)
