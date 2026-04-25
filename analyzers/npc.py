from __future__ import annotations
from models import Opportunity

MIN_WEEKLY_VOLUME = 10_000


class NpcAnalyzer:
    def __init__(self, npc_discount: float, min_profit: float):
        self.npc_discount = npc_discount
        self.min_profit = min_profit

    def analyze(self, items: list[dict], bazaar: dict) -> list[Opportunity]:
        opportunities = []
        for item in items:
            item_id = item.get("id")
            npc_price = item.get("npc_sell_price")
            daily_limit = item.get("daily_limit")  # None = no real NPC daily limit
            name = item.get("name", item_id)

            if not item_id or not npc_price:
                continue
            if daily_limit is None:
                continue
            if item_id not in bazaar:
                continue
            bz = bazaar[item_id]
            qs = bz.get("quick_status", {})
            weekly_volume = qs.get("buyMovingWeek", 0)
            if weekly_volume < MIN_WEEKLY_VOLUME:
                continue

            insta_buy = qs.get("buyPrice", 0)
            if not insta_buy:
                continue

            effective_npc = npc_price * (1 - self.npc_discount)
            profit_per_item = effective_npc - insta_buy
            total_profit = profit_per_item * daily_limit

            if total_profit < self.min_profit:
                continue

            opportunities.append(Opportunity(
                type="NPC",
                item_id=item_id,
                item_name=name,
                profit=total_profit,
                action="JETZT KAUFEN",
                details={
                    "npc_price": npc_price,
                    "effective_npc_price": round(effective_npc, 2),
                    "bazaar_buy": round(insta_buy, 2),
                    "daily_limit": daily_limit,
                    "profit_per_item": round(profit_per_item, 2),
                },
                confidence="high",
            ))

        return sorted(opportunities, key=lambda o: o.profit, reverse=True)
