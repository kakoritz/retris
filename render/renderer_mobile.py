"""
renderer_mobile.py — Android full-screen layout for RETRIS.

Canvas: 460 × 950 logical pixels  (scale 2.348 → 1080×2230 physical)

  y=0   ┌──────────────────────────────────────────┐
        │  Score/Level strip  (90 px) — big text   │
  y=90  ├──────────────────────────────────────────┤
        │  side panels │  board 330×660  │ panels  │
        │  (65px each) │  CELL=33        │         │
  y=750 ├──────────────────────────────────────────┤
        │  Info strip: NEXT pieces | HOLD  (100px) │
  y=850 ├──────────────────────────────────────────┤
        │  Context-sensitive button bar  (100 px)  │
  y=950 └──────────────────────────────────────────┘
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
    _LB_RANK_COLORS,
)
from game_constants import (
    FLASH_COLOR_NORM, FLASH_COLOR_QUAD,
    WOW_POPUP_DURATION, POPUP_DURATION, POPUP_STYLES,
)
import config as _config

# ── geometry ──────────────────────────────────────────────────────────────────
M_CELL     = 33
M_BOARD_W  = 10 * M_CELL            # 330
M_BOARD_H  = 20 * M_CELL            # 660
M_STATS_H  = 90
M_INFO_H   = 100
M_BTN_H    = 100
M_BOARD_X  = (SCREEN_WIDTH - M_BOARD_W) // 2   # 65
M_BOARD_Y  = M_STATS_H                          # 90
M_CANVAS_H = M_STATS_H + M_BOARD_H + M_INFO_H + M_BTN_H   # 950

_CELL_SCALE  = M_CELL / CELL_SIZE
_INFO_ZONE_Y = M_BOARD_Y + M_BOARD_H           # 750
_BTN_ZONE_Y  = _INFO_ZONE_Y + M_INFO_H         # 850

M_PAUSE_RECT = pygame.Rect(SCREEN_WIDTH - 46, 6, 40, M_STATS_H - 12)

# ── colours ───────────────────────────────────────────────────────────────────
_BG_STRIP   = (6,   6,  18)
_BTN_BG     = (10, 10,  26)
_PRESS_BG   = (35, 35,  65)
_BTN_BORDER = (55, 58, 105)
_DIV_COL    = (38, 38,  66)
_LBL_COL    = (85, 88, 135)
_HOLD_DIM   = 80

# ── navigation icons ──────────────────────────────────────────────────────────
_MOBILE_ICONS = {
    'up_nav': [
        [0,0,1,0,0],
        [0,1,1,1,0],
        [1,1,1,1,1],
        [0,0,1,0,0],
        [0,0,1,0,0],
    ],
    'down_nav': [
        [0,0,1,0,0],
        [0,0,1,0,0],
        [1,1,1,1,1],
        [0,1,1,1,0],
        [0,0,1,0,0],
    ],
    'left':   _TC_ICONS['left'],
    'right':  _TC_ICONS['right'],
    'down':   _TC_ICONS['down'],
    'drop':   _TC_ICONS['drop'],
    'hold':   _TC_ICONS['hold'],
    'rotate': _TC_ICONS['rotate'],
}

# ── button bar layouts ────────────────────────────────────────────────────────
# Each entry: (pygame_key, icon_key_or_None, color_id, label, special_type)
# special_type: None | 'select' | 'continue_flash' | 't_piece_menu'
_LAY_GAME = [
    (pygame.K_LEFT,   'left',     1, 'LEFT',   None),
    (pygame.K_DOWN,   'down',     4, 'DOWN',   None),
    (pygame.K_SPACE,  'drop',     6, 'DROP',   None),
    (pygame.K_c,      'hold',     2, 'HOLD',   None),
    (pygame.K_UP,     'rotate',   3, 'ROTATE', None),
    (pygame.K_RIGHT,  'right',    1, 'RIGHT',  None),
]
_LAY_MENU = [
    (pygame.K_UP,     'up_nav',   3, 'UP',     None),
    (pygame.K_RETURN, None,       7, 'SELECT', 'select'),
    (pygame.K_DOWN,   'down_nav', 4, 'DOWN',   None),
]
_LAY_PAUSE = [
    (pygame.K_UP,     'up_nav',   3, 'UP',     None),
    (pygame.K_RETURN, None,       7, 'SELECT', 'select'),
    (pygame.K_DOWN,   'down_nav', 4, 'DOWN',   None),
]
_LAY_NAME = [
    (pygame.K_UP,     'up_nav',   3, 'UP',     None),
    (pygame.K_LEFT,   'left',     1, 'LEFT',   None),
    (pygame.K_RETURN, None,       7, 'OK',     'select'),
    (pygame.K_RIGHT,  'right',    1, 'RIGHT',  None),
    (pygame.K_DOWN,   'down_nav', 4, 'DOWN',   None),
]
_LAY_CONTINUE = [
    (pygame.K_SPACE, None, 7, 'CONTINUE', 'continue_flash'),
]
_LAY_MENU_BTN = [
    (pygame.K_ESCAPE, None, 0, 'MENU', 't_piece_menu'),
]
_LAY_SETTINGS_NAV = [
    (pygame.K_UP,     'up_nav',   3, 'UP',   None),
    (pygame.K_DOWN,   'down_nav', 4, 'DOWN', None),
    (pygame.K_ESCAPE, None,       0, 'MENU', 't_piece_menu'),
]

_STATE_LAYOUTS = {
    'playing':        _LAY_GAME,
    'clearing':       _LAY_GAME,
    'cascading':      _LAY_GAME,
    'demo':           _LAY_MENU_BTN,   # T-piece MENU button exits demo
    'paused':         _LAY_PAUSE,
    'menu':           _LAY_MENU,
    'game_over_anim': _LAY_CONTINUE,
    'game_over':      _LAY_CONTINUE,
    'enter_name':     _LAY_NAME,
    'leaderboard':    _LAY_MENU_BTN,
    'settings':       _LAY_SETTINGS_NAV,
    'about':          _LAY_MENU_BTN,
    'controls':       _LAY_MENU_BTN,
    'music_test':     _LAY_MENU_BTN,
}


def _draw_menu_bg(surf):
    """Tetris-grid background for menu screens — visible but not distracting."""
    cell = 26
    line_col = (32, 32, 68)   # bright enough to see, dark enough to not distract
    for y in range(0, M_CANVAS_H, cell):
        pygame.draw.line(surf, line_col, (0, y), (SCREEN_WIDTH, y), 1)
    for x in range(0, SCREEN_WIDTH, cell):
        pygame.draw.line(surf, line_col, (x, 0), (x, M_CANVAS_H), 1)


def get_layout_keys(state: str) -> list:
    return [row[0] for row in _STATE_LAYOUTS.get(state, _LAY_MENU)]


# ── board ──────────────────────────────────────────────────────────────────────

def draw_mobile_board(surf, board, flash_rows=None, flash_on=False,
                      flash_quad=False, wow_on=False, palette_phase=0):
    theme = LEVEL_THEMES[palette_phase % len(LEVEL_THEMES)]
    # Brighten grid lines slightly for mobile visibility
    raw_gl = theme[1]
    grid_line = tuple(min(255, int(c * 1.6 + 18)) for c in raw_gl)
    surf.fill(grid_line)
    if wow_on and flash_on:
        h = (pygame.time.get_ticks() / 90) % 1.0
        r2, g2, b2 = colorsys.hsv_to_rgb(h, 1.0, 1.0)
        fc = (int(r2*255), int(g2*255), int(b2*255))
    elif flash_quad:
        fc = FLASH_COLOR_QUAD
    else:
        fc = FLASH_COLOR_NORM
    for gy, row in enumerate(board.grid):
        for gx, val in enumerate(row):
            px, py = gx*M_CELL, gy*M_CELL
            if (wow_on and flash_on) or (flash_rows and gy in flash_rows and flash_on):
                pygame.draw.rect(surf, fc, (px, py, M_CELL-1, M_CELL-1))
            elif val:
                surf.blit(get_block(val, M_CELL, palette_phase=palette_phase), (px, py))
            else:
                pygame.draw.rect(surf, theme[0], (px, py, M_CELL-1, M_CELL-1))


def draw_mobile_danger_line(surf):
    y     = 10 * M_CELL
    pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.016)
    gb    = int(20 + 30 * pulse)
    pygame.draw.line(surf, (255, gb, gb), (0, y), (M_BOARD_W-1, y), 2)
    glow = (int(255*0.28), int(gb*0.28), int(gb*0.28))
    pygame.draw.line(surf, glow, (0, y-1), (M_BOARD_W-1, y-1), 1)
    pygame.draw.line(surf, glow, (0, y+2), (M_BOARD_W-1, y+2), 1)


def draw_mobile_piece(surf, piece, palette_phase=0):
    for ri, row in enumerate(piece.shape):
        for ci, val in enumerate(row):
            if val:
                surf.blit(get_block(val, M_CELL, palette_phase=palette_phase),
                          ((piece.x+ci)*M_CELL, (piece.y+ri)*M_CELL))


def draw_mobile_ghost(surf, board, piece, opacity_pct=40, palette_phase=0):
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
                          ((piece.x+ci)*M_CELL, (gy+ri)*M_CELL))


# ── side panels ───────────────────────────────────────────────────────────────

def draw_mobile_side_margins(surf, palette_phase=0):
    theme = LEVEL_THEMES[palette_phase % len(LEVEL_THEMES)]
    gc    = theme[1]
    panel = tuple(max(0, min(255, int(_BTN_BG[i]*0.7 + gc[i]*0.15))) for i in range(3))
    for bx in (0, M_BOARD_X + M_BOARD_W):
        pygame.draw.rect(surf, panel, (bx, M_BOARD_Y, M_BOARD_X, M_BOARD_H))
        pygame.draw.rect(surf, panel, (bx, _INFO_ZONE_Y, M_BOARD_X, M_INFO_H))
    edge = tuple(min(255, c+40) for c in gc)
    pygame.draw.line(surf, edge, (M_BOARD_X-1, M_BOARD_Y),
                     (M_BOARD_X-1, M_BOARD_Y+M_BOARD_H-1), 1)
    pygame.draw.line(surf, edge, (M_BOARD_X+M_BOARD_W, M_BOARD_Y),
                     (M_BOARD_X+M_BOARD_W, M_BOARD_Y+M_BOARD_H-1), 1)


# ── popup ─────────────────────────────────────────────────────────────────────

def draw_mobile_popup(surf, count, timer):
    if timer <= 0 or count not in POPUP_STYLES:
        return
    text_str, base_color, base_size = POPUP_STYLES[count]
    is_wow   = (count in (0, 13, 15))
    duration = WOW_POPUP_DURATION if is_wow else POPUP_DURATION
    elapsed  = duration - timer
    if is_wow:
        y = M_BOARD_H//2 - 18 - int((elapsed/duration)*60)
    else:
        y = int(M_BOARD_H*0.62) - int((elapsed/POPUP_DURATION)*80)
    alpha = 1.0 if timer > 600 else timer/600
    size  = base_size + (5 if elapsed < 200 else 0)
    if base_color is None:
        h = (pygame.time.get_ticks() / (200 if is_wow else 450)) % 1.0
        r2, g2, b2 = colorsys.hsv_to_rgb(h, 1.0, 1.0)
        vivid = (int(r2*255), int(g2*255), int(b2*255))
    else:
        vivid = base_color
    color = tuple(int(c*alpha) for c in vivid)
    f     = _font(size)
    tw, th = f.size(text_str)
    pad_x, pad_y = (14,7) if is_wow else (10,4)
    bx = M_BOARD_W//2 - (tw+pad_x*2)//2
    bg = tuple(int(c*(0.30 if is_wow else 0.22)*alpha) for c in vivid)
    pygame.draw.rect(surf, bg, (bx, y-pad_y, tw+pad_x*2, th+pad_y*2), border_radius=6)
    surf.blit(f.render(text_str, True, tuple(int(c*0.25*alpha) for c in vivid)),
              (M_BOARD_W//2 - tw//2+2, y+2))
    surf.blit(f.render(text_str, True, color), (M_BOARD_W//2 - tw//2, y))


def draw_mobile_level_up(surf, level_num, timer, max_timer, palette_phase=0):
    if timer <= 0 or max_timer <= 0:
        return
    prog  = timer / max_timer
    alpha = max(0.0, min(1.0, min(prog, 1.0-prog)*4))
    theme = LEVEL_THEMES[palette_phase % len(LEVEL_THEMES)]
    bc    = tuple(min(255, int(c*4)) for c in theme[1])
    ov    = pygame.Surface((M_BOARD_W, M_BOARD_H), pygame.SRCALPHA)
    ov.fill((*BG_COLOR, int(190*alpha)))
    surf.blit(ov, (0, 0))
    txt = f"LEVEL {level_num}"
    f   = _font(38)
    tw, th = f.size(txt)
    cx, cy = M_BOARD_W//2, M_BOARD_H//2
    surf.blit(f.render(txt, True, tuple(int(c*0.3*alpha) for c in bc)),
              (cx-tw//2+3, cy-th//2+3))
    surf.blit(f.render(txt, True, tuple(int(c*alpha) for c in bc)),
              (cx-tw//2, cy-th//2))


# ── game-over overlay ─────────────────────────────────────────────────────────

def draw_mobile_game_over(surf, score, stat_pieces=0, stat_tetrises=0,
                          stat_tspins=0, stat_combo=0, stat_time=0.0):
    cx = M_BOARD_W // 2
    cy = M_BOARD_H // 2    # 330
    ov = pygame.Surface((M_BOARD_W, 275), pygame.SRCALPHA)
    ov.fill((0, 0, 0, 215))
    surf.blit(ov, (0, cy - 82))
    t = _font(30).render("GAME  OVER", True, (255, 55, 55))
    surf.blit(t, (cx - t.get_width()//2, cy - 76))
    t = _font(20).render(f"SCORE  {str(score).zfill(7)}", True, YELLOW)
    surf.blit(t, (cx - t.get_width()//2, cy - 38))
    mins, secs = divmod(int(stat_time), 60)
    sy = cy - 10
    for label, val in [("TIME", f"{mins}:{secs:02d}"),
                       ("PIECES", str(stat_pieces)),
                       ("RETRIS!", str(stat_tetrises)),
                       ("T-SPINS", str(stat_tspins)),
                       ("BEST COMBO", f"×{stat_combo}")]:
        tl = _font(12).render(label, True, BORDER_COLOR)
        tv = _font(13).render(val, True, (200, 220, 255))
        surf.blit(tl, (cx - 82, sy))
        surf.blit(tv, (cx + 16, sy))
        sy += 20
    hint = _font(11, bold=False).render(
        "tap  CONTINUE  to return to menu",
        True, tuple(c//2 for c in BORDER_COLOR))
    surf.blit(hint, (cx - hint.get_width()//2, cy + 114))


# ── pause overlay ─────────────────────────────────────────────────────────────

def draw_mobile_pause(surf, blink_on, pause_row=0):
    ov = pygame.Surface((SCREEN_WIDTH, M_CANVAS_H), pygame.SRCALPHA)
    ov.fill((0, 0, 0, 175))
    surf.blit(ov, (0, 0))
    board_cy = M_BOARD_Y + M_BOARD_H // 2   # 90 + 330 = 420

    # PAUSE pixel-art title
    word    = "PAUSE"
    total   = len(word) * 5 * _PAUSE_CELL + (len(word)-1) * 8
    start_x = (SCREEN_WIDTH - total) // 2
    top_y   = board_cy - 160
    for li, ch in enumerate(word):
        lx  = start_x + li * (5*_PAUSE_CELL + 8)
        col = _PAUSE_COLORS[li]
        g   = _PAUSE_GLYPHS[ch]
        for gy in range(5):
            for gx in range(5):
                if g[gy][gx]:
                    x = lx + gx * _PAUSE_CELL
                    y = top_y + gy * _PAUSE_CELL
                    pygame.draw.rect(surf, col, (x, y, _PAUSE_BLOCK, _PAUSE_BLOCK))
                    bright = tuple(min(255, c+90) for c in col)
                    dark   = tuple(max(0, c-60) for c in col)
                    pygame.draw.line(surf, bright, (x,y), (x+_PAUSE_BLOCK-1, y))
                    pygame.draw.line(surf, bright, (x,y), (x, y+_PAUSE_BLOCK-1))
                    pygame.draw.line(surf, dark,
                                     (x+_PAUSE_BLOCK-1, y),
                                     (x+_PAUSE_BLOCK-1, y+_PAUSE_BLOCK-1))
                    pygame.draw.line(surf, dark,
                                     (x, y+_PAUSE_BLOCK-1),
                                     (x+_PAUSE_BLOCK-1, y+_PAUSE_BLOCK-1))

    cx = SCREEN_WIDTH // 2
    items  = ["CONTINUE", "SETTINGS", "QUIT  TO  MENU"]
    item_y = [board_cy - 36, board_cy + 34, board_cy + 104]
    for i, (label, y) in enumerate(zip(items, item_y)):
        selected = (i == pause_row)
        size = 28 if selected else 22
        col  = WHITE if selected else (90, 90, 90)
        _draw_shadow_text(surf, label, size, cx, y, col, center_x=True)
        if selected and blink_on:
            ax = cx - _font(size).size(label)[0]//2 - 32
            _draw_shadow_text(surf, ">", size, ax, y, (255, 220, 0))

    pass   # no hint text on mobile — button bar is self-explanatory


# ── stats strip (top, 90 px) ──────────────────────────────────────────────────

def draw_mobile_stats(surf, score, lines, level, in_game=False):
    """Stats strip: LEVEL X   [SCORE]   LINES X — bold, horizontal, fills the strip."""
    pygame.draw.rect(surf, _BG_STRIP, (0, 0, SCREEN_WIDTH, M_STATS_H))
    pygame.draw.line(surf, _BTN_BORDER, (0, M_STATS_H-1), (SCREEN_WIDTH, M_STATS_H-1), 1)

    cy = M_STATS_H // 2   # 45

    def _centre_y(font_size):
        return cy - _font(font_size).get_height() // 2

    # LEVEL  X — left block
    lbl_l = _font(18).render("LEVEL", True, _LBL_COL)
    val_l = _font(38).render(str(level), True, BORDER_COLOR)
    surf.blit(lbl_l, (8, cy - lbl_l.get_height() // 2 - 12))
    surf.blit(val_l, (8, cy - val_l.get_height() // 2 + 6))

    pygame.draw.line(surf, _DIV_COL, (90, 8), (90, M_STATS_H-8), 1)

    # SCORE — centre, dominant yellow
    sc_txt = _font(36).render(str(score).zfill(8), True, YELLOW)
    sc_x   = 95
    surf.blit(_font(15).render("SCORE", True, _LBL_COL), (sc_x, cy - 24))
    surf.blit(sc_txt, (sc_x, cy - sc_txt.get_height() // 2 + 8))

    pygame.draw.line(surf, _DIV_COL, (360, 8), (360, M_STATS_H-8), 1)

    # LINES  X — right block
    lbl_r = _font(18).render("LINES", True, _LBL_COL)
    val_r = _font(38).render(str(lines), True, BORDER_COLOR)
    surf.blit(lbl_r, (364, cy - lbl_r.get_height() // 2 - 12))
    surf.blit(val_r, (364, cy - val_r.get_height() // 2 + 6))

    if in_game:
        r = M_PAUSE_RECT
        pygame.draw.rect(surf, _BTN_BG, r, border_radius=5)
        pygame.draw.rect(surf, _BTN_BORDER, r, 1, border_radius=5)
        t = _font(18).render("II", True, BORDER_COLOR)
        surf.blit(t, (r.centerx - t.get_width()//2, r.centery - t.get_height()//2))


# ── info strip (100 px, below board) ─────────────────────────────────────────

def _draw_mini_piece(surf, piece, cell, cx, cy, dimmed=False, palette_phase=0):
    if piece is None:
        return
    sh = piece.shape
    pc = max(len(r) for r in sh)
    pr = len(sh)
    ox = cx - pc*cell//2
    oy = cy - pr*cell//2
    for ri, row in enumerate(sh):
        for ci, v in enumerate(row):
            if v:
                blk = get_block(v, cell, palette_phase=palette_phase)
                if dimmed:
                    blk = blk.copy(); blk.set_alpha(_HOLD_DIM)
                surf.blit(blk, (ox+ci*cell, oy+ri*cell))


def draw_mobile_info_strip(surf, piece_queue, hold_piece=None,
                           hold_used=False, hold_has_piece=False,
                           palette_phase=0):
    zy = _INFO_ZONE_Y
    pygame.draw.rect(surf, _BG_STRIP, (0, zy, SCREEN_WIDTH, M_INFO_H))
    pygame.draw.line(surf, _BTN_BORDER, (0, zy), (SCREEN_WIDTH, zy), 1)
    cy = zy + M_INFO_H // 2

    # NEXT1 — prominent left box
    cell1 = 18
    box1  = pygame.Rect(M_BOARD_X + 2, zy+5, 90, M_INFO_H-10)
    pygame.draw.rect(surf, _BTN_BG, box1, border_radius=4)
    pygame.draw.rect(surf, _BTN_BORDER, box1, 1, border_radius=4)
    surf.blit(_font(9).render("NEXT", True, _LBL_COL), (box1.x+3, zy+6))
    _draw_mini_piece(surf, piece_queue[0] if piece_queue else None,
                     cell1, box1.centerx, cy+6, palette_phase=palette_phase)

    # NEXT2-4 — smaller
    cell2   = 12
    slot_w  = 58
    x_start = M_BOARD_X + 98
    for idx in range(3):
        p   = piece_queue[idx+1] if (idx+1) < len(piece_queue) else None
        scx = x_start + slot_w*idx + slot_w//2
        _draw_mini_piece(surf, p, cell2, scx, cy, palette_phase=palette_phase)
        if idx < 2:
            sx = x_start + slot_w*(idx+1)
            pygame.draw.line(surf, _DIV_COL, (sx, zy+14), (sx, zy+M_INFO_H-14), 1)

    # HOLD — right box
    box2 = pygame.Rect(SCREEN_WIDTH - M_BOARD_X - 92, zy+5, 90, M_INFO_H-10)
    if hold_has_piece:
        glow = 0.45 + 0.45*math.sin(pygame.time.get_ticks()/285.0)
        gc   = tuple(int(c*glow) for c in (80, 220, 255))
        pygame.draw.rect(surf, gc, box2.inflate(2,2), 2, border_radius=4)
    bc = tuple(max(c-80,0) for c in BORDER_COLOR) if hold_used else BORDER_COLOR
    pygame.draw.rect(surf, _BTN_BG, box2, border_radius=4)
    pygame.draw.rect(surf, bc, box2, 1, border_radius=4)
    surf.blit(_font(9).render("HOLD", True, _LBL_COL), (box2.x+3, zy+6))
    _draw_mini_piece(surf, hold_piece, cell1, box2.centerx, cy+6,
                     dimmed=hold_used, palette_phase=palette_phase)


# ── context-sensitive button bar ─────────────────────────────────────────────

def draw_mobile_touch_controls(surf, zone_y, zone_h, state='playing'):
    layout = _STATE_LAYOUTS.get(state, _LAY_MENU)
    n      = len(layout)
    btn_w  = SCREEN_WIDTH // n

    try:
        import logic.touch_controls as _tc
        pressed = set(_tc._held.values())
    except Exception:
        pressed = set()

    blink = (pygame.time.get_ticks() // 400) % 2 == 0

    pygame.draw.rect(surf, _BG_STRIP, (0, zone_y, SCREEN_WIDTH, zone_h))
    pygame.draw.line(surf, _BTN_BORDER, (0, zone_y), (SCREEN_WIDTH, zone_y), 1)

    for i, (key, icon_key, color_id, label, special) in enumerate(layout):
        x  = btn_w * i
        w  = btn_w if i < n-1 else SCREEN_WIDTH - btn_w*(n-1)
        cx = x + w // 2
        box = pygame.Rect(x+2, zone_y+3, w-4, zone_h-6)

        if special == 'continue_flash':
            bg = (50, 50, 90) if blink else (22, 22, 50)
            bc = (130, 130, 210) if blink else _BTN_BORDER
        else:
            bg = _PRESS_BG if i in pressed else _BTN_BG
            bc = (tuple(min(255,c+50) for c in _BTN_BORDER)
                  if i in pressed else _BTN_BORDER)

        pygame.draw.rect(surf, bg, box, border_radius=8)
        pygame.draw.rect(surf, bc, box, 2, border_radius=8)
        if i in pressed:
            pygame.draw.line(surf, (110,115,180), (x+8,zone_y+6), (x+w-8,zone_y+6), 1)

        if special in ('select', 'continue_flash'):
            sz  = 22 if special == 'select' else (26 if blink else 21)
            col = WHITE if special == 'select' else (
                  (255, 255, 200) if blink else (160, 160, 130))
            t   = _font(sz).render(label, True, col)
            surf.blit(t, (cx - t.get_width()//2,
                          zone_y + zone_h//2 - t.get_height()//2))

        elif special == 't_piece_menu':
            pc  = pygame.time.get_ticks() // 1500 % 7 + 1
            cll = max(7, zone_h // 9)
            blk = get_block(pc, cll*2)
            T   = [(0,1),(1,0),(1,1),(1,2)]
            ox2 = cx - 3*cll
            oy2 = zone_y + zone_h//2 - cll - 6
            for (r2, c2) in T:
                surf.blit(blk, (ox2+c2*cll*2, oy2+r2*cll*2))
            lbl_t = _font(max(8, zone_h//11)).render("MENU", True, _LBL_COL)
            surf.blit(lbl_t, (cx - lbl_t.get_width()//2,
                               zone_y + zone_h - lbl_t.get_height() - 5))

        elif icon_key is not None:
            cell = max(7, min(btn_w//7, zone_h//9))
            art  = _MOBILE_ICONS.get(icon_key) or _TC_ICONS.get(icon_key)
            if art:
                _draw_block_icon(surf, art, color_id, cell,
                                 cx, zone_y + int(zone_h*0.42))
            lsz = max(7, zone_h//13)
            lt  = _font(lsz).render(label, True, _LBL_COL)
            surf.blit(lt, (cx - lt.get_width()//2,
                           zone_y + zone_h - lsz*2 - 4))


# ── leaderboard ───────────────────────────────────────────────────────────────

def draw_mobile_leaderboard(surf, scores, hi_name=None, hi_score=None):
    surf.fill(BG_COLOR)
    _draw_menu_bg(surf)
    cx = SCREEN_WIDTH // 2
    content_h = M_CANVAS_H - M_BTN_H   # 850px

    # Large title
    _draw_shadow_text(surf, "HIGH  SCORES", 42, cx, 8, YELLOW, center_x=True)
    pygame.draw.line(surf, BORDER_COLOR, (10, 72), (SCREEN_WIDTH-10, 72), 2)

    # Column positions
    X_RANK  = 10
    X_NAME  = 56
    X_SCORE = 158
    X_LVL   = 360
    X_LINES = 414
    Y_HDR   = 80
    ROW_H   = (content_h - Y_HDR - 8) // 10  # ~76px per row

    for label, x in [("#", X_RANK), ("NAME", X_NAME), ("SCORE", X_SCORE),
                     ("LVL", X_LVL), ("LNS", X_LINES)]:
        surf.blit(_font(16, bold=False).render(label, True, BORDER_COLOR), (x, Y_HDR))
    pygame.draw.line(surf, BORDER_COLOR,
                     (10, Y_HDR+24), (SCREEN_WIDTH-10, Y_HDR+24), 1)

    for i in range(10):
        y      = Y_HDR + 28 + i * ROW_H
        e      = scores[i] if i < len(scores) else None
        is_new = bool(e and e["name"] == hi_name and e["score"] == hi_score)

        row_bg = (12, 12, 30) if i % 2 == 0 else _BG_STRIP
        pygame.draw.rect(surf, row_bg, (10, y, SCREEN_WIDTH-20, ROW_H-2))
        if is_new:
            hl = pygame.Surface((SCREEN_WIDTH-20, ROW_H-2), pygame.SRCALPHA)
            hl.fill((255, 220, 0, 30))
            surf.blit(hl, (10, y))

        # Row vertical centre
        ry = y + (ROW_H - 2) // 2 - 12

        rank_c = (_LB_RANK_COLORS[i] if i < 3 else
                  (WHITE if is_new else (170, 170, 170)))

        if e:
            _draw_shadow_text(surf, f"{i+1}", 22, X_RANK, ry, rank_c)
            _draw_shadow_text(surf, e["name"], 26, X_NAME, ry, rank_c)
            sc_col = YELLOW if is_new else (215, 215, 90)
            _draw_shadow_text(surf, str(e["score"]).zfill(7), 22, X_SCORE, ry, sc_col)
            _draw_shadow_text(surf, str(e["level"]), 20, X_LVL, ry,
                              (120,255,120) if is_new else (110,150,110))
            _draw_shadow_text(surf, str(e["lines"]), 20, X_LINES, ry,
                              (160,200,255) if is_new else (110,130,160))
        else:
            _draw_shadow_text(surf, f"{i+1}", 22, X_RANK, ry, (45, 45, 65))
            _draw_shadow_text(surf, "---", 22, X_NAME, ry, (45, 45, 65))
            _draw_shadow_text(surf, "-------", 20, X_SCORE, ry, (45, 45, 65))
            _draw_shadow_text(surf, "-", 20, X_LVL, ry, (45, 45, 65))
            _draw_shadow_text(surf, "-", 20, X_LINES, ry, (45, 45, 65))

        if i < 9:
            pygame.draw.line(surf, (28, 28, 48),
                             (10, y+ROW_H-1), (SCREEN_WIDTH-10, y+ROW_H-1), 1)


# ── mobile menu ───────────────────────────────────────────────────────────────

# Scattered piece positions: (shape_key, x, y, rotation_offset, opacity)
# Fixed positions that look natural across the 460×950 canvas
_SCATTER_PIECES = [
    ('I', 30,  80,  1, 35),
    ('O', 380, 130, 0, 30),
    ('T', 60,  240, 2, 28),
    ('S', 390, 320, 0, 32),
    ('Z', 20,  450, 1, 25),
    ('L', 350, 500, 3, 30),
    ('J', 80,  600, 0, 28),
    ('I', 300, 660, 0, 25),
    ('T', 40,  780, 1, 32),
    ('S', 370, 750, 1, 30),
]

# piece type → color_id
_PIECE_COLOR = {'I':1,'O':2,'T':3,'S':4,'Z':5,'J':6,'L':7}

# All piece shapes (4-rotation) for scatter rendering
_SCATTER_SHAPES = {
    'I': [[[1,1,1,1]], [[1],[1],[1],[1]]],
    'O': [[[2,2],[2,2]]],
    'T': [[[0,3,0],[3,3,3]], [[3,0],[3,3],[3,0]],
          [[3,3,3],[0,3,0]], [[0,3],[3,3],[0,3]]],
    'S': [[[0,4,4],[4,4,0]], [[4,0],[4,4],[0,4]]],
    'Z': [[[5,5,0],[0,5,5]], [[0,5],[5,5],[5,0]]],
    'J': [[[6,0,0],[6,6,6]], [[6,6],[6,0],[6,0]],
          [[6,6,6],[0,0,6]], [[0,6],[0,6],[6,6]]],
    'L': [[[0,0,7],[7,7,7]], [[7,0],[7,0],[7,7]],
          [[7,7,7],[7,0,0]], [[7,7],[0,7],[0,7]]],
}


def draw_mobile_menu(surf, blink_on, updater=None, menu_row=0):
    """Mobile menu: grid bg + scattered pieces, large centered text, no border."""
    from renderer import draw_retris_logo
    from game_constants import VERSION

    surf.fill(BG_COLOR)
    _draw_menu_bg(surf)
    cx = SCREEN_WIDTH // 2

    # ── scattered pieces background ──────────────────────────────────────────
    cell = 20
    for (pt, px, py, rot_idx, alpha) in _SCATTER_PIECES:
        shapes = _SCATTER_SHAPES[pt]
        shape  = shapes[rot_idx % len(shapes)]
        cid    = _PIECE_COLOR[pt]
        cols   = max(len(r) for r in shape)
        rows   = len(shape)
        ox     = px - cols * cell // 2
        oy     = py - rows * cell // 2
        for ri, row in enumerate(shape):
            for ci, v in enumerate(row):
                if v:
                    blk = get_block(cid, cell)
                    blk = blk.copy()
                    blk.set_alpha(alpha)
                    surf.blit(blk, (ox + ci * cell, oy + ri * cell))

    # ── RETRIS logo ───────────────────────────────────────────────────────────
    draw_retris_logo(surf, top_y=160)

    # ── menu items — large, Y-centred in bottom 2/3 ──────────────────────────
    items  = ["START  GAME", "LEADERBOARD", "SETTINGS"]
    item_y = [430, 510, 590]

    for i, (label, y) in enumerate(zip(items, item_y)):
        selected = (i == menu_row)
        color    = WHITE if selected else (75, 75, 75)
        _draw_shadow_text(surf, label, 44, cx, y, color, center_x=True)
        if selected and blink_on:
            ax = cx - _font(44).size(label)[0] // 2 - 36
            _draw_shadow_text(surf, ">", 44, ax, y, (255, 220, 0))

    # ── version string ────────────────────────────────────────────────────────
    ver_col = (55, 55, 55)
    ver_lbl = f"by kakoritz  •  v{VERSION}"
    if updater and updater.status == "available":
        ver_lbl = f"v{VERSION}  •  v{updater.latest_version} available!"
        ver_col = (255, 220, 0) if blink_on else (160, 140, 0)
    t = _font(12, bold=False).render(ver_lbl, True, ver_col)
    surf.blit(t, (cx - t.get_width() // 2, M_CANVAS_H - M_BTN_H - 18))


# ── mobile settings ───────────────────────────────────────────────────────────

# Tap-zone rects for mobile settings (logical canvas coords)
_MS_SLIDERS = {}   # populated at first draw
_MS_DAS_BTNS: list = []
_MS_CONTROLS_BTN = pygame.Rect(20, 730, 420, 60)

_DAS_LABELS  = ['SLOW', 'NORM', 'FAST', 'FASTER']
_DAS_PRESETS = ['slow', 'normal', 'fast', 'instant']


def _slider_row(surf, label, pct, y, row_h=90):
    """Draw a full-width labelled slider row. Returns the slider Rect."""
    cy = y + row_h // 2
    # Label
    surf.blit(_font(22).render(label, True, BORDER_COLOR), (20, y + 8))
    # Value
    pct_txt = _font(20).render(f"{pct}%", True, YELLOW)
    surf.blit(pct_txt, (SCREEN_WIDTH - 20 - pct_txt.get_width(), y + 10))
    # Slider track
    sx, sw, sh = 20, 420, 18
    sy = y + row_h - 32
    pygame.draw.rect(surf, (30, 30, 60), (sx, sy, sw, sh), border_radius=9)
    fill_w = max(0, int(sw * pct / 100))
    if fill_w > 4:
        pygame.draw.rect(surf, YELLOW, (sx, sy, fill_w, sh), border_radius=9)
    pygame.draw.rect(surf, _BTN_BORDER, (sx, sy, sw, sh), 1, border_radius=9)
    # Thumb
    thumb_x = sx + fill_w - 8
    pygame.draw.circle(surf, WHITE, (max(sx+9, thumb_x+8), sy+sh//2), 12)
    return pygame.Rect(sx, sy - 10, sw, sh + 20)


def draw_mobile_settings(surf, music_vol, sfx_vol, ghost_opacity,
                          das_preset, settings_row=0):
    global _MS_SLIDERS, _MS_DAS_BTNS
    surf.fill(BG_COLOR)
    _draw_menu_bg(surf)
    cx = SCREEN_WIDTH // 2

    _draw_shadow_text(surf, "SETTINGS", 38, cx, 20, YELLOW, center_x=True)
    pygame.draw.line(surf, _BTN_BORDER, (20, 72), (SCREEN_WIDTH-20, 72), 1)

    # Volume / opacity sliders
    _MS_SLIDERS['music'] = _slider_row(surf, "MUSIC  VOLUME", music_vol, 85)
    _MS_SLIDERS['sfx']   = _slider_row(surf, "SFX  VOLUME",   sfx_vol,  185)
    _MS_SLIDERS['ghost'] = _slider_row(surf, "GHOST  OPACITY", ghost_opacity, 285)

    pygame.draw.line(surf, _BTN_BORDER, (20, 388), (SCREEN_WIDTH-20, 388), 1)

    # DAS — 4 discrete option blocks
    surf.blit(_font(22).render("INPUT  SPEED", True, BORDER_COLOR), (20, 398))
    _MS_DAS_BTNS.clear()
    btn_w = (SCREEN_WIDTH - 40) // 4   # ~105px each
    for i, (key, lbl) in enumerate(zip(_DAS_PRESETS, _DAS_LABELS)):
        bx  = 20 + i * btn_w
        box = pygame.Rect(bx + 3, 430, btn_w - 6, 58)
        active = (key == das_preset)
        bg  = YELLOW if active else _BTN_BG
        tc  = BG_COLOR if active else (140, 140, 140)
        pygame.draw.rect(surf, bg, box, border_radius=8)
        pygame.draw.rect(surf, _BTN_BORDER, box, 1, border_radius=8)
        t = _font(20).render(lbl, True, tc)
        surf.blit(t, (box.centerx - t.get_width()//2,
                      box.centery - t.get_height()//2))
        _MS_DAS_BTNS.append((box, key))

    # DAS description
    d, r = _config.DAS_SETTINGS[das_preset]
    arr  = "instant" if r == 0 else f"{r} ms repeat"
    surf.blit(_font(14, bold=False).render(f"delay {d} ms  ·  {arr}", True, _LBL_COL),
              (20, 496))

    pygame.draw.line(surf, _BTN_BORDER, (20, 522), (SCREEN_WIDTH-20, 522), 1)

    # CONTROLS link
    ctrl_col = YELLOW if settings_row == 4 else BORDER_COLOR
    pygame.draw.rect(surf, _BTN_BG, _MS_CONTROLS_BTN, border_radius=8)
    pygame.draw.rect(surf, ctrl_col, _MS_CONTROLS_BTN, 1, border_radius=8)
    t = _font(24).render("VIEW  CONTROLS  →", True, ctrl_col)
    surf.blit(t, (_MS_CONTROLS_BTN.centerx - t.get_width()//2,
                  _MS_CONTROLS_BTN.centery - t.get_height()//2))


# ── mobile controls ───────────────────────────────────────────────────────────

_M_CTRL_TABLE = [
    ("LEFT  ◄",     "Move left  (hold = auto-repeat)"),
    ("DOWN  ▼",     "Soft drop"),
    ("DROP",        "Hard drop — instant lock"),
    ("HOLD",        "Swap hold piece"),
    ("ROTATE  ↻",   "Rotate clockwise"),
    ("RIGHT  ►",    "Move right  (hold = auto-repeat)"),
    ("II  (top)",   "Pause game"),
    ("SELECT",      "Confirm menu selection"),
    ("UP / DOWN",   "Navigate menus"),
    ("CONTINUE",    "Skip animation / return to menu"),
    ("MENU",        "Return to main menu from any screen"),
]


def draw_mobile_controls(surf):
    surf.fill(BG_COLOR)
    _draw_menu_bg(surf)
    cx = SCREEN_WIDTH // 2

    _draw_shadow_text(surf, "CONTROLS", 38, cx, 20, YELLOW, center_x=True)
    pygame.draw.line(surf, _BTN_BORDER, (16, 70), (SCREEN_WIDTH-16, 70), 1)

    content_h = M_CANVAS_H - M_BTN_H   # 850
    row_h     = (content_h - 82) // len(_M_CTRL_TABLE)   # dynamic

    for i, (btn, desc) in enumerate(_M_CTRL_TABLE):
        y      = 80 + i * row_h
        row_bg = (12, 12, 30) if i % 2 == 0 else _BG_STRIP
        pygame.draw.rect(surf, row_bg, (10, y, SCREEN_WIDTH-20, row_h-2))
        ry = y + (row_h - 2) // 2 - 10
        # Button name — yellow/bold, left
        _draw_shadow_text(surf, btn, 20, 16, ry, YELLOW)
        # Description — white, right half
        t = _font(16, bold=False).render(desc, True, (190, 190, 210))
        surf.blit(t, (SCREEN_WIDTH//2 - 10, ry + 2))
        if i < len(_M_CTRL_TABLE) - 1:
            pygame.draw.line(surf, (28, 28, 48),
                             (10, y+row_h-1), (SCREEN_WIDTH-10, y+row_h-1), 1)
