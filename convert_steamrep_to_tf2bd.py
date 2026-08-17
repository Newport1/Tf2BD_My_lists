#!/usr/bin/env python3
"""Convert SteamRep's historical 2024 CSV export to a TF2 Bot Detector v3 player list.

Transformation policy:
- summary_rep == BANNED -> TF2BD attribute "suspicious"
- CAUTION and every other status -> omitted
- SteamID64 is preserved exactly as an integer
- full_rep is retained as provenance in proof
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import zipfile
from collections import Counter
from pathlib import Path

SCHEMA = "https://raw.githubusercontent.com/PazerOP/tf2_bot_detector/master/schemas/v3/playerlist.schema.json"


def open_csv(source: Path):
    if source.suffix.lower() == ".zip":
        zf = zipfile.ZipFile(source)
        members = [m for m in zf.infolist() if not m.is_dir() and m.filename.lower().endswith(".csv")]
        if len(members) != 1:
            zf.close()
            raise ValueError(f"expected exactly one CSV in ZIP, found {len(members)}")
        raw = zf.open(members[0], "r")
        text = io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")
        return zf, text
    return None, source.open("r", encoding="utf-8-sig", newline="")


def convert(source: Path, output: Path) -> dict:
    zf, fh = open_csv(source)
    status_counts: Counter[str] = Counter()
    seen: set[int] = set()
    duplicates = 0
    bad_numeric_ids = 0
    players: list[dict] = []

    try:
        reader = csv.DictReader(fh)
        expected = {"steamID64", "summary_rep", "full_rep"}
        if set(reader.fieldnames or []) != expected:
            raise ValueError(f"unexpected CSV columns: {reader.fieldnames!r}")

        for row in reader:
            status = (row.get("summary_rep") or "").strip().upper()
            status_counts[status] += 1
            if status != "BANNED":
                continue

            raw_id = (row.get("steamID64") or "").strip()
            try:
                steamid = int(raw_id, 10)
            except ValueError:
                bad_numeric_ids += 1
                continue

            if steamid in seen:
                duplicates += 1
                continue
            seen.add(steamid)

            entry = {
                "steamid": steamid,
                "attributes": ["suspicious"],
            }
            full_rep = (row.get("full_rep") or "").strip()
            if full_rep:
                entry["proof"] = [f"Historical SteamRep 2024 export: {full_rep}"]
            players.append(entry)
    finally:
        fh.close()
        if zf is not None:
            zf.close()

    doc = {
        "$schema": SCHEMA,
        "file_info": {
            "authors": ["SteamRep (historical source data)"],
            "title": "Historical SteamRep Banned Profiles — Suspicious",
            "description": (
                "SteamRep 2024 BANNED profiles converted for TF2 Bot Detector. "
                "Entries are intentionally marked suspicious rather than cheater: "
                "historical SteamRep reputation/trading bans are not by themselves "
                "proof of TF2 cheating."
            ),
        },
        "players": players,
    }

    output.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {
        "status_counts": dict(status_counts),
        "included_banned": len(players),
        "duplicate_banned_ids": duplicates,
        "non_numeric_banned_ids": bad_numeric_ids,
        "output_bytes": output.stat().st_size,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(convert(args.source, args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
