"""
touch_controls.py — virtual gamepad for Android.

Context-sensitive: key set changes per game state.
Call init() once after display setup, then set_keys_for_state() each frame.
"""
import pygame

# Default game keys
_KEYS_GAME     = [pygame.K_LEFT, pygame.K_DOWN, pygame.K_SPACE,
                  pygame.K_UP, pygame.K_RIGHT]
                  # K_c (HOLD) removed — tap the HOLD box in the info strip instead
_KEYS_MENU     = [pygame.K_UP, pygame.K_RETURN, pygame.K_DOWN]
_KEYS_PAUSE    = [pygame.K_UP, pygame.K_RETURN, pygame.K_DOWN]
_KEYS_NAME     = [pygame.K_UP, pygame.K_LEFT, pygame.K_RETURN,
                  pygame.K_RIGHT, pygame.K_DOWN]
_KEYS_CONTINUE = [pygame.K_SPACE]
_KEYS_MENU_BTN = [pygame.K_ESCAPE]

_STATE_KEYS = {
    'playing':        _KEYS_GAME,
    'clearing':       _KEYS_GAME,
    'cascading':      _KEYS_GAME,
    'demo':           _KEYS_GAME,
    'paused':         _KEYS_PAUSE,
    'menu':           _KEYS_MENU,
    'game_over_anim': _KEYS_CONTINUE,
    'game_over':      _KEYS_CONTINUE,
    'enter_name':     _KEYS_NAME,
    'leaderboard':    _KEYS_MENU_BTN,
    'settings':       _KEYS_MENU_BTN,
    'demo':           _KEYS_MENU_BTN,
    'about':          _KEYS_MENU_BTN,
    'controls':       _KEYS_MENU_BTN,
    'practice':       _KEYS_MENU_BTN,
    'music_test':     _KEYS_MENU_BTN,
}

BUTTONS: list[tuple] = []
_held:   dict[int, int] = {}

# Stored from init() — needed to rebuild BUTTONS on layout change
_canvas_w = 460
_zone_y   = 850
_zone_h   = 100


def init(canvas_w: int, zone_y: int, zone_h: int) -> None:
    global _canvas_w, _zone_y, _zone_h
    _canvas_w = canvas_w
    _zone_y   = zone_y
    _zone_h   = zone_h
    set_keys(_KEYS_GAME)


def set_keys(keys: list) -> None:
    global BUTTONS
    n     = len(keys)
    btn_w = _canvas_w // n
    BUTTONS = [
        (pygame.Rect(btn_w * i, _zone_y,
                     btn_w if i < n-1 else _canvas_w - btn_w*(n-1),
                     _zone_h),
         keys[i])
        for i in range(n)
    ]


def set_keys_for_state(state: str) -> None:
    keys = _STATE_KEYS.get(state, _KEYS_MENU)
    # Only rebuild if number of buttons changed (avoids clearing held each frame)
    if len(keys) != len(BUTTONS):
        _held.clear()
        set_keys(keys)
    elif BUTTONS and BUTTONS[0][1] != keys[0]:
        _held.clear()
        set_keys(keys)


def _hit(lx: int, ly: int) -> int | None:
    for i, (rect, _) in enumerate(BUTTONS):
        if rect.collidepoint(lx, ly):
            return i
    return None


def _post_key(evt_type: int, key: int) -> None:
    pygame.event.post(
        pygame.event.Event(evt_type, key=key, mod=0, unicode='', scancode=0))


def handle(event, dw: int, dh: int, ox: int, oy: int, scale: float) -> None:
    if not BUTTONS:
        return
    if event.type == pygame.FINGERDOWN:
        lx = int((event.x * dw - ox) / scale)
        ly = int((event.y * dh - oy) / scale)
        idx = _hit(lx, ly)
        if idx is not None:
            _held[event.finger_id] = idx
            _post_key(pygame.KEYDOWN, BUTTONS[idx][1])
    elif event.type == pygame.FINGERUP:
        idx = _held.pop(event.finger_id, None)
        if idx is not None:
            _post_key(pygame.KEYUP, BUTTONS[idx][1])
    elif event.type == pygame.FINGERMOTION:
        if event.finger_id not in _held:
            return
        prev = _held[event.finger_id]
        lx = int((event.x * dw - ox) / scale)
        ly = int((event.y * dh - oy) / scale)
        if not BUTTONS[prev][0].collidepoint(lx, ly):
            _post_key(pygame.KEYUP, BUTTONS[prev][1])
            del _held[event.finger_id]
            idx = _hit(lx, ly)
            if idx is not None:
                _held[event.finger_id] = idx
                _post_key(pygame.KEYDOWN, BUTTONS[idx][1])
