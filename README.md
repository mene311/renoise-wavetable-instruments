# renoise-wavetable-instruments

2,342 wavetable instruments for Renoise, sorted by timbre.

## What these are

Each instrument is a gate-scan wavetable. Every frame of the table sits in its own sample
slot behind its own gate, and one macro, **WT Position**, opens them one at a time so the
sound morphs through the table instead of crossfading between two waves.

Load one on a track, hold a note, turn the macro. The frames were cut to sound right
around C-4, so that's the comfortable register to play in.

They were built with [renoise-wavetable-tools](https://github.com/mene311/renoise-wavetable-tools)
out of the wavetable collections listed at the bottom.

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

| source | instruments | terms |
|---|---|---|
| WAVEEDIT ONLINE (waveeditonline.com) | 660 | CC0 |
| Kimura Taro free wavetables (kimurataro.com) | 565 | CC0 |
| Echo Sound Works "Core" (free pack) | 377 | free download, no stated redistribution terms |
| Vital Harvest, VitalBank, Factory presets | 373 | third-party preset collections |
| Growl packs, Discord wavetables, other user presets | 314 | third-party preset content |
| BassTables (AJYoung) | 30 | released free for use in productions |
| survey sample and Kaidiak's instruments | 23 | mixed sources, see provenance.tsv |

`provenance.tsv` records the source table for every instrument, and `catalogue.tsv` has the
measured features for each one.

## Licence

The build tools are MIT. The waveforms inside these instruments come from the collections
above: the CC0 ones carry no restrictions, the rest are reproduced here from freely
available packs and presets with their sources listed in `provenance.tsv`.

No authorship is claimed over any of the source material. If you hold rights to a wavetable
in here and want it gone, open an issue on this repository and that collection will be
removed. No discussion needed.
