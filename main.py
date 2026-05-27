import colorsys
import math
import random
import pygame
import sys

import audio
audio.pre_init()

import config
import highscore
import music
import music_game
from game_over_anim import GameOverAnim
from particles import spawn as spawn_particles
from particles import update as update_particles
from particles import draw as draw_particles
from constants import (
    COLS, ROWS, CELL_SIZE,
    BOARD_WIDTH, BOARD_HEIGHT, SIDEBAR_WIDTH, SCREEN_WIDTH, SCREEN_HEIGHT,
    FPS, BG_COLOR, GRID_COLOR, BORDER_COLOR, WHITE, YELLOW,
    COLORS, SHAPES, SCORE_TABLE, fall_speed,
)
from board import Board
from piece import Piece
from sprites import get_block, get_ghost


# ── states ────────────────────────────────────────────────────────────────────
MENU        = "menu"
PLAYING     = "playing"
CLEARING    = "clearing"
GAME_OVER   = "game_over"
ENTER_NAME  = "enter_name"
LEADERBOARD = "leaderboard"
SETTINGS       = "settings"
GAME_OVER_ANIM = "game_over_anim"
PAUSED         = "paused"
MUSIC_TEST     = "music_test"
CASCADING      = "cascading"   # animated full-board gravity (full cascade mode)

_MUSIC_END = pygame.USEREVENT + 1   # fired by mixer when a track finishes naturally

_INITIALS_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ "

# ── DAS (delayed auto-shift) ──────────────────────────────────────────────────
DAS_DELAY  = 170   # ms before auto-repeat starts
DAS_REPEAT = 50    # ms between repeated moves

# ── lock delay ────────────────────────────────────────────────────────────────
LOCK_DELAY     = 500   # ms grace period after a piece touches the stack
LOCK_MAX_MOVES = 15    # max resets per piece; prevents infinite stalling

# ── line-clear flash animation ────────────────────────────────────────────────
FLASH_MS    = {1: 85, 2: 80, 3: 75, 4: 68}   # ms per on/off phase
FLASH_TOTAL = {1: 2,  2: 4,  3: 6,  4: 10}   # phases per count
FLASH_COLOR_NORM = (255, 255, 255)
FLASH_COLOR_QUAD = (255, 215,   0)

# Perfect-clear (WOW) flash — longer and faster than a Tetris
FLASH_MS_WOW    = 48    # ms per phase
FLASH_TOTAL_WOW = 18    # number of on/off phases

WOW_BONUS          = 5000   # flat score multiplied by (level + 1)
WOW_POPUP_DURATION = 4500   # ms — WOW popup lingers much longer than normal

# ── T-spin scoring (base, before level multiplier) ───────────────────────────
# Full T-spin: last action was a rotation AND 3+ of the 4 bounding-box corners
# are occupied.  Mini: only 2 corners, but both "point-side" corners are blocked.
TSPIN_SCORES      = {0: 400, 1: 800,  2: 1200, 3: 1600}
TSPIN_MINI_SCORES = {0: 100, 1: 200,  2: 400}

# ── combo bonus ───────────────────────────────────────────────────────────────
# Added on top of the line-clear score for each consecutive clear.
# combo=0 on the first clear in a row (no bonus); increments with each further
# consecutive clear so bonus = 50 × combo × (level + 1).
COMBO_BONUS_UNIT = 50

# ── 20G gravity ───────────────────────────────────────────────────────────────
GRAVITY_20G_LEVEL = 20   # level at which gravity becomes instant-drop per tick

# ── placement score ───────────────────────────────────────────────────────────
PLACEMENT_SCORE = 10     # small reward for every piece locked

# ── speed reset ───────────────────────────────────────────────────────────────
SPEED_RESET_INTERVAL = 10000   # every N points, fall speed resets to tier 1

# ── palette shift ─────────────────────────────────────────────────────────────
PALETTE_PHASE_INTERVAL = 10   # levels per palette darkening step (6 phases, then wraps)

# ── page-up/down in-game volume ───────────────────────────────────────────────
PAGE_VOL_STEP = 5   # % per keypress

# ── speed-reset flash overlay ─────────────────────────────────────────────────
SPEED_RESET_FLASH_DURATION = 2500   # ms — "SPEED RESET!" drawn on board

# ── full board cascade animation ──────────────────────────────────────────────
CASCADE_STEP_MS   = 80    # ms between each one-row gravity wave
CASCADE_BONUS_PER_RESET = 5000   # flat score bonus per reset count when cascade completes

# ── sidebar popup ─────────────────────────────────────────────────────────────
POPUP_DURATION    = 2000   # ms
SHAKE_DURATION    = 380    # ms  (quad clear only)
SHAKE_INTENSITY   = 5      # px
HD_FLASH_DURATION = 90     # ms  (hard drop impact)

# Board background colors (Tron dark grid)
_BOARD_LINE = (0, 38, 65)    # dark-cyan shown in the 1 px gaps between cells
_BOARD_CELL = (5, 5, 18)     # near-black cell fill

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

POPUP_STYLES = {
    # count 0 is reserved for the perfect-clear WOW popup (board-centered, rainbow)
    0:  ("!! W O W !!",      None,           32),
    1:  ("Nice!",            (100, 255, 120), 17),
    2:  ("Great!",           (255, 235,  60), 20),
    3:  ("Fantastic!",       (255, 150,  50), 20),
    4:  ("TETRIS!",           None,           24),  # None = rainbow
    5:  ("T-SPIN!",          (200, 100, 255), 22),
    6:  ("T-SPIN MINI",      (180,  80, 200), 17),
    7:  ("B2B TETRIS!",       None,           22),  # None = rainbow
    8:  ("B2B T-SPIN!",      (220, 130, 255), 22),
    # cascade chain popups
    9:  ("Wild!",            ( 80, 255, 180), 18),
    10: ("Woah!",            (255, 200,  50), 20),
    11: ("Crazy!",           (255,  80,  50), 22),
    12: ("INSANE!",          (255,  50, 255), 26),
    # Tetris×Tetris cascade: board-centered rainbow (treated like WOW)
    13: ("TETRIS×TETRIS!",    None,           28),
}

_font_cache: dict = {}

def _font(size: int, bold: bool = True) -> pygame.font.Font:
    key = (size, bold)
    if key not in _font_cache:
        _font_cache[key] = pygame.font.SysFont("monospace", size, bold=bold)
    return _font_cache[key]


# ── T-spin corner detection ───────────────────────────────────────────────────
# The T-piece always fits in a 3×3 bounding box.  The 4 corners are indexed:
#   0=(TL) 1=(TR) 2=(BL) 3=(BR).
# "Point-side" corners are the two that sit on the same side as the T-bump.
# A T-spin mini requires exactly 2 corners blocked AND both point-side corners
# are among them.
_TSPIN_POINT = {
    0: (0, 1),   # state 0 (bump up)    → top corners
    1: (1, 3),   # state 1 (bump right) → right corners
    2: (2, 3),   # state 2 (bump down)  → bottom corners
    3: (0, 2),   # state 3 (bump left)  → left corners
}

# ── SRS wall-kick tables ──────────────────────────────────────────────────────
# Offsets are (dx, dy) in game coordinates (x right, y down).
# Source: Tetris Guideline SRS, with y-axis negated to match screen coords.
#
# Each key is (from_state, to_state). The O-piece never needs kicks; the I-piece
# uses its own table because its rotation centre differs from JLSZT.

_KICKS_JLSZT: dict[tuple, list[tuple]] = {
    (0, 1): [( 0, 0), (-1,  0), (-1, -1), (0,  2), (-1,  2)],
    (1, 0): [( 0, 0), ( 1,  0), ( 1,  1), (0, -2), ( 1, -2)],
    (1, 2): [( 0, 0), ( 1,  0), ( 1,  1), (0, -2), ( 1, -2)],
    (2, 1): [( 0, 0), (-1,  0), (-1, -1), (0,  2), (-1,  2)],
    (2, 3): [( 0, 0), ( 1,  0), ( 1, -1), (0,  2), ( 1,  2)],
    (3, 2): [( 0, 0), (-1,  0), (-1,  1), (0, -2), (-1, -2)],
    (3, 0): [( 0, 0), (-1,  0), (-1,  1), (0, -2), (-1, -2)],
    (0, 3): [( 0, 0), ( 1,  0), ( 1, -1), (0,  2), ( 1,  2)],
}

