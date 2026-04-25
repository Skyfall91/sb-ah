from __future__ import annotations
import statistics
import time
from collections import defaultdict
from models import Opportunity
from utils.nbt import decode_auction_item

def _ah_fee(sell_price: float, derpy: bool = False) -> float:
    """Total BIN fee: tiered listing fee + claiming fee (1% over 1M, 4x during Derpy)."""
    if sell_price > 100_000_000:
        listing = 0.025
    elif sell_price > 10_000_000:
        listing = 0.02
    else:
        listing = 0.01
    claiming = (0.04 if derpy else 0.01) if sell_price > 1_000_000 else 0.0
    return listing + claiming

# Categories from the Hypixel items API that are gameplay-relevant
USEFUL_CATEGORIES = {
    "WEAPON", "SWORD", "BOW", "WAND",
    "ARMOR", "HELMET", "CHESTPLATE", "LEGGINGS", "BOOTS",
    "ACCESSORIES", "TALISMAN", "RING", "BELT", "GLOVES",
    "CONSUMABLE", "POTION", "FOOD",
    "BLOCK", "MATERIAL",
    "PET_ITEM",
    "FISHING_ROD", "FISHING_WEAPON",
    "MINING_TOOL", "HOE", "AXE", "PICKAXE",
    "DUNGEON",
}

# ID patterns that are always cosmetic regardless of category
COSMETIC_ID_PATTERNS = (
    "_PERSONALITY", "_ISLAND", "EPOCH_CAKE", "TRAVEL_SCROLL",
    "_PORTAL", "_RUNE", "_SKIN", "_TROPHY",
)


class AuctionAnalyzer:
    def __init__(self, min_profit: float):
        self.min_profit = min_profit

    def analyze(
        self,
        auctions: list[dict],
        avg_lbin: dict[str, float] | None = None,
        item_categories: dict[str, str] | None = None,
        bazaar: dict | None = None,
        item_npc_prices: dict[str, float] | None = None,
        derpy: bool = False,
    ) -> list[Opportunity]:
        now_ms = int(time.time() * 1000)
        avg_lbin = avg_lbin or {}
        item_categories = item_categories or {}
        bazaar = bazaar or {}
        item_npc_prices = item_npc_prices or {}

        parsed: list[dict] = []
        for a in auctions:
            if not a.get("bin") or a.get("claimed") or a.get("end", 0) < now_ms:
                continue
            ib = a.get("item_bytes", "")
            if not ib:
                continue
            count, skyblock_id = decode_auction_item(ib)
            if not skyblock_id:
                continue
            parsed.append({
                "skyblock_id": skyblock_id,
                "item_name": a.get("item_name", skyblock_id),
                "count": count,
                "total_price": a["starting_bid"],
                "price_per_unit": a["starting_bid"] / count,
                "tier": a.get("tier", "COMMON"),
            })

        by_item: dict[str, list[dict]] = defaultdict(list)
        for p in parsed:
            by_item[p["skyblock_id"]].append(p)

        opportunities: list[Opportunity] = []

        for skyblock_id, listings in by_item.items():
            if any(p in skyblock_id for p in COSMETIC_ID_PATTERNS):
                continue
            if item_categories:
                cat = item_categories.get(skyblock_id, "")
                if cat and cat.upper() not in USEFUL_CATEGORIES:
                    continue

            singles, bundles = [], []
            for l in listings:
                (singles if l["count"] == 1 else bundles).append(l)

            if not singles or not bundles:
                continue

            median_single = statistics.median(l["price_per_unit"] for l in singles)
            cheapest_bundle_pu = min(b["price_per_unit"] for b in bundles)

            bz_item = bazaar.get(skyblock_id, {})
            bz_qs   = bz_item.get("quick_status", {})
            bazaar_sell = bz_qs.get("sellPrice", 0)
            bazaar_buy  = bz_qs.get("buyPrice", 0)
            npc_price   = item_npc_prices.get(skyblock_id, 0)
            on_bazaar   = bazaar_sell > 0

            # Floor: guaranteed exit price (Bazaar instant sell or NPC)
            floor_price = max(bazaar_sell, npc_price)

            if skyblock_id in avg_lbin:
                reference_price = avg_lbin[skyblock_id]
                manipulated = abs(reference_price - median_single) / reference_price > 0.30
                suspicious = False
            else:
                reference_price = median_single
                suspicious = reference_price > cheapest_bundle_pu * 10
                manipulated = suspicious

            if on_bazaar and bazaar_buy > 0 and cheapest_bundle_pu >= bazaar_buy * 0.95:
                continue

            if floor_price > reference_price:
                reference_price = floor_price
                manipulated = False
                suspicious = False

            profitable = []
            fee = _ah_fee(reference_price, derpy=derpy)
            for bundle in bundles:
                sell_revenue = reference_price * bundle["count"] * (1 - fee)
                profit = sell_revenue - bundle["total_price"]
                profit_14 = (profit / bundle["count"]) * 14
                if profit_14 >= self.min_profit:
                    profitable.append((profit_14, profit, bundle))

            if not profitable:
                continue

            profit_per_14, best_profit, best_bundle = max(profitable, key=lambda x: x[1])

            opportunities.append(Opportunity(
                type="AH",
                item_id=skyblock_id,
                item_name=best_bundle["item_name"],
                profit=profit_per_14,
                action="BUY NOW",
                details={
                    "count": best_bundle["count"],
                    "bundle_total": best_bundle["total_price"],
                    "bundle_per_unit": round(best_bundle["price_per_unit"], 1),
                    "single_price": round(reference_price, 1),
                    "median_single": round(median_single, 1),
                    "listings": len(profitable),
                    "tier": best_bundle["tier"],
                    "profit_per_flip": round(best_profit, 1),
                    "manipulated": manipulated,
                    "suspicious": suspicious,
                    "has_lbin": skyblock_id in avg_lbin,
                    "on_bazaar": on_bazaar,
                    "bazaar_sell": round(bazaar_sell, 1) if on_bazaar else None,
                    "npc_price": round(npc_price, 1) if npc_price else None,
                },
                confidence="high" if not suspicious else "medium",
            ))

        return sorted(opportunities, key=lambda o: o.profit, reverse=True)
