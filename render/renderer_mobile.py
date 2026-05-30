"""
renderer_mobile.py — Android full-screen layout for RETRIS.

Canvas: SCREEN_WIDTH × M_CANVAS_H  (460 × 965 logical pixels)

  y=0   ┌──────────────────────────────────────────────┐
        │  Score/Level strip  (M_STATS_H = 60 px)      │
  y=60  ├──────────────────────────────────────────────┤
        │                                              │
        │  Game board  400 × 800  (CELL=40)            │
        │  30 px side margins filled with accent color │
        │                                              │
  y=860 ├──────────────────────────────────────────────┤
        │  Info strip: NEXT pieces + HOLD (55 px)      │
  y=915 ├──────────────────────────────────────────────┤
        │  Touch controls  (M_BTN_H = 50 px, 6 btns)  │
  y=965 └──────────────────────────────────────────────┘

Scale from desktop coords (CELL_SIZE=30): multiply by _CELL_SCALE (4/3).
"""
import pygame
import math
import colorsys

from constants import (
    LEVEL_THEMES, SCREEN_WIDTH, CELL_SIZE, BOARD_WIDTH, BOARD_HEIGHT,
    BG_COLOR, BORDER_COLOR, WHITE, YELLOW,
)
from sprites import get_block, get_ghost
from renderer import (
    _font, _draw_shadow_text, _draw_block_icon, _TC_ICONS,
    _PAUSE_CELL, _PAUSE_BLOCK, _PAUSE_GLYPHS, _PAUSE_COLORS,
)
from game_constants import (
    FLASH_COLOR_NORM, FLASH_COLOR_QUAD,
    WOW_POPUP_DURATION, POPUP_DURATION, POPUP_STYLES,
)

# ── mobile geometry ────────────────────────────────────────────────────────────
M_CELL     = 40
M_BOARD_W  = 10 * M_CELL                            # 400
M_BOARD_H  = 20 * M_CELL                            # 800
M_STATS_H  = 60                                     # top score/level strip
M_INFO_H   = 55                                     # next-pieces + hold strip
M_BTN_H    = 50                                     # touch button zone
M_BOARD_X  = (SCREEN_WIDTH - M_BOARD_W) // 2       # 30 px side margins
M_BOARD_Y  = M_STATS_H                              # 60
M_CANVAS_H = M_STATS_H + M_BOARD_H + M_INFO_H + M_BTN_H  # 965

_CELL_SCALE   = M_CELL / CELL_SIZE                  # 4/3
_INFO_ZONE_Y  = M_BOARD_Y + M_BOARD_H              # 860
_BTN_ZONE_Y   = _INFO_ZONE_Y + M_INFO_H            # 915

# Pause button tap-target in the score strip (top-right corner)
M_PAUSE_RECT = pygame.Rect(SCREEN_WIDTH - 42, 4, 38, M_STATS_H - 8)

# ── colour palette ─────────────────────────────────────────────────────────────
_BG_STRIP    = (6,  6,  18)
_SIDE_COLOR  = (10, 8,  28)   # margin accent — slightly purple vs BG (15,15,35)
_BTN_BG      = (10, 10, 26)
_PRESS_BG    = (30, 30, 58)
_BTN_BORDER  = (55, 58, 105)
_DIV_COL     = (38, 38, 66)
_LBL_COL     = (85, 88, 135)
_HOLD_DIM    = 80

# ── touch button layout (6 buttons, no pause) ─────────────────────────────────
_M_N         = 6
_M_ICON_KEYS = ['left', 'down', 'drop', 'hold', 'rotate', 'right']
_M_COLOR_IDS = [1, 4, 6, 2, 3, 1]
_M_LABELS    = ['LEFT', 'DOWN', 'DROP', 'HOLD', 'ROTATE', 'RIGHT']


# ── board ──────────────────────────────────────────────────────────────────────

