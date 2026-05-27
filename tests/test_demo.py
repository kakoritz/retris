"""Integration tests for demo.py — catches import errors, API mismatches, and bot logic."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import unittest
from unittest.mock import patch, MagicMock
import pygame

# Minimal pygame init required for Piece / Board construction
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
pygame.init()


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_gs_app():
    """Return a real (gs, app) pair in a known-good state."""
    from game_state import GameState
    from app_state import AppState, MENU
    import pygame
    surf = pygame.Surface((460, 600))
    app = AppState(display=surf, screen=surf, current_scale=1.0)
    app.state = MENU
    gs = GameState()
    return gs, app


# ── Piece shape_name kwarg ────────────────────────────────────────────────────

def test_piece_shape_name_i():
    from piece import Piece
    p = Piece(shape_name='I')
    assert p.type == 'I'


def test_piece_shape_name_all_types():
    from piece import Piece
    from constants import SHAPES
    for name in SHAPES:
        p = Piece(shape_name=name)
        assert p.type == name
        assert p.shape  # non-empty grid


def test_piece_no_arg_still_random():
    from piece import Piece
    p = Piece()
    from constants import SHAPES
    assert p.type in SHAPES


# ── SCENARIOS structure ───────────────────────────────────────────────────────

def test_scenarios_count():
    from demo import SCENARIOS
    assert len(SCENARIOS) == 7


def test_scenarios_fields():
    from demo import SCENARIOS
    for label, board_fn, piece_name, target_x, target_rot, wait_ms in SCENARIOS:
        assert isinstance(label, str) and label
        grid = board_fn()
        assert len(grid) == 20
        assert all(len(row) == 10 for row in grid)
        assert isinstance(piece_name, str)
        assert 0 <= target_x < 10
        assert 0 <= target_rot < 4
        assert wait_ms > 0


# ── enter_demo ────────────────────────────────────────────────────────────────

@patch('music_game.start_sequence')
def test_enter_demo_sets_state(mock_start):
    from demo import enter_demo
    from app_state import DEMO
    gs, app = _make_gs_app()
    enter_demo(gs, app)
    assert app.state == DEMO
    assert app.demo_scenario_idx == 0
    assert app.demo_phase == 'setup'
    mock_start.assert_called_once()


# ── _load_scenario ────────────────────────────────────────────────────────────

@patch('music_game.start_sequence')
def test_load_scenario_sets_piece(mock_start):
    from demo import enter_demo, SCENARIOS
    from app_state import DEMO
    gs, app = _make_gs_app()
    enter_demo(gs, app)

    # Manually trigger _load_scenario via the 'setup' phase
    from demo import _load_scenario
    _load_scenario(gs, app)

    label, board_fn, piece_name, target_x, target_rot, _ = SCENARIOS[0]
    assert gs.current.type == piece_name
    assert app.demo_target_col == target_x
    assert app.demo_target_rot == target_rot
    assert app.state == DEMO


@patch('music_game.start_sequence')
def test_load_scenario_patches_board(mock_start):
    from demo import _load_scenario, SCENARIOS
    from app_state import DEMO
    gs, app = _make_gs_app()
    app.demo_scenario_idx = 0
    app.demo_phase = 'setup'

    expected_grid = SCENARIOS[0][1]()  # call the board_fn
    _load_scenario(gs, app)

    for r in range(20):
        assert gs.board.grid[r] == expected_grid[r], f"row {r} mismatch"


# ── update_demo — setup phase transitions ─────────────────────────────────────

@patch('music_game.start_sequence')
def test_update_demo_setup_transitions_to_move(mock_start):
    from demo import enter_demo, update_demo
    from app_state import DEMO
    gs, app = _make_gs_app()
    enter_demo(gs, app)

    update_demo(gs, app, dt=16)  # triggers 'setup' → 'move'
    assert app.demo_phase == 'move'


# ── update_demo — wait phase advances scenario ────────────────────────────────

@patch('music_game.start_sequence')
def test_update_demo_wait_advances_on_timeout(mock_start):
    from demo import enter_demo, update_demo
    from app_state import DEMO
    gs, app = _make_gs_app()
    enter_demo(gs, app)

    app.demo_phase = 'wait'
    app.demo_wait_timer = 10
    app.demo_scenario_idx = 2

    update_demo(gs, app, dt=20)  # timer expires
    assert app.demo_phase == 'setup'
    assert app.demo_scenario_idx == 3


# ── bot rotation call doesn't raise ──────────────────────────────────────────

@patch('music_game.start_sequence')
@patch('audio.play')
def test_bot_rotate_does_not_raise(mock_audio, mock_start):
    from demo import _load_scenario, _BOT_MOVE_INTERVAL
    from app_state import DEMO, PLAYING
    gs, app = _make_gs_app()
    app.demo_scenario_idx = 0
    app.demo_phase = 'setup'
    _load_scenario(gs, app)

    # Force the piece to need a rotation (rot_state != target)
    gs.current.rot_state = 0
    app.demo_target_rot  = 1
    app.demo_bot_timer   = 0
    app.state = PLAYING

    from demo import update_demo
    # Should not raise
    update_demo(gs, app, dt=_BOT_MOVE_INTERVAL + 1)


# ── advance_scenario wraps around ────────────────────────────────────────────

def test_advance_scenario_wraps():
    from demo import _advance_scenario, SCENARIOS
    from app_state import AppState
    import pygame
    surf = pygame.Surface((460, 600))
    app = AppState(display=surf, screen=surf, current_scale=1.0)
    app.demo_scenario_idx = len(SCENARIOS) - 1
    from game_state import GameState
    gs = GameState()
    _advance_scenario(gs, app)
    assert app.demo_scenario_idx == 0
