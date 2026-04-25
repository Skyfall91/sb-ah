# Menu Bar App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the CLI with a macOS Menu Bar app (`menubar.py`) that starts the daemon automatically, shows live opportunities in a dropdown, and requires zero commands to operate.

**Architecture:** A `rumps`-based app reads from the existing SQLite DB every 30s and rebuilds the menu. Daemon is started as a subprocess on app launch and stopped on quit. Helper formatting functions are extracted and unit-tested separately from the GUI.

**Tech Stack:** Python 3.9, rumps==0.4.0, subprocess, pyperclip (clipboard), existing db.py + config.py

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `requirements.txt` | Modify | Add rumps, pyperclip |
| `menubar.py` | Create | Full menu bar app + helper functions |
| `tests/test_menubar_helpers.py` | Create | Unit tests for pure formatting helpers |
| `start.command` | Create | Double-clickable Finder launcher |

---

### Task 1: Add Dependencies

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add rumps and pyperclip to requirements.txt**

Replace the full content of `requirements.txt` with:

```
aiohttp==3.9.5
pyyaml==6.0.1
rich==13.7.1
pytest==8.2.0
pytest-asyncio==0.23.6
rumps==0.4.0
pyperclip==1.8.2
```

- [ ] **Step 2: Install new dependencies**

```bash
pip3 install rumps==0.4.0 pyperclip==1.8.2
```

Expected: both packages install without error.

- [ ] **Step 3: Verify rumps import works**

```bash
python3 -c "import rumps; print(rumps.__version__)"
```

Expected: `0.4.0`

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "feat: add rumps and pyperclip dependencies for menu bar app"
```

---

### Task 2: Helper Functions (TDD)

**Files:**
- Create: `menubar.py` (helpers only, no App class yet)
- Create: `tests/test_menubar_helpers.py`

These pure functions have no rumps dependency and are fully unit-testable.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_menubar_helpers.py
import pytest
from models import Opportunity


def test_format_coins_millions():
    from menubar import format_coins
    assert format_coins(2_300_000) == "~2.3M"


def test_format_coins_thousands():
    from menubar import format_coins
    assert format_coins(540_000) == "~540k"


def test_format_coins_small():
    from menubar import format_coins
    assert format_coins(999) == "999"


def test_opportunity_title_bazaar():
    from menubar import opportunity_title
    opp = Opportunity("BAZAAR", "ENCHANTED_DIAMOND", "Enchanted Diamond",
                      2_300_000, "JETZT KAUFEN", {"volume": "hoch"}, "high")
    assert opportunity_title(opp) == "[BAZAAR] Enchanted Diamond"


def test_opportunity_title_mayor_has_star():
    from menubar import opportunity_title
    opp = Opportunity("MAYOR", "GRIFFIN_FEATHER", "Griffin Feather",
                      900_000, "JETZT INVESTIEREN", {}, "high")
    assert "★" in opportunity_title(opp)


def test_opportunity_subtitle_bazaar():
    from menubar import opportunity_subtitle
    opp = Opportunity("BAZAAR", "ENCHANTED_DIAMOND", "Enchanted Diamond",
                      2_300_000, "JETZT KAUFEN",
                      {"buy_order": 18_200_000, "sell_offer": 20_500_000, "volume": "hoch"},
                      "high")
    subtitle = opportunity_subtitle(opp)
    assert "2.3M" in subtitle
    assert "hoch" in subtitle


def test_opportunity_subtitle_npc():
    from menubar import opportunity_subtitle
    opp = Opportunity("NPC", "SAND", "Sand", 540_000, "JETZT KAUFEN",
                      {"daily_limit": 640}, "high")
    subtitle = opportunity_subtitle(opp)
    assert "540k" in subtitle
    assert "640" in subtitle


def test_opportunity_subtitle_ah_underpriced():
    from menubar import opportunity_subtitle
    opp = Opportunity("AH", "ASPECT_OF_THE_END", "Aspect of the End",
                      7_000_000, "JETZT KAUFEN",
                      {"discount_pct": 28.0, "arbitrage_type": "underpriced"},
                      "high")
    subtitle = opportunity_subtitle(opp)
    assert "28" in subtitle


def test_opportunity_subtitle_mayor():
    from menubar import opportunity_subtitle
    opp = Opportunity("MAYOR", "GRIFFIN_FEATHER", "Griffin Feather",
                      900_000, "JETZT INVESTIEREN",
                      {"current_mayor": "Diana", "avg_increase_pct": 180.0, "cycles_analyzed": 5},
                      "high")
    subtitle = opportunity_subtitle(opp)
    assert "Diana" in subtitle
    assert "180" in subtitle


def test_needs_setup_true_when_no_api_key():
    from menubar import needs_setup
    from config import Config
    assert needs_setup(Config(api_key="")) is True


def test_needs_setup_false_when_api_key_present():
    from menubar import needs_setup
    from config import Config
    assert needs_setup(Config(api_key="abc-123")) is False
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 -m pytest tests/test_menubar_helpers.py -v
```

