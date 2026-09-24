# renoise-wavetable-instruments

1,225 wavetable instruments for Renoise, sorted by timbre, built from CC0 wavetables.

## What these are

Each instrument is a gate-scan wavetable. Every frame of the table sits in its own sample
slot behind its own gate, and one macro, **WT Position**, opens them one at a time so the
sound morphs through the table instead of crossfading between two waves.

Load one on a track, hold a note, turn the macro. The frames were cut to sound right
around C-4, so that's the comfortable register to play in.

They were built with [renoise-wavetable-tools](https://github.com/mene311/renoise-wavetable-tools)
out of the CC0 wavetable collections listed below.

## How they are sorted

Timbre clusters, measured from the single-cycle content of each table (spectral centroid
against its own fundamental, odd-harmonic share, harmonic slope, spectral flatness,
fundamental share, crest factor):

| folder | n | rough character |
|---|---|---|
| bright and gritty | 285 | centroid around the 22nd harmonic, saw and FM territory |
| additive and organ | 252 | rich in odd and even harmonics, mellow |
| sine and soft triangle | 197 | near-sine, odd harmonics, steep rolloff |
| texture and noise | 150 | mostly inharmonic motion |
| metallic and FM | 109 | strong harmonic peaks, bell and vowel shapes |
| octave and folded | 106 | even harmonics, little or no fundamental |
| pulse and round | 92 | odd harmonics with a hollow, square-ish middle |
| white noise | 25 | flat spectrum |
| near sine | 8 | almost a single harmonic |
| impulses and clicks | 1 | huge crest factor |

## Install

Copy the folders into the Renoise user library:

```
~/.local/share/Renoise/User Library/Instruments/Wavetables/
```

Renoise reads subfolders, so its instrument browser shows these categories as they are here.

## Where the waves came from

Both source collections are CC0:

- WAVEEDIT ONLINE (waveeditonline.com), 660 instruments
- Kimura Taro free wavetables (kimurataro.com), 565 instruments

`provenance.tsv` records the source table for every instrument, and `catalogue.tsv` has the
measured features for each one.

Another ~1,100 instruments were built in the same run from packs and presets whose terms
only cover use in your own productions, or are commercial, so they are not redistributed
here.

## Licence

The source wavetables are CC0, so the instruments derived from them carry no added claim:
treat them as public domain. The build tools are MIT.
