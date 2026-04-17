import subprocess
from models import Opportunity


class Notifier:
    def __init__(self, min_profit_notify: int):
        self.min_profit_notify = min_profit_notify

    def notify_if_threshold(self, opp: Opportunity):
        if opp.profit < self.min_profit_notify:
            return
        profit_str = self._format_coins(opp.profit)
        title = f"[{opp.type}] {opp.item_name}"
        body = f"{opp.action} — Profit: {profit_str}"
        self._send(title, body)
        self._play_sound(opp.profit)

    def _send(self, title: str, body: str):
        script = f'display notification "{body}" with title "{title}"'
        subprocess.run(["osascript", "-e", script], check=False)

    def _play_sound(self, profit: float):
        sound = "/System/Library/Sounds/Glass.aiff" if profit < 2_000_000 else "/System/Library/Sounds/Funk.aiff"
        subprocess.run(["afplay", sound], check=False)

    @staticmethod
    def _format_coins(amount: float) -> str:
        if amount >= 1_000_000:
            return f"{amount / 1_000_000:.1f}M"
        if amount >= 1_000:
            return f"{amount / 1_000:.0f}k"
        return str(int(amount))
