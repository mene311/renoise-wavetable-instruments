#!/usr/bin/env python3
"""File what people donate, checking every instrument against the library first.

A donation arrives as a zip in donations/ holding one or more .xrni files and, usually, a
donation.json the browser builder wrote. Each instrument is hashed with tools/wt_hash.py and
compared against hashes/index.json:

  identical   the audio is already in the library -> rejected, and the report says as what
  variant     at least 80% of its frames match something published -> held in donations/review/
              for a human, because a rebuild with other settings is not a new table
  new         filed into instruments/<category>/, with a provenance row, and the index rebuilt

Nothing is deleted: processed zips move to donations/accepted/<date>/ or donations/rejected/<date>/
so there is a record of what arrived and what was decided.

    ./ingest_donations.py --dry-run     say what would happen, change nothing
    ./ingest_donations.py               do it
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wt_hash as H  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
DONATIONS = REPO / "donations"
INSTRUMENTS = REPO / "instruments"
PROVENANCE = REPO / "provenance.tsv"
REPORT = DONATIONS / "REPORT.md"
FALLBACK_CATEGORY = "unsorted"


def safe_name(name: str) -> str:
    """No directories out of a donated zip, and nothing that looks like a path."""
    base = Path(name.replace("\\", "/")).name
    base = re.sub(r"[\x00-\x1f]", "", base).strip()
    if not base.lower().endswith(".xrni"):
        base += ".xrni"
    return base or "donated.xrni"


def read_zip(path: Path) -> tuple[list[tuple[str, bytes]], dict]:
    """Instruments inside a donation, plus its manifest if it has one."""
    manifest: dict = {}
    instruments: list[tuple[str, bytes]] = []
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            if info.filename.lower().endswith("donation.json"):
                try:
                    manifest = json.loads(z.read(info).decode("utf-8", "replace"))
                except Exception:
                    manifest = {}
            elif info.filename.lower().endswith(".xrni"):
                instruments.append((safe_name(info.filename), z.read(info)))
    return instruments, manifest


def category_for(manifest: dict, fallback: str) -> str:
    wanted = (manifest.get("category") or "").strip()
    if not wanted or wanted.startswith("("):
        return fallback
    if (INSTRUMENTS / wanted).is_dir():
        return wanted
    # close enough to an existing folder, case aside
    for existing in INSTRUMENTS.iterdir():
        if existing.is_dir() and existing.name.lower() == wanted.lower():
            return existing.name
    return fallback


def decide(index: dict, frames) -> dict:
    return H.match(index, frames)


def write_provenance(rows: list[dict]) -> None:
    lines = PROVENANCE.read_text().splitlines()
    header = lines[0] if lines else "instrument\tcategory\tsource_table\tcollection"
    body = [l for l in lines[1:] if l.strip()]
    existing = {l.split("\t")[0] for l in body}
    for row in rows:
        if row["instrument"] in existing:
            continue
        body.append("\t".join([row["instrument"], row["category"], row["source_table"],
                               row["collection"]]))
    PROVENANCE.write_text(header + "\n" + "\n".join(sorted(body, key=str.lower)) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--root", default=str(REPO), help="repository to file into (for tests)")
    args = ap.parse_args()

    root = Path(args.root)
    donations = root / "donations"
    instruments_root = root / "instruments"
    index_path = root / "hashes" / "index.json"
    if not donations.is_dir():
        print("no donations/ folder, nothing to do")
        return 0
    index = H.load_index(index_path) if index_path.exists() else {"points": H.POINTS,
                                                                  "instruments": []}

    zips = sorted(p for p in donations.rglob("*.zip") if p.parent == donations)
    if not zips:
        print("no donations waiting")
        return 0

    today = dt.date.today().isoformat()
    accepted_rows: list[dict] = []
    report: list[str] = [f"# Donations received, processed {today}", ""]
    counts = {"accepted": 0, "identical": 0, "review": 0}

    for zip_path in zips:
        print(f"reading {zip_path.name}")
        try:
            donations_in_zip, manifest = read_zip(zip_path)
        except Exception as exc:
            report.append(f"- **{zip_path.name}**: could not be read ({exc})")
            continue
        donor = manifest.get("donor") or "(anonymous)"
        category = category_for(manifest, FALLBACK_CATEGORY)
        (instruments_root / category).mkdir(parents=True, exist_ok=True)
        report.append(f"### {zip_path.name}")
        report.append(f"from {donor}, filed to `{category}` when accepted")
        report.append("")

        for name, blob in donations_in_zip:
            temp = root / ".donation_tmp.xrni"
            temp.write_bytes(blob)
            try:
                frames, _info = H.read_frames(temp)
            except Exception as exc:
                report.append(f"- `{name}`: could not be decoded ({exc})")
                continue
            finally:
                temp.unlink(missing_ok=True)

            result = decide(index, frames)
            if result["verdict"] == "identical":
                counts["identical"] += 1
                report.append(f"- `{name}`: already in the library as `{result['of']}` — not added")
                continue
            if result["verdict"] == "variant":
                counts["review"] += 1
                report.append(f"- `{name}`: {result['matched']} of {result['mine']} frames match "
                              f"`{result['of']}` — held in `donations/review/` for a look")
                if not args.dry_run:
                    (donations / "review").mkdir(exist_ok=True)
                    (donations / "review" / name).write_bytes(blob)
                continue

            counts["accepted"] += 1
            target = instruments_root / category / name
            report.append(f"- `{name}`: new — filed as `instruments/{category}/{name}`")
            if not args.dry_run:
                target.write_bytes(blob)
            accepted_rows.append({
                "instrument": name, "category": category,
                "source_table": f"donated {today} by {donor}",
                "collection": "donations",
            })

        if not args.dry_run:
            bucket = donations / ("accepted" if counts["accepted"] else "rejected") / today
            bucket.mkdir(parents=True, exist_ok=True)
            shutil.move(str(zip_path), str(bucket / zip_path.name))
        report.append("")

    if accepted_rows and not args.dry_run:
        print(f"updating provenance for {len(accepted_rows)} instrument(s)")
        write_provenance(accepted_rows)
        print("rebuilding the index")
        H.build_index(root, root / "hashes" / "index.json")

    report.append("## Summary")
    report.append("")
    for key, value in counts.items():
        report.append(f"- {key}: {value}")
    report.append("")
    if not args.dry_run:
        REPORT.write_text("\n".join(report) + "\n")
    print("\n".join(report[-8:]))
    if args.dry_run:
        print("(dry run: nothing was written)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
