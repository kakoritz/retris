"""
game_logic.py — standalone game-logic helpers.

All functions take explicit (gs: GameState, app: AppState) parameters.
They were originally closures with nonlocal access inside main(); extracting
them here makes the parameter contracts explicit and enables unit testing.

Dependency rule: no renderer or input_handler imports — pure logic only.
"""
import random
import pygame
import audio
import highscore
import music
import rotation
from particles import spawn as spawn_particles
from piece import Piece
from constants import (
    SHAPES, COLS, ROWS, BOARD_WIDTH, BOARD_HEIGHT, CELL_SIZE, SCORE_TABLE, fall_speed,
)
from game_constants import (
    NEXT_FLASH_MS, GRAVITY_20G_LEVEL, LOCK_MAX_MOVES,
    PLACEMENT_SCORE, HD_FLASH_DURATION,
    FLASH_MS, FLASH_TOTAL, FLASH_MS_WOW, FLASH_TOTAL_WOW,
    TSPIN_SCORES, TSPIN_MINI_SCORES, COMBO_BONUS_UNIT,
    WOW_BONUS, WOW_POPUP_DURATION, COLOR_CLEAR_BONUS,
    SHAKE_DURATION, POPUP_DURATION, CASCADE_INTERVAL_GROWTH,
    SPEED_RESET_INTERVAL, SPEED_RESET_FLASH_DURATION, CASCADE_BONUS_PER_RESET,
)
from game_state import GameState
from app_state import (
    AppState, ENTER_NAME, GAME_OVER_ANIM, GAME_OVER, CLEARING, CASCADING, PLAYING,
)


def spawn_next(gs: GameState, app: AppState) -> bool:
    """Dequeue the next piece, refill the queue tail, and reset per-piece state.

    Returns False if the spawned piece immediately overlaps the stack (top-out).
    The caller should call end_game() on False.
    """
    gs.current         = gs.piece_queue.pop(0)
    gs.piece_queue.append(Piece())
    gs.next_flash_timer = NEXT_FLASH_MS
    gs.lock_timer       = 0
    gs.lock_move_count  = 0
    gs.hold_used        = False
    gs.last_action      = 'gravity'
    if gs.level >= GRAVITY_20G_LEVEL:
        while gs.board.is_valid(gs.current, dy=1):
            gs.current.y += 1
    audio.play_spawn(gs.current.color_id)
    return gs.board.is_valid(gs.current)


def do_hold(gs: GameState, app: AppState) -> None:
    """Stash the current piece into the hold slot (or swap with the existing one).

    The piece is reset to its spawn orientation before stashing so that hold
    always returns a fresh piece regardless of how it was rotated.
    Hold is locked for the rest of the active piece's life (hold_used flag).
    """
    if gs.hold_used:
        return
    gs.hold_used       = True
    gs.last_action     = 'gravity'
    gs.lock_timer      = gs.lock_move_count = 0

    # Reset the current piece to spawn state before stashing.
    gs.current.shape     = [row[:] for row in SHAPES[gs.current.type]]
    gs.current.rot_state = 0
    gs.current.x         = COLS // 2 - len(gs.current.shape[0]) // 2
    gs.current.y         = 0

    if gs.hold_piece is None:
        gs.hold_piece = gs.current
        gs.current    = gs.piece_queue.pop(0)
        gs.piece_queue.append(Piece())
        gs.next_flash_timer = NEXT_FLASH_MS
    else:
        gs.current, gs.hold_piece = gs.hold_piece, gs.current
        gs.current.shape     = [row[:] for row in SHAPES[gs.current.type]]
        gs.current.rot_state = 0
        gs.current.x         = COLS // 2 - len(gs.current.shape[0]) // 2
        gs.current.y         = 0

    if gs.level >= GRAVITY_20G_LEVEL:
        while gs.board.is_valid(gs.current, dy=1):
            gs.current.y += 1
    gs.last_action = 'gravity'
    audio.play_spawn(gs.current.color_id)


def start_new_game(gs: GameState, app: AppState) -> None:
    gs.reset()
    app.reset_das()
    audio.play_spawn(gs.current.color_id)