Expected: `ModuleNotFoundError: No module named 'menubar'`

- [ ] **Step 3: Create `menubar.py` with helpers only**

```python
import os
import subprocess
import sys
from datetime import datetime
from typing import Optional

import rumps
import pyperclip

from config import Config, load_config
from db import DB
from models import Opportunity

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
MAX_OPPORTUNITIES = 10
POLL_INTERVAL = 30  # seconds

ICON_RUNNING_WITH_OPPS = "● SB"
ICON_RUNNING_NO_OPPS   = "○ SB"
ICON_STOPPED           = "✕ SB"


def format_coins(amount: float) -> str:
    if amount >= 1_000_000:
        return f"~{amount / 1_000_000:.1f}M"
    if amount >= 1_000:
        return f"~{amount / 1_000:.0f}k"
    return str(int(amount))


def opportunity_title(opp: Opportunity) -> str:
    star = " ★" if opp.type == "MAYOR" else ""
    return f"[{opp.type}] {opp.item_name}{star}"


def opportunity_subtitle(opp: Opportunity) -> str:
    d = opp.details
    profit_str = format_coins(opp.profit)
    if opp.type == "BAZAAR":
        return f"{profit_str} • {d.get('volume', '?')}"
    if opp.type == "NPC":
        return f"{profit_str} • Limit {d.get('daily_limit', '?')}/Tag"
    if opp.type == "AH":
        if d.get("arbitrage_type") == "stack":
            return f"{profit_str} • Stack ({d.get('count', '?')}x)"
        return f"{profit_str} • {d.get('discount_pct', '?')}% unter Median"
    if opp.type == "MAYOR":
        return f"+{d.get('avg_increase_pct', '?')}% bei {d.get('current_mayor', '?')} • {d.get('cycles_analyzed', '?')} Zyklen"
    return profit_str


def needs_setup(cfg: Config) -> bool:
    return not cfg.api_key
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_menubar_helpers.py -v
```

Expected: all 10 tests PASS

- [ ] **Step 5: Commit**

```bash
git add menubar.py tests/test_menubar_helpers.py
git commit -m "feat: menubar helper functions with tests"
```

---

### Task 3: Full Menu Bar App

**Files:**
- Modify: `menubar.py` (append SkyblockApp class)

No unit tests for the GUI class — it requires a running macOS display server. Verified by running the app manually.

- [ ] **Step 1: Append `SkyblockApp` class to `menubar.py`**

Add the following after the existing helper functions in `menubar.py`:

