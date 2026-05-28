"""
highscore.py — top-10 score persistence (highscores.json).

All functions are stateless reads/writes; there is no in-memory cache.
A missing or corrupt file is silently treated as an empty leaderboard.
"""
import json
import os
from pathlib import Path


def _data_dir() -> Path:
    p = os.environ.get('ANDROID_PRIVATE')
    return Path(p) if p else Path(__file__).parent.parent


_FILE      = _data_dir() / "highscores.json"
MAX_SCORES = 10


def load() -> list[dict]:
    """Return the leaderboard as a list of dicts (sorted, best first)."""
    if not _FILE.exists():
        return []
    try:
        with _FILE.open() as f:
            return json.load(f)
    except Exception:
        return []


def qualifies(score: int) -> bool:
    """Return True if score is high enough to enter the top-10."""
    if score == 0:
        return False
    scores = load()
    return len(scores) < MAX_SCORES or score > scores[-1]["score"]


def insert(name: str, score: int, lines: int, level: int) -> list[dict]:
    """Add an entry, re-sort, trim to MAX_SCORES, persist, and return the new list."""
    scores = load()
    scores.append({"name": name, "score": score, "lines": lines, "level": level})
    scores.sort(key=lambda e: e["score"], reverse=True)
    scores = scores[:MAX_SCORES]
    with _FILE.open("w") as f:
        json.dump(scores, f, indent=2)
    return scores


def best() -> int:
    """Return the #1 score, or 0 if the leaderboard is empty."""
    scores = load()
    return scores[0]["score"] if scores else 0
