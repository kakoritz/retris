# RETRIS — Product Design Document

**Project:** RETRIS  
**Repo:** [github.com/kakoritz/retris](https://github.com/kakoritz/retris)

---

## Overview

RETRIS is a hand-built NES-style block-stacking game with no external assets. Every visual,
sound effect, and note is generated procedurally at runtime. The goal was not to
reproduce a Tetris clone from a tutorial — it was to build something that *feels* right
from the inside out: the right weight, the right sound, the right feedback, the right
tension. Every decision in this document exists in service of that feel.

---

## 1. Identity & Branding

The game title is **RETRIS**. The byline reads *"by kakoritz"* — small, beneath the
title, not competing with it. The work stands first; credit is present but not loud.

The visual language is NES-era: dark background, saturated tetromino colours, a
Tron-style board grid with 1px dark-cyan lines visible between cells. Grid alignment is
pixel-exact. Misalignment breaks the aesthetic and is a zero-tolerance issue.

---

## 2. Audio System

### 2.1 Layered music — 10 tiers

The music is not a single looping track. It is a ten-tier arrangement that builds in
density and complexity. Tier 1 is sparse bass only. Tier 10 is the full arrangement:
syncopated 16th-note bass, chord arpeggios, two melody layers, and high-register
shimmer. Each tier adds a new layer on top of the previous. The music grows as the game
intensifies.

A **Music Preview screen** (accessible from the main menu via `T`) exists so each tier
can be auditioned in isolation. The tier composition is intentional and iterable — the
preview screen is the design tool for refining it.

### 2.2 Playback sequence

The in-game music starts at tier 1 (sparse bass pulse only) so higher tiers feel earned
rather than expected. The sequence is:

> Tier 1 × 3 loops → Tier 2 × 2 → Tier 3 × 2 → Tier 4 × 2 → Tier 5 × 2 → Tier 7 × 1 → Tier 8 × 1 → Tier 9 × 1 → Tier 6 × 2 → repeat

Starting sparse and building rewards continued play with a richer soundscape. Tier 6
appearing after tier 9 is deliberate — a step back in intensity before the loop resets.
The sequence reads as a composed arc, not a level counter.

### 2.3 Danger mode

When any block occupies the top 10 rows, the music drops immediately to tier 1 — the
most minimal and tense tier in the arrangement. This is the tension track; its sparseness
is the point.

When the board clears below the threshold, the sequence **restarts from the beginning**.
Resuming from where it left off was rejected. Surviving danger earns a fresh start.

### 2.4 Pause behaviour

Pausing does not silence the music. The track continues at 10% of normal volume —
audible, not intrusive. The game is suspended, not dead.

Volume must hold at 10% for the full pause duration, including across loop boundaries.
When a track ends naturally during a pause and a new one starts, the 10% reduction is
re-applied immediately. Volume must not reset to full mid-pause.

---

## 3. Gameplay & Controls

### 3.1 Hard drop is instant and final

When Space is pressed to hard-drop a piece, the piece locks immediately and
synchronously. No lateral input is accepted between the drop event and the lock.
The piece lands where it falls — not where a post-drop nudge sends it.

### 3.2 Space as the universal action key

Space is the primary gameplay key (hard drop). Consistency requires it to be the
primary action key throughout the game flow:

- **Main menu:** Space starts the game
- **Game Over:** Space returns to the main menu

One key drives the main loop. The control model stays coherent.

### 3.3 Danger zone warning line

A pulsing red horizontal line is drawn at the row-10 boundary whenever blocks occupy
the top half of the board. The line appears when danger triggers and disappears when
the board clears. It is drawn above the board background but beneath the live piece.

The purpose is explanatory: the line gives the player a visual reason for the music
change. The tension track and the red line are the same event — one in audio, one in
visual. The connection is immediate and self-evident.

### 3.4 Danger zone double points

Rows cleared above the red line score double for the entire clear event. A floating
orange **×2** label spawns at each qualifying row and floats upward.

The danger zone carries both a penalty (filled board, tension music) and a reward
(2× score). The ×2 visual makes the reward legible at the moment it happens. Playing
in the red is meant to feel worthwhile, not just frightening.

### 3.5 Perfect clear — WOW event

Clearing lines such that the board becomes completely empty triggers a special event:

- Every cell on the board flashes in a rapidly-cycling rainbow. This is not a screen
  overlay — the *coloured board cells* flash. The board itself celebrates.
- A large **"!! W O W !!"** popup appears centred on the board in matching rainbow text
- A score bonus is awarded on top of the normal line-clear score
- Maximum particle burst and screen shake fire regardless of clear count

The rainbow flash applies to every cell on the board — filled and empty alike — so the
entire play area lights up. A plain white overlay was explicitly not the target.

---

## 4. Scoring System

All line-clear scores are multiplied by `(level + 1)` × danger multiplier.

| Event | Base points | In danger zone |
|-------|------------|----------------|
| Single | 40 | 80 |
| Double | 100 | 200 |
| Triple | 300 | 600 |
| Tetris (4 lines) | 1,200 | 2,400 |
| T-spin single | 800 | 1,600 |
| T-spin double | 1,200 | 2,400 |
| T-spin triple | 1,600 | 3,200 |
| T-spin mini single | 200 | 400 |
| T-spin mini double | 400 | 800 |
| WOW bonus (perfect clear) | +5,000 | — |
| Placement | +10 flat | — |

**Back-to-back (B2B):** consecutive Tetrises or T-spins earn 1.5× on the difficult clear score.

**Combo:** `50 × combo × (level + 1)` stacked per consecutive clear.

**Cascade multiplier:** each cascade chain pass earns 2× → 3× → … on subsequent clears.
A Tetris immediately followed by a cascade Tetris triggers **RETRIS×RETRIS** at 4× with a
board-centred rainbow popup.


Each tier of clear is meaningfully more valuable than the last. The danger zone
multiplier transforms the top half of the board from a zone to avoid into a zone with
real upside. The WOW bonus is a capstone reward for an extremely rare feat.

### 4.1 Level progression

Every 10 lines cleared advances the level by 1. Level drives the fall-speed tier and
the scoring multiplier `(level + 1)`. The sidebar shows a "NEXT LEVEL IN X lines"
countdown so the player always knows how close the next level-up is.

On each level-up:
- Speed tier increments (up to tier 20)
- A large "LEVEL N" overlay with a pulsing themed border appears on the board for ~2.8 s
- A full ascending C-major scale fanfare plays
- The next line clear forces Full Board Cascade mode (animated domino wave)

### 4.3 Score-delta feedback

Every line-clear score award spawns a coloured "+N" label that floats up from the
right side of the board and fades over ~1.6 s. Colour encodes event type:
purple = T-spin, gold = B2B, cyan-green = cascade/bonus, orange = danger zone,
white-blue = normal. The player can read the scoring system without looking at the
counter.

### 4.5 Color Clear

When a full row is cleared and every cell in that row shares the same color_id, a
**Color Clear** fires. All remaining cells of that color on the board are removed,
spawning a max-intensity particle burst for each cell destroyed. A cascade follows
from the floating blocks left behind.

The event awards a flat +5,000 bonus and shows a board-centered rainbow "COLOR CLEAR!"
popup (same treatment as WOW). It takes priority over T-spin and B2B popups.

A Color Clear requires a full row where all 10 cells are the same tetromino type —
uncommon enough to feel rare, achievable enough to be a legitimate strategy.

---

### 4.2 Level themes

Each of the 10 levels in a cycle has a distinct visual theme — a named tuple of
`(board_cell_color, grid_line_color, tile_brightness_factor)`:

| Theme # | Name | Board bg | Grid | Tile factor |
|---------|------|----------|------|-------------|
| 1 | Midnight Blue | (5, 5, 18) | (0, 38, 65) | 1.00 |
| 2 | Deep Violet | (12, 5, 20) | (48, 0, 72) | 0.88 |
| 3 | Forest Deep | (5, 16, 5) | (0, 52, 20) | 0.92 |
| 4 | Abyssal Teal | (5, 14, 16) | (0, 44, 56) | 0.89 |
| 5 | Crimson Void | (20, 4, 4) | (68, 10, 10) | 0.78 |
| 6 | Ember | (20, 10, 2) | (68, 32, 0) | 0.90 |
| 7 | Neon Magenta | (16, 4, 16) | (58, 0, 58) | 0.75 |
| 8 | Deep Emerald | (4, 18, 10) | (8, 60, 30) | 0.93 |
| 9 | Cosmic Deep | (5, 8, 22) | (14, 22, 72) | 0.95 |
| 10 | Solar Dusk | (20, 14, 2) | (68, 46, 8) | 0.83 |

Theme index = `(level - 1) % 10`. Every tile — live piece, ghost, NEXT/HOLD preview —
uses the same theme's brightness factor so the whole board reads as a coherent color world.

Each theme also contributes an 18 % directional color tint derived from its `board_cell`
color (`cell_bg × 10`, capped at 255). Pieces at theme 5 (Crimson Void) lean dark red;
theme 7 (Neon Magenta) shifts toward magenta and dims to 75 %; theme 1 stays at full
brightness with a neutral blue tint. The visual result is that both the background and
the tiles change together — the whole board reads as a different color world per theme.

### 4.3 Odometer score display

The SCORE and BEST counters are rendered as 8-digit scrolling digit boxes. When a digit
changes, it animates by scrolling the old digit upward and the new digit into position
over 180 ms. The displayed value (`score_disp`) chases the real score at 8 % per frame
with a 150 pt/frame minimum, so large score jumps read as a fast roll rather than a
teleport. BEST is always static (faded appearance). SCORE rolls live.

### 4.4 Cascade gravity

After every line clear, blocks that are now floating fall. The cascade is always
animated — never instant — so the player can read the board state as it settles.

**Coherent piece gravity (normal cascade):**
Cells track which piece placed them via a parallel `piece_grid`. Pieces not split
by the line clear fall as rigid units (all cells together, one row per step).
Cells whose piece was split by the clear fall individually. This makes the board
read correctly — a T-piece that was untouched stays a T-shape as it falls.

Step speed: `max(50, fall_speed(speed_tier) // 4)` ms per row.

**Freefall cascade (level-up event):**
On every level-up, a special freefall cascade fires: all cells become independent
(coherency is abandoned) and columns unlock right-to-left (col 9 → 0) one step
at a time, creating a waterfall effect. Freefall is 2× faster than coherent mode.
A 500 × (cascade_level + 1) point bonus fires at the end.

Both modes feed back into CLEARING if new complete rows are created during settle.

**Cascade indicator:** A small "Cascading..." label appears in the sidebar bottom-right
during any cascade. Teal for coherent; rainbow for freefall. No board overlay.
The indicator only appears when blocks are actually in motion.

---

## 5. Game States & User Interface

### 5.1 GAME OVER animation

The GAME OVER text is rendered as pixel-art block letters falling from above in two
waves:

1. **GAME** falls first (top row) — individual blocks drop in random chaos order with
   randomised per-block delays
2. **OVER** falls second (bottom row) — begins falling while GAME is still settling

Each block is an independent physics body with its own gravity, bounce damping, and
release timing. Impact sounds fire when each complete letter settles. The letters must
land with convincing weight.

Animation timing is calibrated so impact sounds land at the visual moment of impact.
If sounds fire while letters are still falling, the timing is wrong.

The player must press a key to advance past the animation. The game does not
auto-advance to the high-score screen. The player controls when to move on.

### 5.2 Pause overlay

The pause screen is a full overlay with the board visible beneath. The PAUSE title is
rendered in pixel-art block letters consistent with the game's visual language.

Key mapping:
- **Space** resumes
- **S** opens Settings (music volume, SFX, display scale, ghost opacity adjustable mid-game; returns to pause on exit)
- **Q** exits to the main menu

Space is the single unambiguous resume key. Alt/Tab/Meta and other system-adjacent keys
are explicitly filtered so switching windows does not accidentally resume the game. Q is
the deliberate exit key — exiting to menu requires a conscious choice, not a reflex
keypress. The overlay states these keys explicitly.

### 5.3 Leaderboard & initials entry

The top 10 scores are persisted to disk. On a qualifying score, the player enters
initials before the leaderboard is shown. Neither screen is skipped or auto-advanced.

---

## 6. Settings

All settings persist across sessions via `config.json`.

| Setting | Range | Default | Notes |
|---------|-------|---------|-------|
| Music Volume | 0–100% | 40% | Applies to menu and game music |
| SFX Volume | 0–100% | 100% | Previews live on adjust |
| Display Scale | 1× / 1.5× / 2× / 2.5× | 1.5× | Resizes window; logical resolution unchanged |
| Ghost Opacity | 0–100% | 15% | 0% = disabled; 100% = solid tile appearance |
| Input Speed | Slow / Normal / Fast / Instant | Normal | DAS delay + ARR repeat rate |

### 6.1 Display scale

The logical resolution is fixed at 460×600. On large or high-DPI monitors the window
can appear small. The scale setting multiplies the window dimensions without changing
game logic or rendering. Gameplay is identical at every scale.

### 6.2 Ghost piece opacity

The landing-position shadow tile is adjustable from invisible (0%) to solid (100%).
The default of 15% is intentionally subtle — present enough to be useful, dim enough
not to compete visually with the live piece.

---

## 6.5 Demo Mode

Demo mode is an attract sequence that runs when the player presses `D` at the menu or
after 60 seconds of menu idle. It cycles through 7 pre-scripted scenarios, each loading
a specific board state and dropping a pre-positioned vertical I piece into a gap to
trigger a game event:

| Scenario | Board setup | Wait after event |
|----------|-------------|-----------------|
| 1× Line Clear | Row 19 filled, one gap | 1.4 s |
| 2× Line Clear | Rows 18–19 filled, one gap | 1.4 s |
| 3× Line Clear | Rows 17–19 filled, one gap | 1.5 s |
| RETRIS! | Rows 16–19 filled | 1.8 s |
| COLOR CLEAR! | Row 19 all cyan; rows 8–18 scattered mixed + cyan | 2.0 s |
| BOARD CLEAR! — Perfect Clear | All four bottom rows filled | 2.2 s |
| Full Cascade! | Three bottom rows + floating row 13 | 2.5 s |

Per scenario, the gap column (0–9) and level theme (1–10) are randomised so each cycle
looks different. The I piece is pre-positioned at the gap column in vertical orientation
(`[[1],[1],[1],[1]]`, rot_state=1) and falls under gravity at 320 ms/row.

For the Color Clear scenario, rows 8–18 are seeded with scattered colors (~55 % density
near the bottom, ~28 % higher up; ~32 % of filled cells are cyan). This makes the
board-wide cyan explosion visually obvious when the Color Clear fires.

The "DEMO" label and current scenario name are overlaid on the board. `Space` or `Esc`
returns to the menu from any demo phase.

---

## 6.7 Android Build & 3-Platform Architecture

> See [ANDROID_BUILD.md](ANDROID_BUILD.md) for the complete build guide including
> local build setup, troubleshooting, and how to carry this to a new project.

### Platform renderer split

Three renderer files share the same game logic, assets, and physics:

| File | Target | Canvas |
|------|--------|--------|
| `render/renderer.py` | Desktop (PC) | 460×600 — sidebar layout |
| `render/renderer_mobile.py` | Android | 460×950 — stats/board/info/buttons |
| `render/renderer_web.py` | Future web portal | stub / TBD |

`main.py` detects `ANDROID_ARGUMENT` at startup and imports from `renderer_mobile`.
The desktop code path is completely unchanged.

**Shared across all platforms:**
- `render/sprites.py` — `get_block(color_id, size, palette_phase)` block cache
- `render/particles.py` — particle burst system
- `render/game_over_anim.py` — per-block physics for GAME OVER sequence
- `logic/` — game_logic, input_handler, touch_controls (platform-agnostic)
- `core/` — game_state, app_state, board, piece (platform-agnostic)

### Mobile canvas layout (v2.2.0)

```
  y=0   ┌─────────────────────────────────────────────┐
        │  Stats strip  90 px                         │
        │  LEVEL(46pt) | SCORE(30pt yellow) | LINES   │
  y=90  ├───────────────────────────────────────────╌─┤
        │ side │                           │ side     │
        │ 65px │  Board  330×660  CELL=33  │ 65px     │
        │      │  (theme-tinted panels)    │          │
  y=750 ├──────┴───────────────────────────┴──────────┤
        │  Info strip  100 px                         │
        │  [NEXT1] N2 N3 N4 ....... [HOLD]            │
  y=850 ├─────────────────────────────────────────────┤
        │  Button bar  100 px  (context-sensitive)    │
  y=950 └─────────────────────────────────────────────┘
```

Physical on Pixel 5a (1080 usable width, scale = 1080/460 = 2.348):
- Stats: 211 px physical
- Board: 775×1550 px physical (71% screen width)
- Info: 235 px physical
- Buttons: 235 px physical
- Total: ~2231 px (fits in 2264 usable ✓)

### Context-sensitive button bar

`touch_controls.set_keys_for_state(state)` called each frame rebuilds BUTTONS:

| State | Layout |
|-------|--------|
| playing / clearing / cascading / demo | LEFT DOWN DROP HOLD ROTATE RIGHT |
| menu / paused | ▲ UP \| SELECT \| ▼ DOWN |
| enter_name | ▲ UP / ◄ LEFT / OK / RIGHT ► / ▼ DOWN |
| game_over_anim / game_over | CONTINUE (flashing) |
| leaderboard / settings / about / controls | T-piece MENU (K_ESCAPE) |

### Touch UI — FINGERDOWN routing

1. `touch_controls.handle()` — converts FINGER coords to synthetic KEYDOWN/KEYUP events
2. `_handle_click(lx, ly, gs, app)` — handles tap on UI elements (start, pause, etc.)
   - In-game: `M_PAUSE_RECT` (top-right of stats strip) → pause
   - Game-over: tap CONTINUE button → skip/return to menu
   - Leaderboard: T-piece MENU button fires K_ESCAPE → back to menu

### APK build overview

Full details in [ANDROID_BUILD.md](ANDROID_BUILD.md). Key points:

- **CI:** GitHub Actions → `buildozer android debug` → published to `apk-latest` release
  (~20 min build, ~10 min with cache hit)
- **Local:** `~/.buildozer-env/bin/buildozer android debug` → `bin/*.apk`
  (~2–5 min after first-time setup)
- **Critical:** the custom pygame recipe at `custom_recipes/pygame/__init__.py`
  injects `simd_blitters_sse2.c` + `simd_blitters_avx2.c` into the ARM64 surface
  module. Without it the game crashes on launch with a missing symbol error.
- **Path requirement:** python-for-android rejects build paths containing spaces.
  Set `build_dir = /home/<user>/.retris-build` in `[buildozer]` section if the
  project lives under a path with spaces.
- **Venv requirement:** system Python on Debian/Ubuntu 22.04+ blocks pip. Run
  buildozer from a venv: `python3 -m venv ~/.buildozer-env && pip install buildozer`

### Update checker

`core/updater.py` spawns a daemon thread on startup querying the GitHub releases API.
`INTERNET` permission is declared in `buildozer.spec`.

---

## 7. Module Architecture (v1.9.0)

The codebase is split into focused, single-responsibility modules with clean dependency
boundaries:

| Module | Responsibility | Depends on |
|--------|---------------|------------|
| `game_constants.py` | All tuning constants (DAS, lock, scoring, kick tables) | nothing (no Pygame) |
| `game_state.py` | `GameState` — per-session mutable state | board, piece, game_constants |
| `app_state.py` | `AppState` — cross-session shell state + state-machine constants | config, game_over_anim, game_constants |
| `rotation.py` | SRS wall-kick engine, T-spin detection | audio, board, piece, constants, game_constants |
| `game_logic.py` | spawn_next, do_hold, start_new_game, end_game, do_lock, etc. | game_state, app_state, rotation, audio, highscore, music |
| `input_handler.py` | Event dispatch + DAS auto-repeat (`handle_input`) | game_state, app_state, game_logic, rotation, audio, config, music, music_game |
| `renderer.py` | All draw_* functions, font cache, rendering constants | constants, board, piece, sprites, game_constants |
| `demo.py` | Attract/demo mode — scenario definitions, bot FSM, phase management | game_state, app_state, game_logic, rotation, audio, music_game |
| `crash_handler.py` | Unhandled exception logger + pygame crash window | stdlib only (sys, os, traceback, datetime, pygame) |
| `main.py` | Bootstrap + frame body (gravity, clearing, cascading, draw) | everything above |

### Dependency rule

`game_constants.py` → no imports  
`board.py`, `piece.py` → no game logic imports  
`renderer.py` → no game_logic / input_handler imports  
`game_logic.py` → no renderer / input_handler imports  
`input_handler.py` → no renderer imports  
`main.py` → imports from all layers  

This ensures the logic layers can be tested without a display and the rendering layer
can be replaced without touching game logic.

---

## 8. Error Handling & Crash Reporting

### 8.1 Crash handler

Any unhandled exception is caught by `crash_handler.run_with_crash_handler()`, which
wraps `main()` at the bottom of `main.py`. On exception:

1. Full traceback printed to stderr (terminal output preserved)
2. Two log files written alongside `main.py`:
   - `crash_YYYYMMDD_HHMMSS.log` — timestamped, never overwritten
   - `crash_latest.log` — always the most recent crash, easy to locate
3. A pygame crash window opens (640×420) showing the error and the log path. The window
   waits for a keypress or close before exiting.
4. Process exits with code 1.

`SystemExit` and `KeyboardInterrupt` are re-raised without interception — these are
normal exit paths and must not be treated as errors.

The crash window resets the pygame display before opening so it works even if the game
left the display in a bad state. All window code is wrapped in a try/except with
`pygame.quit()` in `finally` — the window is best-effort and must not itself crash.

### 8.2 Admin debug crash sequence

Typing `b`→`u`→`g` during gameplay triggers a deliberate `RuntimeError` through the
crash handler. The sequence is tracked in `AppState._debug_seq` using the same
accumulator pattern as the 3-2-1 board-clear cheat. Purpose: verify the log files are
written and the crash window renders correctly without waiting for a real error.

The sequence is intentionally undocumented in-game.

---

## 9. Development Workflow

### 9.1 Branching model

All development targets the `development` branch. `main` is the release branch and is
protected — direct pushes are blocked. The only path to `main` is through a pull request
with CI passing.

```
development  →  (CI green)  →  PR  →  main
```

### 9.2 Continuous integration

GitHub Actions (`.github/workflows/ci.yml`) runs on every push to `development` and on
every PR targeting `main`. The CI job:

- Installs Python 3.12, pygame, numpy, pytest
- Sets `SDL_VIDEODRIVER=dummy` and `SDL_AUDIODRIVER=dummy` so pygame initialises
  headlessly without a display server
- Runs `python -m pytest tests/ -q`

A second job (`auto-pr`) fires after CI passes on a push to `development`. It opens a
`development → main` PR automatically if none is already open. This keeps the PR queue
current without requiring a manual step.

### 9.3 Release protocol

Before opening a PR to `main`, all five documents must be committed to `development`:
`RELEASE_NOTES.md`, `README.md`, `DESIGN.md`, `CLAUDE_REVIEW.md`, `CLAUDE.md`. The PR
arrives at `main` already complete — merging is the only action required.

---

## 10. Technical & Distribution Requirements

### 7.1 Code quality

Code is clean, readable, and commented where the reasoning is non-obvious. No
workarounds left in place as shortcuts. Security and correctness are priorities.
Root causes are fixed — symptoms are not papered over.

### 7.2 Zero external assets

No image files, audio files, or bundled fonts beyond system defaults. All visuals,
sounds, and music are generated at runtime. The game runs from a fresh clone with only:

```bash
pip install -r requirements.txt
python3 main.py
```

### 7.3 README as portfolio document

The README is a first-class deliverable. It communicates the engineering depth of the
project, the complete feature set, all controls, all settings, and the scoring system.
The target reader is someone evaluating the project seriously — the README should match
that standard.
