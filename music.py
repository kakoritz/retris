"""
Procedural chiptune — Tron/Daft Punk electronic composition.
32-bar form (~60 s): bass intro → build → bridge → full.
Sawtooth bass with sub-octave layer; square-wave arpeggio and melody.
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

_RATE      = 44100
_tmp_path  = None
_music_vol = 0.40
_muted     = False


# ── waveform helpers ──────────────────────────────────────────────────────────

def _fade(w, ms=8):
    fade = min(int(_RATE * ms / 1000), len(w) // 4)
    if fade > 0:
        r = 0.5 * (1 - np.cos(np.pi * np.arange(fade) / fade))
        w[:fade] *= r
        w[-fade:] *= r[::-1]


def _saw(freq, ms, vol, decay=1.2):
    """Band-limited sawtooth: warm, harmonically rich electronic bass."""
    if freq == 0:
        return np.zeros(int(_RATE * ms / 1000))
    n = int(_RATE * ms / 1000)
    t = np.linspace(0, ms / 1000, n, endpoint=False)
    w = np.zeros(n)
    for k in range(1, 9):
        w += ((-1) ** (k + 1)) / k * np.sin(2 * np.pi * freq * k * t)
    w = w * (2 / np.pi) * vol * np.exp(-decay * t)
    _fade(w)
    return w


def _sq(freq, ms, vol, decay=2.5):
    """Square wave for arpeggio and melody lines."""
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


def _mix(a, b):
    n = max(len(a), len(b))
    out = np.zeros(n)
    out[:len(a)] += a
    out[:len(b)] += b
    return out


# ── composition ───────────────────────────────────────────────────────────────

def _build() -> np.ndarray:
    BPM = 128
    E8  = int(60000 / (BPM * 2))   # 8th note  ≈ 234 ms
    S16 = E8 // 2                   # 16th note ≈ 117 ms
    Q   = E8 * 2                    # quarter   ≈ 469 ms
    H   = E8 * 4                    # half      ≈ 938 ms

    VB = 0.055   # sawtooth mid-bass
    VS = 0.022   # sub-bass (octave below, long sustain)
    VA = 0.018   # arpeggio
    VM = 0.013   # melody

    # ── Frequencies ───────────────────────────────────────────────────────────
    C2  =  65.4;  D2  =  73.4;  E2  =  82.4;  F2  =  87.3
    G2  =  98.0;  Ab2 = 103.8;  A2  = 110.0;  B2  = 123.5
    C3  = 130.8;  D3  = 146.8;  E3  = 164.8;  F3  = 174.6
    G3  = 196.0;  A3  = 220.0;  B3  = 246.9
    C4  = 261.6;  D4  = 293.7;  E4  = 329.6;  F4  = 349.2
    G4  = 392.0;  Ab4 = 415.3;  A4  = 440.0;  B4  = 493.9
    C5  = 523.3;  D5  = 587.3;  E5  = 659.3;  F5  = 698.5
    G5  = 784.0;  A5  = 880.0
    R   = 0

    def B(f, ms):
        """Thick bass: sawtooth mid + sustained sub-octave."""
        hi = _saw(f,           ms, VB, 1.0)
        lo = _saw(f * 0.5 if f > 0 else 0, ms, VS, 0.45)
        return _mix(hi, lo)

    def Ar(f, ms): return _sq(f, ms, VA, 4.5)
    def Mel(f, ms): return _sq(f, ms, VM, 1.6)
    def Rst(ms):   return np.zeros(int(_RATE * ms / 1000))

    # ══════════════════════════════════════════════════════════════════════════
    # BASS PATTERNS — each is exactly 2 bars = 16 eighth notes
    # ══════════════════════════════════════════════════════════════════════════

    def b_Am():
        """Am ascending/descending arpeggio bass."""
        return _cat(
            B(A2,E8), B(C3,E8), B(E3,E8), B(A3,E8),
            B(G3,E8), B(E3,E8), B(C3,E8), B(A2,E8),
            B(A2,E8), B(A2,E8), B(C3,E8), B(E3,E8),
            B(G3,E8), B(E3,E8), B(D3,E8), B(A2,E8),
        )

    def b_Am_s():
        """Am syncopated — off-beat 16th pops for Daft Punk drive."""
        return _cat(
            # bar 1: syncopated 16ths
            B(A2,S16), Rst(S16), B(C3,S16), Rst(S16),
            B(E3,S16), B(A3,S16), Rst(S16), B(G3,S16),
            B(E3,S16), B(C3,S16), B(A2,S16), Rst(S16),
            B(A2,S16), B(E2,S16), Rst(S16), B(A2,S16),
            # bar 2: solid 8ths for contrast
            B(A2,E8), B(C3,E8), B(E3,E8), B(A3,E8),
            B(G3,E8), B(E3,E8), B(C3,E8), B(E2,E8),
        )

    def b_F():
        """F major groove."""
        return _cat(
            B(F2,E8), B(A2,E8), B(C3,E8), B(F3,E8),
            B(C3,E8), B(A2,E8), B(F2,E8), B(C2,E8),
            B(F2,E8), B(F2,E8), B(A2,E8), B(C3,E8),
            B(F3,E8), B(C3,E8), B(A2,E8), B(F2,E8),
        )

    def b_G():
        """G major groove."""
        return _cat(
            B(G2,E8), B(B2,E8), B(D3,E8), B(G3,E8),
            B(D3,E8), B(B2,E8), B(G2,E8), B(D2,E8),
            B(G2,E8), B(G2,E8), B(B2,E8), B(D3,E8),
            B(G3,E8), B(D3,E8), B(B2,E8), B(G2,E8),
        )

    def b_E():
        """E dominant (V of Am) — tension that resolves to Am at loop restart."""
        return _cat(
            # bar 1
            B(E2,E8), B(Ab2,E8), B(B2,E8), B(E3,E8),
            B(B2,E8), B(Ab2,E8), B(E2,E8), B(E2,E8),
            # bar 2: synco 16ths for maximum tension
            B(E2,S16), Rst(S16), B(E2,S16), B(Ab2,S16),
            B(B2,S16), B(E3,S16), B(B2,S16), B(Ab2,S16),
            B(E2,E8),  B(E2,E8), B(B2,E8),  B(E3,E8),
        )

    # ══════════════════════════════════════════════════════════════════════════
    # ARPEGGIO PATTERNS — 1 bar = 16 sixteenth notes each
    # ══════════════════════════════════════════════════════════════════════════

    def arp_bar(notes):
        return _cat(*[Ar(f, S16) for f in notes])

    _am16 = [A4,C5,E5,A5, E5,C5,A4,E4, A4,C5,E5,A5, E5,C5,A4,E4]
    _f16  = [F4,A4,C5,F5, C5,A4,F4,C4, F4,A4,C5,F5, C5,A4,F4,A4]
    _g16  = [G4,B4,D5,G5, D5,B4,G4,D4, G4,B4,D5,G5, D5,B4,G4,B4]
    _e16  = [E4,Ab4,B4,E5, B4,Ab4,E4,B3, E4,Ab4,B4,E5, B4,Ab4,E5,B4]

    def arp_Am(): return arp_bar(_am16)
    def arp_F():  return arp_bar(_f16)
    def arp_G():  return arp_bar(_g16)
    def arp_E():  return arp_bar(_e16)

    # ══════════════════════════════════════════════════════════════════════════
    # MELODY PHRASES — each 2 bars (quarter + half note lines)
    # ══════════════════════════════════════════════════════════════════════════

    def mel_p1():   # over Am: E5 descending phrase
        return _cat(Mel(E5,Q), Mel(D5,Q), Mel(C5,Q), Mel(B4,Q),
                    Mel(A4,H), Mel(G4,H))

    def mel_p2():   # over Am/F: upper climb
        return _cat(Mel(F5,Q), Mel(E5,Q), Mel(D5,Q), Mel(C5,Q),
                    Mel(D5,H), Mel(E5,H))

    def mel_p3():   # over F/G: high register descent
        return _cat(Mel(G5,Q), Mel(F5,Q), Mel(E5,Q), Mel(D5,Q),
                    Mel(E5,H), Mel(D5,H))

    def mel_p4():   # over G/E: final resolution line, silence last half → clean loop
        return _cat(Mel(E5,Q), Mel(D5,Q), Mel(C5,Q), Mel(B4,Q),
                    Mel(A4,H), Rst(H))

    # ══════════════════════════════════════════════════════════════════════════
    # ASSEMBLY — 4 sections × 8 bars = 32 bars ≈ 60 seconds
    # ══════════════════════════════════════════════════════════════════════════

    # Section 1 (bars 1-8): bass only — establish the groove
    s1 = _cat(b_Am(), b_Am(), b_F(), b_G())

    # Section 2 (bars 9-16): bass + arpeggio — build energy
    s2_bass = _cat(b_Am_s(), b_Am_s(), b_F(), b_G())
    s2_arp  = _cat(arp_Am(), arp_Am(), arp_Am(), arp_Am(),
                   arp_F(),  arp_F(),  arp_G(),  arp_G())
    s2 = _mix(s2_bass, s2_arp)

    # Section 3 (bars 17-24): bass + arp + melody — full theme
    s3_bass = _cat(b_Am(), b_Am(), b_F(), b_G())
    s3_arp  = _cat(arp_Am(), arp_Am(), arp_Am(), arp_Am(),
                   arp_F(),  arp_F(),  arp_G(),  arp_G())
    s3_mel  = _cat(mel_p1(), mel_p2(), mel_p3(), mel_p4())
    s3 = _mix(_mix(s3_bass, s3_arp), s3_mel)

    # Section 4 (bars 25-32): synco bass + arp + melody variation
    # Ends on E dominant → resolves back to Am at loop start
    s4_bass = _cat(b_Am_s(), b_Am_s(), b_F(), b_E())
    s4_arp  = _cat(arp_Am(), arp_Am(), arp_Am(), arp_Am(),
                   arp_F(),  arp_F(),  arp_E(),  arp_E())
    s4_mel  = _cat(mel_p3(), mel_p1(), mel_p2(), mel_p4())
    s4 = _mix(_mix(s4_bass, s4_arp), s4_mel)

    # ── normalize and encode ─────────────────────────────────────────────────
    full = _cat(s1, s2, s3, s4)
    peak = np.max(np.abs(full))
    if peak > 0:
        full = full / peak * 0.22

    pcm    = (full * 32767).astype(np.int16)
    stereo = np.ascontiguousarray(np.column_stack([pcm, pcm]))
    return stereo


# ── WAV I/O ───────────────────────────────────────────────────────────────────

def _write_wav(data: np.ndarray, path: str) -> None:
    with wave.open(path, 'w') as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(_RATE)
        f.writeframes(data.tobytes())


# ── internal volume helper ────────────────────────────────────────────────────

def _apply_volume() -> None:
    try:
        pygame.mixer.music.set_volume(0.0 if _muted else _music_vol)
    except Exception:
        pass


# ── public API ────────────────────────────────────────────────────────────────

def start() -> None:
    global _tmp_path
    if not _HAS_NP:
        return
    try:
        if _tmp_path is None:
            stereo    = _build()
            _tmp_path = os.path.join(tempfile.gettempdir(), "nes_tetris_music_v2.wav")
            _write_wav(stereo, _tmp_path)
        pygame.mixer.music.load(_tmp_path)
        _apply_volume()
        pygame.mixer.music.play(loops=-1)
    except Exception:
        pass


def stop() -> None:
    try:
        pygame.mixer.music.stop()
    except Exception:
        pass


def fadeout(ms: int = 1500) -> None:
    try:
        pygame.mixer.music.fadeout(ms)
    except Exception:
        pass


def start_menu() -> None:
    """Full 32-bar Tron composition — used on the menu screen."""
    start()


def start_game() -> None:
    """Game-play music.  Currently uses the same track; level-based layers TBD."""
    start()


def set_volume(v: float) -> None:
    global _music_vol
    _music_vol = max(0.0, min(1.0, v))
    _apply_volume()


def toggle_mute() -> bool:
    global _muted
    _muted = not _muted
    _apply_volume()
    return _muted


def is_muted() -> bool:
    return _muted
