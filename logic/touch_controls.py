"""
touch_controls.py — virtual D-pad for Android touch input.

Converts FINGERDOWN / FINGERUP / FINGERMOTION events into synthetic
KEYDOWN / KEYUP events so input_handler.py works without any changes.

Button strip occupies the bottom 65 px of the 460×600 logical surface,
semi-transparently overlaid on the two bottom board rows.

Button layout (left → right):
  ◄  move left     (K_LEFT,  DAS-repeatable)
  ↺  rotate CCW    (K_z,     single-fire)
  ▼  soft drop     (K_DOWN,  repeatable)
  ▲  hard drop     (K_SPACE, single-fire)
  ↻  rotate CW     (K_UP,    single-fire)
  □  hold piece    (K_c,     single-fire)
"""
import pygame
from constants import SCREEN_WIDTH, SCREEN_HEIGHT

BTN_H = 65
BTN_Y = SCREEN_HEIGHT - BTN_H
_W6   = SCREEN_WIDTH // 6        # 76 px per button

# (rect, pygame_key, display_label)
BUTTONS: list[tuple] = [
    (pygame.Rect(0,       BTN_Y, _W6,                      BTN_H), pygame.K_LEFT,  '◄'),
    (pygame.Rect(_W6,     BTN_Y, _W6,                      BTN_H), pygame.K_z,     '↺'),
    (pygame.Rect(_W6 * 2, BTN_Y, _W6,                      BTN_H), pygame.K_DOWN,  '▼'),
    (pygame.Rect(_W6 * 3, BTN_Y, _W6,                      BTN_H), pygame.K_SPACE, '▲'),
    (pygame.Rect(_W6 * 4, BTN_Y, _W6,                      BTN_H), pygame.K_UP,    '↻'),
    (pygame.Rect(_W6 * 5, BTN_Y, SCREEN_WIDTH - _W6 * 5,  BTN_H), pygame.K_c,     '□'),
]

# Active presses: finger_id → button index
_held: dict[int, int] = {}


def _hit(lx: int, ly: int) -> int | None:
    for i, (rect, _, _) in enumerate(BUTTONS):
        if rect.collidepoint(lx, ly):
            return i
    return None


def _to_logical(event, dw: int, dh: int,
                ox: int, oy: int, scale: float) -> tuple[int, int]:
    """Map a normalised FINGER position to 460×600 logical coordinates."""
    return (int((event.x * dw - ox) / scale),
            int((event.y * dh - oy) / scale))


def _post_key(evt_type: int, key: int) -> None:
    pygame.event.post(
        pygame.event.Event(evt_type, key=key, mod=0, unicode='', scancode=0)
    )


def handle(event, dw: int, dh: int,
           ox: int, oy: int, scale: float) -> None:
    """Route one FINGER* event to synthetic keyboard events."""
    if event.type == pygame.FINGERDOWN:
        lx, ly = _to_logical(event, dw, dh, ox, oy, scale)
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
        lx, ly = _to_logical(event, dw, dh, ox, oy, scale)
        if not BUTTONS[prev][0].collidepoint(lx, ly):
            _post_key(pygame.KEYUP, BUTTONS[prev][1])
            del _held[event.finger_id]
            idx = _hit(lx, ly)
            if idx is not None:
                _held[event.finger_id] = idx
                _post_key(pygame.KEYDOWN, BUTTONS[idx][1])
