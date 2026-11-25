"""Zaroni Virtual Instruments: piano, bass guitar and drum machine with real-time synthesis."""
import time
import wave
from functools import lru_cache
from types import SimpleNamespace

import numpy as np
import pygame as pg

RATE = 44100
NOTE_SECONDS = 3.0
W, H = 1280, 760
pg.mixer.pre_init(RATE, -16, 2, 256)
pg.init()
pg.mixer.set_num_channels(64)
screen = pg.display.set_mode((W, H))
pg.display.set_caption('Zaroni Virtual Instruments')
font = pg.font.SysFont('Arial', 16)
small = pg.font.SysFont('Arial', 13)
big = pg.font.SysFont('Arial', 26, bold=True)
clock = pg.time.Clock()
now = pg.time.get_ticks

BG, PANEL, BTN, ON = (24, 27, 32), (33, 37, 45), (60, 65, 75), (40, 125, 95)
GREEN, TEXT, DIM = (70, 190, 150), (230, 230, 230), (150, 156, 168)
ORANGE, BLUE, RED = (240, 160, 60), (90, 150, 230), (215, 70, 70)

# ---------------------------------------------------------------- music data
MODES = ['Piano', 'Bass', 'Drums']
NAMES = 'C C# D D# E F F# G G# A A# B'.split()
PIANO_KEYS = 'zsxdcvgbhnjmq2w3er5t6y7u'
BASS_KEYS = '1234567890qwertyuiopasdf'
STRINGS = [43, 38, 33, 28]                      # G2 D2 A1 E1 (MIDI note numbers)
FX = ['Distortion', 'Chorus', 'Compressor', 'Slap']
INLAYS = (3, 5, 7, 9, 12, 15, 17, 19, 21, 24)

SCALES = [('Major', [0, 2, 4, 5, 7, 9, 11]), ('Natural minor', [0, 2, 3, 5, 7, 8, 10]),
          ('Major pentatonic', [0, 2, 4, 7, 9]), ('Minor pentatonic', [0, 3, 5, 7, 10]),
          ('Blues', [0, 3, 5, 6, 7, 10]), ('Dorian', [0, 2, 3, 5, 7, 9, 10]),
          ('Mixolydian', [0, 2, 4, 5, 7, 9, 10])]
CHORDS = [('Major', [0, 4, 7]), ('Minor', [0, 3, 7]), ('Dominant 7', [0, 4, 7, 10]),
          ('Major 7', [0, 4, 7, 11]), ('Minor 7', [0, 3, 7, 10]), ('Diminished', [0, 3, 6]),
          ('Augmented', [0, 4, 8]), ('Sus4', [0, 5, 7])]

# Bass lessons: (title, description, [(string index, fret), ...]); string 0 = G ... 3 = E
LESSONS = [
    ('Open strings', 'Play each open string from low E to high G and back.',
     [(3, 0), (2, 0), (1, 0), (0, 0), (1, 0), (2, 0), (3, 0)]),
    ('E minor pentatonic', 'E G A B D: the most common scale in rock and blues bass.',
     [(3, 0), (3, 3), (2, 0), (2, 2), (1, 0), (1, 2), (0, 0), (0, 2)]),
    ('G major scale', 'One octave starting on the 3rd fret of the E string.',
     [(3, 3), (3, 5), (2, 2), (2, 3), (2, 5), (1, 2), (1, 4), (1, 5)]),
    ('Root-fifth-octave', 'The classic groove shape, on A and then on D.',
     [(3, 5), (2, 7), (1, 7), (2, 7), (2, 5), (1, 7), (0, 7), (1, 7)]),
    ('Chromatic 1-2-3-4', 'Finger independence: one finger per fret on every string.',
     [(s, f) for s in (3, 2, 1, 0) for f in (1, 2, 3, 4)]),
]

PRESETS = [
    ('Rock', ['x.......x.x.....', '....x.......x...', 'x.x.x.x.x.x.x.x.', '................']),
    ('Funk', ['x.....x...x..x..', '....x..x.x..x...', 'xxxxxxxxxxxxxxxx', '............x...']),
    ('House', ['x...x...x...x...', '................', '..x...x...x...x.', '....x.......x...']),
    ('Hip-hop', ['x.....x.x.......', '....x.......x...', 'x.x.x.x.x.x.x.xx', '....x.......x...']),
]
DRUM_COLORS = [(220, 90, 90), (240, 160, 60), (90, 150, 230), (170, 110, 220)]


