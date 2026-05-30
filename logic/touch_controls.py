"""
touch_controls.py — virtual gamepad for Android.

Buttons live in the logical-canvas zone below the game board (y >= SCREEN_HEIGHT).
Call init() once from main() after the display is set up.

Layout (left → right):
  ◀  move left     (K_LEFT,  DAS-repeatable)
  ↺  rotate CCW    (K_z,     single-fire)
  ↓  hard drop     (K_SPACE, single-fire)
  ⏹  hold piece    (K_c,     single-fire)
  ↻  rotate CW     (K_UP,    single-fire)
  ▶  move right    (K_RIGHT, DAS-repeatable)
"""
import pygame

_KEYS = [
    pygame.K_LEFT,   # ◀ move left
    pygame.K_z,      # ↺ rotate CCW
    pygame.K_SPACE,  # ↓ hard drop
    pygame.K_c,      # ⏹ hold
    pygame.K_UP,     # ↻ rotate CW
    pygame.K_RIGHT,  # ▶ move right
]

# (Rect, key) — populated by init(); rects are in logical canvas coordinates
BUTTONS: list[tuple] = []

# Active presses: finger_id → button index
_held: dict[int, int] = {}


def init(canvas_w: int, zone_y: int, zone_h: int) -> None:
    """Set up button rects in logical canvas coordinates."""
    global BUTTONS
    btn_w = canvas_w // 6
    BUTTONS = [
        (pygame.Rect(btn_w * i,
                     zone_y,
                     btn_w if i < 5 else canvas_w - btn_w * 5,
                     zone_h),
         _KEYS[i])
        for i in range(6)
    ]


def _hit(lx: int, ly: int) -> int | None:
    for i, (rect, _) in enumerate(BUTTONS):
        if rect.collidepoint(lx, ly):
            return i
    return None


def _post_key(evt_type: int, key: int) -> None:
    pygame.event.post(
        pygame.event.Event(evt_type, key=key, mod=0, unicode='', scancode=0)
    )


def handle(event, dw: int, dh: int,
           ox: int, oy: int, scale: float) -> None:
    """Route one FINGER* event to synthetic keyboard events.

    Arguments mirror the old letterbox-based signature so input_handler.py
    needs no changes.  With the new width-fill layout ox=oy=0.
    """
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
