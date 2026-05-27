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
from particles import spawn as spawn_particles
from particles import update as update_particles
from particles import draw as draw_particles
from constants import (
    COLS, ROWS, CELL_SIZE,
    BOARD_WIDTH, BOARD_HEIGHT, SCREEN_WIDTH, SCREEN_HEIGHT,
    FPS, BG_COLOR, BORDER_COLOR, SCORE_TABLE, fall_speed,
)
from renderer import (
    _font, _BOARD_LINE,
    draw_board, _draw_danger_line, draw_piece, draw_ghost,
    draw_sidebar, draw_game_over_overlay,
    draw_settings, draw_pause, draw_music_test,
    draw_menu, draw_name_entry, draw_leaderboard,
)
from game_constants import (
    LOCK_DELAY,
    FLASH_MS, FLASH_TOTAL,
    FLASH_MS_WOW, FLASH_TOTAL_WOW,
    WOW_BONUS, WOW_POPUP_DURATION, COLOR_CLEAR_BONUS,
    TSPIN_SCORES, TSPIN_MINI_SCORES,
    COMBO_BONUS_UNIT,
    GRAVITY_20G_LEVEL,
    SPEED_RESET_INTERVAL, CASCADE_INTERVAL_GROWTH,
    PALETTE_PHASE_INTERVAL,
    SPEED_RESET_FLASH_DURATION,
    CASCADE_BONUS_PER_RESET,
    POPUP_DURATION, SHAKE_DURATION, SHAKE_INTENSITY, HD_FLASH_DURATION,
)
from game_state import GameState
from app_state import AppState
from game_logic import spawn_next, end_game, do_lock
from input_handler import handle_input, MUSIC_END

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

    current_scale = config.get_scale()
    display       = _make_display(current_scale)

    if pygame.display.get_driver() == "offscreen":
        print(
            "\nT3TR1S: display unavailable — SDL fell back to offscreen mode.\n"
            "This usually means the X server has run out of client connections\n"
            "(common when VS Code, Firefox, and Discord are all open).\n"
            "Close a few heavy apps and try again.\n"
        )
        pygame.quit()
        sys.exit(1)

    screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("T3TR1S")
    clock = pygame.time.Clock()
    music.start()
    audio.prime()

    gs  = GameState()
    gs.reset()
    app = AppState(display, screen, current_scale)
    app.best = highscore.best()

    while True:
        dt = clock.tick(FPS)

        app.blink_timer += dt
        if app.blink_timer >= 500:
            app.blink_timer = 0
            app.blink_on    = not app.blink_on

        handle_input(gs, app, dt)

        # ── danger detection → tier-1 tension music + warning line ──────────
        if app.state in (PLAYING, CLEARING, CASCADING):
            gs.danger = any(any(row) for row in gs.board.grid[:10])
            music_game.set_danger(gs.danger)

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

        # ── line-clear animation ──────────────────────────────────────────────
        elif app.state == CLEARING:
            gs.clear_timer += dt
            fms    = FLASH_MS_WOW    if gs.wow_active else FLASH_MS.get(gs.clear_count, 80)
            ftotal = FLASH_TOTAL_WOW if gs.wow_active else FLASH_TOTAL.get(gs.clear_count, 2)
            if gs.clear_timer >= fms:
                gs.clear_timer -= fms
                gs.clear_flash_idx += 1
                if gs.clear_flash_idx >= ftotal:
                    # ── scoring ───────────────────────────────────────────────
                    gs.lines += gs.clear_count

                    danger_rows  = [r for r in gs.clear_rows if r < 10]
                    danger_mult  = 2 if danger_rows else 1
                    cascade_mult = min(gs.cascade_level + 1, 4)

                    is_tspin     = gs.tspin_type is not None and not gs.wow_active
                    is_difficult = (gs.clear_count == 4 or is_tspin) and not gs.wow_active
                    if is_tspin:
                        tbl        = TSPIN_MINI_SCORES if gs.tspin_type == 'mini' else TSPIN_SCORES
                        base_score = tbl.get(gs.clear_count, 0) * (gs.level + 1)
                    else:
                        base_score = SCORE_TABLE.get(gs.clear_count, 0) * (gs.level + 1)

                    tetris_x_tetris = (gs.cascade_level == 1
                                       and gs.clear_count == 4
                                       and gs.first_clear_tetris)
                    if tetris_x_tetris:
                        cascade_mult = 4

                    btb_bonus = is_difficult and gs.btb_active
                    if btb_bonus:
                        base_score = int(base_score * 1.5)

                    clear_delta = int(base_score * cascade_mult * danger_mult * gs.reset_bonus_mult)
                    gs.score   += clear_delta

                    if clear_delta > 0:
                        if is_tspin and btb_bonus:
                            _dcol = (220, 130, 255)
                        elif is_tspin:
                            _dcol = (200, 100, 255)
                        elif btb_bonus:
                            _dcol = (255, 215, 0)
                        elif gs.cascade_level > 0:
                            _dcol = (80, 255, 180)
                        elif danger_mult == 2:
                            _dcol = (255, 140, 0)
                        else:
                            _dcol = (220, 220, 255)
                        gs.score_deltas.append({
                            'text':      f"+{clear_delta:,}",
                            'color':     _dcol,
                            'x':         float(BOARD_WIDTH * 0.68),
                            'y':         float(BOARD_HEIGHT * 0.52),
                            'vy':        -70.0,
                            'timer':     1600,
                            'max_timer': 1600,
                        })

                    combo_bonus = COMBO_BONUS_UNIT * gs.combo * (gs.level + 1)
                    gs.score   += combo_bonus
                    if gs.combo >= 1:
                        gs.combo_labels.append({
                            'text':      f"COMBO ×{gs.combo + 1}",
                            'x':         float(BOARD_WIDTH // 2 - 32),
                            'y':         float(BOARD_HEIGHT // 2),
                            'vy':        -90.0,
                            'timer':     1400,
                            'max_timer': 1400,
                        })
                    gs.combo     += 1
                    gs.stat_combo = max(gs.stat_combo, gs.combo)

                    if gs.clear_count == 4:
                        gs.stat_tetrises += 1
                    if is_tspin:
                        gs.stat_tspins += 1

                    if gs.wow_active:
                        gs.score += WOW_BONUS * (gs.level + 1)

                    if is_difficult:
                        gs.btb_active = True
                    elif not gs.wow_active and gs.clear_count > 0:
                        gs.btb_active = False

                    for r in danger_rows:
                        gs.danger_bonuses.append({
                            'x':         float(random.randint(10, BOARD_WIDTH - 50)),
                            'y':         float(r * CELL_SIZE),
                            'vy':        -115.0,
                            'timer':     1300,
                            'max_timer': 1300,
                        })

                    old_level = gs.level
                    gs.level  = gs.lines // 10 + 1
                    if gs.level > old_level:
                        gs.speed_tier = min(gs.speed_tier + (gs.level - old_level), 20)
                        gs.level_up_flash_timer = 700
                        if old_level < GRAVITY_20G_LEVEL <= gs.level:
                            gs.popup_count = 14
                            gs.popup_timer = int(POPUP_DURATION * 1.5)

                    speed_reset_triggered = False
                    while gs.score >= gs.next_speed_reset:
                        gs.next_speed_reset  += SPEED_RESET_INTERVAL + gs.speed_reset_count * CASCADE_INTERVAL_GROWTH
                        gs.speed_tier         = 1
                        gs.speed_reset_count += 1
                        gs.reset_bonus_mult   = round(1.0 + gs.speed_reset_count * 0.1, 1)
                        gs.full_cascade_mode  = not gs.full_cascade_mode
                        speed_reset_triggered = True
                    if speed_reset_triggered:
                        gs.speed_reset_flash_timer = SPEED_RESET_FLASH_DURATION

                    app.best = max(app.best, gs.score)

                    if gs.cascade_level == 0:
                        gs.first_clear_tetris = (gs.clear_count == 4)

                    # ── clear lines ───────────────────────────────────────────
                    gs.board.clear_lines()

                    # ── color clear: blast every remaining cell of that color ──
                    _had_color_clear = False
                    if gs.color_clear_id is not None:
                        cc_removed = gs.board.remove_color(gs.color_clear_id)
                        gs.color_clear_id = None
                        if cc_removed:
                            gs.particles     += spawn_particles(cc_removed, 4)
                            gs.score         += COLOR_CLEAR_BONUS
                            app.best          = max(app.best, gs.score)
                            _had_color_clear  = True

                    # ── visual feedback for THIS clear pass ───────────────────
                    big_clear = (gs.wow_active or gs.clear_count == 4
                                 or (is_tspin and gs.clear_count == 3)
                                 or tetris_x_tetris)
                    gs.particles += spawn_particles(gs.clear_cells, gs.clear_count)
                    if big_clear:
                        gs.shake_timer = SHAKE_DURATION

                    # ── popup selection ───────────────────────────────────────
                    if gs.wow_active:
                        gs.popup_count = 0
                        gs.popup_timer = WOW_POPUP_DURATION
                        gs.wow_active  = False
                    elif _had_color_clear:
                        gs.popup_count = 15
                        gs.popup_timer = WOW_POPUP_DURATION
                    elif tetris_x_tetris:
                        gs.popup_count = 13
                        gs.popup_timer = WOW_POPUP_DURATION
                    elif is_tspin and btb_bonus:
                        gs.popup_count = 8
                        gs.popup_timer = POPUP_DURATION
                    elif is_tspin and gs.tspin_type == 'full':
                        gs.popup_count = 5
                        gs.popup_timer = POPUP_DURATION
                    elif is_tspin:
                        gs.popup_count = 6
                        gs.popup_timer = POPUP_DURATION
                    elif btb_bonus and gs.clear_count == 4:
                        gs.popup_count = 7
                        gs.popup_timer = POPUP_DURATION
                    elif gs.cascade_level >= 4:
                        gs.popup_count = 12
                        gs.popup_timer = POPUP_DURATION
                    elif gs.cascade_level == 3:
                        gs.popup_count = 11
                        gs.popup_timer = POPUP_DURATION
                    elif gs.cascade_level == 2:
                        gs.popup_count = 10
                        gs.popup_timer = POPUP_DURATION
                    elif gs.cascade_level == 1:
                        gs.popup_count = 9
                        gs.popup_timer = POPUP_DURATION
                    else:
                        gs.popup_count = gs.clear_count
                        gs.popup_timer = POPUP_DURATION

                    gs.tspin_type = None

                    # ── cascade check ─────────────────────────────────────────
                    if gs.full_cascade_mode:
                        app.cascade_anim_timer = 0
                        app.state = CASCADING
                    else:
                        gs.board.settle_blocks()
                        cascade_rows = gs.board.full_rows()
                        if cascade_rows:
                            gs.cascade_level += 1
                            full_set          = set(cascade_rows)
                            gs.wow_active     = all(
                                all(c == 0 for c in gs.board.grid[r])
                                for r in range(ROWS) if r not in full_set
                            )
                            gs.clear_rows      = full_set
                            gs.clear_count     = len(cascade_rows)
                            gs.clear_timer     = 0
                            gs.clear_flash_idx = 0
                            gs.clear_cells     = [
                                (col, row_i, gs.board.grid[row_i][col])
                                for row_i in cascade_rows for col in range(COLS)
                                if gs.board.grid[row_i][col]
                            ]
                            audio.play(min(gs.clear_count, 4))
                        else:
                            gs.first_clear_tetris = False
                            gs.cascade_level      = 0
                            if spawn_next(gs, app):
                                app.state = PLAYING
                            else:
                                end_game(gs, app)

        # ── full board cascade animation ──────────────────────────────────────
        elif app.state == CASCADING:
            app.cascade_anim_timer += dt
            _cascade_step = min(fall_speed(gs.speed_tier), 300)
            if app.cascade_anim_timer >= _cascade_step:
                app.cascade_anim_timer -= _cascade_step
                if gs.board.apply_block_gravity():
                    pass
                else:
                    cascade_rows = gs.board.full_rows()
                    if cascade_rows:
                        gs.cascade_level += 1
                        full_set          = set(cascade_rows)
                        gs.wow_active     = all(
                            all(c == 0 for c in gs.board.grid[r])
                            for r in range(ROWS) if r not in full_set
                        )
                        gs.clear_rows      = full_set
                        gs.clear_count     = len(cascade_rows)
                        gs.clear_timer     = 0
                        gs.clear_flash_idx = 0
                        gs.clear_cells     = [
                            (col, row_i, gs.board.grid[row_i][col])
                            for row_i in cascade_rows for col in range(COLS)
                            if gs.board.grid[row_i][col]
                        ]
                        audio.play(min(gs.clear_count, 4))
                        app.state = CLEARING
                    else:
                        cascade_end_bonus = 500 + CASCADE_BONUS_PER_RESET * gs.speed_reset_count
                        gs.score += cascade_end_bonus
                        gs.score_deltas.append({
                            'text':      f"+{cascade_end_bonus:,}",
                            'color':     (80, 255, 180),
                            'x':         float(BOARD_WIDTH * 0.68),
                            'y':         float(BOARD_HEIGHT * 0.45),
                            'vy':        -60.0,
                            'timer':     1600,
                            'max_timer': 1600,
                        })
                        while gs.score >= gs.next_speed_reset:
                            gs.next_speed_reset  += SPEED_RESET_INTERVAL + gs.speed_reset_count * CASCADE_INTERVAL_GROWTH
                            gs.speed_tier         = 1
                            gs.speed_reset_count += 1
                            gs.reset_bonus_mult   = round(1.0 + gs.speed_reset_count * 0.1, 1)
                            gs.full_cascade_mode  = not gs.full_cascade_mode
                            gs.speed_reset_flash_timer = SPEED_RESET_FLASH_DURATION
                        app.best               = max(app.best, gs.score)
                        gs.first_clear_tetris  = False
                        gs.cascade_level       = 0
                        if spawn_next(gs, app):
                            app.state = PLAYING
                        else:
                            end_game(gs, app)

        # ── game-over animation ───────────────────────────────────────────────
        if app.state == GAME_OVER_ANIM:
            hits = app.go_anim.update(dt)
            for bom_idx in hits:
                audio.play_bom(bom_idx)

        # ── popup / particle / fx timers ─────────────────────────────────────
        if gs.popup_timer > 0:
            gs.popup_timer = max(0, gs.popup_timer - dt)
        gs.particles             = update_particles(gs.particles, dt)
        gs.hd_flash_timer        = max(0, gs.hd_flash_timer        - dt)
        gs.shake_timer           = max(0, gs.shake_timer            - dt)
        gs.speed_reset_flash_timer = max(0, gs.speed_reset_flash_timer - dt)
        gs.next_flash_timer      = max(0, gs.next_flash_timer       - dt)
        gs.level_up_flash_timer  = max(0, gs.level_up_flash_timer   - dt)

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

        # ── draw ──────────────────────────────────────────────────────────────
        if app.state == MENU:
            draw_menu(app.screen, app.blink_on)

        elif app.state in (PLAYING, CLEARING, CASCADING, GAME_OVER, GAME_OVER_ANIM, PAUSED):
            app.screen.fill(BG_COLOR)

            palette_phase = ((gs.level - 1) // PALETTE_PHASE_INTERVAL) % 6

            bsurf = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT))
            bsurf.fill(_BOARD_LINE)

            fr = gs.clear_rows if app.state == CLEARING else None
            fo = (gs.clear_flash_idx % 2 == 0) if app.state == CLEARING else False
            fq = (gs.clear_count == 4) if app.state == CLEARING else False
            fw = gs.wow_active if app.state == CLEARING else False
            draw_board(bsurf, gs.board, flash_rows=fr, flash_on=fo, flash_quad=fq,
                       wow_on=fw, palette_phase=palette_phase)

            if gs.danger and app.state in (PLAYING, CLEARING, CASCADING, PAUSED):
                _draw_danger_line(bsurf)

            if app.state in (PLAYING, PAUSED):
                draw_ghost(bsurf, gs.board, gs.current, app.ghost_opacity_pct,
                           palette_phase=palette_phase)
                draw_piece(bsurf, gs.current, palette_phase=palette_phase)

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

            if gs.speed_reset_flash_timer > 0:
                a      = 1.0 if gs.speed_reset_flash_timer > 500 else gs.speed_reset_flash_timer / 500
                sr_col = tuple(int(c * a) for c in (100, 255, 100))
                sr_t   = _font(22).render("SPEED  RESET!", True, sr_col)
                bsurf.blit(sr_t, (BOARD_WIDTH // 2 - sr_t.get_width() // 2, 38))

            if gs.hd_flash_timer > 0:
                alpha = int(190 * gs.hd_flash_timer / HD_FLASH_DURATION)
                fl    = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT), pygame.SRCALPHA)
                fl.fill((255, 255, 255, alpha))
                bsurf.blit(fl, (0, 0))

            if app.state == CASCADING:
                h   = (pygame.time.get_ticks() / 120) % 1.0
                rgb = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(h, 1.0, 1.0))
                cas_t = _font(30).render("CASCADE!", True, rgb)
                cx    = BOARD_WIDTH  // 2 - cas_t.get_width()  // 2
                cy    = BOARD_HEIGHT // 2 - cas_t.get_height() // 2
                pad   = 8
                bg    = pygame.Surface((cas_t.get_width() + pad * 2,
                                        cas_t.get_height() + pad * 2), pygame.SRCALPHA)
                bg.fill((0, 0, 0, 160))
                bsurf.blit(bg, (cx - pad, cy - pad))
                bsurf.blit(cas_t, (cx, cy))

            elif app.state == GAME_OVER:
                draw_game_over_overlay(bsurf, gs.score,
                                       gs.stat_pieces, gs.stat_tetrises, gs.stat_tspins,
                                       gs.stat_combo, gs.stat_time)
            elif app.state == GAME_OVER_ANIM:
                app.go_anim.draw(bsurf)

            ox = oy = 0
            if gs.shake_timer > 0:
                amt = max(1, int(SHAKE_INTENSITY * gs.shake_timer / SHAKE_DURATION))
                ox  = random.randint(-amt, amt)
                oy  = random.randint(-amt, amt)

            app.screen.blit(bsurf, (ox, oy))

            draw_sidebar(app.screen, gs.score, gs.lines, gs.level, gs.piece_queue,
                         app.best, gs.hold_piece, gs.hold_used,
                         gs.speed_tier, gs.next_speed_reset,
                         gs.reset_bonus_mult, gs.full_cascade_mode,
                         palette_phase,
                         gs.popup_count, gs.popup_timer,
                         gs.next_flash_timer, gs.hold_piece is not None,
                         gs.combo, gs.level_up_flash_timer)
            pygame.draw.rect(app.screen, BORDER_COLOR,
                             (0, 0, BOARD_WIDTH, BOARD_HEIGHT), 1)
            pygame.draw.line(app.screen, BORDER_COLOR,
                             (BOARD_WIDTH, 0), (BOARD_WIDTH, SCREEN_HEIGHT), 1)

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

        if app.current_scale == 1.0:
            app.display.blit(app.screen, (0, 0))
        else:
            pygame.transform.smoothscale(app.screen, app.display.get_size(), app.display)
        pygame.display.flip()


if __name__ == "__main__":
    main()
