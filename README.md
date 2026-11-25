# Zaroni Virtual Instruments

A Python desktop application that turns your computer into a small music studio: a **piano**, a **four-string bass guitar** and a **drum machine**, plus a metronome, scale/chord visualizer, interactive bass lessons, a real-time FFT spectrum analyzer and a multitrack recorder. Every sound is synthesized in real time with NumPy. No recorded samples are used.

## Requirements and installation

- Python 3.10+
- `pygame` 2.6+ and `numpy` (see `requirements.txt`)

```bash
python -m pip install -r requirements.txt
python main.py
```

## Features

| Feature                     | Description                                                                                  |
| --------------------------- | -------------------------------------------------------------------------------------------- |
| Piano                       | Two octaves (C4–B5), mouse or computer keyboard, chords, **sustain pedal**                   |
| Bass guitar                 | 4 strings × 24 frets (E1–G4), Karplus-Strong plucked-string synthesis                        |
| Bass effects                | **Distortion, chorus, compressor and slap**, freely combinable                               |
| Metronome                   | Adjustable tempo (40–240 BPM), accented downbeat, visual beat indicator                      |
| Scales and chords           | 7 scales and 8 chord types in any key, highlighted on the piano keys and the bass fretboard  |
| Interactive bass lessons    | 5 guided lessons with target highlighting, instant feedback and an accuracy score            |
| Real-time FFT spectrum      | Live frequency spectrum of everything that is sounding, with pitch detection                 |
| Drum machine                | 16-step sequencer with 4 synthesized drums and 4 preset grooves                              |
| Multitrack recording        | 4 tracks with overdubbing, mute, clear and WAV export                                        |

### Instruments at a glance

| Feature              | Piano                    | Bass guitar                       | Drums                          |
| -------------------- | ------------------------ | --------------------------------- | ------------------------------ |
| Graphical interface  | White and black keys     | Strings and fretboard             | Pads and 16-step grid          |
| Musical range        | Two octaves (C4–B5)      | 4 strings, 24 frets (E1–G4)       | Kick, snare, hi-hat, clap      |
| Mouse interaction    | Click keys               | Click strings and frets           | Click pads and grid cells      |
| Computer keyboard    | Play notes               | Play notes                        | Play pads (1–4)                |
| Sound synthesis      | Harmonics and decay      | Plucked-string synthesis + FX     | Noise and pitch-swept sines    |
| Polyphony            | Chords                   | Multiple simultaneous notes       | Layered hits                   |
| Visual feedback      | Highlighted keys         | Highlighted fret positions        | Flashing pads, step cursor     |
| Extras               | Sustain pedal            | Effects, lessons                  | Presets, sequencer             |
| Instrument switching | Button or TAB            | Button or TAB                     | Button or TAB                  |

Polyphony works by holding several computer keys at once; the mouse plays one note at a time. Each note sounds while the key or mouse button is held and fades out on release (up to three seconds).