def draw_mobile_board(surf: pygame.Surface, board,
                      flash_rows=None, flash_on: bool = False,
                      flash_quad: bool = False, wow_on: bool = False,
                      palette_phase: int = 0) -> None:
    """Draw 10×20 grid onto surf (M_BOARD_W × M_BOARD_H, origin at (0,0))."""
    theme      = LEVEL_THEMES[palette_phase % len(LEVEL_THEMES)]
    board_cell = theme[0]
    grid_line  = theme[1]
    surf.fill(grid_line)

    if wow_on and flash_on:
        h = (pygame.time.get_ticks() / 90) % 1.0
        r, g, b = colorsys.hsv_to_rgb(h, 1.0, 1.0)
        fc = (int(r * 255), int(g * 255), int(b * 255))
    elif flash_quad:
        fc = FLASH_COLOR_QUAD
    else:
        fc = FLASH_COLOR_NORM

    for gy, row in enumerate(board.grid):
        for gx, val in enumerate(row):
            px = gx * M_CELL
            py = gy * M_CELL
            if (wow_on and flash_on) or (flash_rows and gy in flash_rows and flash_on):
                pygame.draw.rect(surf, fc, (px, py, M_CELL - 1, M_CELL - 1))
            elif val:
                surf.blit(get_block(val, M_CELL, palette_phase=palette_phase), (px, py))
            else:
                pygame.draw.rect(surf, board_cell, (px, py, M_CELL - 1, M_CELL - 1))


def draw_mobile_danger_line(surf: pygame.Surface) -> None:
    y     = 10 * M_CELL
    pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.016)
    gb    = int(20 + 30 * pulse)
    pygame.draw.line(surf, (255, gb, gb),             (0, y),     (M_BOARD_W - 1, y),     2)
    glow = (int(255 * 0.28), int(gb * 0.28), int(gb * 0.28))
    pygame.draw.line(surf, glow,                      (0, y - 1), (M_BOARD_W - 1, y - 1), 1)
    pygame.draw.line(surf, glow,                      (0, y + 2), (M_BOARD_W - 1, y + 2), 1)


def draw_mobile_piece(surf: pygame.Surface, piece, palette_phase: int = 0) -> None:
    for ri, row in enumerate(piece.shape):
        for ci, val in enumerate(row):
            if val:
                surf.blit(get_block(val, M_CELL, palette_phase=palette_phase),
                          ((piece.x + ci) * M_CELL, (piece.y + ri) * M_CELL))


def draw_mobile_ghost(surf: pygame.Surface, board, piece,
                      opacity_pct: int = 25, palette_phase: int = 0) -> None:
    if opacity_pct == 0:
        return
    gy = board.ghost_y(piece)
    if gy == piece.y:
        return
    for ri, row in enumerate(piece.shape):
        for ci, val in enumerate(row):
            if val:
                surf.blit(get_ghost(val, opacity_pct=opacity_pct,
                                    palette_phase=palette_phase, size=M_CELL),
                          ((piece.x + ci) * M_CELL, (gy + ri) * M_CELL))


# ── side margin fill ───────────────────────────────────────────────────────────

def draw_mobile_side_margins(surf: pygame.Surface, palette_phase: int = 0) -> None:
    """Fill the 30 px side margins around the board with a subtle accent color."""
    theme    = LEVEL_THEMES[palette_phase % len(LEVEL_THEMES)]
    # Blend SIDE_COLOR with a hint of the level theme grid color
    gc       = theme[1]
    blend    = tuple(int(_SIDE_COLOR[i] * 0.75 + gc[i] * 0.10) for i in range(3))
    lx, rx   = 0, M_BOARD_X + M_BOARD_W
    pygame.draw.rect(surf, blend, (lx, M_BOARD_Y, M_BOARD_X, M_BOARD_H))
    pygame.draw.rect(surf, blend, (rx, M_BOARD_Y, M_BOARD_X, M_BOARD_H))
    # Thin inner highlight at board edges
    edge = tuple(min(255, c + 30) for c in gc)
    pygame.draw.line(surf, edge, (M_BOARD_X - 1, M_BOARD_Y),
                     (M_BOARD_X - 1, M_BOARD_Y + M_BOARD_H - 1), 1)
    pygame.draw.line(surf, edge, (M_BOARD_X + M_BOARD_W, M_BOARD_Y),
                     (M_BOARD_X + M_BOARD_W, M_BOARD_Y + M_BOARD_H - 1), 1)