_KICKS_I: dict[tuple, list[tuple]] = {
    (0, 1): [( 0,  0), (-2,  0), ( 1,  0), (-2,  1), ( 1, -2)],
    (1, 0): [( 0,  0), ( 2,  0), (-1,  0), ( 2, -1), (-1,  2)],
    (1, 2): [( 0,  0), (-1,  0), ( 2,  0), (-1, -2), ( 2,  1)],
    (2, 1): [( 0,  0), ( 1,  0), (-2,  0), ( 1,  2), (-2, -1)],
    (2, 3): [( 0,  0), ( 2,  0), (-1,  0), ( 2, -1), (-1,  2)],
    (3, 2): [( 0,  0), (-2,  0), ( 1,  0), (-2,  1), ( 1, -2)],
    (3, 0): [( 0,  0), ( 1,  0), (-2,  0), ( 1,  2), (-2, -1)],
    (0, 3): [( 0,  0), (-1,  0), ( 2,  0), (-1, -2), ( 2,  1)],
}


def _try_rotate(board: Board, piece: Piece,
                new_shape: list, new_state: int) -> bool:
    """Attempt rotation with full SRS wall kicks.

    Tries each kick offset for the given state transition in order.
    On the first valid position the piece is updated and True is returned.
    """
    key   = (piece.rot_state, new_state)
    table = _KICKS_I if piece.type == 'I' else _KICKS_JLSZT
    # O-piece rotation is a no-op visually; skip kicks entirely.
    kicks = table.get(key, [(0, 0)]) if piece.type != 'O' else [(0, 0)]

    for dx, dy in kicks:
        if board.is_valid(piece, dx=dx, dy=dy, shape=new_shape):
            piece.x        += dx
            piece.y        += dy
            piece.shape     = new_shape
            piece.rot_state = new_state
            audio.play('rotate')
            return True
    return False


# ── board / piece drawing ─────────────────────────────────────────────────────

def draw_board(surf: pygame.Surface, board: Board,
               flash_rows: set | None = None,
               flash_on: bool = False,
               flash_quad: bool = False,
               wow_on: bool = False,
               palette_phase: int = 0) -> None:
    # Determine the flash colour for this frame.
    # WOW (perfect clear) cycles a fast rainbow hue across every cell.
    # Normal Tetris clears use white; quad (4-line) uses gold.
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
                # Perfect clear: the entire board (every cell) flashes rainbow.
                pygame.draw.rect(surf, fc, (px, py, CELL_SIZE - 1, CELL_SIZE - 1))
            elif flash_rows and gy in flash_rows and flash_on:
                pygame.draw.rect(surf, fc, (px, py, CELL_SIZE - 1, CELL_SIZE - 1))
            elif val:
                surf.blit(get_block(val, palette_phase=palette_phase), (px, py))
            else:
                pygame.draw.rect(surf, _BOARD_CELL,
                                 (px, py, CELL_SIZE - 1, CELL_SIZE - 1))


def _draw_danger_line(surf: pygame.Surface) -> None:
    """Horizontal warning line at the row-10 boundary.

    Shown when any filled cell has entered the top 10 rows — the same
    threshold that triggers tier-1 tension music.  A slow sine-wave pulse
    keeps it visually distinct from static board elements without being
    distracting during normal play.
    """
    y = 10 * CELL_SIZE   # pixel y of the row-10 top edge
    t = pygame.time.get_ticks()

    # Smooth pulse: full brightness when sin=1, 60 % when sin=-1 (~2.5 Hz)
    pulse = 0.5 + 0.5 * math.sin(t * 0.016)
    r     = 255
    gb    = int(20 + 30 * pulse)
    col   = (r, gb, gb)

    # 2 px core line
    pygame.draw.line(surf, col, (0, y),     (BOARD_WIDTH - 1, y),     2)
    # 1 px glow fringe — top and bottom of the core line
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
        return   # setting fully disabled — skip entirely
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


# ── popup ─────────────────────────────────────────────────────────────────────

