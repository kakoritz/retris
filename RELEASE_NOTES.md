# RETRIS — Release Notes

---

## v2.2.0 — Full Mobile UI Redesign
*2026-05-30*

### Added
- **Context-sensitive button bar** — the 6-button strip changes layout per game state:
  - In-game: LEFT / DOWN / DROP / HOLD / ROTATE / RIGHT
  - Menu / Pause: UP | SELECT (white text) | DOWN
  - Name entry: UP / LEFT / OK / RIGHT / DOWN
  - Game over: single flashing CONTINUE button
  - Leaderboard / Settings / About: animated T-piece MENU button (fires K_ESCAPE)
- **New leaderboard screen** — always shows 10 rows (empty = dashes), large title,
  alternating row backgrounds, no back button text; animated T-piece MENU button
  in the button bar replaces the desktop BACK button.
- **Navigation icons** — new NES block-art UP ▲ and DOWN ▼ arrows for menu navigation.
- **Ghost opacity 40% default on mobile** — was 15% (desktop default).

### Changed
- **Canvas redesigned** — 460×950 (was 965): stats 90px + board 660px + info 100px
  + buttons 100px. CELL=33 (was 40); board fills 74 % of phone width.
- **Stats strip (90px)** — LEVEL in font-46, SCORE in font-30 yellow, LINES font-26.
  Fills the full strip width. Numbers are now clearly readable.
- **Info strip (100px, doubled)** — NEXT1 in prominent left box (cell=18),
  NEXT2-4 smaller in the middle, HOLD in right box (cell=18) with cyan glow pulse.
- **Touch buttons (100px, doubled)** — each button 235px physical height; comfortably
  tappable. Borders, press highlight, icon + label.
- **Pause overlay** — menu items are bold and larger (font-28 for selected item).

### Fixed
- **Game-over overlay centred** — now uses `M_BOARD_W/H` (330×660) not desktop
  `BOARD_WIDTH/HEIGHT` (300×600); text is properly centred on the mobile board.
- **Pause overlay Y-centred** — content centred at board midpoint (y=420 in canvas),
  no longer floating in the upper quarter.

---

## v2.1.0 — Info Strip Below Board, Bigger Score, Side Margins
*2026-05-30*

### Added
- **Info strip (55px) between board and controls** — NEXT pieces on left (NEXT1
  prominent, NEXT2-4 smaller), HOLD piece on right with cyan glow.
- **Side board margins** — 30px margins filled with level-theme–tinted accent color
  + 1px inner highlight line; no longer plain black strips.

### Changed
- **Stats strip** — score font-24, level/lines font-26; bigger than v2.0 strip.
- **Canvas** — 460×965 (stats 60 + board 800 + info 55 + buttons 50).
- **Pause overlay** — Y-centred on board area (first pass).

### Fixed
- **Game-over overlay** — uses mobile board dimensions for centering.

---

## v2.0.0 — Platform-Split Architecture & Mobile Layout Overhaul
*2026-05-29*

### Added
- **`renderer_mobile.py`** — dedicated Android renderer with a completely
  different layout from the desktop: 460×940 logical canvas, 70 px compact stats
  strip at top, full-width board (CELL=40, 400×800), 70 px touch controls at bottom.
- **Compact stats strip (top)** — horizontal band shows HOLD piece, LVL, LNS,
  8-digit SCORE odometer, NEXT 2 pieces, and a PAUSE `II` tap target — all above
  the board so nothing overlaps gameplay.
- **Button-style touch controls** — 6 bordered buttons with press highlight and NES
  block-art icons: LEFT / DOWN / DROP / HOLD / ROTATE / RIGHT. Height is now ~7 %
  of screen instead of the previous ~40 %.
- **Mobile pause button** — `II` in the stats strip; tap target fires K_ESCAPE to
  pause at any time during gameplay.
- **`renderer_web.py`** — documented stub for the planned web portal / multiplayer
  renderer; includes architecture notes and planned multiplayer API design.
- **3-platform architecture** — `renderer.py` (desktop), `renderer_mobile.py`
  (Android), `renderer_web.py` (future web). Shared core: `logic/`, `core/`,
  `sprites.py`, `particles.py`, `game_over_anim.py`.

### Changed
- **Pause removed from touch zone** — pause button now lives in the top stats strip,
  giving more width to the 6 gameplay buttons.
- **Board cell size on mobile** — CELL=40 (vs desktop CELL=30); board is 400×800 px
  logical, fills 87 % of screen width at 2.35× scale.
- **Mobile canvas height** — 940 px (stats 70 + board 800 + controls 70) vs the
  old dynamic value that gave a 40 % wasted touch zone.
- **Dual render path in `main.py`** — desktop path unchanged; Android uses the
  mobile path with scaled floating-label coordinates (× 4/3 scale factor).

