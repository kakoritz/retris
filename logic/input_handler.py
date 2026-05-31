"""
input_handler.py — pygame event dispatch and DAS (delayed auto-shift) auto-repeat.

handle_input(gs, app, dt) is called once per frame from main(). It:
  1. Drains the pygame event queue and routes each event to the correct state handler.
  2. Runs DAS auto-repeat at the end of the function (outside the event loop) so the
     repeat rate is consistent regardless of how many events arrived that frame.

DAS flow:
  - KEYDOWN LEFT/RIGHT: set das_dir, reset das_timer, fire one immediate move.
  - Every frame while das_dir != 0: accumulate das_timer.
  - After das_delay ms: das_charged = True.
  - With das_repeat == 0 (Instant): fire once per frame while charged.
  - With das_repeat > 0: fire every das_repeat ms while charged.
  - KEYUP: clear das_dir (or swap to opposite if the other key is still held).
"""
import sys
import pygame

import audio
import config
import highscore
import music
import music_game
import rotation
from constants import SCREEN_WIDTH, SCREEN_HEIGHT
from game_constants import GRAVITY_20G_LEVEL, PAGE_VOL_STEP, HD_FLASH_DURATION
from game_state import GameState
from app_state import (
    AppState,
    MENU, PLAYING, CLEARING, CASCADING, GAME_OVER, ENTER_NAME,
    LEADERBOARD, SETTINGS, GAME_OVER_ANIM, PAUSED, MUSIC_TEST, DEMO, ABOUT,
    CONTROLS,
)
from game_logic import (
    start_new_game, end_game, do_hold, do_lock,
    reset_lock, debug_clear_board,
)

MUSIC_END       = pygame.USEREVENT + 1
INITIALS_CHARS  = "ABCDEFGHIJKLMNOPQRSTUVWXYZ "

# ── board gesture tracker ─────────────────────────────────────────────────────
# Tap left half = move left | Tap right half = move right
# Swipe left/up = rotate CCW/CW | Swipe right = rotate CW | Swipe down = drop
# Tap bottom 10% = step down one cell
_board_gestures: dict = {}
_SWIPE_DROP_PX    = 110       # px down for hard drop
_SWIPE_ROT_PX     = 50        # px horizontal/vertical for rotate
_TAP_MAX_PX       = 28        # max movement for a tap
_BOTTOM_ZONE_PCT  = 0.90      # bottom 10% of board = step down
_game_start_ms    = 0         # timestamp of last new game start
_GAME_GRACE_MS    = 500       # ignore gestures for 500ms after game starts
_click_grace_ms   = 0         # ignore _handle_click for 250ms after state change
_CLICK_GRACE_MS   = 250
_DOUBLE_TAP_MS    = 300
_ROTATE_EXPIRE_MS = 450
_last_tap_ms      = 0
_rotate_mode      = False
_rotate_last_ms   = 0


def _post_key(evt_type: int, key: int) -> None:
    pygame.event.post(
        pygame.event.Event(evt_type, key=key, mod=0, unicode='', scancode=0))


