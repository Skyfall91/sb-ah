import argparse
import os
import sys
from datetime import datetime

from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from rich import box

from config import load_config, setup_first_run
from db import DB
from utils.formatting import format_coins

console = Console()

RARITY_COLORS = {
    "COMMON":       "white",
    "UNCOMMON":     "bright_green",
    "RARE":         "bright_blue",
    "EPIC":         "medium_purple1",
    "LEGENDARY":    "gold1",
    "MYTHIC":       "hot_pink",
    "DIVINE":       "bright_cyan",
    "ULTIMATE":     "red1",
    "SPECIAL":      "red1",
    "VERY_SPECIAL": "red1",
}


def _wiki_url(item_name: str) -> str:
    return f"https://hypixelskyblock.minecraft.wiki/w/{item_name.replace(' ', '_')}"


def _colored_name_text(item_name: str, tier: str) -> Text:
    color = RARITY_COLORS.get(tier, "white")
    return Text(item_name, style=f"bold {color} link {_wiki_url(item_name)}")


def _item_name_text(opp) -> Text:
    return _colored_name_text(opp.item_name, opp.details.get("tier", ""))


def _base_table() -> Table:
    return Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold dim", padding=(0, 1), expand=True)


def build_table(opps) -> Table:
    table = _base_table()
    table.add_column("Item", min_width=20, ratio=3)
    table.add_column("Buy", no_wrap=True, ratio=2)
    table.add_column("Sell", no_wrap=True, ratio=2)
    table.add_column("Bundles", justify="right", no_wrap=True, width=8)
    table.add_column("Profit/14", justify="right", style="bold green", no_wrap=True, width=12)

    for i, opp in enumerate(opps):
        d = opp.details
        kaufen = f"{d.get('count','?')}× {format_coins(d.get('bundle_per_unit', 0))}/stk"
        einzeln_price = format_coins(d.get('single_price', 0))
        if d.get("suspicious"):
            einzeln = f"{einzeln_price}/stk [red]⚠[/red]"
        elif d.get("manipulated"):
            einzeln = f"{einzeln_price}/stk [yellow]~[/yellow]"
        elif d.get("on_bazaar"):
            einzeln = f"{einzeln_price}/stk [cyan]BZ[/cyan]"
        elif d.get("npc_price"):
            einzeln = f"{einzeln_price}/stk [blue]NPC[/blue]"
        else:
            einzeln = f"{einzeln_price}/stk"
        bundles = str(d.get("listings", 1))
        row_style = "on grey7" if i % 2 == 0 else ""
        table.add_row(
            _item_name_text(opp),
            kaufen,
            einzeln,
            bundles,
            format_coins(opp.profit) + "/14",
            style=row_style,
        )

    return table



def render(db, cfg, args) -> Panel:
    opps = db.get_opportunities(type_filter="AH", min_profit=cfg.min_profit_display)
    now = datetime.now().strftime("%H:%M:%S")

    if opps:
        content = build_table(opps)
    else:
        content = Text("No AH opportunities — is the daemon running?  python3 daemon.py", style="dim")

    return Panel(
        content,
        title="[bold]AH Flips[/bold]",
        subtitle=f"[dim]Updated {now} · Ctrl+C to quit[/dim]",
        border_style="bright_black",
    )


def cmd_show(args):
    cfg = load_config()
    db = DB()
    console.print(render(db, cfg, args))


def cmd_top(args):
    db = DB()
    hours = args.hours
    rows = db.get_top_sightings(hours=hours)
    if not rows:
        console.print(f"[dim]No data for the last {hours}h — is the daemon running?[/dim]")
        return

    table = _base_table()
    table.add_column("Item", min_width=20, ratio=3)
    table.add_column("Seen", justify="right", no_wrap=True, width=10)
    table.add_column("Reliability", no_wrap=True, ratio=2)
    table.add_column("Avg Buy", justify="right", no_wrap=True, width=11)
    table.add_column("Avg Sell", justify="right", no_wrap=True, width=13)
    table.add_column("Avg Profit/14", justify="right", style="bold green", no_wrap=True, width=13)

    for i, r in enumerate(rows):
        name = _colored_name_text(r["item_name"], r["tier"])

        pct = r["seen"] / r["rounds"]
        filled = int(pct * 12)
        bar = "█" * filled + "░" * (12 - filled)
        bar_color = "green" if pct >= 0.75 else "yellow" if pct >= 0.4 else "red"
        reliability = Text(f"{bar}  {pct*100:.0f}%", style=bar_color)

        buy = format_coins(r["avg_buy_price"]) + "/stk" if r.get("avg_buy_price") else "—"
        sell = format_coins(r["avg_sell_price"]) + "/stk" if r.get("avg_sell_price") else "—"

        row_style = "on grey7" if i % 2 == 0 else ""
        table.add_row(
            name,
            f"{r['seen']}/{r['rounds']}",
            reliability,
            buy,
            sell,
            format_coins(r["avg_profit"]) + "/14",
            style=row_style,
        )

    panel = Panel(
        table,
        title=f"[bold]Top AH Flips — last {hours}h[/bold]",
        subtitle=f"[dim]{rows[0]['rounds']} checks · {len(rows)} items[/dim]",
        border_style="bright_black",
    )
    console.print(panel)


def cmd_daemon(args):
    import subprocess
    here = os.path.dirname(__file__)
    pid_path = os.path.join(here, "daemon.pid")
    if args.action == "start":
        proc = subprocess.Popen(
            [sys.executable, os.path.join(here, "daemon.py")],
            cwd=here,
            stdout=open(os.path.join(here, "daemon.log"), "a"),
            stderr=subprocess.STDOUT,
        )
        with open(pid_path, "w") as f:
            f.write(str(proc.pid))
        console.print(f"[green]Daemon started (PID {proc.pid})[/green]")
    elif args.action == "stop":
        try:
            with open(pid_path) as f:
                pid = int(f.read().strip())
            os.kill(pid, 15)
            os.unlink(pid_path)
            console.print("[green]Daemon stopped[/green]")
        except FileNotFoundError:
            console.print("[yellow]No daemon.pid found — is the daemon running?[/yellow]")


def main():
    parser = argparse.ArgumentParser(prog="skyblock", description="Skyblock AH Flipper")
    sub = parser.add_subparsers(dest="command")

    show = sub.add_parser("show", help="Show current opportunities")
    show.add_argument("--min-profit", help="Minimum profit e.g. 500k or 1m")
    show.set_defaults(min_profit=None)

    top_p = sub.add_parser("top", help="Top AH flips over the last N hours")
    top_p.add_argument("--hours", type=int, default=24, help="Time window in hours (default: 24)")

    daemon_p = sub.add_parser("daemon", help="Control the daemon")
    daemon_p.add_argument("action", choices=["start", "stop"])
    sub.add_parser("setup")

    args = parser.parse_args()

    if args.command == "show" or args.command is None:
        if args.command is None:
            args.min_profit = None
        cmd_show(args)
    elif args.command == "top":
        cmd_top(args)
    elif args.command == "daemon":
        cmd_daemon(args)
    elif args.command == "setup":
        setup_first_run()


if __name__ == "__main__":
    main()