### Fixed
- **Demo-mode music stops looping** — `MUSIC_END` event was not handled in the
  `DEMO` state; adding it means the game-music sequence now advances correctly
  during attract/demo mode.

---

## v1.12.0 — Android Touch Controls & Full-Screen Layout
*2026-05-29*

### Added
- **Full-screen Android layout** — game fills the phone's full width; a dedicated touch
  control zone extends below the play area so controls never overlap the board.
- **NES block-art touch controls** — 7 buttons drawn with the same pixel-block renderer
  as the RETRIS logo: LEFT `<`, DOWN `V`, DROP (return-key shape), HOLD, ROTATE `↻`,
  RIGHT `>`, and an animated PAUSE button.
- **Animated T-piece pause button** — far-right of the touch zone; a T-tetromino slowly
  cycles through all 7 piece colours (one colour per 1.5 s). Tapping it pauses the game
  or opens the menu.
- **Touch game-over flow** — tapping anywhere during the GAME OVER animation skips it;
  tapping the GAME OVER stats screen returns to the menu. Previously locked up on Android.

### Changed
- **Touch zone below game board** — controls now live at `y >= SCREEN_HEIGHT` in logical
  space; the canvas is extended (`SCREEN_HEIGHT + touch_zone_h`) and scaled to the full
  display, replacing the old 65 px overlay that covered the bottom board rows.
- **Pause accessible via touch** — K_ESCAPE now has a dedicated button in the touch zone;
  the small in-game gear icon is no longer the only way to pause on Android.

---

## v1.11.3 — Menu Overhaul & Android APK Fix
*2026-05-29*

### Changed
- **Menu layout** — 4-quarter design: title (top 25 %), tetromino tile art (second 25 %),
  menu items (third 25 %), blank breathing room (bottom 25 %). Replaces old cluttered layout.
- **Settings as menu item** — "SETTINGS" is now the third item in the main menu, selected
  with the same NES cursor as START GAME and LEADERBOARD. The icon button is removed.
- **Info button** — tiny white `i` at the far bottom-right corner; unobtrusive but tappable.
- **Pause menu** — replaced button-style with the same NES cursor selector used in the main
  menu: UP / DOWN navigate, ENTER / SPACE confirm. Items: CONTINUE · SETTINGS · QUIT TO MENU.
- **Pause gear icon** — moved from top-right to bottom-right corner for easier thumb reach on
  mobile.
- **"by kakoritz"** — appears inline with the version string at the bottom of the menu
  instead of as a separate element.

### Fixed
- **Android NEON bridge** — pygame's ARM64 build now compiles with `PG_ENABLE_ARM_NEON 1`
  so `alphablit_alpha_sse2_argb_surf_alpha` is correctly resolved in `surface.so`.
- **CI cache poisoning** — added a recipe-hash stamp so a stale cached pygame build is
  detected and purged when the custom recipe changes, preventing the old broken `surface.so`
  from being silently reused across builds.

---

## v1.11.0 — Update Checker, Menu Redesign, Android Build Fix
*2026-05-28*

### Added
- **In-game update checker** — background thread polls GitHub releases API on startup;
  shows update status, version diff, and release notes on the new About screen.
- **About screen** (`A` at menu / tap ⓘ icon) — displays current version, update
  status, and release notes from current → latest. `ENTER` opens download page when
  update available.
- **Menu redesign** — NES-style shadow text throughout; icon-driven layout with ⓘ
  (About) and ⚙ (Settings) circle icons. Two large bordered tap-friendly buttons:
  `START GAME` and `LEADERBOARD`. Replaces cluttered 6-line key hint block.
- **Controls screen** — accessible from Settings row 5; shows full keyboard reference.
- **In-game pause gear icon** — small `II` button always visible at top-right during
  gameplay; tap it to pause on Android (keyboard ESC still works on desktop).
- **Pause screen buttons** — `CONTINUE` (green) and `QUIT TO MENU` (red) tappable
  buttons replace the text-only pause overlay.
- **Mouse / tap routing** — `MOUSEBUTTONDOWN` and `FINGERDOWN` events now checked
  against button hitboxes in all menu and pause states.

### Fixed
- **Android APK build**: `pygame2` → `pygame_ce`; latest p4a (Python 3.14 target)
  no longer compiles pygame2 as a recipe — uses pygame-ce prebuilt Android wheels.
- `INTERNET` permission added to `buildozer.spec` for the update checker.

---

## v1.11.0 — Animated Cascade, Coherent Piece Gravity, Android APK Build
*(this entry is superseded by the one above — version number reused)*

### Added
- **Android APK build pipeline** — GitHub Actions workflow builds a signed debug
  APK on every merge to `main` and publishes it to the `apk-latest` GitHub Release.
  One-tap download and install from any Android phone.
- **Touch controls** — 6-button strip at screen bottom (left, rotate CCW, soft-drop,
  hard-drop, rotate CW, hold) routes FINGER events through the existing input handler
  unchanged. Active only when `ANDROID_ARGUMENT` env var is present.
