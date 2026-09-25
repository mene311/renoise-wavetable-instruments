#!/usr/bin/env python3
"""Content hashes for wavetable instruments, so a donated table can be checked against the
library before it is sent.

File bytes are useless for this. Renoise stores the sample data inside an .xrni as flac when it
saves and the builder writes plain wav, so two files holding the same table differ byte for byte.
What gets hashed instead is the frames themselves, after decoding:

  exact key   FNV-1a over the 16 bit quantisation of every frame, with its length. Identical
              audio matches; a re-encoded copy does not.
  shape key   the cycle resampled to POINTS evenly spaced points and quantised to 8 bit. This
              survives a different cycle length, a different sample rate, and a different
              rendering of the same shape, which is what catches near duplicates.

docs/wt-hash.js in the tools repository mirrors this file. tests/browser_check.py checks that the
two agree on a real instrument, because a drift between them would silently stop catching
duplicates.

    ./wt_hash.py --build-index                 write hashes/index.json for the whole library
    ./wt_hash.py --check path/to/thing.xrni    report what it matches
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import math
import sys
import zipfile
from pathlib import Path

import subprocess

import numpy as np
import soundfile as sf

POINTS = 24
INDEX_VERSION = 1
FNV_OFFSET = 0x811C9DC5
FNV_PRIME = 0x01000193
MASK32 = 0xFFFFFFFF

REPO = Path(__file__).resolve().parent.parent
INDEX_PATH = REPO / "hashes" / "index.json"


# ── reading instruments ──────────────────────────────────────────────────────


def read_frames(path: Path) -> tuple[list[np.ndarray], dict]:
    """Decode every sample inside an .xrni, in slot order, plus what the XML says."""
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist() if n.startswith("SampleData/")]
        names.sort()
        frames = []
        for name in names:
            frames.append(decode_sample(z.read(name)))
        info = {"frames": len(frames)}
        if "Instrument.xml" in z.namelist():
            xml = z.read("Instrument.xml").decode("utf-8", "replace")
            for tag, key in (("BaseNote", "base_note"), ("Finetune", "finetune"),
                             ("LoopMode", "loop")):
                got = re_first(xml, tag)
                if got is not None:
                    info[key] = got
    return frames, info


def decode_sample(data: bytes) -> np.ndarray:
    """Renoise writes the samples as flac. libsndfile reads most of them; some it calls an
    unimplemented format, and ffmpeg reads those, so it is the fallback."""
    try:
        samples, _rate = sf.read(io.BytesIO(data), dtype="float32", always_2d=True)
        return samples[:, 0].copy()
    except Exception:
        out = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", "pipe:0", "-f", "f32le", "-ac", "1", "-"],
            input=data, capture_output=True,
        )
        if out.returncode != 0 or not out.stdout:
            raise RuntimeError(f"could not decode a sample: {out.stderr.decode()[:80]}")
        return np.frombuffer(out.stdout, dtype="<f4").astype(np.float32).copy()


def re_first(text: str, tag: str):
    import re

    m = re.search(rf"<{tag}>([^<]*)<", text)
    return m.group(1) if m else None


# ── the canonical form, mirrored in javascript ───────────────────────────────


def shape_key(samples: np.ndarray) -> bytes:
    """POINTS evenly spaced points of the cycle, peak normalised, quantised to int8."""
    n = len(samples)
    peak = float(np.max(np.abs(samples))) if n else 0.0
    if peak == 0.0:
        peak = 1.0
    out = bytearray(POINTS)
    if n == 0:
        return bytes(out)
    for k in range(POINTS):
        pos = k * (n - 1) / (POINTS - 1)
        i0 = int(math.floor(pos))
        frac = pos - i0
        i1 = i0 + 1 if i0 + 1 < n else n - 1
        v = (float(samples[i0]) + (float(samples[i1]) - float(samples[i0])) * frac) / peak
        q = int(math.floor(v * 127 + 0.5))       # javascript Math.round is half up
        out[k] = max(-127, min(127, q)) & 0xFF
    return bytes(out)


def fnv_bytes(chunks) -> str:
    h = FNV_OFFSET
    for chunk in chunks:
        for byte in chunk:
            h = ((h ^ byte) * FNV_PRIME) & MASK32
    return f"{h:08x}"


def exact_key(frames: list[np.ndarray]) -> str:
    """FNV-1a over the frames quantised to 16 bit, each frame length included."""
    chunks = []
    for frame in frames:
        length = len(frame)
        chunks.append(bytes([length & 0xFF, (length >> 8) & 0xFF,
                             (length >> 16) & 0xFF, (length >> 24) & 0xFF]))
        q = np.clip(np.floor(np.asarray(frame, dtype=np.float64) * 32767.0 + 0.5), -32768, 32767)
        ints = q.astype("<i2")
        chunks.append(ints.tobytes())
    return fnv_bytes(chunks)


def encode_shapes(frames: list[np.ndarray]) -> str:
    """Every frame's shape key in one blob: shorter in json, one decode per instrument."""
    return base64.b64encode(b"".join(shape_key(f) for f in frames)).decode("ascii")


