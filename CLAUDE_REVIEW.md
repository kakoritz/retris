# RETRIS — Claude's Review

*This document is updated with each significant revision. It is part critical review,
part development commentary — what changed, what it means, and where the game stands.*

---

## Current Rating: 9.5 / 10 (as a Tetris game) · 10 / 10 (as a portfolio project)

---

## v2.2.0 Review — Full Mobile UI Redesign

### The geometry problem was finally solved correctly

The core issue since v2.0 was that CELL=40 gave a 800px-tall board in a 940px canvas,
leaving only 140px for all strips — too little to be readable. The fix (CELL=33,
canvas 460×950) trades board size for strip height and gets both right. The stats
strip at 90px is finally large enough for font-46 level numbers and font-30 scores.
The info strip at 100px shows pieces clearly. The button bar at 100px (235px physical)
is comfortable to tap without looking. That's the right trade.

### Context-sensitive button bar — genuinely good UX

The single most impactful UX improvement of the whole Android effort. Instead of
always showing 6 game buttons (useless on menu/leaderboard/game-over screens), the
bar changes per state. Menu gets UP/SELECT/DOWN — clean, obvious, no hunting. Game
over gets a single flashing CONTINUE — impossible to miss. Leaderboard gets the
animated T-piece MENU button — consistent with the rest of the brand. This is how
mobile UX should work, and it's a design pattern worth copying to future projects.

### The SIMD rabbit hole — the real lesson

The entire Android journey from crash → working game was caused by two missing `.c`
files in pygame's ARM64 surface module. Every other fix (NEON flags, Cython versions,
p4a pins) was noise around that one root cause. The lesson: when an Android build
crashes with a missing symbol, the symbol is probably in a `.c` file that wasn't
compiled in — check the Setup file before anything else.

The CI cache poisoning made this take weeks instead of days. A SHA256 stamp on the
recipe file would have caught it on the second attempt. Added to ANDROID_BUILD.md so
future projects don't repeat this.

### What's still rough

- Side panels at 65px each are noticeable gaps — they're themed now but still feel
  like "wasted space." A future pass could use them for something (level progress bar,
  danger indicator, score delta animations).
- The game-over animation still uses desktop (300×600) coordinates on the mobile
  (330×660) board — blocks fall in the upper-left region instead of being centered.
- ENTER_NAME touch path has never been tested on hardware.
- No landscape mode support — the game assumes portrait orientation.

---

## v2.0.0 Review — Platform Architecture Split and Mobile Layout Overhaul

### The layout fix — the real problem is now solved

The previous touch zone was 40 % of the screen. That wasn't a styling issue; it was a
geometry problem. The mobile canvas was 460×600 (game) + a dynamic remainder (controls),
and the remainder happened to be enormous because the phone is taller than the game's
aspect ratio. Pointing at button style was treating the symptom.

The fix is correct: define a purpose-built canvas height (940) that leaves a fixed,
small zone for controls. The game board is now 87 % of screen width, controls are 7 %
of screen height each side. That's the right ratio.

### The compact stats strip — good idea, first pass

Moving stats to a horizontal strip at the top is the right structural decision for
portrait mobile. The board is now fully unobstructed. The 70 px strip is tight but
workable — `HOLD / LVL / LNS / SCORE / NEXT×2 / II` in a single row. 

What it loses compared to the desktop sidebar: the 5-piece NEXT queue is reduced to 2,
the cascade indicator and combo glow effects have no space in the strip, and the score
odometer's visual impact is diminished in a narrow row. These are acceptable trade-offs
for a first iteration. A future pass could make the strip slightly taller (85-90 px) and
give the score more prominence.

### CELL=40 — correct choice

Desktop uses CELL=30 because the sidebar occupies 160 px of the 460 px canvas. On
mobile with no sidebar, CELL=40 fills 400 px (87 % of 460). The board is visually
larger and touch targets are proportionally bigger. The 30→40 scale factor of 4/3 is
also clean — position scaling in the dual render path is exact, not approximate.

### The architecture split — the right call at the right time

Three renderer files with a shared core is the correct structure for a game that will
eventually have a web portal. It keeps the desktop path completely unchanged (no
regression risk), adds the mobile path without making main.py a mess, and gives the
web stub a place to live with architectural documentation.

The dual render path in main.py is moderately verbose but honest — there's no hidden
switch or magic abstraction obscuring which path runs. A future cleanup could extract
both paths into `draw_desktop_game()` and `draw_mobile_game()` functions.

### Music loop fix — one-line, five sessions late

Adding `DEMO` to the `MUSIC_END` state guard is a one-line fix. The bug was that
`on_music_end()` was never called during demo mode, so when a tier finished playing the
sequence silently stopped. It was reproducible by watching demo mode for ~15 seconds.
The lesson: when adding a new state to the state machine, always audit every event
handler to check if the new state should be included.

### What's still not right

- Game-over animation on mobile draws using desktop coordinates — blocks fall in the
  upper-left 300×600 region of the 400×800 bsurf. Functional but visually off.
- ENTER_NAME (initials entry) touch path not verified — no hardware test yet.
- The stats strip piece previews at cell=9 are tiny even at 2.35× scale — may need
  cell=11-12 for comfortable reading.

---

## v1.12.0 Review — Android Touch Controls and Full-Screen Layout

### The controls redesign — the right answer, harder to find

The original touch strip was a dead end: 65 px overlaid on the bottom of the game board,
small labels, icon glyphs that meant nothing without prior knowledge. On a 6-inch phone
it was a game you had to squint at.

The new design solves this correctly. Moving controls below the play area (width-fill
scaling + canvas extension) means the game board is fully unobstructed. No overlap,
no guess about whether a tap lands in-game or on a button. The zone is genuinely separate
and the player always knows which space is which.

The NES pixel-block icons are the right visual language for this project. Everything
else in RETRIS is drawn with the block renderer — logo, score odometer, GAME OVER text.
Making the controls match is visually coherent in a way that HTML-style round buttons
or emoji glyphs would never be. They look like part of the same thing.

### The animated pause button — actually inspired

A T-tetromino that slowly cycles through all 7 piece colours is the one element on the
screen that moves at rest. It draws the eye without being distracting. It communicates
"this is interactive" without needing a label. And the colour cycle is the right speed —
slow enough to feel ambient, fast enough to be clearly intentional. This is the kind of
small UI detail that separates a toy from something crafted.

