import colorsys
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

_MUSIC_END = pygame.USEREVENT + 1   # fired by mixer when a track finishes naturally

_INITIALS_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ "

# ── DAS (delayed auto-shift) ──────────────────────────────────────────────────
DAS_DELAY  = 170   # ms before auto-repeat starts
DAS_REPEAT = 50    # ms between repeated moves

# ── line-clear flash animation ────────────────────────────────────────────────
FLASH_MS    = {1: 85, 2: 80, 3: 75, 4: 68}   # ms per on/off phase
FLASH_TOTAL = {1: 2,  2: 4,  3: 6,  4: 10}   # phases per count
FLASH_COLOR_NORM = (255, 255, 255)
FLASH_COLOR_QUAD = (255, 215,   0)

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
    1: ("Nice!",       (100, 255, 120), 17),
    2: ("Great!",      (255, 235,  60), 20),
    3: ("Fantastic!",  (255, 150,  50), 20),
    4: ("TETRIS!",      None,           24),   # None = rainbow
}

_font_cache: dict = {}

def _font(size: int, bold: bool = True) -> pygame.font.Font:
    key = (size, bold)
    if key not in _font_cache:
        _font_cache[key] = pygame.font.SysFont("monospace", size, bold=bold)
    return _font_cache[key]


# ── rotation helper ───────────────────────────────────────────────────────────

def _try_rotate(board: Board, piece: Piece, rot: list) -> bool:
    for dx in (0, 1, -1):
        if board.is_valid(piece, dx=dx, shape=rot):
            piece.x += dx
            piece.shape = rot
            audio.play('rotate')
            return True
    return False


# ── board / piece drawing ─────────────────────────────────────────────────────

def draw_board(surf: pygame.Surface, board: Board,
               flash_rows: set | None = None,
               flash_on: bool = False,
               flash_quad: bool = False) -> None:
    fc = FLASH_COLOR_QUAD if flash_quad else FLASH_COLOR_NORM
    for gy, row in enumerate(board.grid):
        for gx, val in enumerate(row):
            px, py = gx * CELL_SIZE, gy * CELL_SIZE
            if flash_rows and gy in flash_rows and flash_on:
                pygame.draw.rect(surf, fc, (px, py, CELL_SIZE - 1, CELL_SIZE - 1))
            elif val:
                surf.blit(get_block(val), (px, py))
            else:
                pygame.draw.rect(surf, _BOARD_CELL,
                                 (px, py, CELL_SIZE - 1, CELL_SIZE - 1))


def draw_piece(surf: pygame.Surface, piece: Piece) -> None:
    for row_i, row in enumerate(piece.shape):
        for col_i, val in enumerate(row):
            if val:
                surf.blit(get_block(val),
                          ((piece.x + col_i) * CELL_SIZE,
                           (piece.y + row_i) * CELL_SIZE))


def draw_ghost(surf: pygame.Surface, board: Board, piece: Piece) -> None:
    gy = board.ghost_y(piece)
    if gy == piece.y:
        return
    for row_i, row in enumerate(piece.shape):
        for col_i, val in enumerate(row):
            if val:
                surf.blit(get_ghost(val),
                          ((piece.x + col_i) * CELL_SIZE,
                           (gy + row_i) * CELL_SIZE))


# ── popup ─────────────────────────────────────────────────────────────────────

def draw_popup(surf: pygame.Surface, count: int, timer: int) -> None:
    if timer <= 0 or count not in POPUP_STYLES:
        return
    text_str, base_color, base_size = POPUP_STYLES[count]
    elapsed = POPUP_DURATION - timer

    # Float upward over lifetime
    y = 440 - int((elapsed / POPUP_DURATION) * 22)

    # Fade out in last 500 ms
    alpha = 1.0 if timer > 500 else timer / 500

    # Pop: bigger font for the first 200 ms
    size = base_size + (5 if elapsed < 200 else 0)

    # Vivid color (before alpha applied)
    if base_color is None:   # rainbow for TETRIS
        h = (pygame.time.get_ticks() / 450) % 1.0
        r, g, b = colorsys.hsv_to_rgb(h, 0.9, 1.0)
        vivid = (int(r * 255), int(g * 255), int(b * 255))
    else:
        vivid = base_color

    color = tuple(int(c * alpha) for c in vivid)

    # Coloured background bar for count ≥ 2
    if count >= 2:
        f = _font(size)
        tw, th = f.size(text_str)
        pad_x, pad_y = 10, 4
        bw, bh = tw + pad_x * 2, th + pad_y * 2
        bx = BOARD_WIDTH + (SIDEBAR_WIDTH - bw) // 2
        bg = tuple(int(c * 0.22 * alpha) for c in vivid)
        pygame.draw.rect(surf, bg, (bx, y - pad_y, bw, bh), border_radius=4)

    t = _font(size).render(text_str, True, color)
    x = BOARD_WIDTH + (SIDEBAR_WIDTH - t.get_width()) // 2
    surf.blit(t, (x, y))


