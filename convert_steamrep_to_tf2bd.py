#!/usr/bin/env python3
"""Convert SteamRep's historical 2024 CSV export to a TF2 Bot Detector v3 player list.

TF2BD's SteamID from_json only accepts:
  - unsigned JSON numbers (nlohmann stores typical SteamID64s as *signed* int64,
    so integer steamids always fail and the whole list is rejected), or
  - strings (SteamID3 like [U:1:123] or a decimal SteamID64)

Community lists and TF2BD's own serializer use SteamID3 strings. This converter
does the same.

Transformation policy:
- summary_rep == BANNED -> TF2BD attribute "suspicious"
- CAUTION and every other status -> omitted
- SteamID64 is converted to SteamID3 ([U:1:account] or [U:1:account:instance])
- Invalid IDs (not a public individual account) are skipped
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
UPDATE_URL = "https://raw.githubusercontent.com/Newport1/Tf2BD_My_lists/main/playerlist.steamrep.json"

# SteamID bit layout used by TF2BD / Steam
ACCOUNT_MASK = 0xFFFFFFFF
INSTANCE_MASK = 0xFFFFF
TYPE_INDIVIDUAL = 1
UNIVERSE_PUBLIC = 1
INSTANCE_DESKTOP = 1


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


def decode_steamid64(id64: int) -> tuple[int, int, int, int]:
    account_id = id64 & ACCOUNT_MASK
    instance = (id64 >> 32) & INSTANCE_MASK
    type_ = (id64 >> 52) & 0xF
    universe = (id64 >> 56) & 0xFF
    return account_id, instance, type_, universe


def to_steamid3(id64: int) -> str | None:
    """Return a TF2BD-parseable SteamID3, or None if the ID is not a public individual."""
    account_id, instance, type_, universe = decode_steamid64(id64)
    if type_ != TYPE_INDIVIDUAL or universe != UNIVERSE_PUBLIC or account_id == 0:
        return None
    if instance == INSTANCE_DESKTOP:
        return f"[U:1:{account_id}]"
    return f"[U:1:{account_id}:{instance}]"


def convert(source: Path, output: Path) -> dict:
    zf, fh = open_csv(source)
    status_counts: Counter[str] = Counter()
    seen: set[str] = set()
    duplicates = 0
    bad_numeric_ids = 0
    invalid_steamids = 0
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
                steamid64 = int(raw_id, 10)
            except ValueError:
                bad_numeric_ids += 1
                continue

            steamid3 = to_steamid3(steamid64)
            if steamid3 is None:
                invalid_steamids += 1
                continue

            if steamid3 in seen:
                duplicates += 1
                continue
            seen.add(steamid3)

            entry = {
                "steamid": steamid3,
                "attributes": ["suspicious"],
            }
            full_rep = (row.get("full_rep") or "").strip()
            if full_rep:
                entry["proof"] = [f"SteamRep 2024: {full_rep}"]
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
            "update_url": UPDATE_URL,
        },
        "players": players,
    }

    # Compact JSON: 50k+ entries; TF2BD re-saves with its own formatting on load.
    output.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    return {
        "status_counts": dict(status_counts),
        "included_banned": len(players),
        "duplicate_banned_ids": duplicates,
        "non_numeric_banned_ids": bad_numeric_ids,
        "invalid_steamids": invalid_steamids,
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