- **Coherent piece gravity** — line-clear cascades now track which pieces were split
  by the clear (`piece_grid` parallel to `board.grid`). Intact pieces fall as rigid
  units; only cells whose row was cleared fall individually. Boards look physically
  correct during multi-clear cascades.
- **Animated cascade settle** — every cascade step is now visible; speed tied to
  current game speed_tier.

### Changed
- **Level-up cascade** is a right-to-left waterfall freefall: all cells independent,
  columns unlock 9 → 0, running at 2× the normal cascade speed.
- **Cascade indicator** — replaced the full-board `CASCADE!` overlay with a small
  "Cascading..." label in the sidebar bottom-right; teal for coherent, rainbow for
  freefall. Silent during normal play if nothing needs to fall.
- **Wild / Woah / Crazy / INSANE** cascade-level popups removed — cascade is now a
  silent mechanic; only the initial line-clear popup fires.
- `config.py` and `highscore.py` write to `ANDROID_PRIVATE` path on Android so saves
  survive between sessions.

### Fixed
- `CASCADE!` board overlay was drawn every frame during CASCADING — removed entirely.
- "Cascading..." sidebar label appeared even when the board was already settled.
- Cascade entered on every line clear regardless of whether any block was floating.

---

## v1.10.3 — Game renamed to RETRIS
*2026-05-27*

### Changed
- Game title changed from **T3TR1S** to **RETRIS** (retro + tetris) throughout:
  window caption, crash window, GAME OVER letter animation, all in-game text,
  and all documentation.
- The 4-line clear event renamed from **TETRIS!** to **RETRIS!** — the game's
  own term for a quad clear. B2B RETRIS! and RETRIS×RETRIS! updated to match.
- Post-game stat label updated to RETRIS! to match.

---

## v1.10.2 — Demo label: "WOW" renamed to "BOARD CLEAR"
*2026-05-27*

### Changed
- Demo scenario label "WOW! — Perfect Clear" renamed to "BOARD CLEAR! — Perfect Clear"
  so players understand what event just occurred without knowing internal terminology.

---

## v1.10.1 — Demo Polish: Tile Tinting, Color Clear Board, Shorter Pauses
*2026-05-27*

### Changed
- **Demo scenario pause times halved** — wait durations reduced from 2.8–4.5 s to
  1.4–2.5 s. Transitions feel brisk instead of stalling.
- **COLOR CLEAR demo board redesigned** — the trigger row (row 19) is still all cyan
  except the gap column, but rows 8–18 are now scattered with mixed colors (~55 %
  density in lower rows, ~28 % higher up) with ~32 % of those cells being cyan.
  When the I piece fills the gap and fires the Color Clear, the board-wide cyan
  explosion is visually obvious rather than ambiguous.
- **Tile tint blending added** — `_apply_palette` in `sprites.py` now derives a
  directional color tint from each theme's board-cell color (`cell_bg × 10`, capped
  at 255) and blends it into the tile at 18 %. Combined with expanded brightness
  factor range (0.75–1.00, up from 0.88–1.00), tile colors now visibly shift per
  theme — Deep Violet pieces lean purple, Crimson Void leans red/dark, Neon Magenta
  shifts toward magenta and noticeably dims.
- **LEVEL_THEMES tile factors** updated: range expanded from 0.88–1.00 to 0.75–1.00.
  Theme 7 (Neon Magenta) at 0.75 is the darkest; theme 1 (Midnight Blue) stays at
  1.00 as the baseline.

### Tests
- 87 tests passing.

---

## v1.10.0 — Level Themes, Demo Mode, Odometer Score, Level-Up Cascade
*2026-05-27*

### Added
- **10 distinct level themes** — every level gets its own board background color, grid
  line color, and tile brightness factor. Themes cycle every 10 levels (level 11 → theme 1
  again). Names: Midnight Blue, Deep Violet, Forest Deep, Abyssal Teal, Crimson Void,
  Ember, Neon Magenta, Deep Emerald, Cosmic Deep, Solar Dusk.
- **Level-up visual overlay** — large "LEVEL N" text centered on the board, with a pulsing
  themed border flash, on every level increment. Displayed for ~2.8 s.
- **Level-up fanfare** — replaced the 3-beep arpeggio with a full ascending C major scale
  fanfare (~700 ms): sweep → C5 → E5 → G5 → C6 → E6 → C7.
- **Level-up triggers Full Cascade** — every level-up forces a cascade pass after the next
  line clear, giving each level-up a kinetic payoff regardless of current board state.
- **"NEXT LEVEL IN X lines" sidebar countdown** — shows how many more lines until the next
  level increment. Replaces the removed speed-reset countdown.