# ── sidebar ───────────────────────────────────────────────────────────────────

def draw_sidebar(surf: pygame.Surface, score: int, lines: int,
                 level: int, next_piece: Piece, best: int,
                 popup_count: int = 0, popup_timer: int = 0) -> None:
    sx = BOARD_WIDTH + 12

    def lbl(text, y): surf.blit(_font(13).render(text, True, BORDER_COLOR), (sx, y))
    def val(text, y): surf.blit(_font(19).render(text, True, YELLOW),       (sx, y))

    lbl("SCORE",  14); val(str(score).zfill(7),  30)
    lbl("BEST",   60); val(str(best).zfill(7),   76)
    lbl("LINES", 108); val(str(lines),           124)
    lbl("LEVEL", 155); val(str(level),           171)

    # NEXT piece box
    lbl("NEXT", 210)
    box_x, box_y = sx - 4, 228
    box_w, box_h = SIDEBAR_WIDTH - 16, 80
    pygame.draw.rect(surf, BORDER_COLOR, (box_x, box_y, box_w, box_h), 1)

    mini = CELL_SIZE - 6
    shape = next_piece.shape
    pc = max(len(r) for r in shape)
    pr = len(shape)
    ox = box_x + (box_w - pc * (mini + 1)) // 2
    oy = box_y + (box_h - pr * (mini + 1)) // 2
    for ri, row in enumerate(shape):
        for ci, v in enumerate(row):
            if v:
                surf.blit(get_block(v, mini),
                          (ox + ci * (mini + 1), oy + ri * (mini + 1)))

    # Controls hint
    for i, h in enumerate(["<>  move",
                            "^ cw   Z ccw",
                            "v  soft drop",
                            "SPC  hard drop",
                            "M  mute music"]):
        surf.blit(_font(11).render(h, True, BORDER_COLOR), (sx, 326 + i * 16))

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
                               "ESC = menu",
                               "L = leaderboard"]):
        t = _font(13, bold=False).render(hint, True, BORDER_COLOR)
        surf.blit(t, (cx - t.get_width() // 2, BOARD_HEIGHT // 2 + 36 + i * 16))


# ── settings ─────────────────────────────────────────────────────────────────

def draw_settings(surf: pygame.Surface, music_vol: int, sfx_vol: int,
                  settings_row: int, muted: bool, scale: float) -> None:
    surf.fill(BG_COLOR)
    cx = SCREEN_WIDTH // 2

    t = _font(30).render("SETTINGS", True, YELLOW)
    surf.blit(t, (cx - t.get_width() // 2, 32))
    pygame.draw.line(surf, BORDER_COLOR, (40, 76), (SCREEN_WIDTH - 40, 76), 1)

    def _vol_row(label, pct, y, selected):
        col = YELLOW if selected else BORDER_COLOR
        surf.blit(_font(14, bold=False).render(label, True, col), (60, y))
        bx, by, bw, bh = 60, y + 24, 200, 14
        pygame.draw.rect(surf, BORDER_COLOR, (bx, by, bw, bh), 1)
        fill_w = int(bw * pct / 100)
        if fill_w > 2:
            pygame.draw.rect(surf, col, (bx + 1, by + 1, fill_w - 2, bh - 2))
        surf.blit(_font(15).render(f"{pct}%", True, col), (bx + bw + 10, by - 2))
        if selected:
            surf.blit(_font(11, bold=False).render("< / >  adjust", True, YELLOW),
                      (bx + bw + 10, by + 14))

    _vol_row("MUSIC VOLUME", music_vol, 98,  settings_row == 0)
    _vol_row("SFX VOLUME",   sfx_vol,   178, settings_row == 1)

    # Scale row
    scale_col = YELLOW if settings_row == 2 else BORDER_COLOR
    surf.blit(_font(14, bold=False).render("DISPLAY SCALE", True, scale_col), (60, 258))
    for i, v in enumerate(config.VALID_SCALES):
        lbl   = f"{v:g}×"
        active = (v == scale)
        box_x = 60 + i * 80
        box_col = YELLOW if (active and settings_row == 2) else (
                  BORDER_COLOR if not active else (160, 160, 60))
        pygame.draw.rect(surf, box_col,
                         (box_x, 282, 68, 24),
                         0 if active else 1)
        tc = BG_COLOR if active else box_col
        surf.blit(_font(14).render(lbl, True, tc),
                  (box_x + 34 - _font(14).size(lbl)[0] // 2, 284))
    if settings_row == 2:
        surf.blit(_font(11, bold=False).render("< / >  change scale  (restarts window)",
                                               True, YELLOW), (60, 312))

    mute_col = (255, 80, 80) if muted else (80, 220, 100)
    t = _font(15).render(f"M  —  MUSIC : {'MUTED' if muted else 'ON'}", True, mute_col)
    surf.blit(t, (cx - t.get_width() // 2, 338))

    pygame.draw.line(surf, BORDER_COLOR, (40, 366), (SCREEN_WIDTH - 40, 366), 1)
    for i, hint in enumerate(["UP / DOWN  :  select row",
                               "LEFT / RIGHT  :  adjust",
                               "ENTER / ESC  :  back to menu"]):
        t = _font(13, bold=False).render(hint, True, BORDER_COLOR)
        surf.blit(t, (cx - t.get_width() // 2, 380 + i * 20))

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
    t = _font(15).render("PRESS  ANY  KEY  TO  RESUME", True, WHITE)
    surf.blit(t, (cx - t.get_width() // 2, 332))
    t = _font(12, bold=False).render("ESC  —  exit to menu", True, BORDER_COLOR)
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
        desc_col = (160, 160, 160) if not sel else (220, 220, 100)
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
        t = _font(17).render("PRESS  ENTER  TO  START", True, WHITE)
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


def main():
    pygame.init()
    pygame.mixer.music.set_endevent(_MUSIC_END)

    current_scale = config.get_scale()
    display = _make_display(current_scale)
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
    music_vol_pct  = 40    # 0-100
    sfx_vol_pct    = 100   # 0-100
    settings_row   = 0     # 0=music, 1=sfx, 2=scale

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

    def _spawn_next():
        nonlocal current, next_piece
        current    = next_piece
        next_piece = Piece()
        audio.play_spawn(current.color_id)
        return board.is_valid(current)

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

            # Music track finished — advance sequence
            if (event.type == _MUSIC_END
                    and state in (PLAYING, CLEARING, PAUSED)):
                music_game.on_music_end()

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
                continue

            # ── MENU ──────────────────────────────────────────────────────────
            if state == MENU:
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    board, current, next_piece, score, lines, level, fall_timer = new_game()
                    best  = highscore.best()
                    popup_count = popup_timer = 0
                    _reset_das()
                    audio.play_spawn(current.color_id)
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
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    pre_pause_vol = pygame.mixer.music.get_volume()
                    pygame.mixer.music.set_volume(max(0.0, pre_pause_vol * 0.10))
                    state = PAUSED
                elif event.key == pygame.K_LEFT:
                    keys_held.add(pygame.K_LEFT)
                    das_dir = -1; das_timer = 0; das_charged = False
                    if board.is_valid(current, dx=-1):
                        current.x -= 1
                        audio.play('move')
                elif event.key == pygame.K_RIGHT:
                    keys_held.add(pygame.K_RIGHT)
                    das_dir = 1; das_timer = 0; das_charged = False
                    if board.is_valid(current, dx=1):
                        current.x += 1
                        audio.play('move')
                elif event.key == pygame.K_DOWN:
                    if board.is_valid(current, dy=1):
                        current.y += 1
                elif event.key == pygame.K_UP:
                    if event.mod & pygame.KMOD_CTRL:
                        _try_rotate(board, current, current.rotated_ccw())
                    else:
                        _try_rotate(board, current, current.rotated_cw())
                elif event.key == pygame.K_z:
                    _try_rotate(board, current, current.rotated_ccw())
                elif event.key == pygame.K_SPACE:
                    hd_flash_timer = HD_FLASH_DURATION
                    while board.is_valid(current, dy=1):
                        current.y += 1
                    audio.play('hard_drop')
                    board.place(current)
                    _reset_das()
                    fall_timer = 0
                    full = board.full_rows()
                    if full:
                        clear_rows      = set(full)
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
                        if not _spawn_next():
                            _end_game()

            # ── GAME OVER ANIM (press any key to continue) ────────────────────
            elif state == GAME_OVER_ANIM:
                if go_anim.all_landed:
                    state = post_anim_state

            # ── PAUSED ────────────────────────────────────────────────────────
            elif state == PAUSED:
                if event.key == pygame.K_ESCAPE:
                    music_game.stop()
                    music.start_menu()
                    state = MENU
                else:
                    pygame.mixer.music.set_volume(pre_pause_vol)
                    state = PLAYING

            # ── GAME OVER ─────────────────────────────────────────────────────
            elif state == GAME_OVER:
                if event.key == pygame.K_r:
                    board, current, next_piece, score, lines, level, fall_timer = new_game()
                    popup_count = popup_timer = 0
                    _reset_das()
                    audio.play_spawn(current.color_id)
                    music_game.stop()
                    music_game.start_sequence()
                    state = PLAYING
                elif event.key == pygame.K_ESCAPE:
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
                    board, current, next_piece, score, lines, level, fall_timer = new_game()
                    popup_count = popup_timer = 0
                    _reset_das()
                    audio.play_spawn(current.color_id)
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
                    settings_row = (settings_row - 1) % 3
                elif event.key == pygame.K_DOWN:
                    settings_row = (settings_row + 1) % 3
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
                    else:
                        scales = config.VALID_SCALES
                        idx = scales.index(current_scale) if current_scale in scales else 0
                        idx = max(0, min(len(scales) - 1,
                                        idx + (1 if event.key == pygame.K_RIGHT else -1)))
                        new_scale = scales[idx]
                        if new_scale != current_scale:
                            current_scale = new_scale
                            config.set_scale(current_scale)
                            display = _make_display(current_scale)

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
                        audio.play('move')

        # ── danger detection → tier-1 tension music ──────────────────────────
        if state in (PLAYING, CLEARING):
            danger = any(any(row) for row in board.grid[:10])
            music_game.set_danger(danger)

        # ── gravity ───────────────────────────────────────────────────────────
        if state == PLAYING:
            fall_timer += dt
            if fall_timer >= fall_speed(level):
                fall_timer = 0
                if board.is_valid(current, dy=1):
                    current.y += 1
                else:
                    board.place(current)
                    audio.play('lock')
                    _reset_das()
                    full = board.full_rows()
                    if full:
                        clear_rows      = set(full)
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
                        if _spawn_next():
                            pass
                        else:
                            _end_game()

        # ── line-clear animation ──────────────────────────────────────────────
        elif state == CLEARING:
            clear_timer += dt
            fms = FLASH_MS.get(clear_count, 80)
            if clear_timer >= fms:
                clear_timer -= fms
                clear_flash_idx += 1
                if clear_flash_idx >= FLASH_TOTAL.get(clear_count, 2):
                    # animation done — score, clear, spawn
                    lines  += clear_count
                    score  += SCORE_TABLE.get(clear_count, 0) * (level + 1)
                    level   = lines // 10 + 1
                    best    = max(best, score)
                    board.clear_lines()
                    particles += spawn_particles(clear_cells, clear_count == 4)
                    if clear_count == 4:
                        shake_timer = SHAKE_DURATION
                    popup_count = clear_count
                    popup_timer = POPUP_DURATION
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
        particles      = update_particles(particles, dt)
        hd_flash_timer = max(0, hd_flash_timer - dt)
        shake_timer    = max(0, shake_timer    - dt)

        # ── draw ──────────────────────────────────────────────────────────────
        if state == MENU:
            draw_menu(screen, blink_on)

        elif state in (PLAYING, CLEARING, GAME_OVER, GAME_OVER_ANIM, PAUSED):
            screen.fill(BG_COLOR)

            # Board content draws to its own surface so shake + flash can offset it
            bsurf = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT))
            bsurf.fill(_BOARD_LINE)

            fr = clear_rows if state == CLEARING else None
            fo = (clear_flash_idx % 2 == 0) if state == CLEARING else False
            fq = (clear_count == 4) if state == CLEARING else False
            draw_board(bsurf, board, flash_rows=fr, flash_on=fo, flash_quad=fq)

            if state in (PLAYING, PAUSED):
                draw_ghost(bsurf, board, current)
                draw_piece(bsurf, current)

            draw_particles(bsurf, particles)

            # Hard-drop white flash
            if hd_flash_timer > 0:
                alpha = int(190 * hd_flash_timer / HD_FLASH_DURATION)
                fl = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT), pygame.SRCALPHA)
                fl.fill((255, 255, 255, alpha))
                bsurf.blit(fl, (0, 0))

            if state == GAME_OVER:
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
                          settings_row, music.is_muted(), current_scale)

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
