"""
Procedural NES-style chiptune sounds — no audio files needed.
Requires numpy. Silently no-ops if unavailable.
"""
import pygame

try:
    import numpy as np
    _HAS_NP = True
except ImportError:
    _HAS_NP = False

_RATE      = 44100
_sounds    = None   # rotate, move, lock, hard_drop, 1-4 (line clears)
_spawns    = None   # 1-7 (per-piece-color spawn tones)
_sfx_scale = 1.0    # 0-1 multiplier applied to all SFX sounds


def pre_init() -> None:
    pygame.mixer.pre_init(_RATE, -16, 2, 512)


# ── waveform helpers ──────────────────────────────────────────────────────────

def _note(freq: float, ms: int, vol: float = 0.28, decay: float = 7.0):
    n = int(_RATE * ms / 1000)
    t = np.linspace(0, ms / 1000, n, endpoint=False)
    return np.sign(np.sin(2 * np.pi * freq * t)) * vol * np.exp(-decay * t)


def _sweep(f_start: float, f_end: float, ms: int,
           vol: float = 0.20, decay: float = 0.5):
    """Square wave with linearly falling/rising pitch."""
    n     = int(_RATE * ms / 1000)
    t     = np.linspace(0, ms / 1000, n, endpoint=False)
    freq  = np.linspace(f_start, f_end, n)
    phase = np.cumsum(2 * np.pi * freq / _RATE)
    return np.sign(np.sin(phase)) * vol * np.exp(-decay * t)


def _silence(ms: int):
    return np.zeros(int(_RATE * ms / 1000))


def _sound(*arrays) -> pygame.mixer.Sound:
    data = np.concatenate(arrays)
    pcm  = (data * 32767).astype(np.int16)
    return pygame.sndarray.make_sound(np.column_stack([pcm, pcm]))


# ── sound tables ─────────────────────────────────────────────────────────────

C5, E5, G5, C6 = 523, 659, 784, 1047


_V = 0.04   # master volume for every sound


def _build() -> dict:
    return {
        'rotate':    _sound(_note(760, 48, _V, 14.0)),
        'move':      _sound(_note(760, 35, _V, 16.0)),
        'lock':      _sound(_note(180, 120, _V, 7.0)),
        'hard_drop': _sound(
            _sweep(900, 120, 260, _V, 0.4),
            _silence(12),
            _note(1600, 55, _V, 28.0),
        ),
        1: _sound(_note(C5, 240, _V, 4.0)),
        2: _sound(_note(C5, 140, _V, 6.5),
                  _silence(18),
                  _note(E5, 250, _V, 4.0)),
        3: _sound(_note(C5, 110, _V, 8.0),
                  _silence(14),
                  _note(E5, 130, _V, 6.5),
                  _silence(14),
                  _note(G5, 280, _V, 3.5)),
        4: _sound(_note(C5, 100, _V, 10.0),
                  _silence(10),
                  _note(E5, 100, _V,  9.0),
                  _silence(10),
                  _note(G5, 100, _V,  8.0),
                  _silence(10),
                  _note(C6, 400, _V,  2.8)),
    }


def _build_spawns() -> dict:
    return {
        1: _sound(_note(1047, 50, _V, 12.0)),   # I  cyan    – C6
        2: _sound(_note( 698, 55, _V,  8.0)),   # O  yellow  – F5
        3: _sound(_note( 440, 60, _V,  7.5)),   # T  purple  – A4
        4: _sound(_note( 587, 55, _V,  9.0)),   # S  green   – D5
        5: _sound(_note( 370, 60, _V, 10.0)),   # Z  red     – F#4
        6: _sound(_note( 247, 65, _V,  6.0)),   # J  blue    – B3
        7: _sound(_note( 523, 55, _V,  8.5)),   # L  orange  – C5
    }


# ── public API ────────────────────────────────────────────────────────────────

def prime() -> None:
    """Pre-build sound tables so set_sfx_volume takes effect immediately."""
    global _sounds, _spawns, _boms
    if not _HAS_NP or not pygame.mixer.get_init():
        return
    if _sounds is None:
        _sounds = _build()
        for s in _sounds.values():
            s.set_volume(_sfx_scale)
    if _spawns is None:
        _spawns = _build_spawns()
        for s in _spawns.values():
            s.set_volume(_sfx_scale)
    if _boms is None:
        _boms = _build_boms()
        for s in _boms.values():
            s.set_volume(_sfx_scale)


def set_sfx_volume(scale: float) -> None:
    global _sfx_scale
    _sfx_scale = max(0.0, min(1.0, scale))
    for table in (_sounds, _spawns, _boms):
        if table:
            for s in table.values():
                s.set_volume(_sfx_scale)


def play(key) -> None:
    global _sounds
    if not _HAS_NP or not pygame.mixer.get_init():
        return
    if _sounds is None:
        _sounds = _build()
        for s in _sounds.values():
            s.set_volume(_sfx_scale)
    snd = _sounds.get(key)
    if snd:
        snd.play()


def play_spawn(color_id: int) -> None:
    global _spawns
    if not _HAS_NP or not pygame.mixer.get_init():
        return
    if _spawns is None:
        _spawns = _build_spawns()
        for s in _spawns.values():
            s.set_volume(_sfx_scale)
    snd = _spawns.get(color_id)
    if snd:
        snd.play()


# ── game-over block-land BOM sounds ──────────────────────────────────────────

_boms = None

_BOM_STARTS = [340, 310, 280, 255, 230, 205, 185, 165]   # sweep start Hz per letter


def _build_boms() -> dict:
    out = {}
    for k, p in enumerate(_BOM_STARTS, 1):
        hit  = _sweep(p, int(p * 0.18), 200, _V * 3.0, 0.12)
        body = _note(int(p * 0.35), 120, _V * 1.8, 5.0)
        n    = max(len(hit), len(body))
        data = np.zeros(n)
        data[:len(hit)]  += hit
        data[:len(body)] += body
        out[k] = _sound(data)
    return out


def play_bom(idx: int) -> None:
    """Deep impact thud for game-over letter drops (idx 1-8)."""
    global _boms
    if not _HAS_NP or not pygame.mixer.get_init():
        return
    if _boms is None:
        _boms = _build_boms()
        for s in _boms.values():
            s.set_volume(_sfx_scale)
    snd = _boms.get(idx)
    if snd:
        snd.play()