- **Odometer score display** — SCORE and BEST rendered as 8-digit pinball-style scrolling
  boxes. Each digit scrolls upward when it changes (180 ms animation per digit). Score
  display chases `gs.score` at 8 % per frame with a 150 pt/frame floor.
- **Demo mode** — press `D` at the menu (or wait 60 s of idle) to enter a pre-scripted
  attract sequence. Cycles through 7 scenarios: 1×, 2×, 3× line clear, Tetris, Color Clear,
  WOW (Perfect Clear), Full Cascade. A bot places pieces automatically. "DEMO" overlay +
  scenario label displayed on board. `Space` or `Esc` exits back to menu.
- **Music sequence starts at tier 1** — game music now begins from sparse bass (tier 1),
  so higher tiers feel earned as the sequence progresses.

### Removed
- **Score-based speed-reset system** — `SPEED_RESET_INTERVAL`, `CASCADE_INTERVAL_GROWTH`,
  `reset_bonus_mult`, `next_speed_reset`, `speed_reset_count`, `speed_reset_flash_timer`,
  and `full_cascade_mode` are all gone. Speed tier still increases with level, but there
  are no threshold resets.

### Changed
- Level system: `level = lines_cleared // 10 + 1` — every 10 lines = 1 level up.
- `palette_phase` parameter throughout the codebase now carries `(level - 1) % 10` (0–9
  level theme index), not the old 6-phase darkening counter.
- Cascade scoring simplified: bonus = `500 × (cascade_level + 1)`.

### Tests
- Removed `test_reset_mult_grows_by_point_one` and `test_cascade_interval_grows`
  (both referenced deleted constants). **70 tests passing.**

---

## v1.9.1 — Crash Handler, Debug Sequence, Expanded Tests, CI/CD
*2026-05-27*

### Added
- **Crash handler** (`crash_handler.py`) — any unhandled exception writes two log files
  (`crash_YYYYMMDD_HHMMSS.log` + `crash_latest.log`) alongside `main.py`, prints the full
  traceback to stderr, and opens a pygame crash window showing the error message and log
  path. Game exits cleanly with code 1.
- **Admin debug crash sequence** — typing `b`→`u`→`g` during gameplay deliberately raises
  a `RuntimeError` through the crash handler, exercising the full pipeline (log write +
  crash window) without requiring a real crash. Sequence tracker lives in `AppState._debug_seq`.
- **Expanded test suite** — 30 integration tests added in `tests/test_game_logic.py`
  covering `spawn_next`, `do_hold`, `start_new_game`, `end_game`, `reset_lock`, `do_lock`,
  and `debug_clear_board`. Total: **72 passing tests**.
- **GitHub Actions CI** (`.github/workflows/ci.yml`) — runs `pytest tests/ -q` headlessly
  (SDL dummy drivers) on every push to `development` and on every PR targeting `main`.
  After a green CI run a second job auto-opens a `development → main` PR if none exists.
- **Development branch workflow** — all work targets the `development` branch. `main` is
  protected; direct pushes are blocked and PRs require CI to pass before merge.

### Changed
- `crash_*.log` and `crash_latest.log` added to `.gitignore`.

---

## v1.9.0 — Multi-Module Architecture Refactor
*2026-05-27*

### Changed
- **main.py split into 7 focused modules** — a six-phase architectural refactor
  reduces main.py from ~2,148 lines to 589. Logic, rendering, input, and state are now
  in separate, independently-importable files.
- **`game_constants.py`** — all gameplay-tuning constants (DAS, lock delay, scoring
  tables, kick tables, popup styles). Zero Pygame dependency; safe in unit tests.
- **`rotation.py`** — SRS wall-kick engine and T-spin corner detection extracted as
  public standalone functions.
- **`game_state.py`** — `GameState` class holds all per-session mutable state; call
  `reset()` to start a new game. Replaces ~50 local variables scattered through `main()`.
- **`app_state.py`** — `AppState` class holds application-shell state that persists
  across game sessions (display surfaces, audio volumes, DAS config, leaderboard cache).
  Also owns all state-machine string constants.
- **`renderer.py`** — every `draw_*` function, the font cache, and rendering-only
  constants. Imported into `main.py`; never imports from `main.py`.
- **`game_logic.py`** — `spawn_next`, `do_hold`, `start_new_game`, `end_game`,
  `reset_lock`, `do_lock`, `debug_clear_board`. Former closures with `nonlocal`;
  now standalone functions taking explicit `(gs, app)` parameters.
- **`input_handler.py`** — full pygame event dispatch and DAS auto-repeat in a single
  `handle_input(gs, app, dt)` call. Owns `MUSIC_END` and `INITIALS_CHARS` constants.
- Test suite: 42/42 tests pass throughout the refactor.

---

## v1.8.1 — Dynamic Cascade Timing
*2026-05-27*

