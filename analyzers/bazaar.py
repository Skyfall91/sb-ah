from models import Opportunity

MIN_WEEKLY_VOLUME = 50_000


class BazaarAnalyzer:
    def __init__(self, bazaar_tax: float, min_profit: float):
        self.bazaar_tax = bazaar_tax
        self.min_profit = min_profit

    def analyze(self, products: dict, items_meta: dict) -> list:
        opportunities = []
        for item_id, product in products.items():
            if not product.get("sell_summary") or not product.get("buy_summary"):
                continue

            sell_price = product["sell_summary"][0]["pricePerUnit"]
            buy_price = product["buy_summary"][0]["pricePerUnit"]
            weekly_volume = min(
                product["quick_status"].get("buyMovingWeek", 0),
                product["quick_status"].get("sellMovingWeek", 0),
            )

            if weekly_volume < MIN_WEEKLY_VOLUME:
                continue

            net_profit = sell_price * (1 - self.bazaar_tax) - buy_price
            if net_profit < self.min_profit:
                continue

            name = items_meta.get(item_id, {}).get("name", item_id)
            volume_label = "hoch" if weekly_volume > 500_000 else "mittel"

            opportunities.append(Opportunity(
                type="BAZAAR",
                item_id=item_id,
                item_name=name,
                profit=net_profit,
                action="JETZT KAUFEN",
                details={
                    "buy_order": buy_price,
                    "sell_offer": sell_price,
                    "volume": volume_label,
                    "weekly_volume": weekly_volume,
                },
                confidence="high" if weekly_volume > 500_000 else "medium",
            ))

        return sorted(opportunities, key=lambda o: o.profit, reverse=True)