```python
class SkyblockApp(rumps.App):
    def __init__(self):
        super().__init__(ICON_STOPPED, quit_button=None)
        self._daemon_proc: Optional[subprocess.Popen] = None
        self._db = DB(os.path.join(PROJECT_DIR, "skyblock.db"))
        self._cfg = load_config(os.path.join(PROJECT_DIR, "config.yaml"))

        self._toggle_item = rumps.MenuItem("Daemon starten", callback=self._toggle_daemon)
        self._setup_item = rumps.MenuItem("Setup...", callback=self._open_setup)
        self._quit_item = rumps.MenuItem("Beenden", callback=self._quit)

        if needs_setup(self._cfg):
            self.menu = [
                rumps.MenuItem("⚠ Setup erforderlich", callback=self._open_setup),
                None,
                self._setup_item,
                self._quit_item,
            ]
        else:
            self._start_daemon()
            self.menu = self._build_menu([])

        rumps.Timer(self._tick, POLL_INTERVAL).start()

    # ── Daemon management ──────────────────────────────────────────────────

    def _start_daemon(self):
        if self._daemon_proc and self._daemon_proc.poll() is None:
            return
        self._daemon_proc = subprocess.Popen(
            [sys.executable, os.path.join(PROJECT_DIR, "daemon.py")],
            cwd=PROJECT_DIR,
            stdout=open(os.path.join(PROJECT_DIR, "daemon.log"), "a"),
            stderr=subprocess.STDOUT,
        )
        self._toggle_item.title = "Daemon stoppen"

    def _stop_daemon(self):
        if self._daemon_proc and self._daemon_proc.poll() is None:
            self._daemon_proc.terminate()
            self._daemon_proc.wait(timeout=5)
        self._daemon_proc = None
        self._toggle_item.title = "Daemon starten"

    def _daemon_alive(self) -> bool:
        return self._daemon_proc is not None and self._daemon_proc.poll() is None

    # ── Timer tick ─────────────────────────────────────────────────────────

    @rumps.timer(POLL_INTERVAL)
    def _tick(self, _sender):
        if not self._daemon_alive():
            self._toggle_item.title = "Daemon starten"
            self.title = ICON_STOPPED
        opps = self._db.get_opportunities(min_profit=self._cfg.min_profit_display)[:MAX_OPPORTUNITIES]
        if self._daemon_alive():
            self.title = ICON_RUNNING_WITH_OPPS if opps else ICON_RUNNING_NO_OPPS
        self.menu.clear()
        for item in self._build_menu(opps):
            self.menu.add(item)

    # ── Menu building ──────────────────────────────────────────────────────

    def _build_menu(self, opps: list) -> list:
        now = datetime.now().strftime("%H:%M")
        items = [
            rumps.MenuItem(f"Letzte Aktualisierung: {now}"),
            None,
        ]
        if opps:
            for opp in opps:
                title = opportunity_title(opp)
                subtitle = opportunity_subtitle(opp)
                item = rumps.MenuItem(title, callback=self._copy_item_name)
                item._opp_name = opp.item_name
                items.append(item)
                items.append(rumps.MenuItem(f"  {subtitle}"))
        else:
            items.append(rumps.MenuItem("Keine Opportunities"))
        items += [
            None,
            self._toggle_item,
            self._setup_item,
            None,
            self._quit_item,
        ]
        return items

    # ── Callbacks ──────────────────────────────────────────────────────────

    def _copy_item_name(self, sender):
        name = getattr(sender, "_opp_name", sender.title)
        pyperclip.copy(name)

    def _toggle_daemon(self, _sender):
        if self._daemon_alive():
            self._stop_daemon()
            self.title = ICON_STOPPED
        else:
            self._start_daemon()

    def _open_setup(self, _sender):
        script = f'tell app "Terminal" to do script "cd {PROJECT_DIR} && python3 cli.py setup"'
        subprocess.run(["osascript", "-e", script], check=False)

    def _quit(self, _sender):
        self._stop_daemon()
        rumps.quit_application()


if __name__ == "__main__":
    SkyblockApp().run()
```

- [ ] **Step 2: Verify imports are clean**

```bash
python3 -c "
import ast, sys
with open('menubar.py') as f:
    ast.parse(f.read())
print('Syntax OK')
"
```

Expected: `Syntax OK`

- [ ] **Step 3: Verify existing tests still pass**

```bash
python3 -m pytest tests/ -q
```

Expected: all 39 tests (+ 10 new helper tests) pass — `49 passed`

- [ ] **Step 4: Commit**

```bash
git add menubar.py
git commit -m "feat: SkyblockApp rumps menu bar app with daemon control"
```

---

### Task 4: Finder Launcher (`start.command`)

**Files:**
- Create: `start.command`

- [ ] **Step 1: Create `start.command`**

```bash
#!/bin/bash
cd "$(dirname "$0")"
python3 menubar.py
```

- [ ] **Step 2: Make it executable**

```bash
chmod +x /Users/robin/Documents/Apps/Skyblock/start.command
```

- [ ] **Step 3: Verify the file is executable**

```bash
ls -la /Users/robin/Documents/Apps/Skyblock/start.command
```

Expected: permissions include `-rwxr-xr-x`

- [ ] **Step 4: Commit**

```bash
git add start.command
git commit -m "feat: add double-clickable start.command Finder launcher"
```

---

### Task 5: First-Run Docs in README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create `README.md`**

```markdown
# Skyblock Investment Tool

Findet automatisch profitable Investitionsmöglichkeiten in Hypixel Skyblock.

## Einrichtung (einmalig)

```bash
pip3 install -r requirements.txt
python3 cli.py setup
```

## Starten

Doppelklick auf **`start.command`** im Finder.

Oder im Terminal:
```bash
python3 menubar.py
```

Das Tool erscheint in der macOS Menüleiste:
- `● SB` — läuft, Opportunities vorhanden
- `○ SB` — läuft, keine Opportunities gerade
- `✕ SB` — Daemon gestoppt

## Menü

Klick auf ein Item kopiert den Namen in die Zwischenablage (direkt im Spiel einfügbar).

## Daemon-Log

```bash
tail -f daemon.log
```
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with quickstart instructions"
```

---

## Final Verification

- [ ] Run full test suite: `python3 -m pytest tests/ -v` — 49 tests pass
- [ ] Syntax check: `python3 -c "import menubar; print('OK')"`
- [ ] Manual smoke test: `python3 menubar.py` — icon appears in menu bar, menu opens correctly