def decode_shapes(b64: str, points: int = POINTS) -> list[bytes]:
    raw = base64.b64decode(b64)
    return [raw[i:i + points] for i in range(0, len(raw), points)]


def shape_distance(a: bytes, b: bytes) -> float:
    """Mean absolute difference in quantisation steps between two shape keys."""
    if len(a) != len(b):
        return 999.0
    return float(np.mean(np.abs(np.frombuffer(a, dtype=np.int8).astype(np.int16) -
                               np.frombuffer(b, dtype=np.int8).astype(np.int16))))


def instrument_record(path: Path, name: str, category: str) -> dict:
    frames, info = read_frames(path)
    return {
        "name": name,
        "category": category,
        "frames": info["frames"],
        "cycle": int(len(frames[0])) if frames else 0,
        "key": exact_key(frames),
        "shapes": encode_shapes(frames),
    }


# ── index ────────────────────────────────────────────────────────────────────


def build_index(root: Path, out: Path, limit: int | None = None) -> dict:
    instruments = []
    paths = sorted(root.rglob("*.xrni"))
    if limit:
        paths = paths[:limit]
    for i, path in enumerate(paths, 1):
        rel = path.relative_to(root / "instruments")
        category = rel.parts[0] if len(rel.parts) > 1 else "(flat)"
        try:
            instruments.append(instrument_record(path, path.name, category))
        except Exception as exc:                      # a broken file must not stop the index
            print(f"  skipped {path.name}: {exc}", file=sys.stderr)
        if i % 250 == 0:
            print(f"  {i}/{len(paths)} hashed")
    doc = {
        "version": INDEX_VERSION,
        "points": POINTS,
        "count": len(instruments),
        "instruments": instruments,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, separators=(",", ":")) + "\n")
    return doc


def load_index(path: Path = INDEX_PATH) -> dict:
    return json.loads(path.read_text())


# ── matching ─────────────────────────────────────────────────────────────────


def match(index: dict, frames: list[np.ndarray], tolerance: float = 3.0) -> dict:
    """Compare one instrument's frames against the index.

    overlap is the share of the new frames that have a close counterpart in a library
    instrument, so a subset pick of an existing table still reads as a duplicate.
    """
    mine = [shape_key(f) for f in frames]
    key = exact_key(frames)
    best = None
    for entry in index["instruments"]:
        if entry["key"] == key:
            return {"verdict": "identical", "overlap": 1.0, "of": entry["name"],
                    "category": entry["category"], "entries": entry["frames"]}
        theirs = decode_shapes(entry["shapes"], index.get("points", POINTS))
        if not theirs or not mine:
            continue
        close = 0
        for a in mine:
            if any(shape_distance(a, b) <= tolerance for b in theirs):
                close += 1
        overlap = close / len(mine)
        if best is None or overlap > best["overlap"]:
            best = {"overlap": overlap, "of": entry["name"], "category": entry["category"],
                    "entries": len(theirs), "matched": close}
    if best and best["overlap"] >= 0.8:
        best["verdict"] = "variant"
        best["mine"] = len(mine)
        return best
    if best:
        best["verdict"] = "new"
        best["mine"] = len(mine)
    return best or {"verdict": "new", "overlap": 0.0, "mine": len(mine)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build-index", action="store_true")
    ap.add_argument("--root", default=str(REPO), help="instrument repository to index")
    ap.add_argument("--out", default=str(INDEX_PATH))
    ap.add_argument("--limit", type=int)
    ap.add_argument("--check", metavar="XRNI")
    args = ap.parse_args()

    if args.build_index:
        print(f"indexing {args.root}")
        doc = build_index(Path(args.root), Path(args.out), args.limit)
        size = Path(args.out).stat().st_size
        print(f"  {doc['count']} instruments, {size/1024:.0f} KB at {args.out}")
        return 0

    if args.check:
        frames, _info = read_frames(Path(args.check))
        result = match(load_index(), frames)
        print(json.dumps(result, indent=2))
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