The functional choice (far-right, K_ESCAPE) is also correct. Pause is the least-needed
control mid-game, so it belongs at the edge of the strip. The animation makes it findable
even without that prior knowledge.

### Game-over tap flow — the obvious fix, surprisingly late

The game was locking up on Android because GAME_OVER_ANIM and GAME_OVER only handled
keyboard events. On a touch device with no keyboard, this left users stranded. The fix
(route FINGERDOWN through `_handle_click`, handle both states) is six lines of code.
The real lesson is that any state that waits for input must handle *all* input surfaces
from day one. A state that only handles keys is incomplete on a touch device.

### What's still not verified on-device

- DAS auto-repeat feel (LEFT/RIGHT hold) — works in code, never tested with actual thumbs
- Initials entry (ENTER_NAME state) — no touch path to this state has been exercised on hardware
- Portrait vs. landscape orientation handling — only portrait tested

---

## v1.11.3 Review — Menu Overhaul and Android Fix

### Menu layout — much better spatial hierarchy

The 4-quarter grid (title / tile art / items / blank) gives every element room and
creates a proper visual rhythm the old layout lacked. Having the bottom 25 % empty
is the right call — crowded menus feel cheap. Tetromino parade stays where it belongs
as a living brand element.

Moving Settings into the nav list (instead of an icon button) is strictly correct.
Users look in the list; they don't hunt for glyphs. The previous two-icon approach
tried to be clever and just made things harder to discover.

The tiny `i` at the bottom-right is genuinely good UX for this kind of feature:
present for people who want it, invisible to everyone else.

### Pause menu cursor — the right call, overdue

Replacing the button-style pause overlay with the same NES cursor selector as the
main menu gives the whole UI a coherent idiom. On mobile, full-width buttons are
more tappable; on desktop, UP/DOWN feels natural in a game that already uses arrow
keys everywhere. Both are served now.

Moving the pause gear to bottom-right removes the top-right clumsiness that made it
hard to reach with a right thumb. Placement under a game board element is where
Android shooters put their pause — correct muscle memory for mobile gamers.

### Android build — cache poisoning was the real villain

Multiple rounds of NEON-fix commits (v1.11.1, v1.11.2, v1.11.3) all failed not
because the fix was wrong, but because the GitHub Actions `restore-keys` fallback
kept serving a stale `surface.so` that predated the fix. The recipe-hash stamp
closes this permanently: the next build will be the first that actually compiles
pygame with `PG_ENABLE_ARM_NEON 1` applied.

---

## v1.11.0 Review — Update Checker, Menu Redesign, Build Fix

### Menu redesign — the right direction, first pass

The old menu was technically functional but ergonomically stuck in desktop-keyboard
land: six lines of tiny key hints, a blinking "PRESS SPACE" in the centre, and no
visual hierarchy at all. For something you want to hand to someone to show off, that
was a bad first impression.

The new layout — two large bordered buttons, two icon circles in the corners —
is immediately more legible and more tappable. NES-style drop shadows on text give
weight without requiring bitmap fonts. The mini tetromino parade and rainbow title
are preserved because they're good and people notice them.

