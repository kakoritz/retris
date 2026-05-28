"""
app_state.py — application-shell state that persists across game sessions.

AppState is constructed once in main() and never reset between games.
It holds everything that belongs to the application shell rather than
a single game: display surfaces, audio volumes, DAS config, leaderboard
cache, animation handles, and the state-machine string constants.

Contrast with game_state.GameState, which is reset on every new game.
"""
import pygame
import config
from game_over_anim import GameOverAnim

# State machine string constants (imported here so callers can use app_state.PLAYING etc.)
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
CASCADING      = "cascading"
DEMO           = "demo"


class AppState:
    """Application-level state that survives across game sessions.

    Constructed once in main(); never reset between games. Holds display
    surfaces, UI state, DAS configuration, leaderboard data, and the
    game-over animation handle.
    """

    def __init__(self, display: pygame.Surface, screen: pygame.Surface,
                 current_scale: float) -> None:
        self.display       = display
        self.screen        = screen
        self.current_scale = current_scale

        self.state: str = MENU

        # ── audio / volume ────────────────────────────────────────────────────
        self.music_vol_pct:     int = 40
        self.sfx_vol_pct:       int = 100
        self.ghost_opacity_pct: int = config.get_ghost_opacity()

        # ── settings screen ───────────────────────────────────────────────────
        self.settings_row:          int = 0
        self.settings_return_state: str = MENU

        # ── game-over animation ───────────────────────────────────────────────
        self.go_anim:         GameOverAnim = GameOverAnim()
        self.post_anim_state: str          = GAME_OVER   # ENTER_NAME or GAME_OVER

        # ── DAS / ARR ─────────────────────────────────────────────────────────
        self.das_dir:     int  = 0
        self.das_timer:   int  = 0
        self.das_charged: bool = False
        self.keys_held:   set  = set()

        _preset             = config.get_das_preset()
        self.das_preset:    str = _preset
        self.das_delay:     int = config.DAS_SETTINGS[_preset][0]
        self.das_repeat:    int = config.DAS_SETTINGS[_preset][1]

        # ── UI timers ─────────────────────────────────────────────────────────
        self.blink_timer:       int   = 0
        self.blink_on:          bool  = True
        self.pre_pause_vol:     float = 0.0
        self.cascade_anim_timer: int  = 0
        self.cascade_col_unlock: int  = 0   # waterfall: columns >= this fall; counts down 9→0
        self.cascade_freefall:   bool = False  # True = level-up block-free-fall; False = coherent

        # ── music preview ─────────────────────────────────────────────────────
        self.music_test_tier: int = 1

        # ── name entry ────────────────────────────────────────────────────────
        self.initials:   list = ['A', 'A', 'A']
        self.ini_cursor: int  = 0

        # ── leaderboard ───────────────────────────────────────────────────────
        self.lb_scores:   list        = []
        self.lb_hi_name:  str | None  = None
        self.lb_hi_score: int | None  = None
        self.best:        int         = 0

        # ── odometer score display ────────────────────────────────────────────
        self.score_disp:        float = 0.0   # displayed value chasing gs.score
        self.score_disp_digits: list  = [0] * 8
        self.score_anim_from:   list  = [0] * 8   # digit value when animation began
        self.score_anim_offs:   list  = [0.0] * 8  # 1.0=just changed → 0.0=settled

        # ── demo mode ─────────────────────────────────────────────────────────
        self.demo_active:           bool = False
        self.demo_scenario_idx:     int  = 0
        self.demo_phase:            str  = 'setup'   # 'setup'|'fall'|'clearing'|'wait'
        self.demo_fall_timer:       int  = 0
        self.demo_wait_timer:       int  = 0
        self.demo_scenario_wait_ms: int  = 0
        self.demo_label:            str  = ''
        self.menu_idle_timer:       int  = 0          # ms since last key at menu

        # ── touch / Android ──────────────────────────────────────────────────
        self.touch_enabled: bool  = False
        self.touch_dw:      int   = 0       # display pixel width  (FINGER coord space)
        self.touch_dh:      int   = 0       # display pixel height
        self.touch_ox:      int   = 0       # letterbox x offset in display pixels
        self.touch_oy:      int   = 0       # letterbox y offset in display pixels
        self.touch_scale:   float = 1.0     # display→logical pixel scale factor

        # ── debug cheat sequences ─────────────────────────────────────────────
        self._cheat_seq: list = []   # 3-2-1 WOW trigger
        self._debug_seq: list = []   # b-u-g fake crash trigger

    def reset_das(self) -> None:
        """Clear DAS state — called when a new game starts or a piece locks."""
        self.das_dir     = 0
        self.das_timer   = 0
        self.das_charged = False
        self.keys_held.clear()
