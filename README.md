# KAKORITZ's T3TR1S

A custom NES-style T3TR1S clone built from scratch in Python and Pygame — no image or audio files required. All sprites, sounds, and music are generated procedurally at runtime.

## Features

- All 7 classic tetrominoes with NES-palette colours
- CW and CCW rotation with wall-kick correction
- DAS (Delayed Auto-Shift) — tap to move one, hold to slide
- Ghost piece showing landing position
- Line-clear flash animation (escalates for double/triple/Tetris)
- Particle burst on every line clear
- Screen shake on a 4-line Tetris clear
- Hard-drop white flash impact effect
- Original chiptune background track (procedurally generated)
- Per-piece spawn tones + move/rotate/lock/hard-drop SFX
- Sidebar feedback popups: *Nice! → Great! → Fantastic! → TETRIS!* with rainbow cycling
- High-score board — top 10 persisted to `highscores.json`, initials entry on qualifying score
- Menu, Game Over, and Leaderboard screens

## Controls

| Key | Action |
|-----|--------|
| `←` / `→` | Move (hold for DAS auto-repeat) |
| `↑` | Rotate clockwise |
| `Ctrl + ↑` or `Z` | Rotate counter-clockwise |
| `↓` | Soft drop |
| `Space` | Hard drop |
| `R` | Restart |
| `Esc` | Back to menu |

## Requirements

- Python 3.10+
- pygame ≥ 2.5
- numpy ≥ 1.24

## Installation

```bash
pip install -r requirements.txt
python main.py
```

## Project Structure

```
main.py        # game loop, states, rendering
board.py       # 10×20 grid, collision, line clearing
piece.py       # tetromino shapes, CW/CCW rotation
constants.py   # grid sizes, colours, scoring, fall-speed curve
sprites.py     # procedural NES-style block surfaces (cached)
audio.py       # procedural SFX: rotate, move, lock, hard-drop, line-clears, spawns
music.py       # procedural 4-bar chiptune loop (writes temp WAV, streams via mixer)
particles.py   # particle burst system for line clears
highscore.py   # JSON top-10 persistence
```

## License

MIT — do whatever you want with it.
