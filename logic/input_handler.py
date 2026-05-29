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


def _resize_display(scale: float) -> pygame.Surface:
    w = int(SCREEN_WIDTH  * scale)
    h = int(SCREEN_HEIGHT * scale)
    return pygame.display.set_mode((w, h))


def _handle_click(lx: float, ly: float, gs, app: AppState) -> bool:
    """Handle a tap/click at logical pixel (lx, ly). Returns True if consumed."""
    from renderer import (MENU_START_RECT, MENU_LB_RECT, MENU_ABOUT_RECT,
                          MENU_SETTINGS_RECT, INGAME_GEAR_RECT,
                          PAUSE_CONTINUE_RECT, PAUSE_QUIT_RECT)
    pt = (int(lx), int(ly))

    if app.state == MENU:
        app.menu_idle_timer = 0
        if MENU_START_RECT.collidepoint(pt):
            start_new_game(gs, app)
            app.best = highscore.best()
            music.fadeout(400)
            music_game.start_sequence()
            app.state = PLAYING
            return True
        if MENU_LB_RECT.collidepoint(pt):
            app.lb_scores  = highscore.load()
            app.lb_hi_name = app.lb_hi_score = None
            app.state      = LEADERBOARD
            return True
        if MENU_ABOUT_RECT.collidepoint(pt):
            app.state = ABOUT
            return True
        if MENU_SETTINGS_RECT.collidepoint(pt):
            app.settings_row          = 0
            app.settings_return_state = MENU
            app.state = SETTINGS
            return True

    elif app.state in (PLAYING, CLEARING, CASCADING):
        if INGAME_GEAR_RECT.collidepoint(pt):
            app.pre_pause_vol = pygame.mixer.music.get_volume()
            pygame.mixer.music.set_volume(max(0.0, app.pre_pause_vol * 0.10))
            app.state = PAUSED
            return True

    elif app.state == PAUSED:
        if INGAME_GEAR_RECT.collidepoint(pt) or PAUSE_CONTINUE_RECT.collidepoint(pt):
            pygame.mixer.music.set_volume(app.pre_pause_vol)
            app.state = PLAYING
            return True
        if PAUSE_QUIT_RECT.collidepoint(pt):
            music_game.stop()
            music.start_menu()
            app.state = MENU
            return True

    return False


def handle_input(gs: GameState, app: AppState, dt: int) -> None:
    """Process all pending pygame events and run DAS auto-repeat."""

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit(); sys.exit()

        if (event.type == MUSIC_END
                and app.state in (PLAYING, CLEARING, CASCADING, PAUSED)):
            music_game.on_music_end()
            if app.state == PAUSED:
                pygame.mixer.music.set_volume(app.pre_pause_vol * 0.10)

        # FINGER events — check UI buttons first, then pass game controls
        if event.type in (pygame.FINGERDOWN, pygame.FINGERUP, pygame.FINGERMOTION):
            if app.touch_enabled:
                if event.type == pygame.FINGERDOWN:
                    lx = (event.x * app.touch_dw - app.touch_ox) / app.touch_scale
                    ly = (event.y * app.touch_dh - app.touch_oy) / app.touch_scale
                    if _handle_click(lx, ly, gs, app):
                        continue
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
            app.menu_idle_timer = 0   # any key resets the idle countdown
            if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
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

        # ── PLAYING ──────────────────────────────────────────────────────────
        elif app.state == PLAYING:
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
                app.pre_pause_vol = pygame.mixer.music.get_volume()
                pygame.mixer.music.set_volume(max(0.0, app.pre_pause_vol * 0.10))
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
            if event.key == pygame.K_q:
                music_game.stop()
                music.start_menu()
                app.state = MENU
            elif event.key == pygame.K_SPACE:
                pygame.mixer.music.set_volume(app.pre_pause_vol)
                app.state = PLAYING
            elif event.key == pygame.K_s:
                pygame.mixer.music.set_volume(app.pre_pause_vol)
                app.settings_row          = 0
                app.settings_return_state = PAUSED
                app.state = SETTINGS

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