## Screen layout

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Title                                                   last note + frequency │
│ [Piano][Bass][Drums]  Volume ━━━━━   [Metronome][-] 100 BPM [+]  ● ● ● ●      │
│ instrument toolbar (pedal / effects / lessons / drum presets)  theory toolbar │
│                                                                              │
│                 instrument: keyboard / fretboard / step grid                 │
│                                                                              │
├───────────────────────────────────┬──────────────────────────────────────────┤
│ Spectrum (real-time FFT)          │ Multitrack recorder: Rec Play Stop Export │
│ ▁▃▅▇▆▄▂▁                          │ Track 1 … Track 4  (select, Mute, Clear)  │
└───────────────────────────────────┴──────────────────────────────────────────┘
```

## Controls

### Global

| Control         | Action                                        |
| --------------- | --------------------------------------------- |
| Piano/Bass/Drums buttons | Open that instrument                  |
| TAB             | Cycle Piano → Bass → Drums                    |
| Mouse           | Play individual notes, press any button       |
| Volume bar      | Click to set the volume of the next notes     |
| F5              | Metronome on/off                              |
| `-` / `=`       | Tempo −5 / +5 BPM (also the `-` `+` buttons)  |
| Left / Right    | Change the root note of the scale/chord view  |
| F8              | Cycle theory view: Off → Scale → Chord        |
| F9              | Start/stop recording on the selected track    |
| F10             | Play/stop all recorded tracks                 |
| ESC             | Close the application                         |

> On macOS laptops, function keys may need the `fn` key. Every function is also available as an on-screen button.

### Piano

Each key shows its note name and the computer key that plays it. The bottom row (`Z S X D C V G B H N J M`) plays the first octave starting at C4; the top row (`Q 2 W 3 E R 5 T 6 Y 7 U`) plays the second octave starting at C5. Letters on black keys (`S D G H J`, `2 3 5 6 7`) play sharps, as on a real keyboard layout.

| Control              | Action                                   |
| -------------------- | ---------------------------------------- |
| Hold SPACE           | Sustain pedal (notes keep ringing)       |
| Sustain pedal button | Latch the pedal on/off with the mouse    |

### Bass guitar

| Control   | Action                          |
| --------- | ------------------------------- |
| Up/Down   | Select bass string              |
| Space     | Play the selected open string   |
| 1–0       | Frets 1–10                      |
| Q–P       | Frets 11–20                     |
| A–F       | Frets 21–24                     |
| F1–F4     | Toggle distortion, chorus, compressor, slap |

Clicking a string on the fretboard also selects it. The selected string's name is highlighted in green on the left.

### Drums

| Control                | Action                                      |
| ---------------------- | ------------------------------------------- |
| 1–4 or click a pad     | Play kick, snare, hi-hat, clap              |
| Space / Start pattern  | Start or stop the 16-step pattern           |
| Click a grid cell      | Turn that step on/off                       |
| Preset button          | Cycle Rock, Funk, House and Hip-hop grooves |
| Clear button           | Erase the pattern                           |

## Feature guide

### Bass effects

The four effects are applied when a bass note is synthesized and can be combined. The signal chain runs in this order: **slap → compressor → distortion → chorus**.

| Effect     | How it works |
| ---------- | ------------ |
| Slap       | Changes the *excitation* of the string: the noise burst is left unfiltered (brighter), a sharp high-frequency transient imitates the thumb hitting the string, and the note decays faster. Without slap, the burst is smoothed for a softer finger-style pluck. |
| Compressor | Measures the signal envelope (RMS over 10 ms). Above a threshold of 0.2 the level is reduced with a 4:1 ratio, then make-up gain restores the peak. Result: a more even, longer-sounding note. |
| Distortion | Soft-clipping waveshaper `tanh(7·x)`, which squares off the waveform and adds harmonics, followed by a light low-pass filter to tame harshness. |
| Chorus     | Mixes the dry signal with a copy delayed by about 20 ms, with the delay swept ±5 ms by a 0.9 Hz LFO. Left and right channels use opposite modulation, giving a wide stereo image. |

### Piano sustain pedal

While the pedal is down (SPACE held, or latched with the on-screen button), releasing a key no longer stops its note: it keeps ringing until the pedal is released or the note decays. Pressing a sustained key again re-strikes it. Releasing the pedal fades out all sustained notes together.

### Metronome

The metronome clicks on every beat at the chosen tempo (40–240 BPM). The first beat of each bar is accented with a higher-pitched click, and four dots in the header show the current beat. The metronome and the drum machine share the same clock, so they always stay in sync; starting a recording or playback restarts the bar so takes line up with the beat.

### Scales and chord visualization

The theory toolbar (Piano and Bass) chooses a **root note** (`<` `>` or Left/Right), a **view** (Off, Scale or Chord) and the **scale or chord type**:

- **Scales:** Major, Natural minor, Major pentatonic, Minor pentatonic, Blues, Dorian, Mixolydian
- **Chords:** Major, Minor, Dominant 7, Major 7, Minor 7, Diminished, Augmented, Sus4

Every key or fret position that belongs to the selection is highlighted: **orange** for the root, **blue** for the other notes. The note names are listed under the toolbar (e.g. `E Minor pentatonic scale: E G A B D`). **Play** plays the scale ascending or strums the chord on the current instrument.

Each scale/chord is stored as a list of semitone intervals from the root; for example, major = `[0, 2, 4, 5, 7, 9, 11]` and a minor 7 chord = `[0, 3, 7, 10]`.

### Interactive bass lessons

Click **Lesson** (Bass mode) to cycle through the lessons:

| # | Lesson               | What it teaches                                        |
| - | -------------------- | ------------------------------------------------------ |
| 1 | Open strings         | String names and tuning, E A D G and back              |
| 2 | E minor pentatonic   | The most common rock/blues bass scale                  |
| 3 | G major scale        | One-octave major scale fingering                       |
| 4 | Root-fifth-octave    | The classic groove shape, on A and D                   |
| 5 | Chromatic 1-2-3-4    | Finger independence across all strings                 |

The next target is marked with a **pulsing orange ring** and the following one with a grey ring. The status line names the note, string and fret. Playing the right pitch (on any string) advances the lesson; a wrong note is counted as a miss and explained. When you finish, the lesson shows your accuracy. **Listen** plays the whole exercise as a demonstration and **Restart** starts over.

### Real-time FFT spectrum

The analyzer mixes the most recent 8192 samples (about 186 ms) of every sounding voice (piano, bass, drums, metronome and playback), applies a Hann window and computes the **Fast Fourier Transform**:

$$
X[k] = \sum_{n=0}^{N-1} x[n]\, w[n]\, e^{-i 2\pi k n / N}, \qquad f_k = \frac{k \cdot f_s}{N}
$$

With *N* = 8192 and *f<sub>s</sub>* = 44,100 Hz, each bin is about 5.4 Hz wide, enough to separate the low bass notes. The magnitudes are converted to decibels and grouped into 72 logarithmically spaced bands from 30 Hz to 8 kHz, so each octave gets the same width, as the ear hears it. Bars fall back slowly for a smooth display.

The readout above the graph shows the detected **pitch**, the nearest note and the deviation in cents. Because a plucked bass string often has louder upper harmonics than its fundamental, the pitch is estimated with a **harmonic product spectrum**: the spectrum is multiplied by copies of itself compressed by factors 2, 3 and 4, so only the fundamental, where all harmonics line up, stays strong. Parabolic interpolation then refines the result between bins.

### Drum machine

A 16-step sequencer (one bar of 4/4 in sixteenth notes) running at the metronome tempo. Each of the four drums is synthesized:

| Drum   | Synthesis                                                                                   |
| ------ | ------------------------------------------------------------------------------------------- |
| Kick   | Sine wave whose pitch drops quickly from ~155 Hz to 45 Hz, plus a short noise click           |
| Snare  | High-passed noise burst mixed with a 185 Hz tone for the drum body                           |
| Hi-hat | Doubly differentiated (strongly high-passed) noise with a very short decay                   |
| Clap   | Three quick noise bursts 11 ms apart followed by a short reverb-like tail                    |

The grid is shaded in groups of four (one beat each). A white outline shows the current step, and the pads flash when they sound.

### Multitrack recording

The recorder stores **performance events**, not audio: each note-on and note-off with its time, instrument, note, effects and volume. This keeps recordings tiny and lets them be replayed through the same synthesizer.

1. Click a track row to **select** it (outlined in green).
2. Press **Rec** (F9) and play. Any instrument can be recorded, including live drum pads. The other tracks play back while you record, so you can **overdub** layer by layer.
3. Press **Stop** to finish the take (a take with no notes leaves the track unchanged).
4. Press **Play** (F10) to hear all tracks together. Use **Mute** to silence a track and **Clear** to erase it.
5. Press **Export WAV** to mix all unmuted tracks into a 16-bit stereo 44.1 kHz file named `zaroni_recording_YYYYMMDD_HHMMSS.wav` in the current folder.

Each track row shows its instruments, number of notes, length and a progress bar during playback. The drum machine pattern and the metronome are guides and are not recorded; drum pads you play yourself are.

## Digital sound synthesis

Rather than playing back recorded audio files, the application **calculates** each note as a waveform (44.1 kHz, 16-bit) the first time it is played and caches it for reuse.

### Musical frequency

All pitched instruments use the equal-tempered tuning formula, where *n* is the MIDI note number and A4 (*n* = 69) is 440 Hz:

$$
f(n) = 440 \times 2^{\frac{n-69}{12}}
$$

Each semitone multiplies the frequency by $2^{1/12} \approx 1.0595$, so twelve semitones (one octave) exactly double it. The current note name and frequency are shown at the top right of the window.

### Piano: additive synthesis with harmonics and decay

A piano note is built by summing its first eight harmonics (multiples of the fundamental frequency *f*). Higher harmonics are quieter and die away faster, which gives the bright attack and mellow tail of a struck string:

$$
y(t) = \sum_{k=1}^{8} \frac{1}{k^{1.4}} \sin(2\pi k f t)\, e^{-(1.5 + 0.65k)\,t}
$$

Harmonics above the Nyquist frequency (22,050 Hz) are skipped to avoid aliasing.

### Bass: Karplus-Strong algorithm

The bass uses a physical modeling technique that approximates the vibration of a plucked string through a feedback delay line and low-pass filtering:

$$
y[n] = \frac{\alpha}{2}\left(y[n-L] + y[n-L+1]\right)
$$

- The delay line starts filled with **random noise**: the "pluck" that excites the string.
- **L** is the delay length in samples, about $L \approx f_s / f$ (sample rate divided by frequency); it sets the pitch.
- **Averaging two neighboring samples** is a simple low-pass filter: high frequencies fade quickly, so the noise turns into a warm, pitched tone, just like a real string.
- **α = 0.996** (0.994 with slap) is the damping factor, slightly below 1, so the vibration loses energy and decays naturally.

Because each new sample only depends on samples at least *L − 1* positions back, the loop is computed in vectorized blocks of *L − 1* samples, which makes a note take a few milliseconds to generate. An extra gentle exponential decay shapes the sustain, and the effects chain is applied afterwards.

The instrument uses standard four-string bass tuning:

| String | Note | Frequency |
| ------ | ---- | --------- |
| 1st    | G2   | 98.00 Hz  |
| 2nd    | D2   | 73.42 Hz  |
| 3rd    | A1   | 55.00 Hz  |
| 4th    | E1   | 41.20 Hz  |

Each fret raises the pitch by one semitone, so the 12th fret plays one octave above the open string.

### Envelope

All notes receive a short fade-in (8 ms for piano and bass, 0.5 ms for percussion, to avoid clicks), a fade-out at the end of their length, and a 100 ms fade-out when the key or mouse button is released.

## Notes

- Bass fret spacing is drawn uniformly for usability, not to physical scale.
- No external samples or audio files are required.
- Timing of the metronome and drum machine is checked about 120 times per second, so jitter stays within a few milliseconds.