### Changed
- **Cascade animation speed now matches current fall speed** — the Full Board Cascade
  wave rate is tied to `fall_speed(speed_tier)` instead of a fixed 80 ms. At the
  start of a game the domino wave is slow and satisfying; as speed increases the
  cascade accelerates proportionally. Capped at 300 ms to prevent extremely slow
  cascades at the lowest speed tiers.

---

## v1.8.0 — Color Clear, Stats, DAS Settings, Combo/Level UX, Drop Scoring, Tests
*2026-05-27*

### Added
- **Color Clear event** — when every cell in a cleared row shares the same color,
  all remaining cells of that color on the board are simultaneously destroyed.
  Triggers a cascade, awards a flat +5,000 bonus, and shows a rainbow "COLOR CLEAR!"
  popup. Genuinely rare (requires a mono-color full row) and spectacular when it fires.
- **Post-game statistics screen** — the GAME OVER overlay now shows: time played,
  pieces placed, Tetrises cleared, T-spins, and best combo streak.
- **DAS / ARR preset in Settings** — new row 4: Slow / Normal / Fast / Instant.
  Controls delay-before-repeat and auto-repeat rate. Persists to `config.json`.
- **Persistent combo indicator** — a "COMBO ×N" line is always visible in the sidebar,
  bright cyan when a streak is active, dimmed when not.
- **Level-up flash** — the sidebar level number briefly turns white for 700 ms on
  each level increment, giving a clear peripheral signal that the level changed.
- **Soft drop / hard drop micro-scoring** — +1 pt per row soft-dropped, +2 pts per
  row hard-dropped (standard Tetris Guideline behaviour).
- **Test suite** — `tests/` directory with 42 passing pytest unit tests covering
  board logic (collision, clearing, cascade gravity, color removal) and scoring
  constants (tables, formulas, multipliers, bonus values).

### Changed
- Sidebar SPEED / FULL CASCADE IN sections shifted down 18 px to accommodate the
  new combo row. NEXT box remains at the same visual position.

---

## v1.7.1 — Settings Accessible from Pause
*2026-05-27*

### Added
- **Settings from pause** — pressing `S` on the pause screen opens the Settings
  screen. Music volume, SFX volume, display scale, and ghost opacity are all
  adjustable mid-game. On exit (Enter or Esc), the game returns to the pause
  screen with 10 % music volume correctly re-applied. The pause overlay now
  shows the `S — settings` hint alongside the existing `Q — exit to menu` line.

---

## v1.7.0 — Cascade Cap, Scaling Reset Interval, Sidebar Cleanup
*2026-05-27*

### Changed
- **Cascade multiplier capped at 4×** — `cascade_mult` was unbounded (`cascade_level + 1`),
  allowing chains of 16+ cascades to produce 17× multipliers that compounded destructively
  with level, danger, and reset bonuses. Cap is now 4× (the INSANE! threshold), keeping
  full-cascade mode exciting without breaking score balance.
- **Scaling reset interval** — the speed reset threshold no longer resets to a flat 10,000
  pts every time. Each subsequent reset adds 5,000 pts to the interval
  (1st = 10k, 2nd = 15k, 3rd = 20k, …). As multipliers accumulate, the next reset becomes
  proportionally harder to reach, keeping pacing meaningful at high scores.
- **Sidebar: 3-line cascade UI → 2-line** — the separate `○/★ FULL CASCADE` indicator line
  is removed. The header now reads "FULL CASCADE IN" with the colour-coded countdown directly
  below. One label explains both the mode and the countdown.

---

## v1.6.0 — 5-Piece Preview, Score Deltas, 20G Alert, Cascade Bonus Fix
*2026-05-27*

### Added
- **5-piece next preview** — the NEXT box now shows piece 1 at full size in the
  top section and pieces 2–5 in a compact 2×2 mini grid below, separated by a
  divider. The queue is drawn from a proper 5-deep `piece_queue` so every preview
  slot always reflects the true upcoming piece order.
- **Score-delta floating labels** — a coloured "+N" label floats up from the right
  side of the board every time a line-clear score is awarded. Colour encodes event
  type: purple = T-spin, gold = B2B, cyan-green = cascade, orange = danger zone,
  white-blue = normal. The cascade-end bonus also shows a delta label.
- **GRAVITY 20G popup** — a fiery orange "GRAVITY 20G" popup appears on the board
  the moment level 20 is reached so the player knows the game mode just changed.
- **Cascade bonus always awarded** — the cascade-end bonus was previously gated on
  `speed_reset_count > 0` (no bonus on first playthrough). It now always pays out
  a base 500 pts + 5,000 per accumulated reset.

### Changed
- **Compact 2-line controls hint** — sidebar controls condensed from 5 lines to 2
  to make room for the taller NEXT box.

### Fixed
- **Cascade bonus countdown stuck at 0** — cascade-end bonus was added to `score`
  outside the reset-check while-loop. The loop now runs after the bonus is applied.

---

