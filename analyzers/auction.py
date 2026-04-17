from __future__ import annotations
import time
from models import Opportunity


class AuctionAnalyzer:
    def __init__(self, min_profit: float, underpriced_threshold: float = 0.25):
        self.min_profit = min_profit
        self.underpriced_threshold = underpriced_threshold

    def analyze(self, auctions: list[dict], median_prices: dict[str, float]) -> list[Opportunity]:
        opportunities = []
        now_ms = int(time.time() * 1000)

        for auction in auctions:
            if not auction.get("bin"):
                continue
            if auction.get("claimed"):
                continue
            if auction.get("end", 0) < now_ms:
                continue

            item_id = auction.get("tag") or auction.get("item_name", "").upper().replace(" ", "_")
            if item_id not in median_prices:
                continue

            median = median_prices[item_id]
            price = auction["starting_bid"]
            count = auction.get("count", 1)
            name = auction.get("item_name", item_id)

            if count > 1:
                price_per_unit = price / count
                if median <= 0 or price_per_unit >= median:
                    continue
                profit = (median - price_per_unit) * count
                if profit < self.min_profit:
                    continue
                opportunities.append(Opportunity(
                    type="AH",
                    item_id=item_id,
                    item_name=name,
                    profit=profit,
                    action="JETZT KAUFEN",
                    details={
                        "auction_price": price,
                        "count": count,
                        "price_per_unit": round(price_per_unit, 2),
                        "median_single_price": median,
                        "arbitrage_type": "stack",
                    },
                    confidence="medium",
                ))
            else:
                if median <= 0:
                    continue
                discount = (median - price) / median
                if discount < self.underpriced_threshold:
                    continue
                profit = median - price
                if profit < self.min_profit:
                    continue
                opportunities.append(Opportunity(
                    type="AH",
                    item_id=item_id,
                    item_name=name,
                    profit=profit,
                    action="JETZT KAUFEN",
                    details={
                        "auction_price": price,
                        "median_price": median,
                        "discount_pct": round(discount * 100, 1),
                        "arbitrage_type": "underpriced",
                    },
                    confidence="high" if discount > 0.4 else "medium",
                ))

        return sorted(opportunities, key=lambda o: o.profit, reverse=True)
