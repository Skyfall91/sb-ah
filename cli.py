import argparse
import os
import sys

from config import load_config, setup_first_run


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
        print(f"Daemon started (PID {proc.pid})")
    elif args.action == "stop":
        try:
            with open(pid_path) as f:
                pid = int(f.read().strip())
            os.kill(pid, 15)
            os.unlink(pid_path)
            print("Daemon stopped")
        except FileNotFoundError:
            print("No daemon.pid found — is the daemon running?")


def main():
    parser = argparse.ArgumentParser(prog="skyblock", description="Skyblock AH Advisor")
    sub = parser.add_subparsers(dest="command")

    advice_p = sub.add_parser("advice", help="AI-powered personalized flip recommendations")
    advice_p.add_argument("--full", action="store_true",
                          help="Include inventory/enderchest/backpack value estimate (slower)")

    wiki_p = sub.add_parser("wiki", help="Manage wiki knowledge base")
    wiki_p.add_argument("action", choices=["update"], help="Crawl wiki and build search index")

    daemon_p = sub.add_parser("daemon", help="Control the daemon")
    daemon_p.add_argument("action", choices=["start", "stop"])

    sub.add_parser("setup")

    args = parser.parse_args()

    if args.command == "advice":
        from config import load_config
        import advisor
        cfg = load_config()
        advisor.run(cfg, full=args.full)
    elif args.command == "wiki":
        from sources import wiki, rag
        print("Crawling wiki (this may take a few minutes)...")
        chunks = wiki.crawl(verbose=True)
        print("\nBuilding search index...")
        rag.build_index(chunks, verbose=True)
        print("\nDone. Run 'python3 cli.py advice' to get recommendations.")
    elif args.command == "daemon":
        cmd_daemon(args)
    elif args.command == "setup":
        setup_first_run()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