def _handle_board_gesture(event, app) -> bool:
    """Board gestures: tap=rotate, swipe L/R=move, swipe down=drop."""
    if not getattr(app, 'touch_enabled', False):
        return False
    if app.state not in ('playing', 'clearing', 'cascading', 'practice'):
        return False

    try:
        from renderer_mobile import M_BOARD_X, M_BOARD_W, M_BOARD_Y, _INFO_ZONE_Y
    except ImportError:
        return False

    lx = (event.x * app.touch_dw - app.touch_ox) / app.touch_scale
    ly = (event.y * app.touch_dh - app.touch_oy) / app.touch_scale

    in_board = (M_BOARD_X <= lx <= M_BOARD_X + M_BOARD_W and
                M_BOARD_Y  <= ly <= _INFO_ZONE_Y)

    # Grace period: ignore board gestures right after a new game starts
    if pygame.time.get_ticks() - _game_start_ms < _GAME_GRACE_MS:
        return False

    if event.type == pygame.FINGERDOWN:
        if in_board:
            _board_gestures[event.finger_id] = (lx, ly, None)
        return False

    elif event.type == pygame.FINGERMOTION:
        if event.finger_id not in _board_gestures:
            return False
        sx, sy, fired = _board_gestures[event.finger_id]
        if fired:
            return False
        dx = lx - sx
        dy = ly - sy
        adx, ady = abs(dx), abs(dy)
        # Swipe down → hard drop
        if dy > _SWIPE_DROP_PX and ady > adx * 1.4:
            _post_key(pygame.KEYDOWN, pygame.K_SPACE)
            _board_gestures[event.finger_id] = (sx, sy, 'drop')
            return True
        # Swipe left → rotate CCW | Swipe right → rotate CW
        if adx > _SWIPE_ROT_PX and adx > ady * 1.3:
            key = pygame.K_UP if dx > 0 else pygame.K_z
            _post_key(pygame.KEYDOWN, key)
            _board_gestures[event.finger_id] = (sx, sy, 'rotate')
            return True
        # Swipe up → rotate CW
        if dy < -_SWIPE_ROT_PX and ady > adx * 1.3:
            _post_key(pygame.KEYDOWN, pygame.K_UP)
            _board_gestures[event.finger_id] = (sx, sy, 'rotate')
            return True

    elif event.type == pygame.FINGERUP:
        if event.finger_id not in _board_gestures:
            return False
        sx, sy, fired = _board_gestures.pop(event.finger_id)
        if fired:
            return False
        dx, dy = abs(lx - sx), abs(ly - sy)
        if dx < _TAP_MAX_PX and dy < _TAP_MAX_PX:
            board_h  = _INFO_ZONE_Y - M_BOARD_Y
            rel_y    = ly - M_BOARD_Y
            board_cx = M_BOARD_X + M_BOARD_W // 2

            if rel_y > board_h * _BOTTOM_ZONE_PCT:
                # Bottom 10% → step down one cell
                _post_key(pygame.KEYDOWN, pygame.K_DOWN)
                _post_key(pygame.KEYUP,   pygame.K_DOWN)
            else:
                # Tap left half → move left | tap right half → move right
                key = pygame.K_RIGHT if lx >= board_cx else pygame.K_LEFT
                _post_key(pygame.KEYDOWN, key)
                _post_key(pygame.KEYUP,   key)
            return True

    return False


def _resize_display(scale: float) -> pygame.Surface:
    w = int(SCREEN_WIDTH  * scale)
    h = int(SCREEN_HEIGHT * scale)
    return pygame.display.set_mode((w, h))


def _set_click_grace():
    """Call after any state-changing tap to prevent FINGERUP firing on new state."""
    global _click_grace_ms
    _click_grace_ms = pygame.time.get_ticks()


