# game_state.py — per-session mutable state, reset on each new game
import pygame
from board import Board
from piece import Piece
from game_constants import LEVEL_POPUP_DURATION


class GameState:
    """All mutable state that belongs to a single game session.

    Call reset() to start a new game. Fields are set as instance attributes
    so every function that receives a GameState can read and write them
    without nonlocal declarations.
    """

    def reset(self) -> None:
        """Initialise (or reinitialise) all per-game variables."""

        # ── board & active piece ──────────────────────────────────────────────
        self.board          = Board()
        self.current        = Piece()
        self.piece_queue    = [Piece() for _ in range(5)]   # 5-deep lookahead

        # ── scoring & level ───────────────────────────────────────────────────
        self.score      = 0
        self.lines      = 0
        self.level      = 1
        self.fall_timer = 0

        # ── hold piece ────────────────────────────────────────────────────────
        self.hold_piece      = None
        self.hold_used       = False   # locked until current piece locks

        # ── lock delay ────────────────────────────────────────────────────────
        self.lock_timer      = 0
        self.lock_move_count = 0   # reset cap: max LOCK_MAX_MOVES resets per piece

        # ── popups & WOW ──────────────────────────────────────────────────────
        self.popup_count = 0
        self.popup_timer = 0
        self.wow_active  = False

        # ── Tetris Guideline mechanics ────────────────────────────────────────
        self.last_action = 'gravity'   # 'rotate'|'move'|'soft_drop'|'hard_drop'|'gravity'
        self.tspin_type  = None        # 'full', 'mini', or None — set in do_lock
        self.btb_active  = False       # back-to-back difficult-clear streak
        self.combo       = 0           # consecutive clears; resets on a piece with no clear
        self.combo_labels: list = []

        # ── speed / cascade ───────────────────────────────────────────────────
        self.speed_tier            = 1
        self.level_cascade_pending = False  # True → level-up forces cascade this clear
        self.cascade_level         = 0      # cascade pass count this lock
        self.first_clear_tetris    = False  # True if first clear this lock was Tetris
        self.broken_piece_ids: set = set()  # piece IDs that had cells in cleared rows

        # ── level-up overlay ─────────────────────────────────────────────────
        self.level_popup_timer  = 0               # ms remaining for "LEVEL N" overlay
        self.level_popup_num    = 0               # which level just reached
        self.level_popup_max    = LEVEL_POPUP_DURATION

        # ── animation timers ─────────────────────────────────────────────────
        self.next_flash_timer        = 0   # NEXT box white-flash on piece change

        # ── floating labels ───────────────────────────────────────────────────
        self.danger_bonuses: list = []   # ×2 labels for danger-zone clears
        self.score_deltas:   list = []   # +N score labels on line clears

        # ── line-clear animation state ────────────────────────────────────────
        self.clear_rows:      set  = set()
        self.clear_count:     int  = 0
        self.clear_timer:     int  = 0
        self.clear_flash_idx: int  = 0
        self.clear_cells:     list = []   # (col, row, color_id) for particle spawns

        self.color_clear_id       = None   # color_id if a mono-color row was cleared
        self.level_up_flash_timer = 0

        # ── end-of-game statistics ────────────────────────────────────────────
        self.stat_pieces:   int   = 0
        self.stat_tetrises: int   = 0
        self.stat_tspins:   int   = 0
        self.stat_combo:    int   = 0
        self.stat_start_ms: int   = pygame.time.get_ticks()
        self.stat_time:     float = 0.0

        # ── visual effects ────────────────────────────────────────────────────
        self.particles:      list = []
        self.shake_timer:    int  = 0
        self.hd_flash_timer: int  = 0   # white flash on hard drop impact
        self.danger:         bool = False