def end_game(gs: GameState, app: AppState) -> None:
    gs.stat_time = (pygame.time.get_ticks() - gs.stat_start_ms) / 1000.0
    music.fadeout(1200)
    app.go_anim.reset()
    if highscore.qualifies(gs.score):
        app.initials        = ['A', 'A', 'A']
        app.ini_cursor      = 0
        app.post_anim_state = ENTER_NAME
    else:
        app.post_anim_state = GAME_OVER
    app.state = GAME_OVER_ANIM


def reset_lock(gs: GameState) -> None:
    """Restart the lock-delay timer on a move or rotation, up to LOCK_MAX_MOVES times.

    Only resets when the piece is grounded — a move that lifts the piece off the
    stack does not consume a reset (the timer just stops running).
    The cap prevents infinite stalling by tapping repeatedly.
    """
    if not gs.board.is_valid(gs.current, dy=1) and gs.lock_move_count < LOCK_MAX_MOVES:
        gs.lock_timer = 0
        gs.lock_move_count += 1


def do_lock(gs: GameState, app: AppState) -> None:
    """Place the current piece, score the placement, and start clearing or spawn next.

    T-spin detection must happen before board.place() — after placement the
    corner cells are no longer reliable for the 3-corner rule.

    WOW (perfect clear) is true when every non-clearing row is completely empty.
    Color clear fires when any cleared row is mono-color (all 10 cells same type).
    """
    gs.tspin_type = rotation.detect_tspin(gs.board, gs.current, gs.last_action)
    gs.board.place(gs.current)
    gs.stat_pieces += 1
    audio.play('lock')
    app.reset_das()
    gs.lock_timer = gs.lock_move_count = 0
    gs.score     += PLACEMENT_SCORE
    gs.cascade_level      = 0
    gs.first_clear_tetris = False
    full = gs.board.full_rows()
    if full:
        full_set       = set(full)
        # WOW: every row outside the clearing set must be completely empty.
        gs.wow_active  = all(
            all(c == 0 for c in gs.board.grid[r])
            for r in range(ROWS) if r not in full_set
        )
        # Color clear: first cleared row where all 10 cells share the same color_id.
        gs.color_clear_id = None
        for row_i in full:
            row_colors = set(gs.board.grid[row_i][c] for c in range(COLS))
            if len(row_colors) == 1:
                gs.color_clear_id = next(iter(row_colors))
                break
        gs.clear_rows      = full_set
        gs.clear_count     = len(full)
        gs.clear_timer     = 0
        gs.clear_flash_idx = 0
        gs.clear_cells     = [
            (col, row_i, gs.board.grid[row_i][col])
            for row_i in full for col in range(COLS)
            if gs.board.grid[row_i][col]
        ]
        audio.play(gs.clear_count)
        app.state = CLEARING
    else:
        gs.combo = 0
        if not spawn_next(gs, app):
            end_game(gs, app)


def debug_clear_board(gs: GameState, app: AppState) -> None:
    """Fill every empty cell with color 1, then trigger a full 20-row clear.

    This fires the WOW (perfect-clear) event and is used to test that path
    without having to play to a natural board clear. Triggered by the 3-2-1
    key sequence during gameplay.
    """
    for r in range(ROWS):
        for c in range(COLS):
            if gs.board.grid[r][c] == 0:
                gs.board.grid[r][c] = 1
    full_set          = set(range(ROWS))
    gs.wow_active     = True
    gs.clear_rows     = full_set
    gs.clear_count    = ROWS
    gs.clear_timer    = 0
    gs.clear_flash_idx = 0
    gs.clear_cells    = [
        (col, row_i, gs.board.grid[row_i][col])
        for row_i in range(ROWS) for col in range(COLS)
    ]
    gs.hd_flash_timer = HD_FLASH_DURATION
    audio.play(4)
    app.state = CLEARING


