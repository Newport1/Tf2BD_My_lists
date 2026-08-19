# TF2BD SteamRep list (unofficial)

Custom TF2 Bot Detector player list derived from the [SteamRep](https://steamrep.com) 2024 archive. **Not official, not verified, and not recommended as a cheater list.** Someone being on this list only means they were flagged on SteamRep before 2024 — it does **not** mean they cheat in TF2.

Every entry is marked **suspicious** so you can decide when you actually meet them.

## Why the old file would not load

TF2 Bot Detector rejected `steamrep-banned-suspicious.tf2bd.json` for two reasons:

1. **SteamIDs were JSON numbers.** TF2BD only accepts SteamID3 strings such as `[U:1:123456]`. Typical SteamID64 values are stored as signed integers by the JSON parser, so the first entry threw and the whole list was discarded.
2. **Wrong filename.** TF2BD only auto-loads `cfg/playerlist.*.json`. A `*.tf2bd.json` name is ignored.

## Install

1. Download [`playerlist.steamrep.json`](https://raw.githubusercontent.com/Newport1/Tf2BD_My_lists/main/playerlist.steamrep.json)
2. Drop it into your TF2BD `cfg` folder (`File → Open Config Folder`)
3. Restart TF2BD

If internet connectivity is allowed, TF2BD will refresh the list from this repo on launch via `file_info.update_url`.

Raw URL:

```
https://raw.githubusercontent.com/Newport1/Tf2BD_My_lists/main/playerlist.steamrep.json
```

## Rebuild from the SteamRep CSV

```
python3 convert_steamrep_to_tf2bd.py SteamRep_Profiles_BannedCaution_2024_csv.zip playerlist.steamrep.json
```