def _handle_click(lx: float, ly: float, gs, app: AppState) -> bool:
    """Handle a tap/click at logical pixel (lx, ly). Returns True if consumed."""
    if pygame.time.get_ticks() - _click_grace_ms < _CLICK_GRACE_MS:
        return False   # grace period — ignore spurious FINGERDOWN after state change
    from renderer import (MENU_START_RECT, MENU_LB_RECT, MENU_SETTINGS_ITEM_RECT,
                          MENU_ABOUT_RECT, INGAME_GEAR_RECT,
                          PAUSE_CONTINUE_RECT, PAUSE_SETTINGS_RECT, PAUSE_QUIT_RECT,
                          BACK_RECT, ABOUT_GITHUB_RECT)
    pt = (int(lx), int(ly))

    if app.state == MENU:
        app.menu_idle_timer = 0

        # Mobile: large tap zones for each menu item (font-52, item_y=400/490/580)
        _mobile_menu = getattr(app, 'touch_enabled', False)
        if _mobile_menu:
            import pygame as _pg
            _cx = SCREEN_WIDTH // 2
            _iw = 420   # generous tap width
            _ih = 70    # generous tap height
            _m_start = _pg.Rect(_cx - _iw//2, 395, _iw, _ih)
            _m_lb    = _pg.Rect(_cx - _iw//2, 485, _iw, _ih)
            _m_set   = _pg.Rect(_cx - _iw//2, 575, _iw, _ih)
        else:
            _m_start = MENU_START_RECT
            _m_lb    = MENU_LB_RECT
            _m_set   = MENU_SETTINGS_ITEM_RECT

        if _m_start.collidepoint(pt):
            global _game_start_ms
            app.menu_row = 0
            start_new_game(gs, app)
            app.best = highscore.best()
            music.fadeout(400)
            music_game.start_sequence()
            app.state = PLAYING
            _game_start_ms = pygame.time.get_ticks()
            _set_click_grace()
            return True
        if _m_lb.collidepoint(pt):
            app.menu_row   = 1
            app.lb_scores  = highscore.load()
            app.lb_hi_name = app.lb_hi_score = None
            app.state      = LEADERBOARD
            return True
        if _m_set.collidepoint(pt):
            app.menu_row              = 2
            app.settings_row          = 0
            app.settings_return_state = MENU
            app.state = SETTINGS
            return True
        if MENU_ABOUT_RECT.collidepoint(pt):
            app.state = ABOUT
            return True

    elif app.state in (PLAYING, CLEARING, CASCADING):
        # Hold box tap — fires hold action directly
        if getattr(app, 'touch_enabled', False):
            try:
                from renderer_mobile import M_HOLD_BOX_RECT
                if M_HOLD_BOX_RECT.collidepoint(pt):
                    pygame.event.post(
                        pygame.event.Event(pygame.KEYDOWN,
                                           key=pygame.K_c, mod=0,
                                           unicode='', scancode=0))
                    return True
            except ImportError:
                pass

        should_pause = INGAME_GEAR_RECT.collidepoint(pt)
        if not should_pause and getattr(app, 'touch_enabled', False):
            try:
                from renderer_mobile import M_PAUSE_RECT
                should_pause = M_PAUSE_RECT.collidepoint(pt)
            except ImportError:
                pass
        if should_pause:
            app.pre_pause_vol = pygame.mixer.music.get_volume()
            pygame.mixer.music.set_volume(max(0.0, app.pre_pause_vol * 0.10))
            app.pause_row = 0
            app.state = PAUSED
            return True

    elif app.state == GAME_OVER_ANIM:
        # Tap anywhere to skip the falling-block animation
        app.state = app.post_anim_state
        return True

    elif app.state == GAME_OVER:
        music_game.stop()
        music.start_menu()
        app.state = MENU; _set_click_grace()
        return True

    elif app.state == PAUSED:
        # Mobile: tap directly on pause menu items
        if getattr(app, 'touch_enabled', False):
            try:
                from renderer_mobile import M_PAUSE_ITEM_RECTS as _MPIR
                if _MPIR[0].collidepoint(pt):   # CONTINUE
                    pygame.mixer.music.set_volume(app.pre_pause_vol)
                    app.state = PLAYING; _set_click_grace()
                    return True
                if _MPIR[1].collidepoint(pt):   # SETTINGS
                    pygame.mixer.music.set_volume(app.pre_pause_vol)
                    app.settings_row          = 0
                    app.settings_return_state = PAUSED
                    app.state = SETTINGS; _set_click_grace()
                    return True
                if _MPIR[2].collidepoint(pt):   # QUIT TO MENU
                    music_game.stop()
                    music.start_menu()
                    app.state = MENU; _set_click_grace()
                    return True
            except (ImportError, Exception):
                pass
            return False   # mobile: never fall through to desktop pause rects
        # Desktop fallback only
        if INGAME_GEAR_RECT.collidepoint(pt) or PAUSE_CONTINUE_RECT.collidepoint(pt):
            pygame.mixer.music.set_volume(app.pre_pause_vol)
            app.state = PLAYING
            return True
        if PAUSE_SETTINGS_RECT.collidepoint(pt):
            pygame.mixer.music.set_volume(app.pre_pause_vol)
            app.settings_row          = 0
            app.settings_return_state = PAUSED
            app.state = SETTINGS
            return True
        if PAUSE_QUIT_RECT.collidepoint(pt):
            music_game.stop()
            music.start_menu()
            app.state = MENU
            return True

    elif app.state == ABOUT:
        if ABOUT_GITHUB_RECT.collidepoint(pt):
            import webbrowser
            webbrowser.open("https://github.com/kakoritz/retris")
            return True
        if BACK_RECT.collidepoint(pt):
            app.state = MENU
            return True

    elif app.state == LEADERBOARD:
        if not getattr(app, 'touch_enabled', False) and BACK_RECT.collidepoint(pt):
            music_game.stop()
            music.start_menu()
            app.state = MENU
            return True

    elif app.state == SETTINGS:
        # Desktop back button
        if BACK_RECT.collidepoint(pt):
            if app.settings_return_state == PAUSED:
                app.pre_pause_vol = app.music_vol_pct / 100
                pygame.mixer.music.set_volume(max(0.0, app.pre_pause_vol * 0.10))
                app.state = PAUSED
            else:
                app.state = MENU
            return True
        # Mobile: tap on sliders / DAS buttons / controls link
        if getattr(app, 'touch_enabled', False):
            try:
                from renderer_mobile import _MS_SLIDERS, _MS_DAS_BTNS, _MS_CONTROLS_BTN
                import config as _cfg
                # Slider taps
                for key, rect in _MS_SLIDERS.items():
                    if rect.collidepoint(pt):
                        pct = max(0, min(100, int((lx - rect.x) / rect.width * 100)))
                        if key == 'music':
                            app.music_vol_pct = pct
                            music_game.set_volume(pct / 100)
                        elif key == 'sfx':
                            app.sfx_vol_pct = pct
                        elif key == 'ghost':
                            app.ghost_opacity_pct = pct
                            _cfg.set_ghost_opacity(pct)
                        return True
                # DAS buttons
                for box, preset_key in _MS_DAS_BTNS:
                    if box.collidepoint(pt):
                        app.das_preset = preset_key
                        d, r = _cfg.DAS_SETTINGS[preset_key]
                        app.das_delay  = d
                        app.das_repeat = r
                        _cfg.set_das_preset(preset_key)
                        return True
                # CONTROLS link
                if _MS_CONTROLS_BTN.collidepoint(pt):
                    app.state = CONTROLS
                    return True
            except (ImportError, Exception):
                pass

    elif app.state == CONTROLS:
        if BACK_RECT.collidepoint(pt):
            app.state = SETTINGS
            return True
        if getattr(app, 'touch_enabled', False):
            try:
                from renderer_mobile import M_PRACTICE_BTN
                if M_PRACTICE_BTN.collidepoint(pt):
                    start_new_game(gs, app)
                    app.state    = 'practice'
                    app._practice_timer = 0
                    return True
            except (ImportError, Exception):
                pass

    elif app.state == 'practice':
        # K_ESCAPE (T-piece MENU button) exits practice → CONTROLS
        pass   # handled by keyboard ESC block below

    return False


def handle_input(gs: GameState, app: AppState, dt: int) -> None:
    """Process all pending pygame events and run DAS auto-repeat."""
    global _rotate_mode, _rotate_last_ms
    # Expire rotate mode if no tap for a while
    if _rotate_mode and (pygame.time.get_ticks() - _rotate_last_ms) > _ROTATE_EXPIRE_MS:
        _rotate_mode = False

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit(); sys.exit()

        if (event.type == MUSIC_END
                and app.state in (PLAYING, CLEARING, CASCADING, PAUSED, DEMO)):
            music_game.on_music_end()
            if app.state == PAUSED:
                pygame.mixer.music.set_volume(app.pre_pause_vol * 0.10)

        # FINGER events — check UI buttons first, then gestures, then button bar
        if event.type in (pygame.FINGERDOWN, pygame.FINGERUP, pygame.FINGERMOTION):
            if app.touch_enabled:
                if event.type == pygame.FINGERDOWN:
                    lx = (event.x * app.touch_dw - app.touch_ox) / app.touch_scale
                    ly = (event.y * app.touch_dh - app.touch_oy) / app.touch_scale
                    if _handle_click(lx, ly, gs, app):
                        continue
                # Board gestures (tap-rotate, swipe-drop)
                _handle_board_gesture(event, app)
                import touch_controls as _tc
                _tc.handle(event, app.touch_dw, app.touch_dh,
                           app.touch_ox, app.touch_oy, app.touch_scale)
            continue

        # Desktop mouse clicks → button hit-testing
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            lx = event.pos[0] / app.current_scale
            ly = event.pos[1] / app.current_scale
            _handle_click(lx, ly, gs, app)
            continue

        # KEYUP: track DAS key releases regardless of state
        if event.type == pygame.KEYUP:
            if event.key == pygame.K_LEFT:
                app.keys_held.discard(pygame.K_LEFT)
                if app.das_dir == -1:
                    app.das_dir   = (1 if pygame.K_RIGHT in app.keys_held else 0)
                    app.das_timer = 0; app.das_charged = False
            elif event.key == pygame.K_RIGHT:
                app.keys_held.discard(pygame.K_RIGHT)
                if app.das_dir == 1:
                    app.das_dir   = (-1 if pygame.K_LEFT in app.keys_held else 0)
                    app.das_timer = 0; app.das_charged = False

        if event.type != pygame.KEYDOWN:
            continue

        # ── global keys (any state) ───────────────────────────────────────────
        if event.key == pygame.K_m:
            music.toggle_mute()
            music_game.set_muted(music.is_muted())
            continue

        if event.key == pygame.K_PAGEUP:
            app.music_vol_pct = min(100, app.music_vol_pct + PAGE_VOL_STEP)
            music.set_volume(app.music_vol_pct / 100)
            music_game.set_volume(app.music_vol_pct / 100)
            continue

        if event.key == pygame.K_PAGEDOWN:
            app.music_vol_pct = max(0, app.music_vol_pct - PAGE_VOL_STEP)
            music.set_volume(app.music_vol_pct / 100)
            music_game.set_volume(app.music_vol_pct / 100)
            continue

        # ── MENU ─────────────────────────────────────────────────────────────
        if app.state == MENU:
            app.menu_idle_timer = 0
            if event.key in (pygame.K_UP, pygame.K_DOWN):
                app.menu_row = (app.menu_row + (1 if event.key == pygame.K_DOWN else -1)) % 3
                import audio as _aud; _aud.play('move')   # navigation click
            elif event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
                import audio as _aud; _aud.play('lock')   # confirm sound
                if app.menu_row == 1:
                    app.lb_scores  = highscore.load()
                    app.lb_hi_name = app.lb_hi_score = None
                    app.state      = LEADERBOARD
                elif app.menu_row == 2:
                    app.settings_row          = 0
                    app.settings_return_state = MENU
                    app.state = SETTINGS
                else:
                    start_new_game(gs, app)
                    app.best = highscore.best()
                    music.fadeout(400)
                    music_game.start_sequence()
                    app.state = PLAYING
            elif event.key == pygame.K_s:
                app.settings_row          = 0
                app.settings_return_state = MENU
                app.state = SETTINGS
            elif event.key == pygame.K_t:
                app.music_test_tier = 1
                music.fadeout(300)
                music_game.start_level(app.music_test_tier)
                app.state = MUSIC_TEST
            elif event.key == pygame.K_d:
                import demo as _dm
                music.fadeout(300)
                _dm.enter_demo(gs, app)
            elif event.key == pygame.K_a:
                app.state = ABOUT

        # ── PLAYING / PRACTICE ───────────────────────────────────────────────
        elif app.state in (PLAYING, 'practice'):
            _CHEAT = [pygame.K_3, pygame.K_2, pygame.K_1]
            if event.key == _CHEAT[len(app._cheat_seq)]:
                app._cheat_seq.append(event.key)
                if len(app._cheat_seq) == 3:
                    app._cheat_seq.clear()
                    debug_clear_board(gs, app)
                    continue
            else:
                app._cheat_seq.clear()

            # Admin crash test: type 'bug' to trigger a fake crash through
            # the crash handler so log output and window can be verified.
            _BUG = [pygame.K_b, pygame.K_u, pygame.K_g]
            if event.key == _BUG[len(app._debug_seq)]:
                app._debug_seq.append(event.key)
                if len(app._debug_seq) == 3:
                    app._debug_seq.clear()
                    raise RuntimeError(
                        "DEBUG CRASH TEST — admin sequence 'bug' fired\n"
                        "This is a deliberate fake crash to verify crash_handler.py.\n"
                        "crash_latest.log should have been written next to main.py.\n"
                        "(Not a real error — safe to ignore.)"
                    )
            else:
                app._debug_seq.clear()

            if event.key in (pygame.K_q, pygame.K_ESCAPE):
                if app.state == 'practice':
                    app.state = CONTROLS
                else:
                    app.pre_pause_vol = pygame.mixer.music.get_volume()
                    pygame.mixer.music.set_volume(max(0.0, app.pre_pause_vol * 0.10))
                    app.pause_row = 0
                    app.state = PAUSED
            elif event.key == pygame.K_LEFT:
                app.keys_held.add(pygame.K_LEFT)
                app.das_dir = -1; app.das_timer = 0; app.das_charged = False
                if gs.board.is_valid(gs.current, dx=-1):
                    gs.current.x -= 1
                    gs.last_action = 'move'
                    audio.play('move')
                    reset_lock(gs)
                    if gs.level >= GRAVITY_20G_LEVEL:
                        while gs.board.is_valid(gs.current, dy=1):
                            gs.current.y += 1
            elif event.key == pygame.K_RIGHT:
                app.keys_held.add(pygame.K_RIGHT)
                app.das_dir = 1; app.das_timer = 0; app.das_charged = False
                if gs.board.is_valid(gs.current, dx=1):
                    gs.current.x += 1
                    gs.last_action = 'move'
                    audio.play('move')
                    reset_lock(gs)
                    if gs.level >= GRAVITY_20G_LEVEL:
                        while gs.board.is_valid(gs.current, dy=1):
                            gs.current.y += 1
            elif event.key == pygame.K_DOWN:
                if gs.board.is_valid(gs.current, dy=1):
                    gs.current.y  += 1
                    gs.score       += 1
                    gs.last_action  = 'soft_drop'
                    gs.lock_timer   = 0
            elif event.key == pygame.K_UP:
                if event.mod & pygame.KMOD_CTRL:
                    if rotation.try_rotate(gs.board, gs.current, *gs.current.rotated_ccw()):
                        gs.last_action = 'rotate'
                        reset_lock(gs)
                else:
                    if rotation.try_rotate(gs.board, gs.current, *gs.current.rotated_cw()):
                        gs.last_action = 'rotate'
                        reset_lock(gs)
            elif event.key == pygame.K_z:
                if rotation.try_rotate(gs.board, gs.current, *gs.current.rotated_ccw()):
                    gs.last_action = 'rotate'
                    reset_lock(gs)
            elif event.key == pygame.K_c:
                do_hold(gs, app)
            elif event.key == pygame.K_SPACE:
                gs.hd_flash_timer = HD_FLASH_DURATION
                _hd_start_y = gs.current.y
                while gs.board.is_valid(gs.current, dy=1):
                    gs.current.y += 1
                gs.score      += (gs.current.y - _hd_start_y) * 2
                gs.last_action = 'hard_drop'
                audio.play('hard_drop')
                gs.fall_timer  = 0
                do_lock(gs, app)

        # ── GAME OVER ANIM ────────────────────────────────────────────────────
        elif app.state == GAME_OVER_ANIM:
            if app.go_anim.all_landed:
                app.state = app.post_anim_state

        # ── PAUSED ────────────────────────────────────────────────────────────
        elif app.state == PAUSED:
            if event.key in (pygame.K_UP, pygame.K_DOWN):
                app.pause_row = (app.pause_row + (1 if event.key == pygame.K_DOWN else -1)) % 3
                import audio as _aud; _aud.play('move')
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                import audio as _aud; _aud.play('lock')
                if app.pause_row == 0:
                    pygame.mixer.music.set_volume(app.pre_pause_vol)
                    app.state = PLAYING
                elif app.pause_row == 1:
                    pygame.mixer.music.set_volume(app.pre_pause_vol)
                    app.settings_row          = 0
                    app.settings_return_state = PAUSED
                    app.state = SETTINGS
                else:
                    music_game.stop()
                    music.start_menu()
                    app.state = MENU
            elif event.key == pygame.K_ESCAPE:
                pygame.mixer.music.set_volume(app.pre_pause_vol)
                app.state = PLAYING

        # ── GAME OVER ─────────────────────────────────────────────────────────
        elif app.state == GAME_OVER:
            if event.key == pygame.K_r:
                start_new_game(gs, app)
                music_game.stop()
                music_game.start_sequence()
                app.state = PLAYING
            elif event.key in (pygame.K_SPACE, pygame.K_ESCAPE):
                music_game.stop()
                music.start_menu()
                app.state = MENU
            elif event.key == pygame.K_l:
                app.lb_scores  = highscore.load()
                app.lb_hi_name = app.lb_hi_score = None
                app.state      = LEADERBOARD

        # ── ENTER NAME ────────────────────────────────────────────────────────
        elif app.state == ENTER_NAME:
            idx = INITIALS_CHARS
            if event.key == pygame.K_UP:
                pos = (idx.index(app.initials[app.ini_cursor]) - 1) % len(idx)
                app.initials[app.ini_cursor] = idx[pos]
            elif event.key == pygame.K_DOWN:
                pos = (idx.index(app.initials[app.ini_cursor]) + 1) % len(idx)
                app.initials[app.ini_cursor] = idx[pos]
            elif event.key == pygame.K_LEFT and app.ini_cursor > 0:
                app.ini_cursor -= 1
            elif event.key in (pygame.K_RIGHT, pygame.K_RETURN, pygame.K_KP_ENTER):
                if app.ini_cursor < 2:
                    app.ini_cursor += 1
                else:
                    name            = ''.join(app.initials).strip() or "???"
                    app.lb_scores   = highscore.insert(name, gs.score, gs.lines, gs.level)
                    app.lb_hi_name  = name
                    app.lb_hi_score = gs.score
                    app.best        = highscore.best()
                    app.state       = LEADERBOARD
            elif pygame.K_a <= event.key <= pygame.K_z:
                app.initials[app.ini_cursor] = chr(event.key).upper()
                if app.ini_cursor < 2:
                    app.ini_cursor += 1

        # ── LEADERBOARD ───────────────────────────────────────────────────────
        elif app.state == LEADERBOARD:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
                music_game.stop()
                music.start_menu()
                app.state = MENU
            elif event.key == pygame.K_r:
                start_new_game(gs, app)
                music_game.stop()
                music_game.start_sequence()
                app.state = PLAYING

        # ── ABOUT ─────────────────────────────────────────────────────────────
        elif app.state == ABOUT:
            if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER):
                if (event.key in (pygame.K_RETURN, pygame.K_KP_ENTER)
                        and app.updater
                        and app.updater.status == "available"):
                    import webbrowser
                    from updater import DOWNLOAD_URL
                    webbrowser.open(DOWNLOAD_URL)
                else:
                    app.state = MENU

        # ── MUSIC PREVIEW ─────────────────────────────────────────────────────
        elif app.state == MUSIC_TEST:
            if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER):
                music_game.stop()
                music.start_menu()
                app.state = MENU
            elif event.key == pygame.K_UP:
                app.music_test_tier = max(1, app.music_test_tier - 1)
                music_game.start_level(app.music_test_tier)
            elif event.key == pygame.K_DOWN:
                app.music_test_tier = min(10, app.music_test_tier + 1)
                music_game.start_level(app.music_test_tier)

        # ── DEMO ──────────────────────────────────────────────────────────────
        elif app.demo_active:
            if event.key in (pygame.K_SPACE, pygame.K_ESCAPE):
                import demo as _dm
                _dm.exit_demo(gs, app)

        # ── CONTROLS ──────────────────────────────────────────────────────────
        elif app.state == CONTROLS:
            if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER):
                app.state = SETTINGS

        # ── SETTINGS ──────────────────────────────────────────────────────────
        elif app.state == SETTINGS:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and app.settings_row == 5:
                    app.state = CONTROLS
                elif app.settings_return_state == PAUSED:
                    app.pre_pause_vol = app.music_vol_pct / 100
                    pygame.mixer.music.set_volume(max(0.0, app.pre_pause_vol * 0.10))
                    app.state = PAUSED
                else:
                    app.state = MENU
            elif event.key == pygame.K_UP:
                app.settings_row = (app.settings_row - 1) % 6
            elif event.key == pygame.K_DOWN:
                app.settings_row = (app.settings_row + 1) % 6
            elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                delta = -5 if event.key == pygame.K_LEFT else 5
                if app.settings_row == 0:
                    app.music_vol_pct = max(0, min(100, app.music_vol_pct + delta))
                    music.set_volume(app.music_vol_pct / 100)
                    music_game.set_volume(app.music_vol_pct / 100)
                elif app.settings_row == 1:
                    app.sfx_vol_pct = max(0, min(100, app.sfx_vol_pct + delta))
                    audio.set_sfx_volume(app.sfx_vol_pct / 100)
                    audio.play('rotate')
                elif app.settings_row == 2:
                    scales = config.VALID_SCALES
                    idx    = scales.index(app.current_scale) if app.current_scale in scales else 0
                    idx    = max(0, min(len(scales) - 1,
                                       idx + (1 if event.key == pygame.K_RIGHT else -1)))
                    new_scale = scales[idx]
                    if new_scale != app.current_scale:
                        app.current_scale = new_scale
                        config.set_scale(app.current_scale)
                        app.display = _resize_display(app.current_scale)
                elif app.settings_row == 3:
                    app.ghost_opacity_pct = max(0, min(100, app.ghost_opacity_pct + delta))
                    config.set_ghost_opacity(app.ghost_opacity_pct)
                else:
                    presets = config.VALID_DAS_PRESETS
                    idx     = presets.index(app.das_preset) if app.das_preset in presets else 1
                    idx     = max(0, min(len(presets) - 1,
                                        idx + (1 if event.key == pygame.K_RIGHT else -1)))
                    app.das_preset               = presets[idx]
                    app.das_delay, app.das_repeat = config.DAS_SETTINGS[app.das_preset]
                    config.set_das_preset(app.das_preset)

    # ── DAS auto-repeat ───────────────────────────────────────────────────────
    if app.state == PLAYING and app.das_dir != 0:
        app.das_timer += dt
        if not app.das_charged:
            if app.das_timer >= app.das_delay:
                app.das_charged = True
                app.das_timer   = 0
        else:
            if app.das_repeat == 0:
                if gs.board.is_valid(gs.current, dx=app.das_dir):
                    gs.current.x += app.das_dir
                    gs.last_action = 'move'
                    audio.play('move')
                    reset_lock(gs)
                    if gs.level >= GRAVITY_20G_LEVEL:
                        while gs.board.is_valid(gs.current, dy=1):
                            gs.current.y += 1
            else:
                while app.das_timer >= app.das_repeat:
                    app.das_timer -= app.das_repeat
                    if gs.board.is_valid(gs.current, dx=app.das_dir):
                        gs.current.x += app.das_dir
                        gs.last_action = 'move'
                        audio.play('move')
                        reset_lock(gs)
                        if gs.level >= GRAVITY_20G_LEVEL:
                            while gs.board.is_valid(gs.current, dy=1):
                                gs.current.y += 1
