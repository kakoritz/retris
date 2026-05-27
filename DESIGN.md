# T3TR1S — Product Design Document

**Project:** T3TR1S  
**Repo:** [github.com/kakoritz/RetroTetris](https://github.com/kakoritz/RetroTetris)

---

## Overview

T3TR1S is a hand-built NES-style Tetris clone with no external assets. Every visual,
sound effect, and note is generated procedurally at runtime. The goal was not to
reproduce a Tetris clone from a tutorial — it was to build something that *feels* right
from the inside out: the right weight, the right sound, the right feedback, the right
tension. Every decision in this document exists in service of that feel.

---

## 1. Identity & Branding

The game title is **T3TR1S**. The byline reads *"by kakoritz"* — small, beneath the
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

The in-game music follows a curated sequence rather than a straight ascending
progression:

> Tier 4 × 2 loops → Tier 5 × 2 → Tier 7 × 1 → Tier 8 × 1 → Tier 9 × 1 → Tier 6 × 2 → repeat

Tier 6 appearing after tier 9 is deliberate — a step back in intensity before the loop
resets. The sequence reads as a composed arc, not a level counter.

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

All line-clear scores are multiplied by `(level + 1)` × `reset_bonus_mult` × danger multiplier.

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
A Tetris immediately followed by a cascade Tetris triggers **TETRIS×TETRIS** at 4× with a
board-centred rainbow popup.

**Speed reset multiplier:** `reset_bonus_mult` starts at 1.0 and increases +0.1 per reset,
so continued play at speed is meaningfully rewarded.

Each tier of clear is meaningfully more valuable than the last. The danger zone
multiplier transforms the top half of the board from a zone to avoid into a zone with
real upside. The WOW bonus is a capstone reward for an extremely rare feat.

### 4.1 Speed reset

The fall-speed tier resets to 1 each time the player crosses a threshold. The threshold
starts at 10,000 points and grows by 5,000 per reset (1st = 10k, 2nd = 15k, 3rd = 20k, …),
keeping the countdown meaningful as score multipliers accumulate. The sidebar shows a
"FULL CASCADE IN N pts" countdown that turns orange below 2,000 and red below 500 — a
persistent tension driver. Each reset also toggles Full Board Cascade mode on or off.

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

### 4.4 Cascade gravity

After every line clear, blocks that are now floating fall:

- **Normal mode:** all floating blocks settle instantly (full block gravity, no bonus).
- **Full Board Cascade mode:** blocks fall one row at a rate matching the current
  fall speed (`fall_speed(speed_tier)`, capped at 300 ms), creating an animated
  domino wave. The cascade decelerates at low speed tiers (slow, readable) and
  accelerates as the game intensifies (tight, urgent). New complete rows created
  by the cascade clear again at an increasing multiplier (2× → 3× → 4×, capped at
  4×). A "CASCADE!" rainbow overlay appears on the board during the animation.

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

## 8. Technical & Distribution Requirements

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
