# Skyblock Menu Bar App — Design Spec
**Date:** 2026-04-17

## Overview

A macOS Menu Bar app (`menubar.py`) built with `rumps` that replaces the CLI as the primary interface for the Skyblock Investment Tool. No commands to remember — start by double-clicking `start.command` or running `python3 menubar.py`. No Apple Developer account required.

---

## Architecture

One new file added to the existing project:

```
Skyblock/
├── menubar.py      # NEW: rumps Menu Bar App (primary entrypoint)
├── start.command   # NEW: double-clickable Finder launcher
├── daemon.py       # unchanged — started as subprocess by menubar.py
├── db.py           # unchanged — menubar.py reads from it
├── cli.py          # kept for debugging
└── ...
```

**Startup flow:**
1. User double-clicks `start.command` (or runs `python3 menubar.py`)
2. App appears in the menu bar, automatically starts daemon as a subprocess
3. Every 30 seconds, app reads from SQLite DB and rebuilds the menu
4. App quit (⌘Q or "Beenden") stops the daemon

**No direct API calls from the menu bar app** — it only reads from the SQLite DB that the daemon writes to.

---

## Icon States

| Icon | Meaning |
|---|---|
| `● SB` (green dot) | Daemon running + opportunities found |
| `○ SB` (empty dot) | Daemon running, no opportunities |
| `✕ SB` (red cross) | Daemon stopped or crashed |

---

## Menu Structure

```
● SB
──────────────────────────────
  Letzte Aktualisierung: 14:32
──────────────────────────────
  [BAZAAR] Enchanted Diamond
    ~2.3M • hoch
  [NPC] Sand
    ~540k • Limit 640/Tag
  [MAYOR] Griffin Feather ★
    +180% bei Diana • einlagern
──────────────────────────────
  (or: "Keine Opportunities")
──────────────────────────────
  Daemon stoppen
  Setup...
  Beenden
```

**Rules:**
- Max 10 opportunities shown, sorted by profit descending
- MAYOR items marked with `★` to stand out
- Clicking an opportunity copies the item name to clipboard (useful for searching in-game)
- "Daemon stoppen" toggles to "Daemon starten" when daemon is not running
- "Setup..." opens the interactive config setup in a new Terminal window
- "Beenden" quits the app and stops the daemon

---

## Polling & Update Logic

- `rumps.Timer` fires every 30 seconds
- Reads opportunities from SQLite DB (no API calls)
- Checks if daemon subprocess is still alive — if not, switches icon to `✕` and toggles menu item to "Daemon starten"
- Rebuilds menu items from DB results on each tick

---

## First-Run Handling

- If `config.yaml` is missing or `api_key` is empty: show "Setup erforderlich" as the only prominent menu item, do not start daemon
- "Setup..." opens: `osascript -e 'tell app "Terminal" to do script "cd /path && python3 cli.py setup"'`

---

## Startup Script (`start.command`)

Double-clickable from Finder — no Terminal knowledge required:

```bash
#!/bin/bash
cd "$(dirname "$0")"
python3 menubar.py
```

Mark executable: `chmod +x start.command`

---

## Dependencies

Add to `requirements.txt`:
```
rumps==0.4.0
```

No Xcode, no signing, no Apple Developer account needed. Works on macOS 10.14+.