## v1.5.3 — Popup Polish, Scaled Explosions, Cascade Fixes, Box Glow
*2026-05-27*

### Changed
- **Popups move onto the board** — all clear-feedback text (Nice!, Great!,
  Fantastic!, TETRIS!, T-SPIN!, cascade labels, etc.) now floats up from
  ~60 % down the board, centred on the play area. Previously they appeared in
  the sidebar out of the player's focal point. WOW and TETRIS×TETRIS were
  already board-centred; everything is now consistent.
- **Scaled particle explosions** — burst intensity scales with row count.
  Single: 2 particles/cell. Double: 3. Triple: 4. Tetris: 6, with larger
  size range and higher velocity cap. Each tier feels meaningfully bigger.
- **Normal cascade uses full block gravity** — previously only completely
  isolated (singleton) blocks fell after a line clear in normal mode, which
  was unpredictable and unsatisfying. Now all floating blocks settle instantly,
  matching standard Tetris variants. Full Cascade mode (toggled by speed reset)
  retains its animated domino-wave treatment with cascade scoring bonuses.
- **Countdown fix** — the "CASCADE IN" counter was stuck at 0 after a speed
  reset because cascade bonus points were added to `score` after the
  reset-check while-loop ran. The check now also runs after the cascade bonus
  is applied.
- **"RESET IN" → "CASCADE IN"** — sidebar label updated for clarity.

### Added
- **NEXT box flash** — the NEXT piece box flashes white for ~220 ms each time
  a new piece is queued, giving a subtle peripheral cue to glance at the preview.
- **HOLD box pulse** — when a piece is in the hold slot the box border pulses
  with a slow cyan glow so the player always knows it's available.
- **Extra box spacing** — more breathing room between labels and piece boxes
  in the sidebar.

### Fixed
- SDL offscreen-mode detection — if the X server is full and pygame falls back
  to the offscreen driver, the game now prints a clear error and exits cleanly
  instead of running invisible while music plays.

---

## v1.5.2 — Animated Cascade, CASCADING State, CPU Safety
*2026-05-27*

### Added
- **Animated full-cascade** — Full Board Cascade mode now plays out as a domino
  wave: one row of blocks falls every 80 ms instead of all blocks teleporting
  instantly. The next piece is blocked until the cascade fully settles.
- **CASCADING game state** — new state between CLEARING and PLAYING that owns
  the cascade animation. Danger detection, music track sequencing, danger line,
  and board rendering all run correctly during cascade.
- **"CASCADE!" overlay** — rainbow-cycling text centered on the board during the
  cascade animation so the player always knows what they're watching.
- **Singleton cascade loop fix** — `apply_singleton_gravity()` now loops until
  no more isolated blocks can fall. Previously a singleton that fell and exposed
  a second singleton above it would leave the upper block floating.

### Files changed
- `main.py` — CASCADING state handler, CASCADE overlay draw, all state-check
  guards updated to include CASCADING

---

## v1.5.1 — Cascade Model, Speed Reset Polish, Sidebar Cleanup
*2026-05-27*

### Added
- **Full Board Cascade mode** — toggles on/off with each speed reset. In this
  mode, after a line clear every block that has empty space below it falls
  (domino gravity). Normal mode uses singleton-only gravity: only isolated
  blocks with no orthogonal neighbours fall.
- **Reset multiplier** (`reset_bonus_mult`) — starts at 1.0 and increases +0.1
  per speed reset. Applied to all line-clear scores. Sidebar shows a ×N.N badge
  next to the speed tier.
- **Cascade bonus** — when the cascade fully settles, awards
  `CASCADE_BONUS_PER_RESET × speed_reset_count` points. Bonus base increases
  by 5,000 per reset.
- **Space-only pause resume** — SPACE is the only key that resumes from PAUSED.
  All other keys are silently ignored (was "any key").
- **"RESET IN N pts" countdown** — replaces the confusing "RST 0 pts" label.
  Turns orange below 2,000 pts remaining, red below 500.
- **Level + Lines combined row** — sidebar fits both onto a single compact line.

### Files changed
- `board.py` — `apply_singleton_gravity()` added
- `main.py` — `full_cascade_mode`, `reset_bonus_mult`, cascade bonus, PAUSED
  handler, sidebar layout, CLEARING handler, `_start_new_game()`

---

## v1.5.0 — Cascade Gravity, Speed Reset, Palette Shift, Page Volume
*2026-05-27*

Six independent systems added in one update. All interact with the existing
scoring hierarchy without breaking it.

### Added
- **Placement score** — each piece locked awards +10 points. Small individually,
  meaningful at high levels and dangerous stacks where every tile counts.
- **Cascade block gravity** — after every line clear, any block that now has
  empty space below it falls. Cascades can produce new full rows, which clear
  again at a multiplier. First cascade: 2×. Second: 3×. Beyond four: "INSANE!".
  Tetris immediately followed by a cascade Tetris triggers the **TETRIS×TETRIS**
  event (4× score, board-centered rainbow popup, lingering like WOW).
