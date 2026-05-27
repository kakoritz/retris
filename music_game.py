"""
music_game.py — 10-tier layered game music.
Tier 1 = sparse bass only. Tier 10 = full arrangement.
Each tier is an 8-bar loop at BPM 128 (~15 s).
Tiers are generated lazily and cached as temp WAV files.
Same harmonic language as music.py (Am groove).
"""
import os
import wave
import tempfile
import pygame

try:
    import numpy as np
    _HAS_NP = True
except ImportError:
    _HAS_NP = False

_RATE       = 44100
_tier_paths: dict = {}
_current_tier     = 0
_game_vol         = 0.40
_muted            = False

# ── sequence definition ───────────────────────────────────────────────────────
# Each entry: (tier, plays).  plays=2 means play twice before advancing.
_GAME_SEQUENCE = [
    (4, 2),
    (5, 2),
    (7, 1),
    (8, 1),
    (9, 1),
    (6, 2),
]

_seq_index = 0    # current position in _GAME_SEQUENCE
_in_danger = False  # True while danger (tier-1) mode is active


# ── waveform helpers ─────────────────────────────────────────────────────────

def _fade(w, ms=6):
    fade = min(int(_RATE * ms / 1000), len(w) // 4)
    if fade > 0:
        r = 0.5 * (1 - np.cos(np.pi * np.arange(fade) / fade))
        w[:fade] *= r
        w[-fade:] *= r[::-1]


def _saw(freq, ms, vol, decay=1.0):
    if freq == 0:
        return np.zeros(int(_RATE * ms / 1000))
    n = int(_RATE * ms / 1000)
    t = np.linspace(0, ms / 1000, n, endpoint=False)
    w = np.zeros(n)
    for k in range(1, 9):
        w += ((-1) ** (k + 1)) / k * np.sin(2 * np.pi * freq * k * t)
    w *= (2 / np.pi) * vol * np.exp(-decay * t)
    _fade(w)
    return w


def _sq(freq, ms, vol, decay=2.0):
    if freq == 0:
        return np.zeros(int(_RATE * ms / 1000))
    n = int(_RATE * ms / 1000)
    t = np.linspace(0, ms / 1000, n, endpoint=False)
    w = np.sign(np.sin(2 * np.pi * freq * t)) * vol * np.exp(-decay * t)
    _fade(w)
    return w


def _cat(*parts):
    arr = [p for p in parts if len(p) > 0]
    return np.concatenate(arr) if arr else np.zeros(0)


def _mix(*tracks):
    if not tracks:
        return np.zeros(0)
    n = max(len(t) for t in tracks)
    out = np.zeros(n)
    for t in tracks:
        out[:len(t)] += t
    return out


def _write_wav(data, path: str) -> None:
    with wave.open(path, 'w') as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(_RATE)
        f.writeframes(data.tobytes())


# ── tier builder ──────────────────────────────────────────────────────────────

def _build_tier(tier: int) -> np.ndarray:
    BPM = 128
    E8  = int(60000 / (BPM * 2))   # eighth note  ≈ 234 ms
    S16 = E8 // 2                   # sixteenth    ≈ 117 ms
    Q   = E8 * 2                    # quarter      ≈ 468 ms
    H   = Q * 2                     # half         ≈ 936 ms
    W   = H * 2                     # whole / bar  ≈ 1872 ms

    VB = 0.055; VS = 0.020; VA = 0.016; VM = 0.012; VSP = 0.007

    C2=65.4;  D2=73.4;  E2=82.4;  F2=87.3;  G2=98.0;  Ab2=103.8
    A2=110.0; B2=123.5; C3=130.8; D3=146.8; E3=164.8; F3=174.6
    G3=196.0; A3=220.0; C4=261.6; D4=293.7; E4=329.6; F4=349.2
    G4=392.0; Ab4=415.3; A4=440.0; B4=493.9
    C5=523.3; D5=587.3; E5=659.3; F5=698.5; G5=784.0; A5=880.0

    def B(f, ms):
        return _mix(_saw(f, ms, VB, 1.0),
                    _saw(f * 0.5 if f > 0 else 0, ms, VS, 0.45))

    def Ar(f, ms):  return _sq(f, ms, VA, 4.5)
    def Mel(f, ms): return _sq(f, ms, VM, 1.6)
    def Sp(f, ms):  return _sq(f, ms, VSP, 7.0)
    def Rst(ms):    return np.zeros(int(_RATE * ms / 1000))

    # ── bass patterns (all 8 bars) ────────────────────────────────────────

    def b_whole():
        """Tier 1: one bass hit per bar (whole-note pulse)."""
        return _cat(*[B(A2, W) for _ in range(8)])

    def b_walk():
        """Tier 2: quarter-note walking Am bass."""
        up   = _cat(B(A2,Q), B(C3,Q), B(E3,Q), B(G3,Q))
        down = _cat(B(A3,Q), B(G3,Q), B(E3,Q), B(C3,Q))
        return _cat(up, down, up, down, up, down, up, down)

    def b_groove():
        """Tier 3: 8th-note Am groove (2-bar pattern × 4)."""
        two = _cat(
            B(A2,E8), B(C3,E8), B(E3,E8), B(A3,E8),
            B(G3,E8), B(E3,E8), B(C3,E8), B(A2,E8),
            B(A2,E8), B(A2,E8), B(C3,E8), B(E3,E8),
            B(G3,E8), B(E3,E8), B(D3,E8), B(A2,E8),
        )
        return _cat(two, two, two, two)

    def b_chord():
        """Tier 4+: 8th-note bass with Am→F→G movement (8 bars)."""
        am = _cat(
            B(A2,E8), B(C3,E8), B(E3,E8), B(A3,E8),
            B(G3,E8), B(E3,E8), B(C3,E8), B(A2,E8),
            B(A2,E8), B(A2,E8), B(C3,E8), B(E3,E8),
            B(G3,E8), B(E3,E8), B(D3,E8), B(A2,E8),
        )
        fb = _cat(
            B(F2,E8), B(A2,E8), B(C3,E8), B(F3,E8),
            B(C3,E8), B(A2,E8), B(F2,E8), B(C2,E8),
            B(F2,E8), B(F2,E8), B(A2,E8), B(C3,E8),
            B(F3,E8), B(C3,E8), B(A2,E8), B(F2,E8),
        )
        gb = _cat(
            B(G2,E8), B(B2,E8), B(D3,E8), B(G3,E8),
            B(D3,E8), B(B2,E8), B(G2,E8), B(D2,E8),
            B(G2,E8), B(G2,E8), B(B2,E8), B(D3,E8),
            B(G3,E8), B(D3,E8), B(B2,E8), B(G2,E8),
        )
        return _cat(am, am, fb, gb)

    def b_synco_chord():
        """Tier 9+: syncopated 16th-note bass with Am→F→G (8 bars)."""
        def synco2(r, c2, c3, c4):
            return _cat(
                B(r,S16),  Rst(S16), B(c2,S16), Rst(S16),
                B(c3,S16), B(c4,S16), Rst(S16), B(c3,S16),
                B(c2,S16), B(r,S16),  B(c2,S16), Rst(S16),
                B(r,S16),  B(r*0.5 if r > 40 else r, S16), Rst(S16), B(r,S16),
                B(r,E8), B(c2,E8), B(c3,E8), B(c4,E8),
                B(c3,E8), B(c2,E8), B(r,E8), B(r,E8),
            )
        am2 = synco2(A2, C3, E3, A3)
        fb2 = synco2(F2, A2, C3, F3)
        gb2 = synco2(G2, B2, D3, G3)
        return _cat(am2, am2, fb2, gb2)

    # ── arpeggio patterns (8 bars) ────────────────────────────────────────

    _am16  = [A4,C5,E5,A5, E5,C5,A4,E4, A4,C5,E5,A5, E5,C5,A4,E4]
    _f16   = [F4,A4,C5,F5, C5,A4,F4,C4, F4,A4,C5,F5, C5,A4,F4,A4]
    _g16   = [G4,Ab4,D5,G5, D5,Ab4,G4,D4, G4,Ab4,D5,G5, D5,Ab4,G4,Ab4]

    def arp_am8():
        bar = _cat(*[Ar(f, S16) for f in _am16])
        return _cat(*[bar for _ in range(8)])

    def arp_chord8():
        bar_am = _cat(*[Ar(f, S16) for f in _am16])
        bar_f  = _cat(*[Ar(f, S16) for f in _f16])
        bar_g  = _cat(*[Ar(f, S16) for f in _g16])
        return _cat(bar_am, bar_am, bar_am, bar_am,
                    bar_f,  bar_f,  bar_g,  bar_g)

    # ── melody layers (8 bars) ────────────────────────────────────────────

    def mel_a():
        """Main descending Am melody (phrase 1 + 2, repeated)."""
        p1 = _cat(Mel(E5,Q), Mel(D5,Q), Mel(C5,Q), Mel(B4,Q),
                  Mel(A4,H), Mel(G4,H))
        p2 = _cat(Mel(F5,Q), Mel(E5,Q), Mel(D5,Q), Mel(C5,Q),
                  Mel(D5,H), Mel(E5,H))
        return _cat(p1, p2, p1, p2)

    def mel_b():
        """High register melody variation (phrases 3 + 4)."""
        p3 = _cat(Mel(G5,Q), Mel(F5,Q), Mel(E5,Q), Mel(D5,Q),
                  Mel(E5,H), Mel(D5,H))
        p4 = _cat(Mel(E5,Q), Mel(D5,Q), Mel(C5,Q), Mel(B4,Q),
                  Mel(A4,H), Rst(H))
        return _cat(p3, p4, p3, p4)

    # ── sparkle (tier 10: shimmering high notes) ─────────────────────────

    def sparkle8():
        notes = [A5,G5,E5,A5, G5,A5,E5,G5,
                 A5,G5,E5,A5, G5,A5,E5,G5]
        bar = _cat(*[Sp(f, S16) for f in notes])
        return _cat(*[bar for _ in range(8)])

    # ── assemble tier ─────────────────────────────────────────────────────

    if   tier == 1:
        layers = [b_whole()]
    elif tier == 2:
        layers = [b_walk()]
    elif tier == 3:
        layers = [b_groove()]
    elif tier == 4:
        layers = [b_chord()]
    elif tier == 5:
        layers = [b_chord(), arp_am8()]
    elif tier == 6:
        layers = [b_chord(), arp_chord8()]
    elif tier == 7:
        layers = [b_chord(), arp_chord8(), mel_a()]
    elif tier == 8:
        layers = [b_chord(), arp_chord8(), mel_a(), mel_b()]
    elif tier == 9:
        layers = [b_synco_chord(), arp_chord8(), mel_a(), mel_b()]
    else:   # tier 10+
        layers = [b_synco_chord(), arp_chord8(), mel_a(), mel_b(), sparkle8()]

    full = _mix(*layers)
    peak = np.max(np.abs(full))
    if peak > 0:
        full = full / peak * 0.22

    pcm    = (full * 32767).astype(np.int16)
    stereo = np.ascontiguousarray(np.column_stack([pcm, pcm]))
    return stereo


# ── internal helpers ──────────────────────────────────────────────────────────

def _ensure_tier(tier: int) -> str:
    """Generate WAV for tier if not cached; return path."""
    if tier not in _tier_paths:
        data = _build_tier(tier)
        path = os.path.join(tempfile.gettempdir(),
                            f"kakoritz_t3tr1s_game_t{tier}.wav")
        _write_wav(data, path)
        _tier_paths[tier] = path
    return _tier_paths[tier]


def _start_tier(tier: int, loops: int = -1) -> None:
    global _current_tier
    if not _HAS_NP:
        return
    tier = max(1, min(10, tier))
    try:
        pygame.mixer.music.load(_ensure_tier(tier))
        pygame.mixer.music.set_volume(0.0 if _muted else _game_vol)
        pygame.mixer.music.play(loops=loops)
        _current_tier = tier
    except Exception:
        pass


def _play_sequence_step() -> None:
    tier, plays = _GAME_SEQUENCE[_seq_index]
    _start_tier(tier, loops=plays - 1)   # plays=2 → loops=1 (play twice)


# ── public API ────────────────────────────────────────────────────────────────

def start_sequence() -> None:
    """Start the game music sequence from the top (called on new game).

    Pre-generates all tier WAV files before playing so every tier transition
    is instant — the OS will have them cached after the first load.
    """
    global _seq_index, _in_danger
    if not _HAS_NP:
        return
    for tier, _ in _GAME_SEQUENCE:
        _ensure_tier(tier)
    _ensure_tier(1)   # danger music
    _seq_index = 0
    _in_danger = False
    _play_sequence_step()


def on_music_end() -> None:
    """Call this from main.py whenever the MUSIC_END mixer event fires."""
    global _seq_index
    if _in_danger:
        return  # tier-1 danger music loops forever; shouldn't fire
    _seq_index = (_seq_index + 1) % len(_GAME_SEQUENCE)
    _play_sequence_step()


def set_danger(dangerous: bool) -> None:
    """Switch to tier-1 tension music when the board is near the top,
    and restart the sequence from the beginning when it clears."""
    global _in_danger, _seq_index
    if dangerous == _in_danger:
        return
    if dangerous:
        _in_danger = True
        _start_tier(1, loops=-1)
    else:
        _in_danger = False
        _seq_index = 0
        _play_sequence_step()


def start_level(level: int) -> None:
    """Manually preview a specific tier (used by the Music Preview screen)."""
    global _current_tier, _in_danger
    if not _HAS_NP:
        return
    tier = max(1, min(10, level))
    if tier == _current_tier:
        return
    _in_danger = False
    _start_tier(tier, loops=-1)


def stop() -> None:
    global _current_tier, _seq_index, _in_danger
    _current_tier = 0
    _seq_index    = 0
    _in_danger    = False
    try:
        pygame.mixer.music.stop()
    except Exception:
        pass


def set_volume(v: float) -> None:
    global _game_vol
    _game_vol = max(0.0, min(1.0, v))


def set_muted(m: bool) -> None:
    """Sync game-music mute state with the global toggle (called from main.py)."""
    global _muted
    _muted = m
    try:
        pygame.mixer.music.set_volume(0.0 if _muted else _game_vol)
    except Exception:
        pass
