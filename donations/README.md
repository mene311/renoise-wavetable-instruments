# Donations

Drop a zip here and it gets checked, then filed if it is new.

## What to send

The builder at <https://mene311.github.io/renoise-wavetable-tools/> has a **Give it to the
library** panel. Build a table, and the panel tells you whether the library already has it, then
packs what is new into a zip with a `donation.json` describing it. Drop that zip on the upload
page and this folder is where it lands.

A zip with one or more `.xrni` files works on its own too. Without a `donation.json` the donor is
recorded as anonymous and the instrument goes to `unsorted/`.

## What happens next

`tools/ingest_donations.py` runs on anything pushed here, and every instrument is hashed against
`hashes/index.json` before it is filed:

- **identical** — the audio is already in the library, so it is rejected and the report says which
  instrument it duplicates. Re-encoding does not hide it: the hash is over the decoded frames, so a
  flac copy matches a wav one.
- **variant** — at least 80% of its frames match something published. Held in `review/` rather than
  filed, because a table rebuilt with other settings is not a new table.
- **new** — filed into `instruments/<category>/`, given a provenance row, and the index is rebuilt.

Processed zips are kept in `accepted/<date>/` or `rejected/<date>/`, and `REPORT.md` says what was
decided and why. Nothing is deleted.

## What can be donated

Things you made, or things you have the right to pass on. The library is mostly CC0 (WaveEdit
Online, Kimura Taro) with free-pack and third-party material credited in `provenance.tsv`, and
takedown requests are honoured — see the repository README. Say how you want to be credited in the
builder's credit field and it ends up in `provenance.tsv` with the date.

## Running it by hand

```sh
python3 tools/ingest_donations.py --dry-run   # say what would happen
python3 tools/ingest_donations.py             # file it
```