- **Speed reset** — fall speed is now tracked on a separate `speed_tier` counter
  independent of level. Every 10,000 points it snaps back to tier 1. A green
  "SPEED RESET!" overlay flashes on the board. The sidebar shows a live
  countdown ("RST N pts") that turns orange below 2,000 and red below 500.
- **Palette shift** — every 10 levels the tile palette darkens by 10 %. After
  6 steps it wraps back to full brightness. The board, live piece, ghost, and
  NEXT/HOLD preview boxes all update together. No change to color identity —
  just luminance so the player feels they've entered a new mode.
- **Page Up / Page Down** — adjusts music volume from anywhere in the game by
  ±5 % per key. No need to visit Settings.
- **Mute now persists** — `music_game.set_muted()` syncs the game-music mute
  flag on every M key press, so mute survives tier transitions and track loops.
- **Zero-gap tier transitions** — `start_sequence()` pre-generates all tier WAV
  files at game start so every tier change is an instant OS-cache read.
- **Alt/Tab/Meta pause filter** — these keys no longer accidentally resume
  the game from the PAUSED screen.

### Cascade popup priority order
`WOW` > `TETRIS×TETRIS` > `B2B T-SPIN` > `T-SPIN` > `T-SPIN MINI` >
`B2B TETRIS` > `INSANE` > `Crazy` > `Woah` > `Wild` > normal clear count

### Files changed
- `board.py` — `apply_block_gravity()`, `settle_blocks()` added
- `sprites.py` — `_apply_palette()`, `palette_phase` parameter on `get_block` / `get_ghost`
- `music_game.py` — `_muted` global, `set_muted()`, mute-aware `_start_tier()`,
  pre-generation in `start_sequence()`
- `main.py` — constants, POPUP_STYLES 9-13, draw functions, CLEARING handler,
  gravity, sidebar, global key handlers, state vars, `_start_new_game()`

---

## v1.4.0 — T-spin, B2B, Combo, 20G
*2026-05-26*

Completes the Tetris Guideline feature set. The game now implements every
standard competitive mechanic.

### Added
- **T-spin detection** (`_detect_tspin` closure in `main.py`) — 3-corner rule against
  the fixed 3×3 bounding box of the T-piece. Full T-spin: 3+ corners occupied. Mini:
  exactly 2 corners occupied, both on the "point side" (`_TSPIN_POINT` lookup table).
  Detection requires `last_action == 'rotate'` — gravity locks, hard drops, and moves
  never award T-spin credit. Detected immediately before `board.place()` in `_do_lock`.
- **T-spin scoring** — separate tables `TSPIN_SCORES` and `TSPIN_MINI_SCORES` (800/1200/1600
  and 200/400 base respectively), all multiplied by `(level + 1)`.
- **Back-to-back multiplier** — consecutive "difficult" clears (Tetris or any T-spin) earn
  1.5× on the line-clear score. A non-difficult clear (single/double/triple without T-spin)
  breaks the chain. `btb_active` flag persists across pieces.
- **Combo counter** — `combo` increments on each consecutive line clear; resets to 0 in
  `_do_lock` when a piece is placed without clearing. Bonus = `50 × combo × (level + 1)`
  per clear (first clear = no bonus; second = 50×; etc.). Floating cyan `COMBO ×N` label
  appears on the board when combo ≥ 2.
- **20G gravity** — at level 20+ (`GRAVITY_20G_LEVEL = 20`), each gravity tick drops the
  piece all the way to the floor instead of one row. Applied on spawn, on each gravity
  tick, and after every lateral move/DAS repeat. Lock delay still applies; hard drop
  remains instant-lock as before.
- **`last_action` tracking** — new state variable set to `'rotate'`, `'move'`,
  `'soft_drop'`, `'hard_drop'`, or `'gravity'` at every piece-movement site. Required for
  T-spin detection; reset to `'gravity'` on piece spawn and hold swap.
- New `POPUP_STYLES` entries: `T-SPIN!` (purple), `T-SPIN MINI` (dim purple),
  `B2B TETRIS!` (rainbow), `B2B T-SPIN!` (bright purple).
- T-spin triple triggers screen shake and max particles (same threshold as Tetris).

### Changed
- CLEARING scoring section fully rewritten to integrate T-spin, B2B, combo, and danger
  multiplier in the correct priority order.
- README scoring table updated with T-spin rows, B2B note, and combo formula.

---

## v1.3.0 — Guideline Mechanics Update
*2026-05-26*

Addresses all core shortcomings identified in the v1.2 gameplay review. The game
now plays to Tetris Guideline standard in every mechanical respect.