# ── popup (board-surface coords) ──────────────────────────────────────────────

def draw_mobile_popup(surf: pygame.Surface, count: int, timer: int) -> None:
    """Popup centred on M_BOARD_W / M_BOARD_H (drawn onto the board surface)."""
    if timer <= 0 or count not in POPUP_STYLES:
        return
    text_str, base_color, base_size = POPUP_STYLES[count]
    is_wow   = (count in (0, 13, 15))
    duration = WOW_POPUP_DURATION if is_wow else POPUP_DURATION
    elapsed  = duration - timer

    if is_wow:
        y = M_BOARD_H // 2 - 18 - int((elapsed / duration) * 60)
    else:
        y = int(M_BOARD_H * 0.62) - int((elapsed / POPUP_DURATION) * 80)

    alpha = 1.0 if timer > 600 else timer / 600
    size  = base_size + (5 if elapsed < 200 else 0)

    if base_color is None:
        h = (pygame.time.get_ticks() / (200 if is_wow else 450)) % 1.0
        r, g, b = colorsys.hsv_to_rgb(h, 1.0, 1.0)
        vivid = (int(r * 255), int(g * 255), int(b * 255))
    else:
        vivid = base_color

    color  = tuple(int(c * alpha) for c in vivid)
    f      = _font(size)
    tw, _th = f.size(text_str)
    pad_x, pad_y = (14, 7) if is_wow else (10, 4)
    bw = tw + pad_x * 2
    bx = M_BOARD_W // 2 - bw // 2
    bg = tuple(int(c * (0.30 if is_wow else 0.22) * alpha) for c in vivid)
    pygame.draw.rect(surf, bg, (bx, y - pad_y, bw, _th + pad_y * 2), border_radius=6)
    shadow = tuple(int(c * 0.25 * alpha) for c in vivid)
    t = f.render(text_str, True, shadow)
    surf.blit(t, (M_BOARD_W // 2 - tw // 2 + 2, y + 2))
    t = f.render(text_str, True, color)
    surf.blit(t, (M_BOARD_W // 2 - tw // 2, y))


# ── level-up overlay ───────────────────────────────────────────────────────────

def draw_mobile_level_up(surf: pygame.Surface, level_num: int,
                         timer: int, max_timer: int,
                         palette_phase: int = 0) -> None:
    if timer <= 0 or max_timer <= 0:
        return
    prog  = timer / max_timer
    alpha = max(0.0, min(1.0, min(prog, 1.0 - prog) * 4))
    theme = LEVEL_THEMES[palette_phase % len(LEVEL_THEMES)]
    gc    = theme[1]
    bc    = tuple(min(255, int(c * 4)) for c in gc)
    ov    = pygame.Surface((M_BOARD_W, M_BOARD_H), pygame.SRCALPHA)
    ov.fill((*BG_COLOR, int(190 * alpha)))
    surf.blit(ov, (0, 0))
    txt  = f"LEVEL {level_num}"
    f    = _font(38)
    tw, th = f.size(txt)
    cx   = M_BOARD_W // 2
    cy   = M_BOARD_H // 2
    shad = tuple(int(c * 0.3 * alpha) for c in bc)
    surf.blit(f.render(txt, True, shad), (cx - tw // 2 + 3, cy - th // 2 + 3))
    surf.blit(f.render(txt, True, tuple(int(c * alpha) for c in bc)),
              (cx - tw // 2, cy - th // 2))


# ── game-over overlay (mobile-board coords) ───────────────────────────────────

def draw_mobile_game_over(surf: pygame.Surface, score: int,
                          stat_pieces: int = 0, stat_tetrises: int = 0,
                          stat_tspins: int = 0, stat_combo: int = 0,
                          stat_time: float = 0.0) -> None:
    """Game-over stats overlay centred on M_BOARD_W × M_BOARD_H."""
    cx = M_BOARD_W // 2
    cy = M_BOARD_H // 2

    ov = pygame.Surface((M_BOARD_W, 260), pygame.SRCALPHA)
    ov.fill((0, 0, 0, 210))
    surf.blit(ov, (0, cy - 70))

    t = _font(28).render("GAME  OVER", True, (255, 60, 60))
    surf.blit(t, (cx - t.get_width() // 2, cy - 64))

    t = _font(18).render(f"SCORE  {str(score).zfill(7)}", True, YELLOW)
    surf.blit(t, (cx - t.get_width() // 2, cy - 28))

    mins, secs = divmod(int(stat_time), 60)
    stats = [
        ("TIME",       f"{mins}:{secs:02d}"),
        ("PIECES",     str(stat_pieces)),
        ("RETRIS!",    str(stat_tetrises)),
        ("T-SPINS",    str(stat_tspins)),
        ("BEST COMBO", f"×{stat_combo}"),
    ]
    sy = cy + 2
    for label, val in stats:
        tl = _font(12).render(label, True, BORDER_COLOR)
        tv = _font(13).render(val, True, (200, 220, 255))
        surf.blit(tl, (cx - 80, sy))
        surf.blit(tv, (cx + 18, sy))
        sy += 18

    for i, hint in enumerate(["SPACE / ESC = menu", "L = leaderboard"]):
        t = _font(12, bold=False).render(hint, True, BORDER_COLOR)
        surf.blit(t, (cx - t.get_width() // 2, sy + 6 + i * 16))


# ── pause overlay ─────────────────────────────────────────────────────────────

def draw_mobile_pause(surf: pygame.Surface, blink_on: bool,
                      pause_row: int = 0) -> None:
    """Full-canvas pause overlay, content centred on the mobile board Y axis."""
    ov = pygame.Surface((SCREEN_WIDTH, M_CANVAS_H), pygame.SRCALPHA)
    ov.fill((0, 0, 0, 175))
    surf.blit(ov, (0, 0))

    # Centre of board area in canvas coords
    board_cy = M_BOARD_Y + M_BOARD_H // 2   # = 60 + 400 = 460

    # PAUSE pixel-art title
    word   = "PAUSE"
    total  = len(word) * 5 * _PAUSE_CELL + (len(word) - 1) * 8
    start_x = (SCREEN_WIDTH - total) // 2
    top_y   = board_cy - 150   # centres the whole block around board_cy
    for li, ch in enumerate(word):
        lx  = start_x + li * (5 * _PAUSE_CELL + 8)
        col = _PAUSE_COLORS[li]
        glyph = _PAUSE_GLYPHS[ch]
        for gy in range(5):
            for gx in range(5):
                if glyph[gy][gx]:
                    x = lx + gx * _PAUSE_CELL
                    y = top_y + gy * _PAUSE_CELL
                    pygame.draw.rect(surf, col, (x, y, _PAUSE_BLOCK, _PAUSE_BLOCK))
                    bright = tuple(min(255, c + 90) for c in col)
                    pygame.draw.line(surf, bright, (x, y), (x + _PAUSE_BLOCK - 1, y))
                    pygame.draw.line(surf, bright, (x, y), (x, y + _PAUSE_BLOCK - 1))
                    dark = tuple(max(0, c - 60) for c in col)
                    pygame.draw.line(surf, dark,
                                     (x + _PAUSE_BLOCK - 1, y),
                                     (x + _PAUSE_BLOCK - 1, y + _PAUSE_BLOCK - 1))
                    pygame.draw.line(surf, dark,
                                     (x, y + _PAUSE_BLOCK - 1),
                                     (x + _PAUSE_BLOCK - 1, y + _PAUSE_BLOCK - 1))

    cx = SCREEN_WIDTH // 2
    items  = ["CONTINUE", "SETTINGS", "QUIT  TO  MENU"]
    item_y = [board_cy - 40, board_cy + 20, board_cy + 80]
    for i, (label, y) in enumerate(zip(items, item_y)):
        selected = (i == pause_row)
        color    = WHITE if selected else (90, 90, 90)
        _draw_shadow_text(surf, label, 22, cx, y, color, center_x=True)
        if selected and blink_on:
            ax = cx - _font(22).size(label)[0] // 2 - 28
            _draw_shadow_text(surf, ">", 22, ax, y, (255, 220, 0))

    hint = _font(11, bold=False).render(
        "UP / DOWN : select    ENTER : confirm", True, BORDER_COLOR)
    surf.blit(hint, (cx - hint.get_width() // 2, board_cy + 140))


# ── stats strip (top) ─────────────────────────────────────────────────────────

def draw_mobile_stats(surf: pygame.Surface,
                      score: int, lines: int, level: int,
                      in_game: bool = False) -> None:
    """Top strip: BIG score, level, lines, and pause button (in-game only)."""
    pygame.draw.rect(surf, _BG_STRIP, (0, 0, SCREEN_WIDTH, M_STATS_H))
    pygame.draw.line(surf, _BTN_BORDER, (0, M_STATS_H - 1), (SCREEN_WIDTH, M_STATS_H - 1), 1)

    cy = M_STATS_H // 2 + 2   # vertical center for numbers

    # ── LVL ──────────────────────────────────────────────────────────────────
    surf.blit(_font(9).render("LVL", True, _LBL_COL), (6, 4))
    lv = _font(26).render(str(level), True, BORDER_COLOR)
    surf.blit(lv, (6, 16))

    # ── LINES ────────────────────────────────────────────────────────────────
    surf.blit(_font(9).render("LNS", True, _LBL_COL), (76, 4))
    ln = _font(26).render(str(lines), True, BORDER_COLOR)
    surf.blit(ln, (76, 16))

    pygame.draw.line(surf, _DIV_COL, (148, 6), (148, M_STATS_H - 6), 1)

    # ── SCORE ────────────────────────────────────────────────────────────────
    surf.blit(_font(9).render("SCORE", True, _LBL_COL), (154, 4))
    sc = _font(24).render(str(score).zfill(8), True, YELLOW)
    surf.blit(sc, (154, 15))

    # ── PAUSE button (in-game only) ──────────────────────────────────────────
    if in_game:
        r = M_PAUSE_RECT
        pygame.draw.rect(surf, _BTN_BG, r, border_radius=4)
        pygame.draw.rect(surf, _BTN_BORDER, r, 1, border_radius=4)
        t = _font(16).render("II", True, BORDER_COLOR)
        surf.blit(t, (r.centerx - t.get_width() // 2, r.centery - t.get_height() // 2))


# ── info strip (below board) ──────────────────────────────────────────────────

def _draw_mini_piece(surf, piece, cell: int, cx: int, cy: int,
                     dimmed: bool = False, palette_phase: int = 0) -> None:
    if piece is None:
        return
    sh = piece.shape
    pc = max(len(r) for r in sh)
    pr = len(sh)
    ox = cx - pc * cell // 2
    oy = cy - pr * cell // 2
    for ri, row in enumerate(sh):
        for ci, v in enumerate(row):
            if v:
                blk = get_block(v, cell, palette_phase=palette_phase)
                if dimmed:
                    blk = blk.copy()
                    blk.set_alpha(_HOLD_DIM)
                surf.blit(blk, (ox + ci * cell, oy + ri * cell))


def draw_mobile_info_strip(surf: pygame.Surface,
                           piece_queue: list,
                           hold_piece=None,
                           hold_used: bool = False,
                           hold_has_piece: bool = False,
                           palette_phase: int = 0) -> None:
    """Info strip between board and buttons: NEXT pieces on left, HOLD on right."""
    zy = _INFO_ZONE_Y
    pygame.draw.rect(surf, _BG_STRIP, (0, zy, SCREEN_WIDTH, M_INFO_H))
    pygame.draw.line(surf, _BTN_BORDER, (0, zy),
                     (SCREEN_WIDTH, zy), 1)

    cy = zy + M_INFO_H // 2

    # ── NEXT1 (prominent, far left) ──────────────────────────────────────────
    cell1  = 14
    box1   = pygame.Rect(3, zy + 3, 54, M_INFO_H - 6)
    pygame.draw.rect(surf, _BTN_BG, box1, border_radius=3)
    pygame.draw.rect(surf, _BTN_BORDER, box1, 1, border_radius=3)
    surf.blit(_font(8).render("NXT", True, _LBL_COL), (5, zy + 4))
    _draw_mini_piece(surf, piece_queue[0] if piece_queue else None,
                     cell1, box1.centerx, cy, palette_phase=palette_phase)

    # ── NEXT2, NEXT3, NEXT4 (smaller, centre section) ────────────────────────
    cell2   = 10
    slot_w  = 80
    x_start = 60
    for idx in range(3):
        p   = piece_queue[idx + 1] if (idx + 1) < len(piece_queue) else None
        scx = x_start + slot_w * idx + slot_w // 2
        _draw_mini_piece(surf, p, cell2, scx, cy, palette_phase=palette_phase)
        if idx < 2:
            sx = x_start + slot_w * (idx + 1)
            pygame.draw.line(surf, _DIV_COL,
                             (sx, zy + 8), (sx, zy + M_INFO_H - 8), 1)

    # ── HOLD (far right) ─────────────────────────────────────────────────────
    box2   = pygame.Rect(SCREEN_WIDTH - 57, zy + 3, 54, M_INFO_H - 6)
    if hold_has_piece:
        t_ms = pygame.time.get_ticks()
        glow = 0.45 + 0.45 * math.sin(t_ms / 285.0)
        gc   = tuple(int(c * glow) for c in (80, 220, 255))
        pygame.draw.rect(surf, gc, box2.inflate(2, 2), 2, border_radius=3)
    border_col = tuple(max(c - 80, 0) for c in BORDER_COLOR) if hold_used else BORDER_COLOR
    pygame.draw.rect(surf, _BTN_BG, box2, border_radius=3)
    pygame.draw.rect(surf, border_col, box2, 1, border_radius=3)
    surf.blit(_font(8).render("HLD", True, _LBL_COL),
              (SCREEN_WIDTH - 55, zy + 4))
    _draw_mini_piece(surf, hold_piece, cell1, box2.centerx, cy,
                     dimmed=hold_used, palette_phase=palette_phase)


# ── touch controls ─────────────────────────────────────────────────────────────

def draw_mobile_touch_controls(surf: pygame.Surface,
                                zone_y: int, zone_h: int) -> None:
    """6 bordered touch buttons with press highlight."""
    btn_w = SCREEN_WIDTH // _M_N

    try:
        import logic.touch_controls as _tc
        pressed = set(_tc._held.values())
    except Exception:
        pressed = set()

    cell    = max(6, min(btn_w // 7, zone_h // 7))
    cy_icon = zone_y + int(zone_h * 0.42)
    lbl_sz  = max(7, zone_h // 8)
    cy_lbl  = zone_y + zone_h - lbl_sz - 3

    pygame.draw.rect(surf, _BG_STRIP, (0, zone_y, SCREEN_WIDTH, zone_h))
    pygame.draw.line(surf, _BTN_BORDER, (0, zone_y), (SCREEN_WIDTH, zone_y), 1)

    for i in range(_M_N):
        x  = btn_w * i
        w  = btn_w if i < _M_N - 1 else SCREEN_WIDTH - btn_w * (_M_N - 1)
        cx = x + w // 2
        box = pygame.Rect(x + 2, zone_y + 3, w - 4, zone_h - 6)

        bg = _PRESS_BG if i in pressed else _BTN_BG
        pygame.draw.rect(surf, bg, box, border_radius=6)
        bc = tuple(min(255, c + 50) for c in _BTN_BORDER) if i in pressed else _BTN_BORDER
        pygame.draw.rect(surf, bc, box, 1, border_radius=6)
        if i in pressed:
            pygame.draw.line(surf, (100, 105, 170),
                             (x + 6, zone_y + 5), (x + w - 6, zone_y + 5), 1)

        _draw_block_icon(surf, _TC_ICONS[_M_ICON_KEYS[i]], _M_COLOR_IDS[i],
                         cell, cx, cy_icon)
        lbl = _font(lbl_sz).render(_M_LABELS[i], True, _LBL_COL)
        surf.blit(lbl, (cx - lbl.get_width() // 2, cy_lbl))
