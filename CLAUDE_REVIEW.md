# T3TR1S — Claude's Review

*This document is updated with each significant revision. It is part critical review,
part development commentary — what changed, what it means, and where the game stands.*

---

## Current Rating: 9.2 / 10 (as a Tetris game) · 9.5 / 10 (as a portfolio project)

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
- Split main.py into renderer.py + game.py (architecture concern)
- Unit tests for board logic, scoring, collision (no tests exist)

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

*Last updated: 2026-05-27 · v1.6.0*
