# CLAUDE.md — T3TR1S Project Instructions

Standard protocol for every code change, no exceptions.

---

## Push Protocol

Before every `git push`, all five documents must be updated to reflect the changes:

| File | Purpose |
|------|---------|
| `RELEASE_NOTES.md` | Changelog entry for the new version (Added / Changed / Fixed sections) |
| `README.md` | Features list, controls table, scoring table — keep current with the game |
| `DESIGN.md` | Design intent for new systems; update any specs that changed |
| `CLAUDE_REVIEW.md` | Honest critical review of what changed, what it means, rating update |
| `CLAUDE.md` | This file — update if protocol changes |

Version number format: `v1.MAJOR.MINOR` — bump MINOR for any visible change, MAJOR for a significant new system.

---

## Project Facts

- **Language:** Python 3.10+, Pygame 2.5+, NumPy
- **No external assets** — every pixel, sound, and note is generated at runtime
- **Logical resolution:** 460×600 (SCREEN_WIDTH × SCREEN_HEIGHT); scaled to window via `current_scale`
- **State machine states:** MENU, PLAYING, CLEARING, CASCADING, GAME_OVER_ANIM, GAME_OVER, ENTER_NAME, LEADERBOARD, SETTINGS, PAUSED, MUSIC_TEST
- **FPS:** 60, enforced via `clock.tick(FPS)`
- **Board:** 10 cols × 20 rows, `board.grid[row][col]` stores color_id (0 = empty)

## Key Variable Relationships

- `level` drives: scoring multiplier `(level + 1)`, palette phase, 20G gate
- `speed_tier` drives: fall speed (`fall_speed(speed_tier)`); resets when score crosses `next_speed_reset`
- `next_speed_reset`: starts at `SPEED_RESET_INTERVAL` (10k); each reset adds `SPEED_RESET_INTERVAL + speed_reset_count * CASCADE_INTERVAL_GROWTH (5k)` to the threshold
- `reset_bonus_mult`: starts 1.0, +0.1 per speed reset; applied to line-clear scores
- `full_cascade_mode`: toggles on/off each speed reset; True = animated CASCADING state after clears
- `palette_phase`: `((level - 1) // PALETTE_PHASE_INTERVAL) % 6`

## Popup Style Map

```
0  = WOW (board-centred, rainbow)          13 = TETRIS×TETRIS (board-centred, rainbow)
1  = Nice!       2 = Great!                5  = T-SPIN!        6  = T-SPIN MINI
3  = Fantastic!  4 = TETRIS! (rainbow)     7  = B2B TETRIS!    8  = B2B T-SPIN!
9  = Wild!      10 = Woah!   11 = Crazy!  12 = INSANE!
```
Priority: WOW > T×T > B2B T-SPIN > T-SPIN > T-SPIN MINI > B2B TETRIS > INSANE > Crazy > Woah > Wild > normal count

## Files

```
main.py           bootstrap + game loop frame body (~590 lines)
game_state.py     GameState — per-session mutable state, reset() on new game
app_state.py      AppState — shell state across sessions; state-machine constants
game_logic.py     spawn_next, do_hold, start_new_game, end_game, do_lock, etc.
input_handler.py  event dispatch + DAS auto-repeat (handle_input)
renderer.py       all draw_* functions, font cache, rendering constants
rotation.py       SRS wall-kick engine, T-spin detection
game_constants.py gameplay-tuning constants — no Pygame dependency
board.py          grid, collision, line-clear, cascade gravity
piece.py          tetromino shapes, CW/CCW rotation, 7-bag randomiser
constants.py      geometry, NES palette, scoring tables, fall-speed curve
sprites.py        cached block/ghost surfaces; palette_phase keyed
audio.py          PCM SFX synthesis
music_game.py     10-tier adaptive chiptune engine
music.py          menu music (standalone 32-bar composition)
particles.py      particle burst system (intensity 1–4)
game_over_anim.py per-block physics for GAME OVER sequence
highscore.py      JSON top-10 persistence
config.py         settings persistence (config.json)
tests/            pytest unit tests (42 tests, board + scoring)
```

## Code Style

- No comments unless the WHY is non-obvious
- No docstrings on internal helpers
- State transitions are explicit string constants (PLAYING, CLEARING, etc.)
- Rendering separated from logic
- `_font(size)` for all text — cached, never created per-frame
- All block surfaces go through `get_block(color_id, size, palette_phase)` — never built inline
