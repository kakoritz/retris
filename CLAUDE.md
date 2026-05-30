# CLAUDE.md — RETRIS Project Instructions

Standard protocol for every code change, no exceptions.

---

## Branch & Push Protocol

### Branching rules
- **All work goes to `development`** — never commit directly to `main`
- `main` is the public release branch; it is protected and requires a PR to merge into
- CI (GitHub Actions) runs `pytest tests/ -q` on every push to `development` and on every PR targeting `main`
- Only open a PR from `development` → `main` when the feature/fix is QA-complete and CI is green
- Branch protection on `main` blocks force-pushes and direct pushes; PRs require CI to pass

### Workflow summary
```
work locally on development
  → update the five docs below (still on development)
  → git push origin development
  → CI runs automatically
  → open PR development → main (code + docs already committed)
  → merge PR (CI must be green)
```

### Docs to update on development before opening a PR

All five documents must be committed to `development` as part of the change — the PR should arrive at main already complete:

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
- **Logical resolution:** 460×600 desktop · 460×940 mobile (M_CANVAS_H); scaled to display via `current_scale`
- **State machine states:** MENU, PLAYING, CLEARING, CASCADING, GAME_OVER_ANIM, GAME_OVER, ENTER_NAME, LEADERBOARD, SETTINGS, PAUSED, MUSIC_TEST, DEMO
- **FPS:** 60, enforced via `clock.tick(FPS)`
- **Board:** 10 cols × 20 rows, `board.grid[row][col]` stores color_id (0 = empty)

## Key Variable Relationships

- `level` drives: scoring multiplier `(level + 1)`, level theme, 20G gate; `level = lines_cleared // 10 + 1`
- `speed_tier` drives: fall speed (`fall_speed(speed_tier)`); increments by 1 per level-up, capped at 20
- `level_cascade_pending`: set True on level-up; consumed in `tick_clearing` to force CASCADING state
- `level_theme`: `(level - 1) % 10` — index into `LEVEL_THEMES` in constants.py; passed as `palette_phase` parameter throughout renderer/sprites call sites

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
main.py           bootstrap + game loop frame body
game_state.py     GameState — per-session mutable state, reset() on new game
app_state.py      AppState — shell state across sessions; state-machine constants
game_logic.py     spawn_next, do_hold, start_new_game, end_game, do_lock, etc.
input_handler.py  event dispatch + DAS auto-repeat (handle_input)
renderer.py       desktop draw_* functions, font cache, rendering constants
renderer_mobile.py  Android layout (460×950, CELL=33, 4-zone canvas, context buttons)
renderer_web.py   future web/multiplayer renderer stub
ANDROID_BUILD.md  full APK build guide — CI, local build, SIMD fix, troubleshooting
rotation.py       SRS wall-kick engine, T-spin detection
game_constants.py gameplay-tuning constants — no Pygame dependency
board.py          grid, collision, line-clear, cascade gravity
piece.py          tetromino shapes, CW/CCW rotation, 7-bag randomiser
constants.py      geometry, NES palette, scoring tables, fall-speed curve, LEVEL_THEMES
sprites.py        cached block/ghost surfaces; palette_phase (level_theme 0–9) keyed
audio.py          PCM SFX synthesis
music_game.py     10-tier adaptive chiptune engine
music.py          menu music (standalone 32-bar composition)
demo.py           attract/demo mode — 7 scripted scenarios, placement bot FSM
particles.py      particle burst system (intensity 1–4)
game_over_anim.py per-block physics for GAME OVER sequence
highscore.py      JSON top-10 persistence
config.py         settings persistence (config.json)
tests/            pytest unit tests (70 tests, board + scoring + game_logic)
```

## Code Style

- No comments unless the WHY is non-obvious
- No docstrings on internal helpers
- State transitions are explicit string constants (PLAYING, CLEARING, etc.)
- Rendering separated from logic
- `_font(size)` for all text — cached, never created per-frame
- All block surfaces go through `get_block(color_id, size, palette_phase)` — never built inline
