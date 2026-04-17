from __future__ import annotations
from models import Opportunity

STACK_SIZE = 64


class NpcAnalyzer:
    def __init__(self, npc_discount: float, min_profit: float):
        self.npc_discount = npc_discount
        self.min_profit = min_profit

    def analyze(self, items: list[dict], bazaar: dict) -> list[Opportunity]:
        opportunities = []
        for item in items:
            item_id = item.get("id")
            npc_price = item.get("npc_sell_price")
            daily_limit = item.get("daily_limit", STACK_SIZE)
            name = item.get("name", item_id)

            if not item_id or npc_price is None:
                continue
            if item_id not in bazaar:
                continue
            bz = bazaar[item_id]
            if not bz.get("buy_summary"):
                continue

            bazaar_buy = bz["buy_summary"][0]["pricePerUnit"]
            effective_npc = npc_price * (1 - self.npc_discount)
            profit_per_item = bazaar_buy - effective_npc
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
                    "bazaar_buy": bazaar_buy,
                    "daily_limit": daily_limit,
                    "profit_per_item": round(profit_per_item, 2),
                },
                confidence="high",
            ))

        return sorted(opportunities, key=lambda o: o.profit, reverse=True)
