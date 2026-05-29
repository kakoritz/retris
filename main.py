"""
main.py — bootstrap and per-frame game loop.

Responsibilities:
  - Initialise pygame, display, audio, and music.
  - Construct GameState and AppState (once each).
  - Per frame: handle input → update game state → draw → flip display.
  - Host the CLEARING scoring block (the only remaining logic island here;
    candidate for game_logic.py in a future pass).

Entry point: run_with_crash_handler(main) at the bottom of the file.
"""
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.abspath(__file__))
for _d in ("core", "sounds", "render", "logic"):
    _p = _os.path.join(_ROOT, _d)
    if _p not in _sys.path:
        _sys.path.insert(0, _p)
del _os, _d, _p, _ROOT

import colorsys
import os
import random
import pygame
import sys

import audio
audio.pre_init()

import config
import highscore
import music
import music_game
from particles import update as update_particles, draw as draw_particles
from constants import (
    BOARD_WIDTH, BOARD_HEIGHT, SCREEN_WIDTH, SCREEN_HEIGHT,
    FPS, BG_COLOR, BORDER_COLOR, fall_speed,
)
from renderer import (
    _font,
    draw_board, _draw_danger_line, draw_piece, draw_ghost,
    draw_sidebar, draw_game_over_overlay,
    draw_level_up_overlay, draw_demo_overlay,
    draw_settings, draw_pause, draw_music_test,
    draw_menu, draw_name_entry, draw_leaderboard,
    draw_touch_controls, draw_about, draw_controls, draw_ingame_gear,
)
from game_constants import (
    LOCK_DELAY, GRAVITY_20G_LEVEL,
    SHAKE_DURATION, SHAKE_INTENSITY, HD_FLASH_DURATION,
    VERSION,
)
from game_state import GameState
from app_state import AppState
from game_logic import spawn_next, end_game, do_lock, tick_clearing, tick_cascading
from input_handler import handle_input, MUSIC_END
import demo as demo_mod
from updater import UpdateChecker

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
CASCADING      = "cascading"
DEMO           = "demo"
ABOUT          = "about"
CONTROLS       = "controls"


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
    ox, oy = 1, 6
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
    pygame.mixer.music.set_endevent(MUSIC_END)

    pygame.display.set_icon(_build_icon())

    _android = 'ANDROID_ARGUMENT' in os.environ
    if _android:
        display       = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        _dw, _dh      = display.get_size()
        current_scale = min(_dw / SCREEN_WIDTH, _dh / SCREEN_HEIGHT)
        _lw           = int(SCREEN_WIDTH  * current_scale)
        _lh           = int(SCREEN_HEIGHT * current_scale)
        _touch_ox     = (_dw - _lw) // 2
        _touch_oy     = (_dh - _lh) // 2
    else:
        current_scale = config.get_scale()
        display       = _make_display(current_scale)
        _dw, _dh      = display.get_size()
        _touch_ox = _touch_oy = 0

    if pygame.display.get_driver() == "offscreen":
        print(
            "\nRETRIS: display unavailable — SDL fell back to offscreen mode.\n"
            "This usually means the X server has run out of client connections\n"
            "(common when VS Code, Firefox, and Discord are all open).\n"
            "Close a few heavy apps and try again.\n"
        )
        pygame.quit()
        sys.exit(1)

    screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("RETRIS")
    clock = pygame.time.Clock()
    music.start()
    audio.prime()

    gs  = GameState()
    gs.reset()
    app = AppState(display, screen, current_scale)
    app.best    = highscore.best()
    app.updater = UpdateChecker(VERSION)

    if _android:
        app.touch_enabled = True
        app.touch_dw      = _dw
        app.touch_dh      = _dh
        app.touch_ox      = _touch_ox
        app.touch_oy      = _touch_oy
        app.touch_scale   = current_scale

    while True:
        dt = clock.tick(FPS)

        app.blink_timer += dt
        if app.blink_timer >= 500:
            app.blink_timer = 0
            app.blink_on    = not app.blink_on

        handle_input(gs, app, dt)

        # ── danger detection → tier-1 tension music + warning line ──────────
        if app.state in (PLAYING, CLEARING, CASCADING) and not app.demo_active:
            gs.danger = any(any(row) for row in gs.board.grid[:10])
            music_game.set_danger(gs.danger)
        elif app.demo_active and gs.danger:
            gs.danger = False
            music_game.set_danger(False)

        # ── gravity + lock delay ─────────────────────────────────────────────
        if app.state == PLAYING:
            grounded = not gs.board.is_valid(gs.current, dy=1)

            gs.fall_timer += dt
            if gs.fall_timer >= fall_speed(gs.speed_tier):
                gs.fall_timer = 0
                if not grounded:
                    if gs.level >= GRAVITY_20G_LEVEL:
                        while gs.board.is_valid(gs.current, dy=1):
                            gs.current.y += 1
                    else:
                        gs.current.y  += 1
                        gs.lock_timer  = 0
                    gs.last_action = 'gravity'

            grounded = not gs.board.is_valid(gs.current, dy=1)
            if grounded:
                gs.lock_timer += dt
                if gs.lock_timer >= LOCK_DELAY:
                    do_lock(gs, app)

        # ── line-clear animation + scoring ────────────────────────────────────
        elif app.state == CLEARING:
            tick_clearing(gs, app, dt)

        # ── full board cascade animation ──────────────────────────────────────
        elif app.state == CASCADING:
            tick_cascading(gs, app, dt)

        # ── game-over animation ───────────────────────────────────────────────
        if app.state == GAME_OVER_ANIM:
            hits = app.go_anim.update(dt)
            for bom_idx in hits:
                audio.play_bom(bom_idx)

        # ── popup / particle / fx timers ─────────────────────────────────────
        if gs.popup_timer > 0:
            gs.popup_timer = max(0, gs.popup_timer - dt)
        gs.particles            = update_particles(gs.particles, dt)
        gs.hd_flash_timer       = max(0, gs.hd_flash_timer       - dt)
        gs.shake_timer          = max(0, gs.shake_timer           - dt)
        gs.next_flash_timer     = max(0, gs.next_flash_timer      - dt)
        gs.level_up_flash_timer = max(0, gs.level_up_flash_timer  - dt)
        gs.level_popup_timer    = max(0, gs.level_popup_timer      - dt)

        # ── odometer update ──────────────────────────────────────────────────
        if app.state in (PLAYING, CLEARING, CASCADING, DEMO):
            delta = gs.score - app.score_disp
            if delta > 0:
                chase = max(delta * 0.08, 150.0) * (dt / 1000.0) * 60
                app.score_disp = min(float(gs.score), app.score_disp + chase)
            new_digits = [int(d) for d in str(int(app.score_disp)).zfill(8)]
            for i in range(8):
                if new_digits[i] != app.score_disp_digits[i]:
                    if app.score_anim_offs[i] == 0.0:
                        app.score_anim_from[i] = app.score_disp_digits[i]
                    app.score_anim_offs[i] = 1.0
            app.score_disp_digits = new_digits
            for i in range(8):
                if app.score_anim_offs[i] > 0:
                    app.score_anim_offs[i] = max(0.0, app.score_anim_offs[i] - dt / 180.0)

        # ── menu idle timer → auto-demo ──────────────────────────────────────
        if app.state == MENU:
            app.menu_idle_timer += dt
            if app.menu_idle_timer >= 60_000:
                demo_mod.enter_demo(gs, app)

        s = dt / 1000.0
        for db in gs.danger_bonuses:
            db['y']     += db['vy'] * s
            db['timer'] -= dt
        gs.danger_bonuses = [db for db in gs.danger_bonuses if db['timer'] > 0]

        for cl in gs.combo_labels:
            cl['y']     += cl['vy'] * s
            cl['timer'] -= dt
        gs.combo_labels = [cl for cl in gs.combo_labels if cl['timer'] > 0]

        for sd in gs.score_deltas:
            sd['y']     += sd['vy'] * s
            sd['timer'] -= dt
        gs.score_deltas = [sd for sd in gs.score_deltas if sd['timer'] > 0]

        # ── demo bot update ──────────────────────────────────────────────────
        if app.demo_active:
            demo_mod.update_demo(gs, app, dt)

        # ── draw ──────────────────────────────────────────────────────────────
        if app.state == MENU:
            draw_menu(app.screen, app.blink_on, updater=app.updater,
                      menu_row=app.menu_row)

        elif app.state in (PLAYING, CLEARING, CASCADING, GAME_OVER, GAME_OVER_ANIM,
                           PAUSED, DEMO):
            app.screen.fill(BG_COLOR)

            level_theme = (gs.level - 1) % 10   # 0-9 cycling per level

            bsurf = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT))

            fr = gs.clear_rows if app.state == CLEARING else None
            fo = (gs.clear_flash_idx % 2 == 0) if app.state == CLEARING else False
            fq = (gs.clear_count == 4) if app.state == CLEARING else False
            fw = gs.wow_active if app.state == CLEARING else False
            draw_board(bsurf, gs.board, flash_rows=fr, flash_on=fo, flash_quad=fq,
                       wow_on=fw, palette_phase=level_theme)

            if gs.danger and not app.demo_active and app.state in (PLAYING, CLEARING, CASCADING, PAUSED):
                _draw_danger_line(bsurf)

            if app.state in (PLAYING, PAUSED, DEMO):
                draw_ghost(bsurf, gs.board, gs.current, app.ghost_opacity_pct,
                           palette_phase=level_theme)
                draw_piece(bsurf, gs.current, palette_phase=level_theme)

            draw_particles(bsurf, gs.particles)

            for db in gs.danger_bonuses:
                a = int(255 * db['timer'] / db['max_timer'])
                t = _font(20).render("×2", True, (255, 90, 0))
                t.set_alpha(a)
                bsurf.blit(t, (int(db['x']), int(db['y'])))

            for cl in gs.combo_labels:
                a  = int(255 * cl['timer'] / cl['max_timer'])
                ct = _font(18).render(cl['text'], True, (0, 220, 240))
                ct.set_alpha(a)
                bsurf.blit(ct, (int(cl['x']), int(cl['y'])))

            for sd in gs.score_deltas:
                a   = int(255 * sd['timer'] / sd['max_timer'])
                sdt = _font(16).render(sd['text'], True, sd['color'])
                sdt.set_alpha(a)
                bsurf.blit(sdt, (int(sd['x']) - sdt.get_width() // 2, int(sd['y'])))

            if gs.hd_flash_timer > 0:
                alpha = int(190 * gs.hd_flash_timer / HD_FLASH_DURATION)
                fl    = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT), pygame.SRCALPHA)
                fl.fill((255, 255, 255, alpha))
                bsurf.blit(fl, (0, 0))

            if app.state == GAME_OVER:
                draw_game_over_overlay(bsurf, gs.score,
                                       gs.stat_pieces, gs.stat_tetrises, gs.stat_tspins,
                                       gs.stat_combo, gs.stat_time)
            elif app.state == GAME_OVER_ANIM:
                app.go_anim.draw(bsurf)

            # ── level-up overlay (independent of CASCADING label above) ──────
            if gs.level_popup_timer > 0:
                draw_level_up_overlay(bsurf, gs.level_popup_num,
                                      gs.level_popup_timer, gs.level_popup_max,
                                      level_theme)

            # ── demo overlay ──────────────────────────────────────────────────
            if app.state == DEMO:
                draw_demo_overlay(bsurf, app.demo_label)

            ox = oy = 0
            if gs.shake_timer > 0:
                amt = max(1, int(SHAKE_INTENSITY * gs.shake_timer / SHAKE_DURATION))
                ox  = random.randint(-amt, amt)
                oy  = random.randint(-amt, amt)

            app.screen.blit(bsurf, (ox, oy))

            # ── level-up border flash on the main screen ───────────────────
            if gs.level_popup_timer > 0 and gs.level_popup_max > 0:
                lp_prog  = gs.level_popup_timer / gs.level_popup_max
                lp_alpha = min(1.0, 2.0 * (1.0 - abs(lp_prog - 0.5) / 0.5))
                from constants import LEVEL_THEMES
                gc       = LEVEL_THEMES[level_theme][1]
                bc       = tuple(min(255, int(c * 4)) for c in gc)
                ba       = int(200 * lp_alpha)
                bf       = pygame.Surface((BOARD_WIDTH + 4, BOARD_HEIGHT + 4),
                                          pygame.SRCALPHA)
                pygame.draw.rect(bf, (*bc, ba), (0, 0, BOARD_WIDTH + 4, BOARD_HEIGHT + 4),
                                 4)
                app.screen.blit(bf, (-2, -2))

            lines_to_next = gs.level * 10 - gs.lines
            draw_sidebar(app.screen, gs.score, gs.lines, gs.level, gs.piece_queue,
                         app.best, gs.hold_piece, gs.hold_used,
                         gs.speed_tier, lines_to_next,
                         level_theme,
                         gs.popup_count, gs.popup_timer,
                         gs.next_flash_timer, gs.hold_piece is not None,
                         gs.combo, gs.level_up_flash_timer,
                         app.score_disp_digits, app.score_anim_from, app.score_anim_offs,
                         cascading=app.state == CASCADING,
                         cascade_freefall=app.cascade_freefall)
            pygame.draw.rect(app.screen, BORDER_COLOR,
                             (0, 0, BOARD_WIDTH, BOARD_HEIGHT), 1)
            pygame.draw.line(app.screen, BORDER_COLOR,
                             (BOARD_WIDTH, 0), (BOARD_WIDTH, SCREEN_HEIGHT), 1)

            draw_ingame_gear(app.screen)

            if app.state == PAUSED:
                draw_pause(app.screen, app.blink_on)

        elif app.state == ENTER_NAME:
            draw_name_entry(app.screen, app.initials, app.ini_cursor, app.blink_on,
                            gs.score, gs.lines, gs.level)

        elif app.state == LEADERBOARD:
            draw_leaderboard(app.screen, app.lb_scores, app.lb_hi_name, app.lb_hi_score)

        elif app.state == SETTINGS:
            draw_settings(app.screen, app.music_vol_pct, app.sfx_vol_pct,
                          app.settings_row, music.is_muted(), app.current_scale,
                          app.ghost_opacity_pct, app.das_preset)

        elif app.state == MUSIC_TEST:
            draw_music_test(app.screen, app.music_test_tier)

        elif app.state == ABOUT:
            draw_about(app.screen, app.updater)

        elif app.state == CONTROLS:
            draw_controls(app.screen)

        # Touch D-pad overlay (Android only)
        if app.touch_enabled:
            draw_touch_controls(app.screen)

        # Blit logical surface → physical display
        if app.touch_enabled:
            lw = int(SCREEN_WIDTH  * app.current_scale)
            lh = int(SCREEN_HEIGHT * app.current_scale)
            app.display.fill((0, 0, 0))
            app.display.blit(
                pygame.transform.smoothscale(app.screen, (lw, lh)),
                (app.touch_ox, app.touch_oy),
            )
        elif app.current_scale == 1.0:
            app.display.blit(app.screen, (0, 0))
        else:
            pygame.transform.smoothscale(app.screen, app.display.get_size(), app.display)
        pygame.display.flip()


if __name__ == "__main__":
    from crash_handler import run_with_crash_handler
    run_with_crash_handler(main)