def name(n): return NAMES[n % 12] + str(n // 12 - 1)
def hz(n): return 440 * 2 ** ((n - 69) / 12)


# ---------------------------------------------------------------- synthesis
T = np.arange(int(RATE * NOTE_SECONDS)) / RATE


def smooth(x, n):
    """Moving average of width n (a simple low-pass filter), same length as x."""
    c = np.cumsum(np.insert(x, 0, 0.0))
    y = (c[n:] - c[:-n]) / n
    return np.concatenate((np.full(n // 2, y[0]), y, np.full(len(x) - len(y) - n // 2, y[-1])))


def piano_wave(f):
    """Additive synthesis: 8 harmonics, higher ones quieter and decaying faster."""
    return sum(np.sin(2 * np.pi * f * k * T) * np.exp(-T * (1.5 + k * .65)) / k ** 1.4
               for k in range(1, 9) if f * k < RATE / 2)


def bass_wave(n, fx):
    """Karplus-Strong plucked string followed by the selected effects chain."""
    f = hz(n)
    L = max(2, round(RATE / f - .5))
    rng = np.random.default_rng(n)
    slap = 'Slap' in fx
    exc = rng.uniform(-1, 1, L)
    if not slap:
        exc = smooth(exc, 3)                     # softer finger pluck
    y = np.zeros(len(T))
    y[:L] = exc
    a = .994 if slap else .996
    i = L
    while i < len(y):                            # vectorised in blocks of L-1 samples
        j = min(i + L - 1, len(y))
        y[i:j] = a * .5 * (y[i - L:j - L] + y[i - L + 1:j - L + 1])
        i = j
    y *= np.exp(-T * (1.2 if slap else .7))
    y /= max(np.max(np.abs(y)), 1e-9)
    if slap:                                     # bright thumb transient
        y += np.diff(rng.uniform(-1, 1, len(T) + 1)) * np.exp(-T * 350) * .45
    if 'Compressor' in fx:
        env = np.sqrt(smooth(y * y, 441)) + 1e-9
        thr, ratio = .2, 4
        y = y * np.where(env > thr, (thr + (env - thr) / ratio) / env, 1)
        y /= np.max(np.abs(y))                   # make-up gain
    if 'Distortion' in fx:
        y = smooth(np.tanh(7 * y) / np.tanh(7), 3)
    right = None
    if 'Chorus' in fx:
        lfo = .005 * np.sin(2 * np.pi * .9 * T)
        left = .75 * y + .6 * np.interp(T - (.02 + lfo), T, y, left=0)
        right = .75 * y + .6 * np.interp(T - (.02 - lfo), T, y, left=0)
        y = left
    return y, right


def drum_t(sec): return np.arange(int(RATE * sec)) / RATE
def noise(n, seed): return np.random.default_rng(seed).uniform(-1, 1, n)


def kick():
    t = drum_t(.5)
    f = 45 + 110 * np.exp(-t * 28)               # fast pitch drop
    return np.sin(2 * np.pi * np.cumsum(f) / RATE) * np.exp(-t * 7) + noise(len(t), 1) * np.exp(-t * 400) * .25


def snare():
    t = drum_t(.3)
    return np.diff(noise(len(t) + 1, 2)) * .5 * np.exp(-t * 16) + np.sin(2 * np.pi * 185 * t) * np.exp(-t * 22) * .6


def hihat():
    t = drum_t(.12)
    return np.diff(noise(len(t) + 2, 3), 2) * np.exp(-t * 55)


def clap():
    t = drum_t(.35)
    env = sum(np.where(t >= o, np.exp(-(t - o) * 220), 0) for o in (0, .011, .022))
    env = env + np.where(t >= .033, np.exp(-(t - .033) * 14) * .6, 0)
    return np.diff(noise(len(t) + 1, 4)) * env


def click_wave(accent):
    t = drum_t(.05)
    return np.sin(2 * np.pi * (2000 if accent else 1400) * t) * np.exp(-t * 90)


DRUMS = [('Kick', kick, 1.0), ('Snare', snare, .85), ('Hi-hat', hihat, .5), ('Clap', clap, .75)]


def finish(left, right=None, level=1.0, attack=.008):
    """Click-free envelope, normalisation and conversion to a stereo pygame Sound."""
    t = np.arange(len(left)) / RATE
    env = np.minimum(t / attack, 1) * np.minimum((t[-1] - t) / min(.08, t[-1] / 4), 1)
    right = left if right is None else right
    st = np.column_stack((left * env, right * env))
    st *= 22000 * level / max(np.max(np.abs(st)), 1e-9)
    snd = pg.sndarray.make_sound(np.ascontiguousarray(st.astype(np.int16)))
    return snd, pg.sndarray.samples(snd)


@lru_cache(maxsize=192)
def sound(inst, n, fx=()):
    if inst == 'Piano':
        return finish(piano_wave(hz(n)))
    if inst == 'Bass':
        return finish(*bass_wave(n, fx))
    if inst == 'Drums':
        return finish(DRUMS[n][1](), level=DRUMS[n][2], attack=.0005)
    return finish(click_wave(n), level=.55, attack=.0005)


# ---------------------------------------------------------------- state
S = SimpleNamespace(
    mode='Piano', volume=.65, selected=3, last='', status='',
    pedal_held=False, pedal_latched=False, fx={k: False for k in FX},
    bpm=100, metro=False, drums=False, step=0, next_step=0, preset=0,
    view='Off', root=0, scale=0, chord=0,
    lesson=None, lstep=0, lhits=0, lmiss=0, lmsg='',
    sel_track=0, recording=False, playing=False, t0=0, rec=[], rec_open={}, tid=0, pb=[0] * 4,
)
active = {}            # token -> playing note
sustained = set()      # piano tokens released while the sustain pedal is down
voices = []            # [samples, start_ms, volume, release_ms] for the spectrum analyser
scheduled = []         # (time_ms, callback)
pattern = [[False] * 16 for _ in DRUMS]
tracks = [dict(events=[], length=0, mute=False) for _ in range(4)]
drum_flash = [0] * len(DRUMS)


def fx_now(): return tuple(k for k in FX if S.fx[k])
def is_pb(token): return isinstance(token, tuple) and token[0] == 'pb'
def sustain_on(): return S.pedal_held or S.pedal_latched
def rec_time(): return now() - S.t0
def schedule(delay, fn): scheduled.append((now() + delay, fn))


def play(token, inst, n, fx=(), pos=None, vol=None, live=True):
    """Start a note. token identifies it for stop(); None means a one-shot sound."""
    if token in sustained:
        stop(token, force=True)
    if token is not None and token in active:
        return
    vol = S.volume if vol is None else vol
    snd, samples = sound(inst, n, fx)
    ch = snd.play()
    if ch is None:
        return
    ch.set_volume(vol)
    voice = [samples, now(), vol, None]
    voices.append(voice)
    if token is not None:
        active[token] = dict(ch=ch, snd=snd, inst=inst, n=n, pos=pos, voice=voice)
    if inst == 'Drums':
        drum_flash[n] = now()
    if not live:
        return
    S.last = f'{inst}: {name(n)}  |  {hz(n):.2f} Hz' if inst != 'Drums' else f'Drums: {DRUMS[n][0]}'
    if inst == 'Bass':
        lesson_check(n)
    if S.recording:
        tid = None
        if token is not None:
            S.tid += 1
            tid = S.rec_open[token] = S.tid
        S.rec.append(('on', rec_time(), tid, inst, n, fx, pos, vol))


def stop(token, force=False):
    a = active.get(token)
    if a is None:
        return
    if not force and a['inst'] == 'Piano' and sustain_on() and not is_pb(token):
        sustained.add(token)
        return
    sustained.discard(token)
    del active[token]
    if a['ch'].get_sound() is a['snd']:
        a['ch'].fadeout(100)
    a['voice'][3] = now()
    if token in S.rec_open:
        S.rec.append(('off', rec_time(), S.rec_open.pop(token)))


def release_live():
    for t in list(active):
        if not is_pb(t):
            stop(t, force=True)


def pedal_changed():
    if not sustain_on():
        for t in list(sustained):
            stop(t, force=True)


def toggle_latch():
    S.pedal_latched = not S.pedal_latched
    pedal_changed()


def switch(m):
    release_live()
    S.pedal_held = False
    S.mode = m


def bass_pos(n):
    options = [(s, n - STRINGS[s]) for s in range(4) if 0 <= n - STRINGS[s] <= 24]
    return min(options, key=lambda p: p[1]) if options else None


# ---------------------------------------------------------------- metronome and drum machine
def seq_running(): return S.metro or S.drums
def set_bpm(v): S.bpm = max(40, min(240, v))


def seq_toggle(attr):
    if not seq_running():
        S.step, S.next_step = 0, now()
    setattr(S, attr, not getattr(S, attr))


def update_seq():
    if not seq_running():
        return
    t = now()
    if t - S.next_step > 250:                    # window was stalled: resync instead of bursting
        S.next_step = t
    while t >= S.next_step:
        s = S.step % 16
        if S.drums:
            for d in range(len(DRUMS)):
                if pattern[d][s]:
                    play(None, 'Drums', d, live=False)
        if S.metro and s % 4 == 0:
            play(None, 'Click', int(s == 0), live=False)
        S.step += 1
        S.next_step += 60000 / S.bpm / 4         # sixteenth notes


def load_preset(i):
    S.preset = i
    pattern[:] = [[c == 'x' for c in row] for row in PRESETS[i][1]]


def clear_pattern():
    for row in pattern:
        row[:] = [False] * 16


def toggle_step(d, s): pattern[d][s] = not pattern[d][s]


# ---------------------------------------------------------------- scales and chords
def theory_list(): return SCALES if S.view == 'Scale' else CHORDS
def theory_index(): return S.scale if S.view == 'Scale' else S.chord


def theory_pcs():
    if S.view == 'Off':
        return set()
    return {(S.root + i) % 12 for i in theory_list()[theory_index()][1]}


def theory_text():
    if S.view == 'Off':
        return ''
    nm, ints = theory_list()[theory_index()]
    return f'{NAMES[S.root]} {nm} {S.view.lower()}: ' + ' '.join(NAMES[(S.root + i) % 12] for i in ints)


def shift_root(d): S.root = (S.root + d) % 12
def cycle_view(): S.view = {'Off': 'Scale', 'Scale': 'Chord', 'Chord': 'Off'}[S.view]


def cycle_type():
    if S.view == 'Scale':
        S.scale = (S.scale + 1) % len(SCALES)
    elif S.view == 'Chord':
        S.chord = (S.chord + 1) % len(CHORDS)
    else:
        S.view = 'Scale'


def theory_play():
    if S.view == 'Off' or S.mode == 'Drums':
        return
    inst = S.mode
    base = (60 if inst == 'Piano' else 40) + S.root
    fx = fx_now() if inst == 'Bass' else ()
    ints = theory_list()[theory_index()][1]
    if S.view == 'Chord':
        for k, i in enumerate(ints):
            play(('demo', k), inst, base + i, fx, bass_pos(base + i), live=False)
            schedule(1200, lambda k=k: stop(('demo', k), True))
    else:
        for k, n in enumerate([base + i for i in ints] + [base + 12]):
            schedule(k * 280, lambda k=k, n=n: play(('demo', k), inst, n, fx, bass_pos(n), live=False))
            schedule(k * 280 + 260, lambda k=k: stop(('demo', k), True))


# ---------------------------------------------------------------- bass lessons
def lesson_done(): return S.lesson is not None and S.lstep >= len(LESSONS[S.lesson][2])


def lesson_target():
    s, f = LESSONS[S.lesson][2][S.lstep]
    return s, f, STRINGS[s] + f


def lesson_set(i):
    S.lesson, S.lstep, S.lhits, S.lmiss = i, 0, 0, 0
    S.lmsg = 'Play the highlighted note.' if i is not None else ''


def lesson_cycle():
    nxt = 0 if S.lesson is None else S.lesson + 1
    lesson_set(nxt if nxt < len(LESSONS) else None)


def lesson_check(n):
    if S.lesson is None or lesson_done():
        return
    _, _, target = lesson_target()
    if n == target:
        S.lstep += 1
        S.lhits += 1
        if lesson_done():
            acc = 100 * S.lhits / (S.lhits + S.lmiss)
            S.lmsg = f'Lesson complete! Accuracy {acc:.0f}%. Restart or pick the next lesson.'
        else:
            S.lmsg = 'Correct!'
    else:
        S.lmiss += 1
        S.lmsg = f'Not quite: you played {name(n)}, the target is {name(target)}.'


def lesson_listen():
    for k, (s, f) in enumerate(LESSONS[S.lesson][2]):
        schedule(k * 420, lambda k=k, s=s, f=f: play(('demo', k), 'Bass', STRINGS[s] + f, fx_now(), (s, f), live=False))
        schedule(k * 420 + 380, lambda k=k: stop(('demo', k), True))


# ---------------------------------------------------------------- multitrack recorder
def transport_stop():
    if S.recording:
        for tid in S.rec_open.values():
            S.rec.append(('off', rec_time(), tid))
        S.rec_open.clear()
        if S.rec:
            tracks[S.sel_track].update(events=S.rec, length=rec_time())
            S.status = f'Track {S.sel_track + 1} recorded ({sum(e[0] == "on" for e in S.rec)} notes)'
        else:
            S.status = 'Nothing recorded: track unchanged'
    S.recording = S.playing = False
    for t in list(active):
        if is_pb(t):
            stop(t, force=True)


def transport_start(record):
    transport_stop()
    if not record and not any(tr['events'] for tr in tracks):
        S.status = 'Nothing to play yet: record a track first'
        return
    S.recording, S.playing, S.t0, S.pb, S.rec = record, True, now(), [0] * 4, []
    if record:
        S.status = f'Recording track {S.sel_track + 1}...'
    if seq_running():                            # align drums/metronome with the take
        S.step, S.next_step = 0, now()


def rec_toggle():
    if S.recording:
        transport_stop()
    else:
        transport_start(True)


def play_toggle():
    if S.playing and not S.recording:
        transport_stop()
    else:
        transport_start(False)


def update_transport():
    if not S.playing:
        return
    t, busy = rec_time(), S.recording
    for i, tr in enumerate(tracks):
        if S.recording and i == S.sel_track:
            continue
        ev = tr['events']
        while S.pb[i] < len(ev) and ev[S.pb[i]][1] <= t:
            e = ev[S.pb[i]]
            S.pb[i] += 1
            if e[0] == 'on' and not tr['mute']:
                play(None if e[2] is None else ('pb', i, e[2]), *e[3:8], live=False)
            elif e[0] == 'off':
                stop(('pb', i, e[2]), force=True)
        busy = busy or (ev and t <= tr['length'])
    if not busy:
        transport_stop()


def select_track(i):
    if not S.recording:
        S.sel_track = i


def toggle_mute(i): tracks[i]['mute'] = not tracks[i]['mute']


def clear_track(i):
    if not (S.recording and i == S.sel_track):
        tracks[i].update(events=[], length=0)


def track_info(tr):
    if not tr['events']:
        return 'empty'
    insts = sorted({e[3] for e in tr['events'] if e[0] == 'on'})
    notes = sum(e[0] == 'on' for e in tr['events'])
    return f'{" + ".join(insts)} | {notes} notes | {tr["length"] / 1000:.1f} s'


def export_wav():
    live = [tr for tr in tracks if tr['events'] and not tr['mute']]
    if not live:
        S.status = 'Nothing to export'
        return
    mix = np.zeros((int((max(tr['length'] for tr in live) / 1000 + NOTE_SECONDS) * RATE), 2))
    fade = int(.1 * RATE)
    for tr in live:
        offs = {e[2]: e[1] for e in tr['events'] if e[0] == 'off'}
        for e in tr['events']:
            if e[0] != 'on':
                continue
            _, t, tid, inst, n, fx, pos, vol = e
            wav = sound(inst, n, fx)[1].astype(float) * vol
            if tid in offs:                      # cut at release with a 100 ms fade, like live play
                keep = int((offs[tid] - t) * RATE / 1000)
                if keep < len(wav):
                    end = min(len(wav), keep + fade)
                    wav = wav[:end]
                    wav[keep:end] *= np.linspace(1, 0, end - keep)[:, None]
            s = int(t * RATE / 1000)
            seg = wav[:max(0, len(mix) - s)]
            mix[s:s + len(seg)] += seg
    peak = np.max(np.abs(mix))
    if peak > 32000:
        mix *= 32000 / peak
    fname = time.strftime('zaroni_recording_%Y%m%d_%H%M%S.wav')
    with wave.open(fname, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(mix.astype('<i2').tobytes())
    S.status = f'Exported {fname}'


# ---------------------------------------------------------------- FFT spectrum
SPEC_N = 8192
HANN = np.hanning(SPEC_N)
FREQS = np.fft.rfftfreq(SPEC_N, 1 / RATE)
NB, F_LO, F_HI = 72, 30, 8000
EDGES = np.geomspace(F_LO, F_HI, NB + 1)
B_LO = np.searchsorted(FREQS, EDGES[:-1])
B_HI = np.maximum(np.searchsorted(FREQS, EDGES[1:]), B_LO + 1)
bars = np.zeros(NB)
peak = [None]


def analyse():
    """Mix the last SPEC_N samples of every sounding voice and update the spectrum bars."""
    t = now()
    buf = np.zeros(SPEC_N)
    alive = []
    for v in voices:
        samples, start, vol, rel = v
        pos = int((t - start) * RATE / 1000)
        fade = 1.0 if rel is None else 1 - (t - rel) / 100
        if fade <= 0 or pos - SPEC_N >= len(samples):
            continue
        alive.append(v)
        lo, hi = max(0, pos - SPEC_N), min(len(samples), pos)
        if hi > lo:
            buf[lo - pos + SPEC_N:hi - pos + SPEC_N] += samples[lo:hi, 0] * (vol * fade)
    voices[:] = alive
    mag = np.abs(np.fft.rfft(buf * HANN)) / (SPEC_N / 4) / 32768
    db = 20 * np.log10(mag + 1e-9)
    level = np.clip((db + 80) / 80, 0, 1)
    bars[:] = np.maximum([level[a:b].max() for a, b in zip(B_LO, B_HI)], bars * .88)
    peak[0] = None
    if db[1:B_HI[-1]].max() < -55:
        return
    # Harmonic product spectrum: multiplying the spectrum with copies compressed by 2, 3 and 4
    # reinforces the fundamental even when an upper harmonic is the loudest partial.
    lo, hi = np.searchsorted(FREQS, [F_LO, 1500])
    hps = np.log(mag[:hi] + 1e-12)
    for h in (2, 3, 4):
        hps += np.log(mag[::h][:hi] + 1e-12)
    k = lo + int(np.argmax(hps[lo:hi]))
    if k >= 1:
        a, b, c = db[k - 1], db[k], db[k + 1]
        p = .5 * (a - c) / (a - 2 * b + c) if a - 2 * b + c else 0
        peak[0] = (k + p) * RATE / SPEC_N


# ---------------------------------------------------------------- drawing
widgets = []           # (rect, callback(pos)) registered while drawing, hit-tested on click
WHITE = [n for n in range(60, 84) if n % 12 in (0, 2, 4, 5, 7, 9, 11)]
whites = [(pg.Rect(20 + i * 88, 145, 87, 300), n) for i, n in enumerate(WHITE)]
blacks = [(pg.Rect(r.right - 26, 145, 52, 185), n + 1) for r, n in whites if n % 12 in (0, 2, 5, 7, 9)]
LEFT, FW, SY = 90, 44, [190, 250, 310, 370]


def text(s, x, y, color=TEXT, f=None, anchor='topleft'):
    img = (f or font).render(str(s), True, color)
    screen.blit(img, img.get_rect(**{anchor: (x, y)}))


def hot(rect, fn): widgets.append((pg.Rect(rect), fn))


def button(rect, label, on=False, fn=None, color=None, f=None):
    r = pg.Rect(rect)
    pg.draw.rect(screen, color or (ON if on else BTN), r, border_radius=6)
    text(label, *r.center, f=f, anchor='center')
    if fn:
        hot(r, lambda p: fn())


def draw_header():
    text('Zaroni Virtual Instruments', 20, 12, f=big)
    text(S.last, W - 20, 20, GREEN, anchor='topright')
    for i, m in enumerate(MODES):
        button((20 + i * 118, 55, 110, 32), m, S.mode == m, lambda m=m: switch(m))
    text('Volume', 390, 62)
    pg.draw.rect(screen, BTN, (460, 66, 200, 8), border_radius=4)
    pg.draw.rect(screen, GREEN, (460, 66, int(S.volume * 200), 8), border_radius=4)
    hot((455, 56, 210, 28), lambda p: setattr(S, 'volume', min(1, max(0, (p[0] - 460) / 200))))
    button((700, 55, 120, 32), 'Metronome', S.metro, lambda: seq_toggle('metro'))
    button((830, 55, 32, 32), '-', fn=lambda: set_bpm(S.bpm - 5))
    text(f'{S.bpm} BPM', 906, 71, anchor='center')
    button((950, 55, 32, 32), '+', fn=lambda: set_bpm(S.bpm + 5))
    beat = ((S.step - 1) % 16) // 4 if seq_running() else -1
    for i in range(4):
        pg.draw.circle(screen, (ORANGE if i == 0 else GREEN) if i == beat else BTN, (1005 + i * 24, 71), 8)


def draw_theory_bar():
    button((810, 100, 28, 30), '<', fn=lambda: shift_root(-1))
    text(NAMES[S.root], 858, 115, anchor='center')
    button((878, 100, 28, 30), '>', fn=lambda: shift_root(1))
    button((914, 100, 110, 30), f'View: {S.view}', S.view != 'Off', cycle_view)
    label = theory_list()[theory_index()][0] if S.view != 'Off' else 'Scales / chords'
    button((1030, 100, 150, 30), label, fn=cycle_type)
    button((1186, 100, 74, 30), 'Play', fn=theory_play)
    text(theory_text(), W - 20, 462, ORANGE, anchor='topright')


def draw_piano():
    button((20, 100, 190, 30), 'Sustain pedal: ' + ('ON' if sustain_on() else 'OFF'), sustain_on(), toggle_latch)
    text('Hold SPACE, or click to latch', 222, 107, DIM)
    draw_theory_bar()
    notes = {a['n'] for a in active.values() if a['inst'] == 'Piano'}
    pcs = theory_pcs()
    for r, n in whites + blacks:
        black = n % 12 in (1, 3, 6, 8, 10)
        if n in notes:
            col = GREEN
        elif pcs and n % 12 == S.root:
            col = (170, 100, 30) if black else (250, 200, 130)
        elif n % 12 in pcs:
            col = (40, 80, 130) if black else (185, 215, 250)
        else:
            col = (12, 14, 18) if black else (245, 245, 245)
        pg.draw.rect(screen, col, r, border_radius=3)
        if not black:
            pg.draw.rect(screen, (90, 90, 90), r, 1, border_radius=3)
        tc = (220, 220, 220) if black else (40, 40, 40)
        text(name(n), r.x + 7, r.bottom - 46, tc, small)
        text(PIANO_KEYS[n - 60].upper(), r.x + 7, r.bottom - 26, tc)
        hot(r, lambda p, n=n: play('mouse', 'Piano', n))
    text('Keys Z..U play notes | hold SPACE: sustain pedal | Left/Right: theory root | TAB: switch', 20, 462, DIM)


def bass_click(p):
    x, y = p
    s = min(range(4), key=lambda i: abs(y - SY[i]))
    fret = int((x - LEFT) // FW)
    if abs(y - SY[s]) < 30 and 0 <= fret <= 24:
        S.selected = s
        play('mouse', 'Bass', STRINGS[s] + fret, fx_now(), (s, fret))


def draw_bass():
    for i, k in enumerate(FX):
        button((20 + i * 116, 100, 110, 30), f'F{i + 1} {k}', S.fx[k], lambda k=k: S.fx.update({k: not S.fx[k]}), f=small)
    label = 'Lesson: off' if S.lesson is None else f'Lesson {S.lesson + 1}/{len(LESSONS)}'
    button((490, 100, 170, 30), label, S.lesson is not None, lesson_cycle)
    if S.lesson is not None:
        button((666, 100, 64, 30), 'Restart', fn=lambda: lesson_set(S.lesson), f=small)
        button((736, 100, 64, 30), 'Listen', fn=lesson_listen, f=small)
    draw_theory_bar()
    pg.draw.rect(screen, (100, 67, 44), (LEFT, 160, 25 * FW, 240), border_radius=4)
    for fret in range(25):
        x = LEFT + fret * FW
        pg.draw.line(screen, (190, 190, 180), (x, 160), (x, 400), 4 if fret == 1 else 2)
        text(fret, x + 22, 140, DIM, small, 'midtop')
        if fret in INLAYS:
            pg.draw.circle(screen, (205, 190, 155), (x + 22, 280), 5)
    pcs = theory_pcs()
    lit = {a['pos'] for a in active.values() if a['inst'] == 'Bass'}
    targets = []
    if S.lesson is not None and not lesson_done():
        seq = LESSONS[S.lesson][2]
        targets = seq[S.lstep:S.lstep + 2]
    for s, y in enumerate(SY):
        text(name(STRINGS[s]), 25, y - 10, GREEN if S.selected == s else TEXT)
        pg.draw.line(screen, (215, 215, 210), (LEFT, y), (LEFT + 25 * FW, y), 2 + s)
        for fret in range(25):
            cx, pc = LEFT + fret * FW + 22, (STRINGS[s] + fret) % 12
            if pc in pcs:
                pg.draw.circle(screen, ORANGE if pc == S.root else BLUE, (cx, y), 9)
            if targets and (s, fret) == targets[0]:
                pg.draw.circle(screen, ORANGE, (cx, y), int(21 + 3 * np.sin(now() / 150)), 3)
            elif len(targets) > 1 and (s, fret) == targets[1]:
                pg.draw.circle(screen, DIM, (cx, y), 18, 2)
            if (s, fret) in lit:
                pg.draw.circle(screen, (60, 190, 140), (cx, y), 18)
                text(NAMES[(STRINGS[s] + fret) % 12], cx, y, (15, 30, 25), anchor='center')
    hot((LEFT, 160, 25 * FW, 240), bass_click)
    if S.lesson is None:
        text('Tip: click "Lesson" to start an interactive bass lesson.', 20, 412, DIM)
    else:
        title, desc, seq = LESSONS[S.lesson]
        text(f'{title}: {desc}', 20, 408, ORANGE)
        if lesson_done():
            text(S.lmsg, 20, 430, GREEN)
        else:
            s, f, n = lesson_target()
            text(f'Step {S.lstep + 1}/{len(seq)}: play {name(n)} ({name(STRINGS[s])} string, fret {f})   {S.lmsg}', 20, 430)
    text('UP/DOWN string | SPACE open | 1-0 Q-P A-F frets 1-24 | F1-F4 effects | TAB switch', 20, 462, DIM)


def draw_drums():
    button((20, 100, 160, 30), 'Stop pattern' if S.drums else 'Start pattern', S.drums, lambda: seq_toggle('drums'))
    button((188, 100, 170, 30), f'Preset: {PRESETS[S.preset][0]}', fn=lambda: load_preset((S.preset + 1) % len(PRESETS)))
    button((366, 100, 80, 30), 'Clear', fn=clear_pattern)
    text('16 steps = one bar of 4/4 at the metronome tempo', 460, 107, DIM)
    cur = (S.step - 1) % 16 if S.drums else -1
    for d, (nm, _, _) in enumerate(DRUMS):
        y = 150 + d * 62
        flash = now() - drum_flash[d] < 110
        button((20, y, 100, 54), f'{d + 1}  {nm}', flash, lambda d=d: play(None, 'Drums', d))
        for s in range(16):
            r = pg.Rect(130 + s * 70, y, 64, 54)
            base = (52, 57, 67) if (s // 4) % 2 == 0 else (44, 48, 57)
            pg.draw.rect(screen, DRUM_COLORS[d] if pattern[d][s] else base, r, border_radius=5)
            if s == cur:
                pg.draw.rect(screen, TEXT, r, 2, border_radius=5)
            hot(r, lambda p, d=d, s=s: toggle_step(d, s))
    for s in range(16):
        text(s + 1, 130 + s * 70 + 32, 396, DIM if s % 4 else TEXT, small, 'midtop')
    text('1-4: play pads | SPACE: start/stop pattern | click cells to edit | TAB: switch', 20, 462, DIM)


def draw_spectrum():
    pg.draw.rect(screen, PANEL, (20, 490, 600, 240), border_radius=8)
    text('Spectrum (real-time FFT)', 32, 498)
    analyse()
    if peak[0]:
        f = peak[0]
        n = round(69 + 12 * np.log2(f / 440))
        cents = 1200 * np.log2(f / hz(n))
        text(f'Pitch {f:.1f} Hz  ~ {name(n)} {cents:+.0f} cents', 608, 500, ORANGE, small, 'topright')
    plot = pg.Rect(32, 525, 576, 175)
    for i in range(1, 4):
        y = plot.y + plot.h * i // 4
        pg.draw.line(screen, (45, 50, 60), (plot.x, y), (plot.right, y))
    bw = plot.w / NB
    for i, v in enumerate(bars):
        h = int(v * plot.h)
        col = [int(GREEN[c] + (ORANGE[c] - GREEN[c]) * v) for c in range(3)]
        pg.draw.rect(screen, col, (plot.x + i * bw + 1, plot.bottom - h, max(1, bw - 2), h))
    for f, lab in ((50, '50'), (100, '100'), (200, '200'), (500, '500'), (1000, '1k'), (2000, '2k'), (5000, '5k')):
        x = plot.x + plot.w * np.log(f / F_LO) / np.log(F_HI / F_LO)
        pg.draw.line(screen, (70, 75, 85), (x, plot.bottom), (x, plot.bottom + 4))
        text(lab, x, plot.bottom + 6, DIM, small, 'midtop')


def draw_recorder():
    pg.draw.rect(screen, PANEL, (640, 490, 620, 240), border_radius=8)
    text('Multitrack recorder', 652, 498)
    text(S.status, 1248, 500, DIM, small, 'topright')
    button((652, 526, 90, 30), 'Rec (F9)', S.recording, rec_toggle, RED if S.recording else None)
    button((748, 526, 90, 30), 'Play (F10)', S.playing and not S.recording, play_toggle)
    button((844, 526, 70, 30), 'Stop', fn=transport_stop)
    button((920, 526, 110, 30), 'Export WAV', fn=export_wav)
    if S.playing:
        t = rec_time() / 1000
        text(f'{"REC" if S.recording else "PLAY"} {int(t // 60):02d}:{t % 60:04.1f}', 1248, 534,
             RED if S.recording else GREEN, anchor='topright')
    for i, tr in enumerate(tracks):
        r = pg.Rect(652, 566 + i * 40, 596, 34)
        armed = i == S.sel_track
        pg.draw.rect(screen, (48, 53, 63) if armed else (40, 44, 52), r, border_radius=6)
        if armed:
            pg.draw.rect(screen, RED if S.recording else GREEN, r, 2, border_radius=6)
        if S.playing and tr['length'] and not (S.recording and armed):
            frac = min(1, rec_time() / tr['length'])
            pg.draw.rect(screen, GREEN, (r.x + 4, r.bottom - 5, int((r.w - 8) * frac), 2))
        hot(r, lambda p, i=i: select_track(i))
        text(f'Track {i + 1}', r.x + 10, r.y + 8)
        text(track_info(tr), r.x + 80, r.y + 10, DIM, small)
        button((r.right - 112, r.y + 4, 46, 26), 'Mute', fn=lambda i=i: toggle_mute(i), f=small,
               color=ORANGE if tr['mute'] else None)
        button((r.right - 60, r.y + 4, 54, 26), 'Clear', fn=lambda i=i: clear_track(i), f=small)


def draw():
    widgets.clear()
    screen.fill(BG)
    draw_header()
    {'Piano': draw_piano, 'Bass': draw_bass, 'Drums': draw_drums}[S.mode]()
    draw_spectrum()
    draw_recorder()
    text('F5 metronome | -/= tempo | Left/Right theory root | F8 scale/chord view | F9 record | '
         'F10 play | TAB switch instrument | ESC quit', 20, 738, DIM, small)


# ---------------------------------------------------------------- input
def on_keydown(e):
    k = pg.key.name(e.key)
    if e.key == pg.K_ESCAPE:
        return False
    if e.key == pg.K_TAB:
        switch(MODES[(MODES.index(S.mode) + 1) % len(MODES)])
    elif e.key == pg.K_F5:
        seq_toggle('metro')
    elif e.key in (pg.K_MINUS, pg.K_KP_MINUS):
        set_bpm(S.bpm - 5)
    elif e.key in (pg.K_EQUALS, pg.K_KP_PLUS):
        set_bpm(S.bpm + 5)
    elif e.key == pg.K_F8:
        cycle_view()
    elif e.key in (pg.K_LEFT, pg.K_RIGHT):
        shift_root(-1 if e.key == pg.K_LEFT else 1)
    elif e.key == pg.K_F9:
        rec_toggle()
    elif e.key == pg.K_F10:
        play_toggle()
    elif S.mode == 'Piano':
        if e.key == pg.K_SPACE:
            S.pedal_held = True
        elif len(k) == 1 and k in PIANO_KEYS:
            play(e.key, 'Piano', 60 + PIANO_KEYS.index(k))
    elif S.mode == 'Bass':
        fkeys = [pg.K_F1, pg.K_F2, pg.K_F3, pg.K_F4]
        if e.key in fkeys:
            fx = FX[fkeys.index(e.key)]
            S.fx[fx] = not S.fx[fx]
        elif e.key in (pg.K_UP, pg.K_DOWN):
            S.selected = (S.selected + (-1 if e.key == pg.K_UP else 1)) % 4
        elif e.key == pg.K_SPACE:
            play(e.key, 'Bass', STRINGS[S.selected], fx_now(), (S.selected, 0))
        elif len(k) == 1 and k in BASS_KEYS:
            fret = BASS_KEYS.index(k) + 1
            play(e.key, 'Bass', STRINGS[S.selected] + fret, fx_now(), (S.selected, fret))
    elif S.mode == 'Drums':
        if e.key == pg.K_SPACE:
            seq_toggle('drums')
        elif len(k) == 1 and k in '1234':
            play(None, 'Drums', int(k) - 1)
    return True


def on_keyup(e):
    if e.key == pg.K_SPACE and S.pedal_held:
        S.pedal_held = False
        pedal_changed()
    stop(e.key)


def run_scheduled():
    t = now()
    due = [s for s in scheduled if s[0] <= t]
    for s in due:
        scheduled.remove(s)
        s[1]()


def main():
    load_preset(0)
    running = True
    while running:
        for e in pg.event.get():
            if e.type == pg.QUIT:
                running = False
            elif e.type == pg.WINDOWFOCUSLOST:
                release_live()
            elif e.type == pg.KEYDOWN:
                running = on_keydown(e)
            elif e.type == pg.KEYUP:
                on_keyup(e)
            elif e.type == pg.MOUSEBUTTONDOWN and e.button == 1:
                for r, fn in reversed(widgets):
                    if r.collidepoint(e.pos):
                        fn(e.pos)
                        break
            elif e.type == pg.MOUSEBUTTONUP and e.button == 1:
                stop('mouse')
        run_scheduled()
        update_seq()
        update_transport()
        draw()
        pg.display.flip()
        clock.tick(120)
    transport_stop()
    pg.quit()


if __name__ == '__main__':
    main()