### Added
- **7-bag randomiser** (`piece.py`) — replaces pure `random.choice`. Every bag contains
  exactly one of each of the 7 piece types, shuffled before dealing. Worst-case drought
  is now 12 pieces between any two of the same type, vs. theoretically infinite under
  pure random.
- **Full SRS wall kicks** (`main.py`) — `_try_rotate` now uses the Tetris Guideline kick
  tables. JLSZT pieces test 5 offsets per rotation direction; I-piece uses its own table
  with wider horizontal and vertical tests. The O-piece correctly skips kicks. Vertical
  kicks (`dy`) are now tested, eliminating the silent-failure edge cases on floor/ceiling
  rotations.
- **Lock delay** (`main.py`) — 500 ms grace period after a piece touches the stack.
  Any successful move or rotate resets the clock. A cap of 15 resets per piece prevents
  infinite stalling. Hard drop bypasses lock delay entirely (intent is instant commitment).
- **Hold piece** (`main.py`, `draw_sidebar`) — press `C` to hold the current piece.
  Held piece returns to spawn orientation and position. Hold is locked for the remainder
  of the active piece's life and resets when the piece locks. Hold box rendered in the
  sidebar; dims when hold is unavailable.
- **`_start_new_game()` helper** — consolidates all new-game reset logic (board, hold,
  lock state, DAS, popups) into one place, called from every game-start path.

### Changed
- `Piece.rotated_cw()` and `rotated_ccw()` now return `(shape, new_rot_state)` tuples
  instead of just the shape. Call sites updated to unpack with `*`.
- `Piece` now tracks `rot_state: int` (0=spawn, 1=CW, 2=180, 3=CCW), required for SRS
  kick table lookups.
- Controls hint in sidebar updated to reflect `C` hold key.
- README updated: features list, controls table, ghost opacity default corrected to 15 %.

---

## v1.2.1 — Window Icon
*2026-05-26*

- Procedural 32×32 T-piece window icon (`_build_icon` in `main.py`). Rendered at
  startup using the same NES-bevel style as in-game blocks. Set before
  `pygame.display.set_mode` so the OS picks it up on window creation.

---

## v1.2.0 — Debug Cheat + DESIGN.md Finalisation
*2026-05-26*

- Secret 3-2-1 keypress sequence during play triggers a full 20-row board clear,
  firing the WOW perfect-clear event. Undocumented. Useful for testing the WOW path
  without playing to a board clear.
- `DESIGN.md` rewritten in pure declarative language — no first/second person, no
  literal prompt text.

---

## v1.1.0 — Gameplay Systems Expansion
*2026-05-25*

### Added
- **Danger zone** — pulsing red horizontal line at the row-10 boundary. Appears when
  any block occupies the top 10 rows; disappears when the board clears below threshold.
- **Danger bonus** — rows cleared above the red line score 2×. Floating orange ×2
  labels spawn at each qualifying row and float upward with alpha fade.
- **WOW / perfect-clear event** — clearing lines such that the board becomes completely
  empty triggers: full-board rainbow flash (all cells cycle HSV), `!! W O W !!` popup,
  +5,000 × (level + 1) bonus, maximum particles and screen shake.
- **Ghost piece opacity setting** — 0–100 %, default 15 %, persisted in `config.json`.
  `sprites.py` ghost cache extended with opacity as a key dimension.
- **Hold piece display** — *(placeholder in this version; full mechanic in v1.3.0)*

### Fixed
- Pause music volume leak: volume no longer resets to full when a track loop ends
  during pause. `on_music_end()` re-applies the 90 % reduction immediately.
- Escape key in pause no longer exits to menu. Q is now the deliberate exit; any other
  key (including Esc) resumes.
- `BORDER_COLOR` changed from `(80, 80, 120)` to `(185, 185, 220)` — fixes near-invisible
  text throughout the game.
- GAME OVER physics timing: gravity increased, delays tightened so letter impacts sync
  with BOM sounds.
- `DONE_WAIT` defined in `game_over_anim.py` (was referenced but never assigned).

---

## v1.0.0 — Initial Release
*2026-05-24*

- Full Tetris clone with NES-palette tetrominoes, DAS, wall kicks, hard drop, ghost piece
- 10-tier adaptive chiptune music engine, all PCM-synthesised, no audio files
- Danger mode: tier-1 tension track when board fills to top 10 rows
- Per-piece spawn tones + SFX for move / rotate / lock / hard drop / line clear
- Sidebar popups: Nice! → Great! → Fantastic! → TETRIS! (rainbow)
- GAME OVER animation: per-block physics bodies with gravity and bounce
- High-score board: top 10 persisted to `highscores.json`
- Initials entry on qualifying score
- Pause overlay at 10 % music volume
- Music Preview screen (audition all 10 tiers from menu)
- Settings: music volume, SFX volume, display scale (1×–2.5×), ghost opacity
- Resolution scaling: 460×600 logical surface → configurable window size
- Zero external assets: no image, audio, or font files beyond system defaults