def draw_popup(surf: pygame.Surface, count: int, timer: int) -> None:
    if timer <= 0 or count not in POPUP_STYLES:
        return
    text_str, base_color, base_size = POPUP_STYLES[count]

    # WOW (0) and TETRIS×TETRIS (13) use the board-centred position + long duration.
    is_wow   = (count in (0, 13))
    duration = WOW_POPUP_DURATION if is_wow else POPUP_DURATION
    elapsed  = duration - timer

    # Float upward over lifetime
    if is_wow:
        y = BOARD_HEIGHT // 2 - 18 - int((elapsed / duration) * 40)
    else:
        y = 440 - int((elapsed / POPUP_DURATION) * 22)

    # Fade out in last 600 ms
    alpha = 1.0 if timer > 600 else timer / 600

    # Pop: bigger font for the first 200 ms
    size = base_size + (5 if elapsed < 200 else 0)

    # Vivid colour — None means rainbow cycling
    if base_color is None:
        # WOW cycles faster than TETRIS for extra energy
        speed = 200 if is_wow else 450
        h = (pygame.time.get_ticks() / speed) % 1.0
        r, g, b = colorsys.hsv_to_rgb(h, 1.0, 1.0)
        vivid = (int(r * 255), int(g * 255), int(b * 255))
    else:
        vivid = base_color

    color = tuple(int(c * alpha) for c in vivid)
    f     = _font(size)
    tw, th = f.size(text_str)

    if is_wow:
        # WOW: large glowing rectangle centred on the board
        pad_x, pad_y = 18, 8
        bw, bh = tw + pad_x * 2, th + pad_y * 2
        bx = BOARD_WIDTH // 2 - bw // 2
        bg = tuple(int(c * 0.30 * alpha) for c in vivid)
        pygame.draw.rect(surf, bg, (bx, y - pad_y, bw, bh), border_radius=6)
        # Drop shadow for legibility over the board
        shadow = tuple(int(c * 0.25 * alpha) for c in vivid)
        t = f.render(text_str, True, shadow)
        surf.blit(t, (BOARD_WIDTH // 2 - tw // 2 + 2, y + 2))
        t = f.render(text_str, True, color)
        surf.blit(t, (BOARD_WIDTH // 2 - tw // 2, y))
    else:
        # Normal popup: sidebar-right column
        if count >= 2:
            pad_x, pad_y = 10, 4
            bw, bh = tw + pad_x * 2, th + pad_y * 2
            bx = BOARD_WIDTH + (SIDEBAR_WIDTH - bw) // 2
            bg = tuple(int(c * 0.22 * alpha) for c in vivid)
            pygame.draw.rect(surf, bg, (bx, y - pad_y, bw, bh), border_radius=4)
        t = f.render(text_str, True, color)
        x = BOARD_WIDTH + (SIDEBAR_WIDTH - t.get_width()) // 2
        surf.blit(t, (x, y))


# ── sidebar ───────────────────────────────────────────────────────────────────

def draw_sidebar(surf: pygame.Surface, score: int, lines: int,
                 level: int, next_piece: Piece, best: int,
                 hold_piece=None, hold_used: bool = False,
                 speed_tier: int = 1, next_speed_reset: int = SPEED_RESET_INTERVAL,
                 reset_bonus_mult: float = 1.0, full_cascade_mode: bool = False,
                 palette_phase: int = 0,
                 popup_count: int = 0, popup_timer: int = 0) -> None:
    sx = BOARD_WIDTH + 12

    def lbl(text, y): surf.blit(_font(13).render(text, True, BORDER_COLOR), (sx, y))
    def val(text, y): surf.blit(_font(19).render(text, True, YELLOW),       (sx, y))

    lbl("SCORE", 14); val(str(score).zfill(7), 30)
    lbl("BEST",  60); val(str(best).zfill(7),  76)

    # Level and Lines share one compact row
    surf.blit(_font(12).render("LVL",   True, BORDER_COLOR), (sx,      108))
    surf.blit(_font(12).render("LINES", True, BORDER_COLOR), (sx + 65, 108))
    surf.blit(_font(17).render(str(level), True, YELLOW),    (sx,      122))
    surf.blit(_font(17).render(str(lines), True, YELLOW),    (sx + 65, 122))

    # Speed tier + optional multiplier badge
    surf.blit(_font(12).render("SPEED", True, BORDER_COLOR), (sx, 150))
    surf.blit(_font(17).render(f"T{speed_tier}", True, YELLOW), (sx, 164))
    if reset_bonus_mult > 1.005:
        surf.blit(_font(12).render(f"×{reset_bonus_mult:.1f}", True, (255, 200, 50)),
                  (sx + 48, 167))

    # Reset countdown
    surf.blit(_font(12).render("RESET IN", True, BORDER_COLOR), (sx, 191))
    pts_left = max(0, next_speed_reset - score)
    if pts_left > 2000:
        rst_col = (100, 255, 100)
    elif pts_left > 500:
        rst_col = (255, 200, 50)
    else:
        rst_col = (255, 80, 80)
    surf.blit(_font(14).render(f"{pts_left:,} pts", True, rst_col), (sx, 204))

    # Full-cascade mode indicator — always shown so layout is stable
    if full_cascade_mode:
        fc_col  = (80, 255, 180)
        fc_mark = "★ FULL CASCADE"
    else:
        fc_col  = (60, 70, 80)
        fc_mark = "○ FULL CASCADE"
    surf.blit(_font(11).render(fc_mark, True, fc_col), (sx, 222))

    mini  = CELL_SIZE - 6
    box_w = SIDEBAR_WIDTH - 16
    box_h = 68
    box_x = sx - 4

    def _draw_piece_box(piece, label: str, by: int, dimmed: bool = False) -> None:
        surf.blit(_font(13).render(label, True, BORDER_COLOR), (sx, by))
        bby = by + 18
        border_col = tuple(max(c - 80, 0) for c in BORDER_COLOR) if dimmed else BORDER_COLOR
        pygame.draw.rect(surf, border_col, (box_x, bby, box_w, box_h), 1)
        if piece is not None:
            shape = piece.shape
            pc = max(len(r) for r in shape)
            pr = len(shape)
            ox = box_x + (box_w - pc * (mini + 1)) // 2
            oy = bby   + (box_h - pr * (mini + 1)) // 2
            for ri, row in enumerate(shape):
                for ci, v in enumerate(row):
                    if v:
                        blk = get_block(v, mini, palette_phase=palette_phase)
                        if dimmed:
                            faded = blk.copy()
                            faded.set_alpha(90)
                            surf.blit(faded, (ox + ci * (mini + 1), oy + ri * (mini + 1)))
                        else:
                            surf.blit(blk, (ox + ci * (mini + 1), oy + ri * (mini + 1)))

    _draw_piece_box(next_piece, "NEXT", 238)
    _draw_piece_box(hold_piece, "HOLD", 324, dimmed=hold_used)

    # Controls hint
    for i, h in enumerate(["<>  move",
                            "^ cw   Z ccw",
                            "v  soft drop",
                            "SPC  hard drop",
                            "C   hold"]):
        surf.blit(_font(11).render(h, True, BORDER_COLOR), (sx, 414 + i * 16))

    draw_popup(surf, popup_count, popup_timer)


# ── game-over overlay ─────────────────────────────────────────────────────────

def draw_game_over_overlay(surf: pygame.Surface, score: int) -> None:
    ov = pygame.Surface((BOARD_WIDTH, 120), pygame.SRCALPHA)
    ov.fill((0, 0, 0, 200))
    surf.blit(ov, (0, BOARD_HEIGHT // 2 - 40))
    cx = BOARD_WIDTH // 2

    t = _font(26).render("GAME OVER", True, (255, 60, 60))
    surf.blit(t, (cx - t.get_width() // 2, BOARD_HEIGHT // 2 - 32))

    t = _font(17).render(f"SCORE  {str(score).zfill(7)}", True, YELLOW)
    surf.blit(t, (cx - t.get_width() // 2, BOARD_HEIGHT // 2 + 4))

    for i, hint in enumerate(["R = restart",
                               "SPACE / ESC = menu",
                               "L = leaderboard"]):
        t = _font(13, bold=False).render(hint, True, BORDER_COLOR)
        surf.blit(t, (cx - t.get_width() // 2, BOARD_HEIGHT // 2 + 36 + i * 16))


# ── settings ─────────────────────────────────────────────────────────────────

def draw_settings(surf: pygame.Surface, music_vol: int, sfx_vol: int,
                  settings_row: int, muted: bool, scale: float,
                  ghost_opacity: int = 25) -> None:
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

    # ── display scale (button row) ─────────────────────────────────────────────
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

    # ── ghost / shadow opacity (slider) ────────────────────────────────────────
    _vol_row("GHOST  OPACITY", ghost_opacity, 300, settings_row == 3)
    if settings_row == 3 and ghost_opacity == 0:
        surf.blit(_font(11, bold=False).render("shadow disabled", True, BORDER_COLOR),
                  (60, 336))
    elif settings_row == 3 and ghost_opacity == 100:
        surf.blit(_font(11, bold=False).render("full solid tile", True, BORDER_COLOR),
                  (60, 336))

    # ── mute toggle ───────────────────────────────────────────────────────────
    mute_col = (255, 80, 80) if muted else (80, 220, 100)
    t = _font(15).render(f"M  —  MUSIC : {'MUTED' if muted else 'ON'}", True, mute_col)
    surf.blit(t, (cx - t.get_width() // 2, 372))

    pygame.draw.line(surf, BORDER_COLOR, (40, 400), (SCREEN_WIDTH - 40, 400), 1)
    for i, hint in enumerate(["UP / DOWN  :  select row",
                               "LEFT / RIGHT  :  adjust",
                               "ENTER / ESC  :  back to menu"]):
        t = _font(13, bold=False).render(hint, True, BORDER_COLOR)
        surf.blit(t, (cx - t.get_width() // 2, 414 + i * 20))

    pygame.draw.rect(surf, BORDER_COLOR, (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), 2)


# ── music tier descriptions ───────────────────────────────────────────────────

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


# ── pause overlay ────────────────────────────────────────────────────────────

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
    t = _font(15).render("PRESS  SPACE  TO  RESUME", True, WHITE)
    surf.blit(t, (cx - t.get_width() // 2, 332))
    t = _font(12, bold=False).render("Q  —  exit to menu", True, BORDER_COLOR)
    surf.blit(t, (cx - t.get_width() // 2, 356))


# ── music preview ────────────────────────────────────────────────────────────

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

        # Selector arrow
        if sel:
            pygame.draw.polygon(surf, YELLOW,
                                [(46, y + 8), (54, y + 13), (46, y + 18)])

        # Tier number
        surf.blit(_font(16).render(f"TIER {i:>2}", True, col), (62, y + 4))

        # Description
        desc_col = BORDER_COLOR if not sel else (220, 220, 100)
        surf.blit(_font(12, bold=False).render(_TIER_DESC[i], True, desc_col),
                  (158, y + 7))

        # Underline for selected row
        if sel:
            pygame.draw.line(surf, YELLOW,
                             (62, y + ROW_H - 4), (SCREEN_WIDTH - 40, y + ROW_H - 4), 1)

    pygame.draw.rect(surf, BORDER_COLOR, (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), 2)


# ── menu ──────────────────────────────────────────────────────────────────────

_TITLE_COLORS = [
    (160,   0, 240),
    (  0, 240, 240),
    (240, 240,   0),
    (  0, 240,   0),
    (  0,  60, 240),
    (240,   0,   0),
]


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


def draw_menu(surf: pygame.Surface, blink_on: bool) -> None:
    surf.fill(BG_COLOR)
    cx = SCREEN_WIDTH // 2

    letters = list("T3TR1S")
    widths  = [_font(56).size(l)[0] for l in letters]
    x = cx - sum(widths) // 2
    for letter, color in zip(letters, _TITLE_COLORS):
        t = _font(56).render(letter, True, color)
        surf.blit(t, (x, 58)); x += t.get_width()

    pygame.draw.line(surf, BORDER_COLOR, (cx - 160, 130), (cx + 160, 130), 1)
    t = _font(12, bold=False).render("by kakoritz", True, BORDER_COLOR)
    surf.blit(t, (cx - t.get_width() // 2, 135))
    pygame.draw.line(surf, BORDER_COLOR, (cx - 160, 153), (cx + 160, 153), 1)

    slot_w = SCREEN_WIDTH // len(SHAPES)
    for i, pt in enumerate(SHAPES):
        _draw_mini_piece(surf, SHAPES[pt], slot_w * i + slot_w // 2, 218, 16)

    if blink_on:
        t = _font(17).render("PRESS  SPACE  TO  START", True, WHITE)
        surf.blit(t, (cx - t.get_width() // 2, 288))

    for i, line in enumerate(["<  >  move       ^ rotate CW",
                               "Z rotate CCW     v  soft drop",
                               "SPACE hard drop",
                               "S  settings      M  mute",
                               "T  music preview"]):
        t = _font(12, bold=False).render(line, True, BORDER_COLOR)
        surf.blit(t, (cx - t.get_width() // 2, 358 + i * 18))

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

def draw_leaderboard(surf: pygame.Surface, scores: list,
                     hi_name: str | None, hi_score: int | None) -> None:
    surf.fill(BG_COLOR)
    cx = SCREEN_WIDTH // 2

    t = _font(26).render("HIGH  SCORES", True, YELLOW)
    surf.blit(t, (cx - t.get_width() // 2, 28))

    pygame.draw.line(surf, BORDER_COLOR, (30, 64), (SCREEN_WIDTH - 30, 64), 1)

    t = _font(13).render("  #  NAME    SCORE   LINES  LVL", True, BORDER_COLOR)
    surf.blit(t, (30, 72))
    pygame.draw.line(surf, BORDER_COLOR, (30, 88), (SCREEN_WIDTH - 30, 88), 1)

    for i, e in enumerate(scores):
        is_new = (e["name"] == hi_name and e["score"] == hi_score)
        row = (f"  {i+1:<2}  {e['name']:<4}  "
               f"{str(e['score']).zfill(7)}  "
               f"{e['lines']:>5}  {e['level']:>3}")
        t = _font(15).render(row, True, YELLOW if is_new else WHITE)
        surf.blit(t, (30, 98 + i * 26))

    pygame.draw.line(surf, BORDER_COLOR,
                     (30, SCREEN_HEIGHT - 56), (SCREEN_WIDTH - 30, SCREEN_HEIGHT - 56), 1)
    for i, hint in enumerate(["ENTER / ESC : menu", "R : play again"]):
        t = _font(13, bold=False).render(hint, True, BORDER_COLOR)
        surf.blit(t, (cx - t.get_width() // 2, SCREEN_HEIGHT - 46 + i * 18))

    pygame.draw.rect(surf, BORDER_COLOR, (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), 2)


# ── game helper ───────────────────────────────────────────────────────────────

def new_game():
    return Board(), Piece(), Piece(), 0, 0, 1, 0


# ── main loop ─────────────────────────────────────────────────────────────────

def _make_display(scale: float) -> pygame.Surface:
    w = int(SCREEN_WIDTH  * scale)
    h = int(SCREEN_HEIGHT * scale)
    return pygame.display.set_mode((w, h))


def _build_icon() -> pygame.Surface:
    """32×32 window icon: T-piece (stem pointing up) in T-piece purple.

    Layout (each X = one cell, cs=10px):
        . X .
        X X X
    Rendered with the same NES bevel style used for in-game blocks.
    """
    color = (160, 0, 240)
    cs    = 10
    surf  = pygame.Surface((32, 32), pygame.SRCALPHA)
    ox, oy = 1, 6   # centres the 30×20 piece in the 32×32 canvas
    hi  = tuple(min(c + 90, 255) for c in color)
    sh  = tuple(max(c - 80,   0) for c in color)
    for cx, cy in [(1, 0), (0, 1), (1, 1), (2, 1)]:
        x = ox + cx * cs
        y = oy + cy * cs
        pygame.draw.rect(surf, (*color, 255),    (x, y, cs, cs))
        pygame.draw.rect(surf, (8, 8, 20, 255),  (x, y, cs, cs), 1)
        pygame.draw.line(surf, (*hi, 255), (x+1, y+1),    (x+cs-2, y+1))
        pygame.draw.line(surf, (*hi, 255), (x+1, y+1),    (x+1, y+cs-2))
        pygame.draw.line(surf, (*sh, 255), (x+2, y+cs-2), (x+cs-2, y+cs-2))
        pygame.draw.line(surf, (*sh, 255), (x+cs-2, y+2), (x+cs-2, y+cs-2))
    return surf


def main():
    pygame.init()
    pygame.mixer.music.set_endevent(_MUSIC_END)

    # Icon must be set before set_mode so the OS picks it up on window creation.
    pygame.display.set_icon(_build_icon())

    current_scale = config.get_scale()
    display = _make_display(current_scale)

    if pygame.display.get_driver() == "offscreen":
        print(
            "\nT3TR1S: display unavailable — SDL fell back to offscreen mode.\n"
            "This usually means the X server has run out of client connections\n"
            "(common when VS Code, Firefox, and Discord are all open).\n"
            "Close a few heavy apps and try again.\n"
        )
        pygame.quit()
        sys.exit(1)

    # Logical surface: everything renders here at the native 460×600 size
    screen  = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

    pygame.display.set_caption("T3TR1S")
    clock = pygame.time.Clock()
    music.start()

    audio.prime()   # pre-build SFX so volume slider takes effect immediately

    state = MENU
    board, current, next_piece, score, lines, level, fall_timer = new_game()
    best  = highscore.best()

    # settings
    music_vol_pct    = 40                          # 0-100
    sfx_vol_pct      = 100                         # 0-100
    ghost_opacity_pct = config.get_ghost_opacity() # 0-100, persisted
    settings_row     = 0                           # 0=music 1=sfx 2=scale 3=ghost

    # game-over animation
    go_anim         = GameOverAnim()
    post_anim_state = GAME_OVER   # ENTER_NAME or GAME_OVER after animation

    # line-clear animation
    clear_rows:      set   = set()
    clear_count:     int   = 0
    clear_timer:     int   = 0
    clear_flash_idx: int   = 0

    # DAS
    das_dir:     int  = 0
    das_timer:   int  = 0
    das_charged: bool = False
    keys_held:   set  = set()

    # popup
    popup_count: int = 0
    popup_timer: int = 0

    # name entry
    initials   = ['A', 'A', 'A']
    ini_cursor = 0

    # leaderboard
    lb_scores   = []
    lb_hi_name  = None
    lb_hi_score = None

    blink_timer    = 0
    blink_on       = True
    pre_pause_vol  = 0.0
    music_test_tier = 1

    particles:      list = []
    shake_timer:    int  = 0
    hd_flash_timer: int  = 0
    clear_cells:    list = []
    danger:         bool = False   # True when any block occupies the top-10 rows
    wow_active:     bool = False   # True during a perfect-clear (board-empty) event
    # Each entry: {'x', 'y', 'vy', 'timer', 'max_timer'}
    # Spawned when rows above the danger line are cleared; float upward and fade.
    danger_bonuses: list = []
    _cheat_seq:     list = []   # tracks 3→2→1 debug sequence; never exposed in docs

    # lock delay
    lock_timer:      int  = 0    # counts up while piece is grounded
    lock_move_count: int  = 0    # resets used this piece; caps at LOCK_MAX_MOVES

    # hold piece
    hold_piece:      object = None   # Piece or None
    hold_used:       bool   = False  # True after hold is used; resets on piece lock

    # T-spin / back-to-back / combo
    last_action: str       = 'gravity'  # 'rotate','move','soft_drop','hard_drop','gravity'
    tspin_type:  str|None  = None       # 'full', 'mini', or None — detected at lock time
    btb_active:  bool      = False      # True when last difficult clear enables B2B
    combo:       int       = 0          # consecutive clears; 0 = no bonus yet
    # Floating "COMBO ×N" labels drawn on the board (same system as danger_bonuses)
    combo_labels: list     = []

    # speed tier + reset system
    speed_tier:       int   = 1                      # drives fall speed; resets every SPEED_RESET_INTERVAL pts
    next_speed_reset: int   = SPEED_RESET_INTERVAL   # score threshold for next reset
    speed_reset_count: int  = 0                      # total resets so far this game
    reset_bonus_mult: float = 1.0                    # +0.1 per reset; multiplies line-clear scores

    # full board cascade mode: toggled on/off by each speed reset
    full_cascade_mode: bool = False

    # cascade gravity (per clear chain)
    cascade_level:      int  = 0     # 0 = initial clear; 1+ = cascade passes
    first_clear_tetris: bool = False  # True if the initial lock clear was 4 lines

    # speed-reset overlay
    speed_reset_flash_timer: int = 0

    # full cascade animation
    cascade_anim_timer: int = 0

    def _spawn_next():
        nonlocal current, next_piece, lock_timer, lock_move_count, hold_used
        nonlocal last_action
        current          = next_piece
        next_piece       = Piece()
        lock_timer       = 0
        lock_move_count  = 0
        hold_used        = False
        last_action      = 'gravity'
        # 20G: immediately drop new piece to the floor on spawn.
        if level >= GRAVITY_20G_LEVEL:
            while board.is_valid(current, dy=1):
                current.y += 1
        audio.play_spawn(current.color_id)
        return board.is_valid(current)

    def _do_hold():
        """Swap current piece into the hold slot (or take from hold if occupied).

        The held piece is reset to its spawn orientation and position.
        Hold is locked for the rest of the current piece's life — one hold per piece.
        """
        nonlocal current, next_piece, hold_piece, hold_used
        nonlocal lock_timer, lock_move_count, last_action
        if hold_used:
            return
        hold_used   = True
        last_action = 'gravity'
        lock_timer  = lock_move_count = 0

        # Reset current to spawn state before stashing it.
        from constants import SHAPES, COLS as _COLS
        current.shape     = [row[:] for row in SHAPES[current.type]]
        current.rot_state = 0
        current.x         = _COLS // 2 - len(current.shape[0]) // 2
        current.y         = 0

        if hold_piece is None:
            hold_piece = current
            current    = next_piece
            next_piece = Piece()
        else:
            current, hold_piece = hold_piece, current
            # Reset swapped-in piece to spawn position
            current.shape     = [row[:] for row in SHAPES[current.type]]
            current.rot_state = 0
            current.x         = _COLS // 2 - len(current.shape[0]) // 2
            current.y         = 0

        # 20G: floor the swapped-in piece immediately.
        if level >= GRAVITY_20G_LEVEL:
            while board.is_valid(current, dy=1):
                current.y += 1
        last_action = 'gravity'
        audio.play_spawn(current.color_id)

    def _detect_tspin() -> str | None:
        """Return 'full', 'mini', or None based on T-spin corner rule.

        A T-spin requires the last action to be a rotation and the piece to be
        the T-piece.  Full T-spin: 3+ of the 4 corners of the 3×3 bounding box
        are occupied (wall or stack).  Mini: exactly 2 corners occupied, and
        both are on the "point side" of the T (the side the bump faces).
        """
        if current.type != 'T' or last_action != 'rotate':
            return None
        px, py = current.x, current.y
        # Corner positions of the fixed 3×3 bounding box: TL, TR, BL, BR
        corners = [(px, py), (px+2, py), (px, py+2), (px+2, py+2)]

        def _blocked(cx: int, cy: int) -> bool:
            return (cx < 0 or cx >= COLS or cy >= ROWS
                    or (cy >= 0 and board.grid[cy][cx] != 0))

        flags = [_blocked(cx, cy) for cx, cy in corners]
        n     = sum(flags)

        if n >= 3:
            return 'full'
        if n == 2:
            pi, pj = _TSPIN_POINT[current.rot_state]
            if flags[pi] and flags[pj]:
                return 'mini'
        return None

    def _start_new_game():
        nonlocal board, current, next_piece, score, lines, level, fall_timer
        nonlocal hold_piece, hold_used, lock_timer, lock_move_count
        nonlocal popup_count, popup_timer, wow_active
        nonlocal last_action, tspin_type, btb_active, combo, combo_labels
        nonlocal speed_tier, next_speed_reset, speed_reset_count, reset_bonus_mult
        nonlocal full_cascade_mode, cascade_level, first_clear_tetris
        nonlocal speed_reset_flash_timer, danger_bonuses
        board, current, next_piece, score, lines, level, fall_timer = new_game()
        hold_piece   = None
        hold_used    = False
        lock_timer   = lock_move_count = 0
        popup_count  = popup_timer = 0
        wow_active   = False
        last_action  = 'gravity'
        tspin_type   = None
        btb_active   = False
        combo        = 0
        combo_labels = []
        speed_tier          = 1
        next_speed_reset    = SPEED_RESET_INTERVAL
        speed_reset_count   = 0
        reset_bonus_mult    = 1.0
        full_cascade_mode   = False
        cascade_level       = 0
        first_clear_tetris  = False
        speed_reset_flash_timer = 0
        danger_bonuses = []
        _reset_das()
        audio.play_spawn(current.color_id)

    def _end_game():
        nonlocal state, initials, ini_cursor, post_anim_state
        music.fadeout(1200)
        go_anim.reset()
        if highscore.qualifies(score):
            initials        = ['A', 'A', 'A']
            ini_cursor      = 0
            post_anim_state = ENTER_NAME
        else:
            post_anim_state = GAME_OVER
        state = GAME_OVER_ANIM

    def _reset_das():
        nonlocal das_dir, das_timer, das_charged
        das_dir = 0; das_timer = 0; das_charged = False; keys_held.clear()

    def _reset_lock():
        """Reset the lock-delay clock after a successful move or rotate.

        Only resets if the piece is currently grounded AND we have moves left.
        Once LOCK_MAX_MOVES resets are used the piece locks on the next tick
        regardless — this prevents a player from stalling indefinitely.
        """
        nonlocal lock_timer, lock_move_count
        if not board.is_valid(current, dy=1) and lock_move_count < LOCK_MAX_MOVES:
            lock_timer = 0
            lock_move_count += 1

    def _do_lock():
        """Place the current piece, check for clears, spawn the next piece."""
        nonlocal state, lock_timer, lock_move_count
        nonlocal clear_rows, clear_count, clear_timer, clear_flash_idx
        nonlocal clear_cells, wow_active, tspin_type, combo
        nonlocal score, cascade_level, first_clear_tetris
        # Detect T-spin BEFORE placing — piece position + last_action must be current.
        tspin_type = _detect_tspin()
        board.place(current)
        audio.play('lock')
        _reset_das()
        lock_timer = lock_move_count = 0
        score += PLACEMENT_SCORE   # tiny reward for every piece locked
        cascade_level = 0
        first_clear_tetris = False
        full = board.full_rows()
        if full:
            full_set        = set(full)
            wow_active      = all(
                all(c == 0 for c in board.grid[r])
                for r in range(ROWS) if r not in full_set
            )
            clear_rows      = full_set
            clear_count     = len(full)
            clear_timer     = 0
            clear_flash_idx = 0
            clear_cells     = [
                (col, row_i, board.grid[row_i][col])
                for row_i in full for col in range(COLS)
                if board.grid[row_i][col]
            ]
            audio.play(clear_count)
            state = CLEARING
        else:
            combo = 0   # piece placed without clearing — streak broken
            if not _spawn_next():
                _end_game()

    def _debug_clear_board():
        """Fill every row solid then hand off to the normal CLEARING path so
        the WOW event fires exactly as it would in real play."""
        nonlocal clear_rows, clear_count, clear_timer, clear_flash_idx
        nonlocal clear_cells, wow_active, state, hd_flash_timer
        for r in range(ROWS):
            for c in range(COLS):
                if board.grid[r][c] == 0:
                    board.grid[r][c] = 1  # colour 1 — any non-zero value clears
        full_set        = set(range(ROWS))
        wow_active      = True             # board will be empty after the clear
        clear_rows      = full_set
        clear_count     = ROWS             # 20-line "clear" — uses WOW flash path
        clear_timer     = 0
        clear_flash_idx = 0
        clear_cells     = [
            (col, row_i, board.grid[row_i][col])
            for row_i in range(ROWS) for col in range(COLS)
        ]
        hd_flash_timer  = HD_FLASH_DURATION
        audio.play(4)                      # Tetris clear sound — closest available
        state           = CLEARING

    while True:
        dt = clock.tick(FPS)

        blink_timer += dt
        if blink_timer >= 500:
            blink_timer = 0
            blink_on    = not blink_on

        # ── events ────────────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            # Music track finished — advance sequence.
            # After on_music_end() the new track resets its volume to _game_vol,
            # so we must re-apply the 90 % reduction if we're still paused.
            if (event.type == _MUSIC_END
                    and state in (PLAYING, CLEARING, CASCADING, PAUSED)):
                music_game.on_music_end()
                if state == PAUSED:
                    pygame.mixer.music.set_volume(pre_pause_vol * 0.10)

            # KEYUP: track DAS key releases regardless of state
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_LEFT:
                    keys_held.discard(pygame.K_LEFT)
                    if das_dir == -1:
                        das_dir = (1 if pygame.K_RIGHT in keys_held else 0)
                        das_timer = 0; das_charged = False
                elif event.key == pygame.K_RIGHT:
                    keys_held.discard(pygame.K_RIGHT)
                    if das_dir == 1:
                        das_dir = (-1 if pygame.K_LEFT in keys_held else 0)
                        das_timer = 0; das_charged = False

            if event.type != pygame.KEYDOWN:
                continue

            # ── global keys (any state) ───────────────────────────────────────
            if event.key == pygame.K_m:
                music.toggle_mute()
                music_game.set_muted(music.is_muted())
                continue

            if event.key == pygame.K_PAGEUP:
                music_vol_pct = min(100, music_vol_pct + PAGE_VOL_STEP)
                music.set_volume(music_vol_pct / 100)
                music_game.set_volume(music_vol_pct / 100)
                continue

            if event.key == pygame.K_PAGEDOWN:
                music_vol_pct = max(0, music_vol_pct - PAGE_VOL_STEP)
                music.set_volume(music_vol_pct / 100)
                music_game.set_volume(music_vol_pct / 100)
                continue

            # ── MENU ──────────────────────────────────────────────────────────
            if state == MENU:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
                    _start_new_game()
                    best = highscore.best()
                    music.fadeout(400)
                    music_game.start_sequence()
                    state = PLAYING
                elif event.key == pygame.K_s:
                    settings_row = 0
                    state = SETTINGS
                elif event.key == pygame.K_t:
                    music_test_tier = 1
                    music.fadeout(300)
                    music_game.start_level(music_test_tier)
                    state = MUSIC_TEST

            # ── PLAYING ───────────────────────────────────────────────────────
            elif state == PLAYING:
                # Secret 3-2-1 debug sequence: triggers a full board clear + WOW.
                _CHEAT = [pygame.K_3, pygame.K_2, pygame.K_1]
                if event.key == _CHEAT[len(_cheat_seq)]:
                    _cheat_seq.append(event.key)
                    if len(_cheat_seq) == 3:
                        _cheat_seq.clear()
                        _debug_clear_board()
                        continue
                else:
                    # Any key that doesn't advance the sequence (including a wrong
                    # digit) resets it, so the user must press 3-2-1 cleanly.
                    _cheat_seq.clear()

                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    pre_pause_vol = pygame.mixer.music.get_volume()
                    pygame.mixer.music.set_volume(max(0.0, pre_pause_vol * 0.10))
                    state = PAUSED
                elif event.key == pygame.K_LEFT:
                    keys_held.add(pygame.K_LEFT)
                    das_dir = -1; das_timer = 0; das_charged = False
                    if board.is_valid(current, dx=-1):
                        current.x -= 1
                        last_action = 'move'
                        audio.play('move')
                        _reset_lock()
                        if level >= GRAVITY_20G_LEVEL:
                            while board.is_valid(current, dy=1):
                                current.y += 1
                elif event.key == pygame.K_RIGHT:
                    keys_held.add(pygame.K_RIGHT)
                    das_dir = 1; das_timer = 0; das_charged = False
                    if board.is_valid(current, dx=1):
                        current.x += 1
                        last_action = 'move'
                        audio.play('move')
                        _reset_lock()
                        if level >= GRAVITY_20G_LEVEL:
                            while board.is_valid(current, dy=1):
                                current.y += 1
                elif event.key == pygame.K_DOWN:
                    if board.is_valid(current, dy=1):
                        current.y += 1
                        last_action = 'soft_drop'
                        lock_timer  = 0
                elif event.key == pygame.K_UP:
                    if event.mod & pygame.KMOD_CTRL:
                        if _try_rotate(board, current, *current.rotated_ccw()):
                            last_action = 'rotate'
                            _reset_lock()
                    else:
                        if _try_rotate(board, current, *current.rotated_cw()):
                            last_action = 'rotate'
                            _reset_lock()
                elif event.key == pygame.K_z:
                    if _try_rotate(board, current, *current.rotated_ccw()):
                        last_action = 'rotate'
                        _reset_lock()
                elif event.key == pygame.K_c:
                    _do_hold()
                elif event.key == pygame.K_SPACE:
                    # Hard drop: instant commitment — no lock delay.
                    hd_flash_timer = HD_FLASH_DURATION
                    while board.is_valid(current, dy=1):
                        current.y += 1
                    last_action = 'hard_drop'
                    audio.play('hard_drop')
                    fall_timer  = 0
                    _do_lock()

            # ── GAME OVER ANIM (press any key to continue) ────────────────────
            elif state == GAME_OVER_ANIM:
                if go_anim.all_landed:
                    state = post_anim_state

            # ── PAUSED ────────────────────────────────────────────────────────
            # Only Space resumes — Q exits, everything else is ignored.
            # This prevents Alt+Tab, window events, or accidental keypresses
            # from resuming mid-game.
            elif state == PAUSED:
                if event.key == pygame.K_q:
                    music_game.stop()
                    music.start_menu()
                    state = MENU
                elif event.key == pygame.K_SPACE:
                    pygame.mixer.music.set_volume(pre_pause_vol)
                    state = PLAYING
                # all other keys silently ignored while paused

            # ── GAME OVER ─────────────────────────────────────────────────────
            elif state == GAME_OVER:
                if event.key == pygame.K_r:
                    _start_new_game()
                    music_game.stop()
                    music_game.start_sequence()
                    state = PLAYING
                elif event.key in (pygame.K_SPACE, pygame.K_ESCAPE):
                    music_game.stop()
                    music.start_menu()
                    state = MENU
                elif event.key == pygame.K_l:
                    lb_scores   = highscore.load()
                    lb_hi_name  = lb_hi_score = None
                    state       = LEADERBOARD

            # ── ENTER NAME ────────────────────────────────────────────────────
            elif state == ENTER_NAME:
                idx = _INITIALS_CHARS
                if event.key == pygame.K_UP:
                    pos = (idx.index(initials[ini_cursor]) - 1) % len(idx)
                    initials[ini_cursor] = idx[pos]
                elif event.key == pygame.K_DOWN:
                    pos = (idx.index(initials[ini_cursor]) + 1) % len(idx)
                    initials[ini_cursor] = idx[pos]
                elif event.key == pygame.K_LEFT and ini_cursor > 0:
                    ini_cursor -= 1
                elif event.key in (pygame.K_RIGHT, pygame.K_RETURN, pygame.K_KP_ENTER):
                    if ini_cursor < 2:
                        ini_cursor += 1
                    else:
                        name        = ''.join(initials).strip() or "???"
                        lb_scores   = highscore.insert(name, score, lines, level)
                        lb_hi_name  = name
                        lb_hi_score = score
                        best        = highscore.best()
                        state       = LEADERBOARD
                elif pygame.K_a <= event.key <= pygame.K_z:
                    initials[ini_cursor] = chr(event.key).upper()
                    if ini_cursor < 2:
                        ini_cursor += 1

            # ── LEADERBOARD ───────────────────────────────────────────────────
            elif state == LEADERBOARD:
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
                    music_game.stop()
                    music.start_menu()
                    state = MENU
                elif event.key == pygame.K_r:
                    _start_new_game()
                    music_game.stop()
                    music_game.start_sequence()
                    state = PLAYING

            # ── MUSIC PREVIEW ─────────────────────────────────────────────────
            elif state == MUSIC_TEST:
                if event.key in (pygame.K_ESCAPE, pygame.K_RETURN,
                                 pygame.K_KP_ENTER):
                    music_game.stop()
                    music.start_menu()
                    state = MENU
                elif event.key == pygame.K_UP:
                    music_test_tier = max(1, music_test_tier - 1)
                    music_game.start_level(music_test_tier)
                elif event.key == pygame.K_DOWN:
                    music_test_tier = min(10, music_test_tier + 1)
                    music_game.start_level(music_test_tier)

            # ── SETTINGS ──────────────────────────────────────────────────────
            elif state == SETTINGS:
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
                    state = MENU
                elif event.key == pygame.K_UP:
                    settings_row = (settings_row - 1) % 4
                elif event.key == pygame.K_DOWN:
                    settings_row = (settings_row + 1) % 4
                elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    delta = -5 if event.key == pygame.K_LEFT else 5
                    if settings_row == 0:
                        music_vol_pct = max(0, min(100, music_vol_pct + delta))
                        music.set_volume(music_vol_pct / 100)
                        music_game.set_volume(music_vol_pct / 100)
                    elif settings_row == 1:
                        sfx_vol_pct = max(0, min(100, sfx_vol_pct + delta))
                        audio.set_sfx_volume(sfx_vol_pct / 100)
                        audio.play('rotate')   # instant SFX preview
                    elif settings_row == 2:
                        scales = config.VALID_SCALES
                        idx = scales.index(current_scale) if current_scale in scales else 0
                        idx = max(0, min(len(scales) - 1,
                                        idx + (1 if event.key == pygame.K_RIGHT else -1)))
                        new_scale = scales[idx]
                        if new_scale != current_scale:
                            current_scale = new_scale
                            config.set_scale(current_scale)
                            display = _make_display(current_scale)
                    else:   # row 3 — ghost opacity
                        ghost_opacity_pct = max(0, min(100, ghost_opacity_pct + delta))
                        config.set_ghost_opacity(ghost_opacity_pct)

        # ── DAS auto-repeat ───────────────────────────────────────────────────
        if state == PLAYING and das_dir != 0:
            das_timer += dt
            if not das_charged:
                if das_timer >= DAS_DELAY:
                    das_charged = True
                    das_timer   = 0
            else:
                while das_timer >= DAS_REPEAT:
                    das_timer -= DAS_REPEAT
                    if board.is_valid(current, dx=das_dir):
                        current.x += das_dir
                        last_action = 'move'
                        audio.play('move')
                        _reset_lock()
                        if level >= GRAVITY_20G_LEVEL:
                            while board.is_valid(current, dy=1):
                                current.y += 1

        # ── danger detection → tier-1 tension music + warning line ──────────
        # Row indices 0-9 are the top half of the board.  Any filled cell there
        # triggers tension mode; clearing back below row 10 releases it.
        if state in (PLAYING, CLEARING, CASCADING):
            danger = any(any(row) for row in board.grid[:10])
            music_game.set_danger(danger)

        # ── gravity + lock delay ─────────────────────────────────────────────
        if state == PLAYING:
            grounded = not board.is_valid(current, dy=1)

            fall_timer += dt
            if fall_timer >= fall_speed(speed_tier):
                fall_timer = 0
                if not grounded:
                    if level >= GRAVITY_20G_LEVEL:
                        # 20G: drop all the way to the floor on each gravity tick.
                        while board.is_valid(current, dy=1):
                            current.y += 1
                    else:
                        current.y  += 1
                        lock_timer  = 0   # reset lock clock on natural descent
                    last_action = 'gravity'

            # Lock delay: count up while grounded; expire → lock the piece.
            grounded = not board.is_valid(current, dy=1)   # re-check after drop
            if grounded:
                lock_timer += dt
                if lock_timer >= LOCK_DELAY:
                    _do_lock()

        # ── line-clear animation ──────────────────────────────────────────────
        elif state == CLEARING:
            clear_timer += dt
            # WOW (perfect clear) gets a longer, faster rainbow flash.
            fms   = FLASH_MS_WOW    if wow_active else FLASH_MS.get(clear_count, 80)
            ftotal = FLASH_TOTAL_WOW if wow_active else FLASH_TOTAL.get(clear_count, 2)
            if clear_timer >= fms:
                clear_timer -= fms
                clear_flash_idx += 1
                if clear_flash_idx >= ftotal:
                    # ── scoring ───────────────────────────────────────────────
                    lines += clear_count

                    # Danger-zone multiplier: any cleared row above row 10 → 2×.
                    danger_rows = [r for r in clear_rows if r < 10]
                    danger_mult = 2 if danger_rows else 1

                    # Cascade multiplier: 1× for the first clear, 2× for first
                    # cascade, 3× for second, etc.
                    cascade_mult = cascade_level + 1

                    # Base line-clear score: T-spin tables override SCORE_TABLE.
                    is_tspin      = tspin_type is not None and not wow_active
                    is_difficult  = (clear_count == 4 or is_tspin) and not wow_active
                    if is_tspin:
                        tbl        = TSPIN_MINI_SCORES if tspin_type == 'mini' else TSPIN_SCORES
                        base_score = tbl.get(clear_count, 0) * (level + 1)
                    else:
                        base_score = SCORE_TABLE.get(clear_count, 0) * (level + 1)

                    # Tetris×Tetris: first clear was a Tetris AND this cascade
                    # is also a Tetris — override cascade mult to 4×.
                    tetris_x_tetris = (cascade_level == 1
                                       and clear_count == 4
                                       and first_clear_tetris)
                    if tetris_x_tetris:
                        cascade_mult = 4

                    # Back-to-back: 1.5× on consecutive difficult clears.
                    btb_bonus = is_difficult and btb_active
                    if btb_bonus:
                        base_score = int(base_score * 1.5)

                    score += int(base_score * cascade_mult * danger_mult * reset_bonus_mult)

                    # Combo bonus: 50 × combo count × (level + 1); combo = 0 on
                    # first clear in a row (no bonus yet), increments each clear.
                    combo_bonus = COMBO_BONUS_UNIT * combo * (level + 1)
                    score      += combo_bonus
                    if combo >= 1:   # spawn label when there's an actual bonus
                        combo_labels.append({
                            'text':      f"COMBO ×{combo + 1}",
                            'x':         float(BOARD_WIDTH // 2 - 32),
                            'y':         float(BOARD_HEIGHT // 2),
                            'vy':        -90.0,
                            'timer':     1400,
                            'max_timer': 1400,
                        })
                    combo += 1

                    if wow_active:
                        score += WOW_BONUS * (level + 1)

                    # Update B2B state for next clear.
                    if is_difficult:
                        btb_active = True
                    elif not wow_active and clear_count > 0:
                        btb_active = False   # non-difficult clear breaks the chain

                    # Spawn a floating ×2 label for each danger-zone row cleared.
                    for r in danger_rows:
                        danger_bonuses.append({
                            'x':         float(random.randint(10, BOARD_WIDTH - 50)),
                            'y':         float(r * CELL_SIZE),
                            'vy':        -115.0,
                            'timer':     1300,
                            'max_timer': 1300,
                        })

                    # Track level and speed tier.
                    old_level = level
                    level     = lines // 10 + 1
                    if level > old_level:
                        speed_tier = min(speed_tier + (level - old_level), 20)

                    # Speed reset: every SPEED_RESET_INTERVAL points fall speed
                    # drops back to tier 1, the score multiplier rises by 0.1,
                    # and Full Cascade Mode toggles on/off.
                    speed_reset_triggered = False
                    while score >= next_speed_reset:
                        next_speed_reset     += SPEED_RESET_INTERVAL
                        speed_tier            = 1
                        speed_reset_count    += 1
                        reset_bonus_mult      = round(1.0 + speed_reset_count * 0.1, 1)
                        full_cascade_mode     = not full_cascade_mode
                        speed_reset_triggered = True
                    if speed_reset_triggered:
                        speed_reset_flash_timer = SPEED_RESET_FLASH_DURATION

                    best  = max(best, score)

                    # Track whether this (first) clear was a Tetris so that a
                    # cascade Tetris can trigger the T×T event.
                    if cascade_level == 0:
                        first_clear_tetris = (clear_count == 4)

                    # ── clear lines, then settle floating blocks ───────────────
                    board.clear_lines()

                    # ── visual feedback for THIS clear pass ───────────────────
                    big_clear = (wow_active or clear_count == 4
                                 or (is_tspin and clear_count == 3)
                                 or tetris_x_tetris)
                    particles += spawn_particles(clear_cells, big_clear)
                    if big_clear:
                        shake_timer = SHAKE_DURATION

                    # ── popup selection ───────────────────────────────────────
                    # Priority: WOW > T×T > T-spin/B2B > cascade level > normal
                    if wow_active:
                        popup_count = 0
                        popup_timer = WOW_POPUP_DURATION
                        wow_active  = False
                    elif tetris_x_tetris:
                        popup_count = 13   # "TETRIS×TETRIS!" — board-centred
                        popup_timer = WOW_POPUP_DURATION
                    elif is_tspin and btb_bonus:
                        popup_count = 8   # "B2B T-SPIN!"
                        popup_timer = POPUP_DURATION
                    elif is_tspin and tspin_type == 'full':
                        popup_count = 5   # "T-SPIN!"
                        popup_timer = POPUP_DURATION
                    elif is_tspin:
                        popup_count = 6   # "T-SPIN MINI"
                        popup_timer = POPUP_DURATION
                    elif btb_bonus and clear_count == 4:
                        popup_count = 7   # "B2B TETRIS!"
                        popup_timer = POPUP_DURATION
                    elif cascade_level >= 4:
                        popup_count = 12   # "INSANE!"
                        popup_timer = POPUP_DURATION
                    elif cascade_level == 3:
                        popup_count = 11   # "Crazy!"
                        popup_timer = POPUP_DURATION
                    elif cascade_level == 2:
                        popup_count = 10   # "Woah!"
                        popup_timer = POPUP_DURATION
                    elif cascade_level == 1:
                        popup_count = 9    # "Wild!"
                        popup_timer = POPUP_DURATION
                    else:
                        popup_count = clear_count
                        popup_timer = POPUP_DURATION

                    tspin_type = None   # consumed

                    # ── cascade check ─────────────────────────────────────────
                    # Normal mode: only completely isolated singleton blocks fall.
                    # Full Cascade Mode (active after each odd speed reset):
                    #   every block with empty space below it falls — the
                    #   "Full Board Cascade Effect."
                    if full_cascade_mode:
                        # Animated domino fall — hand off to CASCADING state.
                        cascade_anim_timer = 0
                        state = CASCADING
                    else:
                        # Loop until no more isolated blocks can fall — a singleton
                        # dropping away from its neighbour can expose a new singleton
                        # above it.
                        while board.apply_singleton_gravity():
                            pass
                        cascade_rows = board.full_rows()
                        if cascade_rows:
                            cascade_level  += 1
                            full_set        = set(cascade_rows)
                            wow_active      = all(
                                all(c == 0 for c in board.grid[r])
                                for r in range(ROWS) if r not in full_set
                            )
                            clear_rows      = full_set
                            clear_count     = len(cascade_rows)
                            clear_timer     = 0
                            clear_flash_idx = 0
                            clear_cells     = [
                                (col, row_i, board.grid[row_i][col])
                                for row_i in cascade_rows for col in range(COLS)
                                if board.grid[row_i][col]
                            ]
                            audio.play(min(clear_count, 4))
                        else:
                            first_clear_tetris = False
                            cascade_level      = 0
                            if _spawn_next():
                                state = PLAYING
                            else:
                                _end_game()

        # ── full board cascade animation ──────────────────────────────────────
        # Blocks fall one row at a time on a timer — domino effect.
        # When nothing can fall, check for newly-formed full rows.
        elif state == CASCADING:
            cascade_anim_timer += dt
            if cascade_anim_timer >= CASCADE_STEP_MS:
                cascade_anim_timer -= CASCADE_STEP_MS
                if board.apply_block_gravity():
                    pass   # still falling — next frame will move the next wave
                else:
                    # Nothing moved — cascade is complete.
                    cascade_rows = board.full_rows()
                    if cascade_rows:
                        cascade_level  += 1
                        full_set        = set(cascade_rows)
                        wow_active      = all(
                            all(c == 0 for c in board.grid[r])
                            for r in range(ROWS) if r not in full_set
                        )
                        clear_rows      = full_set
                        clear_count     = len(cascade_rows)
                        clear_timer     = 0
                        clear_flash_idx = 0
                        clear_cells     = [
                            (col, row_i, board.grid[row_i][col])
                            for row_i in cascade_rows for col in range(COLS)
                            if board.grid[row_i][col]
                        ]
                        audio.play(min(clear_count, 4))
                        state = CLEARING
                    else:
                        # Cascade settled with no new rows — award cascade bonus
                        # and spawn the next piece.
                        if speed_reset_count > 0:
                            score += CASCADE_BONUS_PER_RESET * speed_reset_count
                            best   = max(best, score)
                        first_clear_tetris = False
                        cascade_level      = 0
                        if _spawn_next():
                            state = PLAYING
                        else:
                            _end_game()

        # ── game-over animation ───────────────────────────────────────────────
        if state == GAME_OVER_ANIM:
            hits = go_anim.update(dt)
            for bom_idx in hits:
                audio.play_bom(bom_idx)

        # ── popup / particle / fx timers ─────────────────────────────────────
        if popup_timer > 0:
            popup_timer = max(0, popup_timer - dt)
        particles            = update_particles(particles, dt)
        hd_flash_timer       = max(0, hd_flash_timer       - dt)
        shake_timer          = max(0, shake_timer           - dt)
        speed_reset_flash_timer = max(0, speed_reset_flash_timer - dt)

        # Advance danger-bonus ×2 floating labels (float upward, count down).
        s = dt / 1000.0
        for db in danger_bonuses:
            db['y']     += db['vy'] * s
            db['timer'] -= dt
        danger_bonuses = [db for db in danger_bonuses if db['timer'] > 0]

        # Advance combo floating labels.
        for cl in combo_labels:
            cl['y']     += cl['vy'] * s
            cl['timer'] -= dt
        combo_labels = [cl for cl in combo_labels if cl['timer'] > 0]

        # ── draw ──────────────────────────────────────────────────────────────
        if state == MENU:
            draw_menu(screen, blink_on)

        elif state in (PLAYING, CLEARING, CASCADING, GAME_OVER, GAME_OVER_ANIM, PAUSED):
            screen.fill(BG_COLOR)

            # Palette phase: darkens tiles by 10 % per 10 levels, wraps every 6 steps.
            palette_phase = ((level - 1) // PALETTE_PHASE_INTERVAL) % 6

            # Board content draws to its own surface so shake + flash can offset it
            bsurf = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT))
            bsurf.fill(_BOARD_LINE)

            fr = clear_rows if state == CLEARING else None
            fo = (clear_flash_idx % 2 == 0) if state == CLEARING else False
            fq = (clear_count == 4) if state == CLEARING else False
            fw = wow_active if state == CLEARING else False
            draw_board(bsurf, board, flash_rows=fr, flash_on=fo, flash_quad=fq,
                       wow_on=fw, palette_phase=palette_phase)

            # Danger warning line — drawn over the board but under the live piece
            # so the player can still see the boundary while actively placing blocks.
            if danger and state in (PLAYING, CLEARING, CASCADING, PAUSED):
                _draw_danger_line(bsurf)

            if state in (PLAYING, PAUSED):
                draw_ghost(bsurf, board, current, ghost_opacity_pct,
                           palette_phase=palette_phase)
                draw_piece(bsurf, current, palette_phase=palette_phase)

            draw_particles(bsurf, particles)

            # Danger-zone bonus ×2 floating labels
            for db in danger_bonuses:
                a = int(255 * db['timer'] / db['max_timer'])
                t = _font(20).render("×2", True, (255, 90, 0))
                t.set_alpha(a)
                bsurf.blit(t, (int(db['x']), int(db['y'])))

            # Combo floating labels (centred, cyan)
            for cl in combo_labels:
                a  = int(255 * cl['timer'] / cl['max_timer'])
                ct = _font(18).render(cl['text'], True, (0, 220, 240))
                ct.set_alpha(a)
                bsurf.blit(ct, (int(cl['x']), int(cl['y'])))

            # Speed-reset "SPEED RESET!" overlay (board-centred, fades out)
            if speed_reset_flash_timer > 0:
                a = 1.0 if speed_reset_flash_timer > 500 else speed_reset_flash_timer / 500
                sr_col = tuple(int(c * a) for c in (100, 255, 100))
                sr_t   = _font(22).render("SPEED  RESET!", True, sr_col)
                bsurf.blit(sr_t, (BOARD_WIDTH // 2 - sr_t.get_width() // 2, 38))

            # Hard-drop white flash
            if hd_flash_timer > 0:
                alpha = int(190 * hd_flash_timer / HD_FLASH_DURATION)
                fl = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT), pygame.SRCALPHA)
                fl.fill((255, 255, 255, alpha))
                bsurf.blit(fl, (0, 0))

            if state == CASCADING:
                h = (pygame.time.get_ticks() / 120) % 1.0
                rgb = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(h, 1.0, 1.0))
                cas_t = _font(30).render("CASCADE!", True, rgb)
                cx = BOARD_WIDTH // 2 - cas_t.get_width() // 2
                cy = BOARD_HEIGHT // 2 - cas_t.get_height() // 2
                pad = 8
                bg = pygame.Surface((cas_t.get_width() + pad * 2,
                                     cas_t.get_height() + pad * 2), pygame.SRCALPHA)
                bg.fill((0, 0, 0, 160))
                bsurf.blit(bg, (cx - pad, cy - pad))
                bsurf.blit(cas_t, (cx, cy))

            elif state == GAME_OVER:
                draw_game_over_overlay(bsurf, score)
            elif state == GAME_OVER_ANIM:
                go_anim.draw(bsurf)

            # Screen shake (quad only) — randomise offset each frame
            ox = oy = 0
            if shake_timer > 0:
                amt = max(1, int(SHAKE_INTENSITY * shake_timer / SHAKE_DURATION))
                ox  = random.randint(-amt, amt)
                oy  = random.randint(-amt, amt)

            screen.blit(bsurf, (ox, oy))

            draw_sidebar(screen, score, lines, level, next_piece, best,
                         hold_piece, hold_used,
                         speed_tier, next_speed_reset,
                         reset_bonus_mult, full_cascade_mode,
                         palette_phase,
                         popup_count, popup_timer)
            pygame.draw.rect(screen, BORDER_COLOR,
                             (0, 0, BOARD_WIDTH, BOARD_HEIGHT), 1)
            pygame.draw.line(screen, BORDER_COLOR,
                             (BOARD_WIDTH, 0), (BOARD_WIDTH, SCREEN_HEIGHT), 1)

            if state == PAUSED:
                draw_pause(screen, blink_on)

        elif state == ENTER_NAME:
            draw_name_entry(screen, initials, ini_cursor, blink_on,
                            score, lines, level)

        elif state == LEADERBOARD:
            draw_leaderboard(screen, lb_scores, lb_hi_name, lb_hi_score)

        elif state == SETTINGS:
            draw_settings(screen, music_vol_pct, sfx_vol_pct,
                          settings_row, music.is_muted(), current_scale,
                          ghost_opacity_pct)

        elif state == MUSIC_TEST:
            draw_music_test(screen, music_test_tier)

        # Scale the logical surface to the actual display window
        if current_scale == 1.0:
            display.blit(screen, (0, 0))
        else:
            pygame.transform.smoothscale(screen, display.get_size(), display)
        pygame.display.flip()


if __name__ == "__main__":
    main()