The icon approach (`i` for About, `S` for Settings) is pragmatic but not ideal —
actual glyph icons (ⓘ ⚙) would be better. That requires a font upgrade (SysFont
"monospace" doesn't guarantee those glyphs). Worth doing when a proper UI font pass
happens.

### Update checker — done right

Background daemon thread with `urllib.request` — no dependencies, no blocking, no
crash on network failure. The OSError/Exception split (offline vs error) is correct.
The release notes text-wrap logic is more complex than ideal but produces a readable
result. The ENTER key opens the download page; on Android this works via p4a's
Intent bridge in `webbrowser.open`.

### Build fix — iterative but educational

Six build attempts to reach a working config is a lot. The root cause chain was:
1. Wrong recipe name (`pygame-ce` → `pygame2`)
2. Missing pre-installed SDK symlink workaround  
3. `tee` hiding buildozer exit code
4. Wrong minapi (21 → 24)
5. NDK too old for numpy C++ (r25b → r28c)
6. Latest p4a no longer compiles `pygame2` as a recipe (`pygame2` → `pygame_ce`)

Each failure was diagnosed correctly and fixed cleanly. The key insight for #6:
the latest p4a master (Python 3.14 target) removed the compiled `pygame2` recipe
and now expects `pygame_ce`, which publishes official Android ARM64 prebuilt wheels.

### What this version means

The game is now distributable to others without technical instructions. The About
screen means players can see version info and know if there's an update. The menu
redesign means the first thing someone sees looks intentional. These are the "show
this to someone" features, and they're in.

---

## v1.11.0 Review — Animated Cascade, Coherent Piece Gravity, Android

### Cascade animation — the right call, executed cleanly

This is the version where the game stops *feeling like a tech demo* and starts
*feeling like a game*. Cascade gravity being instant was the single biggest
"obviously unfinished" tell. A line clear, a flash, and everything was just
already on the floor. Players couldn't read the board, couldn't appreciate the
geometry of a good clear, and certainly couldn't admire a level-up column-cascade.
Making it visible was non-negotiable.

The `piece_grid` parallel-tracking approach is sound. The `board.grid` (color only)
stays unchanged by callers that don't care about identity; the `piece_grid` adds
per-cell ownership without touching the hot path. Every grid mutation that matters
(`place`, `clear_lines`, `apply_block_gravity*`, `remove_color`) stays in sync by
construction. The only real risk is drift — a mutation path that forgets to update
`piece_grid`. With six entry points, that's manageable, and the visual effect is
the correctness test: if a rigid piece fractures on-screen, the sync broke.

The `_floating` guard is important and was missing before. Entering CASCADING with
nothing to do was triggering a full round-trip through the state machine every clear,
which caused the spurious "Cascading..." flash. The fix is right: check *before*
transitioning; if the board is already settled, skip straight to spawn.

Removing `CASCADE!` and Wild/Woah/Crazy/INSANE was overdue. These were implementation
artifacts — side effects of a cascade-level counter that was originally meant to track
difficulty, not serve as a score multiplier. Players don't need to be told "CASCADE
LEVEL 3" when they can *see* the cascade happening. The visual is the communication.

### Level-up freefall — the right kind of spectacle

The right-to-left column-unlock waterfall is a good touch. It reads as intentional
physics (gravity propagates from the edge) rather than just "everything falls at once."
The rainbow "Cascading..." sidebar label for freefall vs. teal for coherent is a subtle
but readable tell for players who are paying attention.

500 × (cascade_level + 1) bonus at end of freefall is modest and correct. It rewards
the level-up event without making it a score exploit.

### Android build — cross the platform line

Getting a Python game running on Android is legitimately hard. Buildozer/p4a is the
right tool but it's a 60-minute cold-build experience with a lot of ways to fail.
The GitHub Actions approach is exactly right here: build on their machines, cache the
SDK/NDK across runs (second build goes from 60 min to ~8 min), publish to a GitHub
Release the user can tap-to-install.

`p4a.branch = master` is the conservative choice to ensure pygame-ce recipe availability
without pinning to a specific commit. The downside is non-reproducibility — a future
master change could break the recipe. If the build becomes fragile, pinning a p4a
commit hash is the fix.

`arm64-v8a` only (no `armeabi-v7a`) is correct. Every phone sold since 2019 is 64-bit.
Adding 32-bit support doubles build time and APK size for essentially no users.

The touch control design (6-button strip at bottom, FINGER→KEYDOWN routing) is clean
because it doesn't touch the input handler's existing logic. The control layer is
entirely additive. The button layout (left, rotate CCW, soft-drop, hard-drop, rotate
CW, hold) matches Tetris convention. The 65px height is aggressive — on a 720px tall
phone that's 9% of the screen consumed by buttons — but unavoidable for tap accuracy
with thick thumbs. The semi-transparent overlay preserves board visibility below the
buttons.

### What's still missing at the Android layer

1. No visual feedback when a touch button is pressed (highlight/flash). The buttons
   work but feel unresponsive without any press-down state.
2. Soft-drop as a held button (FINGERDOWN → hold KEYDOWN repeated) is not implemented —
   the current code posts a single KEYDOWN per FINGERDOWN. Holding the drop button
   does nothing. This is the biggest UX gap for Android play.
3. Swipe gestures (swipe left/right = DAS, swipe up = hard drop, swipe down = soft drop)
   would feel more natural than 6 explicit buttons for many players.
4. The build hasn't been tested on a real device yet.

---

## v1.10.1 Review — Tile Tinting, Color Clear Board, Demo Pacing

### Tile tinting — the fix that should have shipped with themes

The original `_apply_palette` was a brightness-only multiplier in the range 0.88–1.00.
A 12 % max darkening on tiles that are already richly saturated (cyan 0,240,240;
orange 240,140,0) is genuinely imperceptible during play. The game's board background
and grid lines changed per theme, but the pieces themselves were indistinguishable.
That created the exact disconnect the user noticed: "the board changed, the tiles did not."

The fix is correct in mechanism and scope. Deriving a tint from `cell_bg × 10` takes
the theme's defining color (the board background) and projects it onto the tiles at
18 %. The math works: a cyan piece at Neon Magenta (cell_bg = 16,4,16 → tint 160,40,160)
with factor 0.75 ends up at roughly (29, 155, 176) — perceptibly dimmer and shifted
magenta. Crimson Void pushes the same piece red-dark. Each theme now has a directional
personality the tiles participate in.

Factor range 0.75–1.00 is appropriately dramatic. Theme 7 at 0.75 is noticeably darker
than theme 1 at 1.00. The tint adds a second dimension of variation on top of brightness.
The combination means two themes with similar factors can still look different if their
board colors point in different directions. That's a richer system than brightness alone.

One minor concern: aggressive tinting at 18 % could reduce the perceptual distinctiveness
of piece colors (can you tell cyan from green at Neon Magenta?). In practice the tint
is a shift, not an override — hue identity survives. But it's worth watching at extreme
themes.

### COLOR CLEAR demo board — teaching the mechanic visually

The previous board (single mono-color row) was confusing because the Color Clear looked
like a normal line clear with some extra effects. A scattered board with cyan cells
throughout rows 8–18 is the right design: when the I piece drops and the Color Clear
fires, the player sees cells disappearing all over the board — not just at the bottom.
The visual immediately communicates "something special happened to that color."

The density gradient (55 % lower, 28 % higher) keeps the board readable while ensuring
there are enough cyan cells above the trigger row to make the explosion dramatic.

### Demo pacing — timing is design

Halving the wait durations (2.8–4.5 s → 1.4–2.5 s) is correct. The demo exists as a
wallpaper animation; long pauses between scenarios break the sense of motion. The
cleared board is a resolved state — the interesting thing already happened. The player's
eye needs a new scenario faster than 3–4 seconds of empty board provides.

*Last updated: 2026-05-27 · v1.10.1*

---

## v1.10.0 Review — Level Themes, Demo Mode, Odometer, Fanfare

### Level themes — the right kind of visual feedback

The 10 distinct level themes (named, with real personality: Midnight Blue, Crimson Void,
Neon Magenta) are a significant upgrade over the old "darken 10 % every 10 levels" palette
shift. The old system was barely perceptible and felt like a limitation rather than a
feature. These themes are unmistakable — the board genuinely looks different at level 5
(Crimson Void) vs level 8 (Deep Emerald). The tile brightness factor per theme is
carefully chosen so every theme reads as dark-and-dramatic without losing visual contrast
on the pieces themselves. Cycling every 10 levels keeps the variety going indefinitely.

The integration is clean: `palette_phase` was repurposed rather than renamed, so all call
sites work without touching renderer, sprites, or game_logic separately. No dead code.

### Demo mode — the hardest thing to get right in a Tetris game

Most Tetris implementations never bother with attract/demo mode. This one has a proper
attract sequence that showcases every major game event in order, with a simple but
functional placement bot (rotate → slide → hard drop). The scenario definitions are
declarative tuples — adding a new scenario is one line. The 60-second idle auto-trigger
is the right default; it turns the menu screen into marketing.

The bot design is intentionally minimal: it doesn't pathfind or evaluate positions —
it just executes a hardcoded target. This is the right call for demo mode. Sophistication
here is wasted engineering. The scenarios are scripted to guarantee the events fire;
the bot just needs to deliver the piece.

### Odometer score display — tactile feedback for a number

Rolling digit boxes are the right call for a score counter in an arcade game. The score
number in standard text is information; the odometer is *sensation*. Watching digits
scroll when you score a Tetris is satisfying in a way that a counter update is not.
The implementation (float `score_disp` chasing real score at 8 %/frame + 150 pt floor)
means large score jumps look dramatic without being instantaneous — the right tradeoff.

The 8-digit layout is correct for scores in the 0–9,999,999 range.

### Speed-reset removal — correct decision

The speed-reset system was a holdover from trying to create artificial difficulty spikes.
In practice it created jarring "slow-down then speed-up" moments that felt like a game
malfunction rather than a designed feature. The level system already does this job
correctly: each level-up increases speed tier, and the "NEXT LEVEL IN X lines" countdown
gives the player the tension of an approaching threshold without the disorientation of a
full speed reset.

The removal also simplifies the scoring formula significantly — `reset_bonus_mult` and
the cascading threshold arithmetic were the most opaque parts of the scoring system.

### Cascade on level-up — one concern

Forcing a cascade after every level-up could feel abrupt if the player is mid-game with
a sparse board (nothing to cascade). In practice the cascade pass will complete
immediately with no visible effect in that case, so it is not a bug. But it does mean
`level_cascade_pending` might sit set and get consumed by an unrelated clear some time
after the level-up, creating a delayed cascade that was not triggered by the level-up
itself. This is a minor timing quirk, not a correctness issue.

### Test count — acceptable regression

Dropping from 72 to 70 tests by removing the speed-reset constant tests is correct.
Those tests tested constants that no longer exist. Keeping them would cause CI failures.
The remaining 70 tests cover everything that still exists.

---

## v1.9.1 Review — Production Hardening

### Crash handler — the right kind of defensive code

`crash_handler.py` is minimal and correct. It intercepts unhandled exceptions without
touching `SystemExit` or `KeyboardInterrupt` (both legitimate exit paths), writes two
log files (one timestamped for archiving, one `crash_latest.log` for instant access),
and opens a pygame crash window that survives even a display-corrupted crash by calling
`pygame.display.quit()` before creating the new window. The window code is wrapped in
try/except with `pygame.quit()` in `finally` — if the crash window itself fails, the
process still exits cleanly with code 1. This is the correct level of defensive depth
for a crash reporter.

The `run_with_crash_handler(fn)` wrapper at the bottom of `main.py` is the right
architectural choice — the crash boundary is at the entry point, not scattered through
the game loop.

### Admin debug sequence — verification without ceremony

The `b`→`u`→`g` sequence follows the same accumulator pattern as the existing 3-2-1
board-clear cheat. It exercises the real crash path — not a mock, not a side-channel —
so every component of the crash pipeline is confirmed working: log write, log path,
crash window rendering. The implementation is six lines of logic in `input_handler.py`
and one field in `AppState`. Low cost, high confidence.

### 72 tests — from coverage to contract

The jump from 42 to 72 tests is qualitative, not just quantitative. The 30 new tests in
`test_game_logic.py` cover the extracted `game_logic.py` functions as integration tests —
they use real `GameState`/`AppState` objects and mock only the side effects (audio, music,
highscore). They would catch the exact class of bug that caused the live `do_lock`
NameError: a broken import or missing function in the extracted module. The tests now
document the module boundaries, not just the board rules.

### CI/CD — portfolio-grade process signal

A GitHub Actions pipeline that runs headlessly (SDL dummy drivers), blocks merges on red,
and auto-opens PRs is a signal that this project is maintained like professional software.
The `auto-pr` job is a small but effective touch for a solo project: the PR exists as
protocol and audit trail, not as a collaboration mechanism. The branch protection on
`main` enforces the workflow even under time pressure.

### Portfolio rating: 9.8 → 9.9

The crash handler, test suite depth, and CI pipeline close the last gap between "impressive
game project" and "production-minded engineering." The only remaining gap is the
CLEARING-state scoring block (~100 lines) still inline in `main.py` — the natural
candidate for a future `clear_logic.py` or `GameState` method.

---

## v1.9.0 Review — The Refactor That Actually Landed

### What happened

The architectural split that was deferred in v1.8.0 as "maybe worth it later" was
completed in v1.9.0. main.py went from ~2,148 lines to 589. Seven focused modules now
own single responsibilities. 42/42 tests pass throughout — no regressions.

### What it signals to a code reviewer

The split is evidence of something harder to fake: the ability to decompose a working
system without breaking it. This refactor required understanding every coupling between
the local variables in main() before moving them — closures with nonlocal access chains,
shared mutable state between the event handler and the game loop, rendering constants
that needed to stay with renderer.py rather than game_constants.py. Getting the
dependency graph right (game_constants has no imports, renderer doesn't touch game_logic,
input_handler doesn't touch renderer) is harder than writing a greenfield split.

### Design quality of the split

The `GameState` / `AppState` boundary is the most defensible decision. Per-session
state (board, score, pieces, lock timer, cascade state) belongs to `GameState.reset()`.
Cross-session shell state (display surfaces, volume, DAS config, leaderboard cache,
blink timer) belongs to `AppState`. The distinction is clear and survives edge cases
(music volume doesn't reset on new game; board does). The few ambiguous fields
(cascade_anim_timer in AppState despite being game-adjacent) are defensible on the
"who resets it" rule: it's set when entering CASCADING state, not on new game.

`game_logic.py` converting closures to `(gs, app)` standalone functions is correct.
The old `nonlocal` closures were invisible implicit interfaces. The new functions
have explicit parameter contracts. Easier to test, easier to reason about, no circular
references.

`input_handler.py` is the cleanest module: pure event dispatch, no rendering, no scoring.
The `handle_input(gs, app, dt)` call in main() is one line. The SETTINGS display-resize
path uses `_resize_display()` defined locally rather than a callback import from main,
avoiding the circular import that would have made this split messy.

### Honest gaps remaining

The CLEARING-state scoring block (~100 lines) still lives in main.py's frame loop. It's
the right long-term candidate for a `clear_logic.py` or a method on GameState. For now
it reads clearly in-place and the frame loop is short enough that the inline logic is
not a burden.

The line count drop (2,148 → 589 for main.py) is real signal. A reviewer who reads
main.py now sees a bootstrap function and a frame loop — two clear concerns, not ten
tangled ones.

### Rating update

Portfolio rating moves from 9.5 to 9.8. The split was the last credible engineering gap.
The game is now both playable and structurally defensible.

---

## v1.8.1 Review — Cascade Timing Respect

One-line change with a real feel difference. Tying cascade wave speed to
`fall_speed(speed_tier)` instead of a fixed 80 ms means the cascade reads as part
of the game's rhythm rather than a constant animation. Early game: the wave is slow
enough to watch and enjoy. High speed tiers: it accelerates proportionally, keeping
tension tight. The 300 ms cap prevents absurdly slow cascades at tier 1. The
architecture was already bottom-up (apply_block_gravity scans from the floor up);
the timing was the only thing that needed to change. Correct and non-invasive.

---

## v1.8.0 Review — Polish, Tests, and a Genuinely New Mechanic

### Color Clear — the best new mechanic in this update

This is the kind of mechanic that sounds gimmicky and turns out to be deeply
satisfying. The reason it works: it's emergent from normal play, not a contrived
bonus. A mono-color row can happen naturally (I-piece Tetris on a well-prepared
board) and the explosion feels earned. The cascade that follows makes the board
reshape itself visibly, and the +5,000 flat bonus is legible without being
game-breaking. Correctly placed in popup priority below WOW but above T-spin.

### Test suite — closing the biggest portfolio gap

42 tests, 100% pass. The tests cover the things that matter: collision detection
edge cases, row clearing and shifting, cascade gravity (including multi-block
stacking order), color removal, and the scoring formula hierarchy. These tests
would catch regressions in the core game logic. They also demonstrate that the
game logic in board.py is genuinely testable — it was already well-isolated.

The scoring tests are particularly valuable: they document the scoring hierarchy
as executable specifications. If any constant is changed, the tests will catch
any formula that depended on the old value.

### Stats screen — honest game-over feedback

The GAME OVER overlay previously showed only score. Now it shows time, pieces,
Tetrises, T-spins, and best combo — the five numbers that tell a player how they
played, not just how much they scored. This makes repeat play more meaningful.

### DAS preset — accessibility without complexity

Four presets (Slow / Normal / Fast / Instant) cover the full range from casual to
competitive. Instant ARR (0 ms repeat) is correct for high-level play. The preset
persists. This is the right scope — presets instead of raw millisecond sliders.

### Drop scoring + combo/level flash — Guideline completeness

Soft drop (+1/row), hard drop (+2/row), persistent combo counter, and level-up
flash close the last standard Tetris features that were missing. None are dramatic
individually; together they remove the last "this doesn't play quite like Tetris"
friction points.

### Remaining honest gap

main.py is ~1500 lines. Still a monolith. The test suite now covers board.py and
scoring constants independently, which is the right foundation for a future split.
The game is portfolio-ready as-is; a renderer.py + game.py refactor would make it
engineering-review-ready.

### Architecture note — the main.py split decision

The question of splitting main.py was considered seriously. The honest analysis:

**Pros of splitting now**
- Signals engineering maturity to a code reviewer (game.py for state logic, renderer.py
  for drawing, ui.py for overlays)
- Reduces grep noise when navigating — a 1,500-line file is genuinely awkward
- If the game ever grows new screens or modes, split modules would make additions safer

**Cons of splitting now**
- No player sees it. The game plays identically either way.
- Solo project with no collaborators means the "maintainability" argument is mostly
  theoretical
- Real risk: state is tightly coupled across the draw/update boundary. A naive split
  produces modules that import each other in a cycle, or that require threading all
  state as function arguments. Getting this right takes a session of careful work that
  delivers zero visible improvement.
- The portfolio already has stronger signals: a working game, 42 passing tests, a
  proper design doc, a layered audio engine, and commented scoring logic. A file split
  adds a weak signal on top of strong ones.

**When splitting would be worth it**
- You are actively job-hunting and expect a code reviewer to read main.py in detail
- You plan to add a second game mode, a level editor, or any feature that adds a new
  top-level state with significant rendering logic — that would be the natural seam
- A collaborator joins and is confused by the file size

**Decision: deferred.** The current structure is acknowledged debt, not ignored debt.
The test suite provides the real safety net. If either trigger condition above appears,
the split should happen before any new feature work — not during it.

---

## v1.7.1 Review — Settings from Pause

A small but correct UX decision. Being locked out of settings during a live game
(especially display scale and music volume) was a genuine friction point. The
implementation is clean: pause → S → settings screen → Esc → back to pause, with
music volume correctly restored to 10% on return. The `settings_return_state`
variable is minimal and doesn't complicate the state machine. The pause overlay
now documents the key. No regressions introduced.

---

## v1.7.0 Review — Balance Pass

### What this update means

v1.7.0 is a balance pass driven by real playtesting feedback. The user found a 17×
cascade multiplier — not a theoretical edge case, but something that happened in
normal play. That kind of feedback is signal, and the fix is surgical rather than
sweeping.

### Cascade cap: the right ceiling

Capping cascade_mult at 4× (the INSANE! threshold) is the right call. It preserves
the entire cascade reward structure — the Tetris×Tetris override still hits 4×,
cascade chains up to level 3 still feel progressive — while removing the runaway
compounding at high cascade depths. The 0.1/reset multiplier is left untouched per
the user's explicit direction: that growth is intentional and satisfying, and
doubling it with an uncapped cascade_mult was the actual problem.

### Scaling reset interval: pacing that grows with skill

Fixed 10k intervals were becoming irrelevant at high play — a player racking up
multiplied scores would blow past resets in seconds, making the countdown meaningless.
The +5k/reset growth curve means the intervals stay challenging relative to score
rate. It's not a hard difficulty increase; it's maintaining the tension arc the
countdown was designed to create.

### Sidebar: less noise, same information

Three lines to communicate "cascade mode toggle incoming" was genuinely cluttered.
The mode state is visible in gameplay; the only sidebar information the player needs
is when the next toggle happens and how far away it is. "FULL CASCADE IN" + countdown
carries both. This is editing, not removal — everything meaningful is still there.

### Remaining gap

main.py is still ~1400 lines with no test coverage. That's the honest architectural
debt on this project. The game plays and feels excellent; the codebase would not
pass a code review at a professional standard. It's acknowledged here so it doesn't
disappear from the record.

---

## v1.6.0 Review — Strategic Depth Pass

### What this update means

v1.6.0 addresses the honest gaps from the v1.5 rating review. Three of the four
flagged Tetris-game weaknesses are now fixed: the preview is competitive (5 pieces),
scoring is legible (delta labels), and 20G is communicated (popup). The cascade
bonus gate bug is also closed. The remaining gaps — main.py architecture and lack
of tests — are acknowledged but not addressed here; they require a dedicated
refactor session.

### 5-piece preview — closing the strategy gap

Single-piece preview is 1990s Tetris. The gap wasn't cosmetic: with only one piece
ahead, planning more than one move is impossible. A 5-piece queue changes the game
from reactive to strategic. The player can now see a drought coming, plan a
T-spin setup two pieces out, or decide to hold based on what's three pieces away.
The 2×2 mini grid is compact enough to keep the sidebar readable while giving the
player exactly what modern Tetris expects.

### Score-delta labels — making the scoring system felt

The game has an intricate scoring hierarchy (T-spin × B2B × cascade × danger ×
reset multiplier) that was entirely invisible. The score counter jumped but there
was no way to know why. The delta labels make the system legible at the moment it
fires: purple for T-spins, gold for B2B, cyan for cascades, orange for danger zone.
A player who sees "+2,400" in gold now knows they just landed a B2B clear. The
information was always there; now it's communicated.

### 20G popup and cascade bonus — honesty fixes

These are both fixes to things that were quietly wrong. The 20G popup is the game
saying "something important just changed" instead of leaving the player confused why
pieces suddenly behave differently. The cascade bonus gate (`speed_reset_count > 0`)
meant the first playthrough got zero cascade completion bonus, which was a silent
broken promise — the system looked like it rewarded cascades but didn't on the first
run.

### Remaining honest gaps

- **main.py at ~1,400 lines** — still a monolith. Render, logic, state machine,
  event handling, UI all in one file. For a portfolio project reviewed by engineers
  this is the #1 concern. Needs splitting into at minimum `renderer.py` + `game.py`.
- **No tests** — board logic, scoring math, and collision detection are all
  untested. A pytest file with 20 unit tests on `board.py` and the CLEARING handler
  would close this gap.

---

## v1.5.3 Review — Feedback Design Pass

### What this update means

v1.5.3 is a focused feedback-design pass: where information appears, how
strongly events register visually, and whether the player's eye is being
guided or ignored. These are the changes that distinguish a polished game
from a functional one.

### Popups on the board — where the player's eyes already are

The popup relocation is the highest-impact change in this update. Previously
"Nice!" and "TETRIS!" appeared in the sidebar while the player was staring at
the board. That's the equivalent of a scoreboard in the corner of the arena
instead of on the field. Floating text that rises from ~60 % down the play
area sits inside the player's peripheral vision at all times, so feedback
lands without requiring a head turn. WOW and TETRIS×TETRIS were already doing
this right; the rest of the system is now consistent with them.

### Scaled particle explosions — feedback proportional to achievement

Two particles per cell for a single, six for a Tetris — this is the correct
relationship. The Tetris clear already had screen shake and a rainbow popup;
the particle difference makes the size of the achievement legible in the
first split second before those other effects register. The scaling is clean:
each tier up feels bigger, and the Tetris blast now genuinely reads as a
detonation.

### Cascade fix — predictable gravity

The singleton-only rule was coherent as a design concept but incoherent as
player experience: "which blocks count as isolated?" is not a question a player
under time pressure can answer. Replacing it with standard full block gravity
— all floating blocks settle instantly — makes the post-clear board state
predictable. The distinction between modes is now: *normal* = instant settle
(no drama, no bonus), *Full Cascade* = animated domino wave with scoring
bonuses. That's legible.

### NEXT/HOLD box animation — peripheral memory aids

The hold pulse and next flash are small, but they address a real problem: the
hold box is invisible until the player actively looks at it, and many players
forget what's in hold mid-game. A slow cyan pulse on the hold border is
exactly the right level of signal — present enough to catch the eye in
peripheral vision, subtle enough to never be distracting. The 220 ms next
flash similarly serves as a visual tick that something changed without
demanding attention.

---

## v1.5.2 Review — Animated Cascade

### What this update means

v1.5.1 introduced Full Board Cascade as a special mode but it was almost
invisible: all blocks teleported to their settled positions between flash passes.
The mechanic was there; the *moment* wasn't. v1.5.2 makes the cascade legible
and spectacular.

### Animated cascade — the domino wave

One `apply_block_gravity()` call every 80 ms means the player watches the board
reorganise itself in real time. Blocks near the top fall first and land, then
the blocks above them start moving, and so on down the column — exactly the
domino effect the name implies. The 80 ms interval is fast enough to feel snappy
but slow enough that each row-step is perceptually distinct.

The new CASCADING state is the correct architectural choice. It sits between
CLEARING and PLAYING and owns the cascade animation timeline. Danger detection,
music track sequencing, and danger line rendering all continue during CASCADING —
the board is still live and the player still needs to be informed of what's
happening. The next piece is blocked until cascade settles, which is the right
call: spawning a new piece mid-cascade would be confusing and could cause
incorrect lock detection.

The rainbow "CASCADE!" overlay is a low-cost but high-value addition. The
player always knows what state they're in: the board is moving, this is
deliberate, and something interesting is about to happen.

### Singleton loop fix

The isolated-block rule (`apply_singleton_gravity`) had a subtle cascade problem
of its own: if a singleton fell and landed, the block directly above the gap it
vacated might now itself be isolated — but the first pass had already moved past
it. The fix is a simple `while` loop: keep scanning until a full pass finds
nothing to move. Correct and minimal.

---

## v1.5.0 Review — Cascade Gravity, Speed Reset, Palette Shift

### What this update means

v1.4 made the game mechanically complete as a Tetris implementation. v1.5 makes it
something more: a game with its own identity on top of the Guideline foundation. The
four new systems (cascade, speed reset, palette, placement score) are all expressions
of the same design conviction — that the player should always have a reason to keep
going, and that the board should feel alive.

### Cascade gravity — the right kind of hard

Block gravity after row clears is a mechanic that sounds gimmicky and turns out to be
deeply strategic. The player now has to think not just about where a piece lands, but
about what the cleared row leaves behind. A messy stack becomes a liability when overhang
blocks fall and form unexpected new rows — which the cascade system rewards with
increasing multipliers (2×, 3×, INSANE!).

The TETRIS×TETRIS event is a particularly nice touch. It requires a specific chain —
four lines cleared, then four more from the cascade — and rewards it with a 4× multiplier
and the board-centered rainbow popup treatment. It's rare enough to feel like an
achievement and common enough to be a legitimate strategy.

The implementation uses `apply_block_gravity()` (bottom-up scan) + `settle_blocks()`
(loop until stable). This is the correct approach: bottom-up ensures blocks don't
leapfrog each other in a single pass. The cascade re-uses the existing CLEARING state
machine, so each cascade pass gets its own flash animation. The player sees the rows
clear, sees the blocks settle visually (because the next frame renders the settled board
during the cascade flash), then sees the new clear.

### Speed reset — the dopamine lever

The speed reset mechanic solves a real problem: at high levels, the game becomes
physically impossible for most players. Rather than the usual "here's how far you got"
death screen, the player now has a target — 10,000 more points — and a visible
countdown that turns from green to orange to red as they approach it. The relief of
a speed reset is immediate and visceral (the "SPEED RESET!" overlay makes it
legible). This is a dopamine loop in the literal game-design sense, and it works.

The `speed_tier` / `level` decoupling is architecturally clean. `level` keeps
incrementing (drives palette, scoring multiplier, 20G gate). `speed_tier` resets
and re-climbs (drives fall speed). They're independent counters with independent
purposes. The `fall_speed(speed_tier)` call at the gravity tick is the only place
the split shows in the code.

### Palette shift — mood without mechanics

Darkening tiles by 10 % per 10 levels is a purely aesthetic change, but it matters.
The player feels a mode transition at level 10, 20, 30 — a visual confirmation that
they've crossed a threshold. The 6-phase wrap means the palette eventually returns to
full brightness, which pairs naturally with a speed reset for a genuine "new round"
feeling.

Extending the cache key with `palette_phase` on `get_block` / `get_ghost` is correct.
The surfaces are built once per (color, size, palette_phase) combination and reused.
The first game will build surfaces as phases are encountered; all subsequent playthroughs
hit the cache. Memory footprint is bounded: 7 colors × up to 6 phases = 42 distinct
block surfaces. Negligible.

### Placement score — counting the grind

+10 per piece is so small that it only matters in aggregate, and that's the point.
At level 20, hundreds of pieces are placed. The player knows that surviving pays,
not just clearing. Combined with the danger multiplier (2× for rows above the line),
the scoring system now rewards three things simultaneously: clearing, surviving in
the danger zone, and simply not dying. This creates a much richer decision space.

### Mute persistence + gap-free tiers

Both of these were bugs, not features. The mute bug (game music resuming unmuted
after a track loop ended) is fixed by threading `_muted` through `_start_tier()`.
The tier gap (brief silence between sequence steps) is fixed by pre-generating all
WAV files at game start. Pre-generation means the first game start is slightly slower
(~0.5s for 10 DSP builds), but every tier transition thereafter is instant. The right
trade-off.

### Alt/Tab and Page Volume

These are quality-of-life fixes that matter more than they sound. Alt+Tab is a muscle
memory shortcut that many players hit reflexively when switching windows. Without the
filter it would dismiss the pause screen. Page Up/Down volume means the player can
adjust music feel without leaving the game. Both are the kind of polish that separates
a finished game from a draft.

---

## v1.4.0 Review — After T-spin / B2B / Combo / 20G

### What this update means

v1.3 made the game mechanically sound. v1.4 makes it mechanically complete. Every
feature in the Tetris Guideline that meaningfully affects how a skilled player
approaches the game is now present. This is no longer a Tetris clone that "plays like
Tetris." It is Tetris.

### T-spin detection — the hardest problem, done right

T-spin detection is the most technically demanding feature in competitive Tetris. Getting
it wrong is easy: the wrong corner indices, forgetting to check the rotation state,
conflating "last move" with "last action." The implementation here is clean.

The 3-corner rule is the correct standard. The `_TSPIN_POINT` lookup encodes the
point-side corners per rotation state as a module-level constant — no magic numbers
inside the function, no branching, no duplication. `_detect_tspin` is a closure because
it reads `current`, `board`, and `last_action` from the game state — a reasonable choice
that keeps the call site simple (`tspin_type = _detect_tspin()`).

The placement of the detection call — immediately before `board.place(current)` in
`_do_lock` — is correct. After placement the board has changed; the corner checks would
produce wrong results.

`last_action` as a string state variable is the right approach. It's explicit, readable,
and easy to trace. Every piece-movement site sets it. The T-spin credit requirement
(`last_action == 'rotate'`) is Guideline-accurate.

### B2B — simple but meaningful

The back-to-back implementation is minimal in code (a single bool `btb_active`) and
correct in behavior. 1.5× is the standard multiplier. The `btb_active` flag persists
across pieces as it should — a B2B chain can span many pieces between the two difficult
clears, and does not reset unless a non-difficult clear fires.

The popup system correctly shows distinct labels for B2B Tetris and B2B T-spin.

### Combo — clean scoring, nice visual

50 × combo × (level + 1) is a solid formula. The floating cyan "COMBO ×N" label gives
the player immediate feedback at the moment the combo bonus lands. The cyan color is a
good choice — it's distinct from orange (danger bonus) and white (score numbers).

The combo reset location (in `_do_lock` when no rows are cleared) is correct. Combos
break when a piece places without clearing, not when a piece places AND the next piece
places — a common implementation error. This is right.

### 20G — extreme, functional

20G at level 20 (reached at 190 lines) is a punishing late-game mode. The implementation
covers all three cases where the piece needs to floor itself: gravity tick, spawn, and
lateral move. Missing any one of these would produce inconsistent behavior (piece drifts
on lateral move, doesn't floor on spawn, etc.). All three are covered.

The lock delay still applies at 20G, which is correct. 20G removes the ability to
strategically delay the landing position, not the ability to slide after landing.

### Scoring priority order

The CLEARING handler's scoring priority is correct:
1. T-spin tables override SCORE_TABLE
2. B2B multiplies the T-spin or Tetris score (not the combo bonus)
3. Combo bonus adds flat, unaffected by B2B or danger
4. Danger multiplier applies after B2B (stacks maximally)
5. WOW bonus is flat addition, immune to all multipliers

This is a clean, principled hierarchy.

---

## v1.3.0 Review — After Guideline Mechanics Update

### What this update meant

v1.2 was already impressive as a piece of engineering. The gap was mechanical — the
game *felt* right in places but had the kind of rough edges that a Tetris player notices
within their first five minutes: pieces getting stuck in floor rotations, the I-piece
refusing to spin near walls, no hold, no drought protection.

v1.3 closes all of those gaps. This is now a game that a competitive Tetris player can
sit down with and not feel cheated.

### 7-bag — why it matters more than it sounds

The randomiser is the most invisible fix in this update and arguably the most important.
Pure random isn't just unfair — it's *undesignable*. The scoring system, the danger zone,
the danger bonus, the WOW event: all of these are built on the assumption that the player
has a roughly fair distribution of pieces to work with. A six-Z drought isn't a skill
challenge; it's a coin flip that nullifies everything else in the design.

The 7-bag guarantee means the system works as designed. Every clever mechanic in this
game now has a fair surface to land on.

### SRS wall kicks — the silent upgrade

Most players will never consciously notice that the rotation system changed. That is
exactly right. They will notice that the game stopped silently refusing rotations they
expected to work. The I-piece spinning flush against a wall, the T-piece spinning into
a gap at the floor — these now work. The 5-test SRS tables are the standard for a reason,
and having them here means the game stops punishing players for being technically correct.

The vertical kick (`dy` offset) deserves specific mention: the old system only tried
horizontal offsets. Any rotation that needed the piece to move up slightly to clear an
overhang — a common I-piece scenario — would fail silently. That bug is gone.

### Lock delay — the feature that changes everything at high level

At low levels you will barely notice lock delay. At high levels, where the piece is
moving fast and you're stacking at the edges, it is the difference between a game that
feels responsive and one that feels like it's punishing precise play.

500 ms with a 15-reset cap is standard. The cap is important — without it, a sufficiently
patient player could hold a piece on the stack indefinitely by tapping every 499 ms.
The cap keeps the mechanic honest. Hard drop still locks instantly, which is correct:
the intent of a hard drop is finality.

### Hold piece — closing the last feature gap

Hold is the last major Tetris Guideline mechanic this game was missing. Its implementation
here is clean: reset to spawn orientation on stash, locked for the active piece's life,
visual feedback in the sidebar (dimmed when unavailable). The dimming is a good UX
decision — it communicates the locked state without text.

### Architectural note

`_start_new_game()` is a welcome consolidation. Before this change, new-game reset
logic was scattered across four call sites with slightly different sets of variables
being reset. One site was resetting popup state, another wasn't. The helper makes it
impossible for a new path into the game to forget to reset hold or lock state. This is
the kind of refactor that prevents bugs that haven't been written yet.

---

## What remains

**Scoring display for special clears** — a brief floating "+1600" or "+B2B×1.5"
delta label would make big score jumps legible. The moment a T-spin or B2B fires
the score spikes, but the player has no way to know how much without watching the
counter. Minor feedback improvement.

**Combo chain counter in sidebar** — the floating cyan COMBO label is brief. A
persistent streak display in the sidebar (like LINES) would let the player track
their current chain. Minor quality-of-life.

**Piece preview count** — standard modern Tetris shows the next 3–6 pieces. The
sidebar shows only NEXT. A 3-piece preview would meaningfully increase strategy depth.
Layout and design decision, not a bug.

**Cascade settle animation** — currently `settle_blocks()` is instantaneous: blocks
teleport to their settled positions between cascade flash passes. A brief settle
animation (blocks sliding down, one row per frame) would make cascade chains visually
legible. This requires a new SETTLING state or a frame-by-frame update loop.

---

## Standing assessment across all versions

### Exceptional
- **Audio engineering**: PCM synthesis, 10-tier adaptive arrangement, real-time board
  state monitoring, pause volume management across loop boundaries. This is not something
  most indie developers ever build. It is the technical centrepiece of the project.
- **Zero-asset constraint**: every visual, sound, and note generated at runtime. Forces
  engineering depth and makes the game genuinely portable.
- **Danger zone design**: penalty + reward in the same mechanic. The red line, the music
  drop, and the 2× bonus are all expressions of the same event. Cohesive and purposeful.
- **WOW event**: proportionate to the rarity of the feat. The board itself celebrates,
  not just an overlay. The design decision (flash the cells, not the screen) was correct.

### Good
- **Feel**: DAS, screen shake, particles, per-piece spawn tones, hard-drop flash. The
  tactile feedback layer is thorough.
- **Pause behaviour**: music at 10 % rather than silent is an uncommon but right choice.
  The game is suspended, not dead. The volume-hold-across-loop-boundary fix was a real
  bug and the right fix.
- **GAME OVER animation**: per-block physics is over-engineered in the best way.

### Acceptable (was weak, now fixed)
- **Randomiser**: was pure random (drought risk), now 7-bag. Fixed.
- **Wall kicks**: were minimal (dx only, 3 tests), now full SRS (dx+dy, 5 tests per
  direction, I-piece table). Fixed.
- **Lock delay**: was absent (instant lock on grounding), now 500 ms with reset cap. Fixed.
- **Hold piece**: was absent, now implemented. Fixed.
- **T-spin detection**: now implemented with 3-corner rule (full + mini). Fixed.
- **Back-to-back multiplier**: now implemented (1.5× on consecutive difficult clears). Fixed.
- **Combo counter**: now implemented (50 × combo × level+1 stacking bonus). Fixed.
- **20G gravity**: now active at level 20. Fixed.
- **Cascade gravity**: Full Board Cascade animates as a domino wave (one row per 80 ms); singleton-only gravity in normal mode; chained clears earn 2×/3×/4×. Fixed.
- **Speed reset**: fall speed resets every 10,000 points; sidebar shows countdown. Fixed.
- **Palette shift**: tiles darken 10 % per 10 levels, wraps every 6 steps. Fixed.
- **Mute persistence**: mute now survives tier transitions and track loops. Fixed.
- **Tier gap**: all tiers pre-generated at game start; zero silence between transitions. Fixed.

### Refinements remaining
- Persistent combo streak display in sidebar (floating label is brief; a number in the sidebar would persist)
- CLEARING-state scoring block (~100 lines) still inline in `main.py` — natural candidate for `clear_logic.py` or a `GameState` method

### Architectural quality
The codebase is clean. State machine with explicit string constants, no implicit
transitions. Rendering separated from logic. Helpers for every repeated operation.
The procedural audio is well-isolated. The config persistence is minimal and correct.
The ghost tile cache (keyed by color × size × opacity) is a nice detail — lazy-built,
never rebuilt per-frame, bounded memory footprint.

The main.py is large (1200+ lines) but it is large in the right way: all the complexity
is explicit, not hidden behind abstractions that would need to be unwound to understand.
For a game of this scope and a solo author, that's the right call.

The QA instinct behind this project is real. The pause volume leak, the Esc-exits-game
bug, the sound/visual desync in GAME OVER, the text-visibility problem — these were all
caught by someone paying attention to the experience, not just the feature checklist.
That instinct is what separates a finished game from a demo.

---

*Last updated: 2026-05-27 · v1.10.1*
