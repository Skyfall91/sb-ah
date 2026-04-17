import argparse
import sys
from rich.console import Console
from rich.text import Text
from config import load_config, setup_first_run
from db import DB

console = Console()

DIVIDER = "━" * 42


def format_coins(amount: float) -> str:
    if amount >= 1_000_000:
        return f"~{amount / 1_000_000:.1f}M"
    if amount >= 1_000:
        return f"~{amount / 1_000:.0f}k"
    return str(int(amount))


def print_opportunity(opp):
    d = opp.details
    console.print(f" [{opp.type}] [bold]{opp.item_name}[/bold]")
    if opp.type == "BAZAAR":
        console.print(f"  → Buy Order: {format_coins(d['buy_order'])} | Sell Offer: {format_coins(d['sell_offer'])}")
        console.print(f"  → Profit: {format_coins(opp.profit)} pro Transaktion")
        console.print(f"  → Volumen: {d.get('volume', '?')}")
    elif opp.type == "NPC":
        console.print(f"  → NPC Preis: {format_coins(d['effective_npc_price'])}/stk | Bazaar Buy: {format_coins(d['bazaar_buy'])}/stk")
        console.print(f"  → Profit: {format_coins(opp.profit)} | Limit: {d['daily_limit']} Stück/Tag")
    elif opp.type == "AH":
        if d.get("arbitrage_type") == "stack":
            console.print(f"  → Stack ({d['count']}x) für {format_coins(d['auction_price'])} = {format_coins(d['price_per_unit'])}/stk")
            console.print(f"  → Einzelverkauf: {format_coins(d['median_single_price'])}/stk | Profit: {format_coins(opp.profit)}")
        else:
            console.print(f"  → AH Preis: {format_coins(d['auction_price'])} | Median: {format_coins(d['median_price'])}")
            console.print(f"  → {d.get('discount_pct', '?')}% unter Median | Profit: {format_coins(opp.profit)}")
    elif opp.type == "MAYOR":
        console.print(f"  → Jetzt kaufen bei: {format_coins(d['current_price'])}/stk")
        console.print(f"  → Historisch bei {d['current_mayor']}: Ø +{d['avg_increase_pct']}% ({d['cycles_analyzed']} Zyklen)")
        console.print(f"  → Empfehlung: einlagern")
    console.print()


def cmd_show(args):
    cfg = load_config()
    db = DB()
    type_filter = args.type.upper() if args.type else None

    min_profit = cfg.min_profit_display
    if args.min_profit:
        raw = args.min_profit.lower().replace("m", "000000").replace("k", "000")
        try:
            min_profit = int(raw)
        except ValueError:
            console.print(f"[red]Invalid --min-profit value: {args.min_profit}[/red]")
            sys.exit(1)

    all_opps = db.get_opportunities(type_filter=type_filter, min_profit=min_profit)
    if args.mayor:
        buy_opps = []
        invest_opps = [o for o in all_opps if o.type == "MAYOR"]
    else:
        buy_opps = [o for o in all_opps if o.action == "JETZT KAUFEN"]
        invest_opps = [o for o in all_opps if o.action == "JETZT INVESTIEREN"]

    if buy_opps:
        console.print(f"\n[bold green]{DIVIDER}[/bold green]")
        console.print(f"[bold green] JETZT KAUFEN[/bold green]")
        console.print(f"[bold green]{DIVIDER}[/bold green]")
        for opp in buy_opps:
            print_opportunity(opp)

    if invest_opps:
        console.print(f"[bold yellow]{DIVIDER}[/bold yellow]")
        mayor_name = invest_opps[0].details.get("current_mayor", "") if invest_opps else ""
        label = f" JETZT INVESTIEREN (Mayor: {mayor_name})" if mayor_name else " JETZT INVESTIEREN"
        console.print(f"[bold yellow]{label}[/bold yellow]")
        console.print(f"[bold yellow]{DIVIDER}[/bold yellow]")
        for opp in invest_opps:
            print_opportunity(opp)

    if not buy_opps and not invest_opps:
        console.print("[dim]Keine Opportunities gefunden. Läuft der Daemon? python3 daemon.py[/dim]")


def cmd_daemon(args):
    import subprocess
    import os
    if args.action == "start":
        proc = subprocess.Popen(
            ["python3", "daemon.py"],
            stdout=open("daemon.log", "a"),
            stderr=subprocess.STDOUT,
        )
        with open("daemon.pid", "w") as f:
            f.write(str(proc.pid))
        console.print(f"[green]Daemon gestartet (PID {proc.pid})[/green]")
    elif args.action == "stop":
        try:
            with open("daemon.pid") as f:
                pid = int(f.read().strip())
            os.kill(pid, 15)
            os.unlink("daemon.pid")
            console.print("[green]Daemon gestoppt[/green]")
        except FileNotFoundError:
            console.print("[yellow]Keine daemon.pid gefunden — läuft der Daemon?[/yellow]")


def main():
    parser = argparse.ArgumentParser(prog="skyblock", description="Skyblock Investment Tool")
    sub = parser.add_subparsers(dest="command")

    show = sub.add_parser("show", help="Zeige aktuelle Opportunities")
    show.add_argument("--type", choices=["bazaar", "npc", "ah", "mayor"], help="Filter nach Typ")
    show.add_argument("--min-profit", help="Mindestprofit z.B. 500k oder 1m")
    show.add_argument("--mayor", action="store_true", help="Nur Mayor/Event-Investitionen")

    daemon_p = sub.add_parser("daemon", help="Daemon steuern")
    daemon_p.add_argument("action", choices=["start", "stop"])

    sub.add_parser("setup", help="Konfiguration neu einrichten")

    args = parser.parse_args()

    if args.command == "show" or args.command is None:
        if args.command is None:
            args.type = None
            args.min_profit = None
            args.mayor = False
        cmd_show(args)
    elif args.command == "daemon":
        cmd_daemon(args)
    elif args.command == "setup":
        setup_first_run()


if __name__ == "__main__":
    main()
