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
from utils.formatting import format_coins

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
MAX_OPPORTUNITIES = 10
POLL_INTERVAL = 30  # seconds

ICON_RUNNING_WITH_OPPS = "● SB"
ICON_RUNNING_NO_OPPS   = "○ SB"
ICON_STOPPED           = "✕ SB"


def opportunity_title(opp: Opportunity) -> str:
    star = " ★" if opp.type == "MAYOR" else ""
    return f"[{opp.type}] {opp.item_name}{star}"


def opportunity_subtitle(opp: Opportunity) -> str:
    d = opp.details
    profit_str = format_coins(opp.profit)
    if opp.type == "BAZAAR":
        return f"Buy Order aufgeben → Sell Offer • {profit_str} Profit ({d.get('volume', '?')} Volumen)"
    if opp.type == "NPC":
        order = format_coins(d.get("bazaar_buy", 0))
        npc = format_coins(d.get("effective_npc_price", 0))
        return f"Buy Order {order} → NPC {npc}/Stk • {profit_str}/Tag (max. {d.get('daily_limit', '?')} Stück)"
    if opp.type == "AH":
        if d.get("arbitrage_type") == "stack":
            return f"Stack ({d.get('count', '?')}x) kaufen → einzeln verkaufen • {profit_str} Profit"
        return f"Aus AH kaufen → weiterverkaufen • {profit_str} Profit ({d.get('discount_pct', '?')}% unter Median)"
    if opp.type == "MAYOR":
        return f"Jetzt kaufen → nach {d.get('current_mayor', '?')} verkaufen • +{d.get('avg_increase_pct', '?')}% erwartet ({d.get('cycles_analyzed', '?')} Zyklen)"
    return profit_str


def needs_setup(cfg: Config) -> bool:
    return not cfg.api_key


class SkyblockApp(rumps.App):
    def __init__(self):
        super().__init__(ICON_STOPPED, quit_button=None)
        self._daemon_proc: Optional[subprocess.Popen] = None
        self._log_fh = None
        self._db = DB(os.path.join(PROJECT_DIR, "skyblock.db"))
        self._cfg = load_config(os.path.join(PROJECT_DIR, "config.yaml"))

        self._toggle_item = rumps.MenuItem("Daemon starten", callback=self._toggle_daemon)
        self._refresh_item = rumps.MenuItem("Jetzt aktualisieren", callback=self._tick)
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
        if self._log_fh:
            self._log_fh.close()
            self._log_fh = None
        self._log_fh = open(os.path.join(PROJECT_DIR, "daemon.log"), "a")
        self._daemon_proc = subprocess.Popen(
            [sys.executable, os.path.join(PROJECT_DIR, "daemon.py")],
            cwd=PROJECT_DIR,
            stdout=self._log_fh,
            stderr=subprocess.STDOUT,
        )
        self._toggle_item.title = "Daemon stoppen"

    def _stop_daemon(self):
        if self._daemon_proc and self._daemon_proc.poll() is None:
            self._daemon_proc.terminate()
            try:
                self._daemon_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._daemon_proc.kill()
                self._daemon_proc.wait()
        self._daemon_proc = None
        if self._log_fh:
            self._log_fh.close()
            self._log_fh = None
        self._toggle_item.title = "Daemon starten"

    def _daemon_alive(self) -> bool:
        return self._daemon_proc is not None and self._daemon_proc.poll() is None

    # ── Timer tick ─────────────────────────────────────────────────────────

    def _tick(self, _sender):
        alive = self._daemon_alive()
        if not alive:
            self._toggle_item.title = "Daemon starten"
        try:
            opps = self._db.get_opportunities(min_profit=self._cfg.min_profit_display)[:MAX_OPPORTUNITIES]
        except Exception:
            self.title = ICON_STOPPED if not alive else self.title
            return
        self.title = (ICON_RUNNING_WITH_OPPS if opps else ICON_RUNNING_NO_OPPS) if alive else ICON_STOPPED
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
            self._refresh_item,
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
        safe_dir = PROJECT_DIR.replace('"', '\\"')
        script = f'tell app "Terminal" to do script "cd \\"{safe_dir}\\" && python3 cli.py setup"'
        subprocess.run(["osascript", "-e", script], check=False)

    def _quit(self, _sender):
        self._stop_daemon()
        rumps.quit_application()


if __name__ == "__main__":
    SkyblockApp().run()
