"""
GAME OVER animation: pixel-art block letters fall in chaos order.
OVER lands first (bottom row), then GAME falls on top (top row).
Each individual block falls independently with a random delay.
BOM impact sound fires when every block in a letter has landed.
"""
import random
import pygame
from constants import BOARD_WIDTH, BOARD_HEIGHT, COLORS

# ── pixel font (5×5 grid, 1 = filled block) ──────────────────────────────────

_GLYPHS = {
    'G': [[0,1,1,1,0],
          [1,0,0,0,0],
          [1,0,1,1,1],
          [1,0,0,0,1],
          [0,1,1,1,0]],
    'A': [[0,1,1,0,0],
          [1,0,0,1,0],
          [1,1,1,1,0],
          [1,0,0,1,0],
          [1,0,0,1,0]],
    'M': [[1,0,0,0,1],
          [1,1,0,1,1],
          [1,0,1,0,1],
          [1,0,0,0,1],
          [1,0,0,0,1]],
    'E': [[1,1,1,1,0],
          [1,0,0,0,0],
          [1,1,1,0,0],
          [1,0,0,0,0],
          [1,1,1,1,0]],
    'O': [[0,1,1,1,0],
          [1,0,0,0,1],
          [1,0,0,0,1],
          [1,0,0,0,1],
          [0,1,1,1,0]],
    'V': [[1,0,0,0,1],
          [1,0,0,0,1],
          [0,1,0,1,0],
          [0,1,0,1,0],
          [0,0,1,0,0]],
    'R': [[1,1,1,1,0],
          [1,0,0,0,1],
          [1,1,1,1,0],
          [1,0,1,0,0],
          [1,0,0,1,0]],
}

# Block cell size: 10 px block + 2 px gap = 12 px per cell
_BLOCK = 10
_CELL  = 12
_LGAP  = 8    # pixels between adjacent letters

_LETTER_W = 5 * _CELL   # 60 px

# Two rows: OVER (bottom), GAME (top)
_GAME_SPEC = [('G', 1), ('A', 2), ('M', 3), ('E', 4)]   # falls first (top row)
_OVER_SPEC = [('O', 5), ('V', 6), ('E', 7), ('R', 8)]   # falls second (bottom row)

# tetromino color IDs assigned to each bom_idx (1-8)
_LETTER_COLOR_ID = {1: 1, 2: 7, 3: 3, 4: 6, 5: 5, 6: 4, 7: 2, 8: 1}

GRAVITY = 2400   # px / s²
DAMPING = 0.28   # velocity kept on each bounce
MIN_VEL = 130    # below this on impact → stick

_FONT_CACHE: dict = {}

def _f(size: int, bold: bool = False) -> "pygame.font.Font":
    key = (size, bold)
    if key not in _FONT_CACHE:
        _FONT_CACHE[key] = pygame.font.SysFont("monospace", size, bold=bold)
    return _FONT_CACHE[key]


def _letter_start_x(letter_index: int) -> int:
    total = 4 * _LETTER_W + 3 * _LGAP
    return (BOARD_WIDTH - total) // 2 + letter_index * (_LETTER_W + _LGAP)


