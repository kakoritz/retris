# game_constants.py — gameplay-tuning constants extracted from main.py
# No Pygame dependency; safe to import in unit tests without a display.

VERSION = "1.11.2"

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
COLOR_CLEAR_BONUS  = 5000   # flat bonus for clearing a mono-color row

# ── T-spin scoring (base, before level multiplier) ───────────────────────────
TSPIN_SCORES      = {0: 400, 1: 800,  2: 1200, 3: 1600}
TSPIN_MINI_SCORES = {0: 100, 1: 200,  2: 400}

# ── combo bonus ───────────────────────────────────────────────────────────────
COMBO_BONUS_UNIT = 50

# ── 20G gravity ───────────────────────────────────────────────────────────────
GRAVITY_20G_LEVEL = 20

# ── placement score ───────────────────────────────────────────────────────────
PLACEMENT_SCORE = 10

# ── page-up/down in-game volume ───────────────────────────────────────────────
PAGE_VOL_STEP = 5   # % per keypress

# ── level-up overlay ──────────────────────────────────────────────────────────
LEVEL_POPUP_DURATION = 2800   # ms — "LEVEL N" overlay on the board

# ── next-piece box flash ─────────────────────────────────────────────────────
NEXT_FLASH_MS = 220   # ms — brief white outline on NEXT box when piece changes

# ── sidebar popup ─────────────────────────────────────────────────────────────
POPUP_DURATION    = 2000   # ms
SHAKE_DURATION    = 380    # ms  (quad clear only)
SHAKE_INTENSITY   = 5      # px
HD_FLASH_DURATION = 90     # ms  (hard drop impact)

# ── popup style table ─────────────────────────────────────────────────────────
POPUP_STYLES = {
    0:  ("!! W O W !!",      None,           32),
    1:  ("Nice!",            (100, 255, 120), 17),
    2:  ("Great!",           (255, 235,  60), 20),
    3:  ("Fantastic!",       (255, 150,  50), 20),
    4:  ("RETRIS!",           None,           24),
    5:  ("T-SPIN!",          (200, 100, 255), 22),
    6:  ("T-SPIN MINI",      (180,  80, 200), 17),
    7:  ("B2B RETRIS!",       None,           22),
    8:  ("B2B T-SPIN!",      (220, 130, 255), 22),
    9:  ("Wild!",            ( 80, 255, 180), 18),
    10: ("Woah!",            (255, 200,  50), 20),
    11: ("Crazy!",           (255,  80,  50), 22),
    12: ("INSANE!",          (255,  50, 255), 26),
    13: ("RETRIS×RETRIS!",    None,           28),
    14: ("GRAVITY  20G",     (255, 80,   0),  24),
    15: ("COLOR CLEAR!",     None,           28),
}

# ── T-spin corner detection ───────────────────────────────────────────────────
# Indices: 0=(TL) 1=(TR) 2=(BL) 3=(BR).
# "Point-side" corners sit on the same side as the T-bump.
_TSPIN_POINT = {
    0: (0, 1),   # state 0 (bump up)    → top corners
    1: (1, 3),   # state 1 (bump right) → right corners
    2: (2, 3),   # state 2 (bump down)  → bottom corners
    3: (0, 2),   # state 3 (bump left)  → left corners
}

# ── SRS wall-kick tables ──────────────────────────────────────────────────────
# Offsets are (dx, dy), x right / y down. Source: Tetris Guideline SRS.
_KICKS_JLSZT: dict = {
    (0, 1): [( 0, 0), (-1,  0), (-1, -1), (0,  2), (-1,  2)],
    (1, 0): [( 0, 0), ( 1,  0), ( 1,  1), (0, -2), ( 1, -2)],
    (1, 2): [( 0, 0), ( 1,  0), ( 1,  1), (0, -2), ( 1, -2)],
    (2, 1): [( 0, 0), (-1,  0), (-1, -1), (0,  2), (-1,  2)],
    (2, 3): [( 0, 0), ( 1,  0), ( 1, -1), (0,  2), ( 1,  2)],
    (3, 2): [( 0, 0), (-1,  0), (-1,  1), (0, -2), (-1, -2)],
    (3, 0): [( 0, 0), (-1,  0), (-1,  1), (0, -2), (-1, -2)],
    (0, 3): [( 0, 0), ( 1,  0), ( 1, -1), (0,  2), ( 1,  2)],
}

_KICKS_I: dict = {
    (0, 1): [( 0,  0), (-2,  0), ( 1,  0), (-2,  1), ( 1, -2)],
    (1, 0): [( 0,  0), ( 2,  0), (-1,  0), ( 2, -1), (-1,  2)],
    (1, 2): [( 0,  0), (-1,  0), ( 2,  0), (-1, -2), ( 2,  1)],
    (2, 1): [( 0,  0), ( 1,  0), (-2,  0), ( 1,  2), (-2, -1)],
    (2, 3): [( 0,  0), ( 2,  0), (-1,  0), ( 2, -1), (-1,  2)],
    (3, 2): [( 0,  0), (-2,  0), ( 1,  0), (-2,  1), ( 1, -2)],
    (3, 0): [( 0,  0), ( 1,  0), (-2,  0), ( 1,  2), (-2, -1)],
    (0, 3): [( 0,  0), (-1,  0), ( 2,  0), (-1, -2), ( 2,  1)],
}