def _setup_cascade_clear(gs: GameState, cascade_rows: list) -> None:
    """Shared helper: configure gs for another CLEARING pass after a cascade."""
    gs.cascade_level += 1
    full_set           = set(cascade_rows)
    gs.wow_active      = all(
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


def tick_clearing(gs: GameState, app: AppState, dt: int) -> None:
    """Advance the CLEARING flash animation and, when complete, score and transition.

    Called every frame while app.state == CLEARING.
    Scoring priority: T-spin → B2B → combo → danger → cascade → WOW bonus.
    After scoring: transitions to CASCADING (full cascade mode) or loops back
    to CLEARING (normal cascade) or PLAYING (no further cascades).
    """
    gs.clear_timer += dt
    fms    = FLASH_MS_WOW    if gs.wow_active else FLASH_MS.get(gs.clear_count, 80)
    ftotal = FLASH_TOTAL_WOW if gs.wow_active else FLASH_TOTAL.get(gs.clear_count, 2)
    if gs.clear_timer < fms:
        return
    gs.clear_timer -= fms
    gs.clear_flash_idx += 1
    if gs.clear_flash_idx < ftotal:
        return

    # ── scoring ───────────────────────────────────────────────────────────────
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

    gs.board.clear_lines()

    # Color clear: remove every remaining cell of the cleared color.
    _had_color_clear = False
    if gs.color_clear_id is not None:
        cc_removed = gs.board.remove_color(gs.color_clear_id)
        gs.color_clear_id = None
        if cc_removed:
            gs.particles    += spawn_particles(cc_removed, 4)
            gs.score        += COLOR_CLEAR_BONUS
            app.best         = max(app.best, gs.score)
            _had_color_clear = True

    big_clear = (gs.wow_active or gs.clear_count == 4
                 or (is_tspin and gs.clear_count == 3)
                 or tetris_x_tetris)
    gs.particles += spawn_particles(gs.clear_cells, gs.clear_count)
    if big_clear:
        gs.shake_timer = SHAKE_DURATION

    # ── popup priority ────────────────────────────────────────────────────────
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

    # ── cascade check ─────────────────────────────────────────────────────────
    if gs.full_cascade_mode:
        app.cascade_anim_timer = 0
        app.state = CASCADING
    else:
        gs.board.settle_blocks()
        cascade_rows = gs.board.full_rows()
        if cascade_rows:
            _setup_cascade_clear(gs, cascade_rows)
            # app.state stays CLEARING for the next pass
        else:
            gs.first_clear_tetris = False
            gs.cascade_level      = 0
            if spawn_next(gs, app):
                app.state = PLAYING
            else:
                end_game(gs, app)


def tick_cascading(gs: GameState, app: AppState, dt: int) -> None:
    """Advance the full-board cascade animation one step per interval.

    Called every frame while app.state == CASCADING.
    Each step drops all floating blocks one row. When the board settles,
    checks for new full rows (→ CLEARING again) or ends the cascade
    (awards bonus, spawns next piece).
    """
    app.cascade_anim_timer += dt
    _cascade_step = min(fall_speed(gs.speed_tier), 300)
    if app.cascade_anim_timer < _cascade_step:
        return
    app.cascade_anim_timer -= _cascade_step

    if gs.board.apply_block_gravity():
        return  # board still settling — wait for next step

    cascade_rows = gs.board.full_rows()
    if cascade_rows:
        _setup_cascade_clear(gs, cascade_rows)
        app.state = CLEARING
    else:
        # Cascade fully settled — award end-of-cascade bonus.
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
            gs.next_speed_reset        += SPEED_RESET_INTERVAL + gs.speed_reset_count * CASCADE_INTERVAL_GROWTH
            gs.speed_tier               = 1
            gs.speed_reset_count       += 1
            gs.reset_bonus_mult         = round(1.0 + gs.speed_reset_count * 0.1, 1)
            gs.full_cascade_mode        = not gs.full_cascade_mode
            gs.speed_reset_flash_timer  = SPEED_RESET_FLASH_DURATION
        app.best              = max(app.best, gs.score)
        gs.first_clear_tetris = False
        gs.cascade_level      = 0
        if spawn_next(gs, app):
            app.state = PLAYING
        else:
            end_game(gs, app)