class GameOverAnim:

    def __init__(self) -> None:
        self._blocks:       list = []
        self._letter_done:  dict = {}   # bom_idx → bool
        self.all_landed:    bool = False
        self.overlay_alpha: int  = 0
        self._done_timer:   int  = 0
        self._build()

    def _build(self) -> None:
        GAME_TOP = 230   # y of top row of GAME letters
        OVER_TOP = 320   # y of top row of OVER letters

        # GAME falls first: each block gets a random delay in [0, 1800] ms
        for li, (ch, bom) in enumerate(_GAME_SPEC):
            self._add_letter(ch, bom, _letter_start_x(li), GAME_TOP,
                             delay_min=0, delay_range=1800)

        # OVER falls after: delay in [2600, 4400] ms
        for li, (ch, bom) in enumerate(_OVER_SPEC):
            self._add_letter(ch, bom, _letter_start_x(li), OVER_TOP,
                             delay_min=2600, delay_range=1800)

    def _add_letter(self, ch: str, bom_idx: int,
                    lx: int, top_y: int,
                    delay_min: int, delay_range: int) -> None:
        color = COLORS.get(_LETTER_COLOR_ID[bom_idx], (255, 255, 255))
        self._letter_done[bom_idx] = False

        for gy in range(5):
            for gx in range(5):
                if _GLYPHS[ch][gy][gx]:
                    tx = lx + gx * _CELL
                    ty = float(top_y + gy * _CELL)
                    self._blocks.append({
                        'tx':     tx,
                        'ty':     ty,
                        'x':      float(tx),
                        'y':      float(-_BLOCK - random.randint(10, 300)),
                        'vy':     0.0,
                        'delay':  random.randint(delay_min,
                                                 delay_min + delay_range),
                        'color':  color,
                        'bom':    bom_idx,
                        'landed': False,
                    })

    def reset(self) -> None:
        self._blocks      = []
        self._letter_done = {}
        self.all_landed   = False
        self.overlay_alpha = 0
        self._done_timer  = 0
        self._build()

    def update(self, dt: int) -> list:
        """Advance one frame. Returns list of BOM indices that just completed."""
        s = dt / 1000.0
        self.overlay_alpha = min(200, self.overlay_alpha + int(230 * s))

        for blk in self._blocks:
            if blk['landed']:
                continue
            blk['delay'] -= dt
            if blk['delay'] > 0:
                continue

            blk['vy'] += GRAVITY * s
            blk['y']  += blk['vy'] * s

            if blk['y'] >= blk['ty']:
                blk['y'] = blk['ty']
                if blk['vy'] > MIN_VEL:
                    blk['vy'] = -blk['vy'] * DAMPING
                else:
                    blk['vy']   = 0.0
                    blk['landed'] = True

        # Check which letters just finished
        just_bom: list = []
        for bom_idx, done in self._letter_done.items():
            if not done:
                letter_blocks = [b for b in self._blocks if b['bom'] == bom_idx]
                if letter_blocks and all(b['landed'] for b in letter_blocks):
                    self._letter_done[bom_idx] = True
                    just_bom.append(bom_idx)

        if not self.all_landed:
            if self._blocks and all(b['landed'] for b in self._blocks):
                self.all_landed = True
        if self.all_landed:
            self._done_timer += dt

        return just_bom

    def is_finished(self) -> bool:
        return self.all_landed and self._done_timer >= DONE_WAIT

    def draw(self, surf: pygame.Surface) -> None:
        if self.overlay_alpha > 0:
            ov = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT), pygame.SRCALPHA)
            ov.fill((0, 0, 0, self.overlay_alpha))
            surf.blit(ov, (0, 0))

        for blk in self._blocks:
            if blk['delay'] > 0:
                continue
            y = int(blk['y'])
            if y < -_BLOCK:
                continue
            x   = int(blk['x'])
            col = blk['color']

            # Main face
            pygame.draw.rect(surf, col, (x, y, _BLOCK, _BLOCK))
            # Top / left highlight
            bright = tuple(min(255, c + 90) for c in col)
            pygame.draw.line(surf, bright, (x, y), (x + _BLOCK - 1, y))
            pygame.draw.line(surf, bright, (x, y), (x, y + _BLOCK - 1))
            # Bottom / right shadow
            dark = tuple(max(0, c - 60) for c in col)
            pygame.draw.line(surf, dark,
                             (x + _BLOCK - 1, y),
                             (x + _BLOCK - 1, y + _BLOCK - 1))
            pygame.draw.line(surf, dark,
                             (x, y + _BLOCK - 1),
                             (x + _BLOCK - 1, y + _BLOCK - 1))

        if self.all_landed:
            t = _f(14).render("PRESS  ANY  KEY", True, (200, 200, 200))
            surf.blit(t, (BOARD_WIDTH // 2 - t.get_width() // 2,
                          BOARD_HEIGHT - 46))
