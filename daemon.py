import asyncio
import logging
from config import load_config, setup_first_run
from db import DB
from sources.hypixel import HypixelClient
from sources import moulberry
from analyzers.auction import AuctionAnalyzer
from analyzers.npc import NpcAnalyzer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


async def run_auction_loop(cfg, db: DB, hypixel: HypixelClient):
    ah_analyzer = AuctionAnalyzer(min_profit=cfg.min_profit_display)
    npc_analyzer = NpcAnalyzer(npc_discount=cfg.npc_discount, min_profit=cfg.min_profit_display)
    loop = asyncio.get_running_loop()
    while True:
        try:
            auctions, avg_lbin, items_raw, bazaar = await asyncio.gather(
                hypixel.get_auctions(),
                loop.run_in_executor(None, moulberry.get_avg_lbin),
                hypixel.get_items(),
                hypixel.get_bazaar(),
            )
            item_categories = {}
            item_npc_prices = {}
            items_with_limit = []
            for item in items_raw:
                iid = item["id"]
                item_categories[iid] = item.get("category", "")
                item_npc_prices[iid] = item.get("npc_sell_price", 0)
                if item.get("daily_limit"):
                    items_with_limit.append(item)

            ah_opps = ah_analyzer.analyze(
                auctions,
                avg_lbin=avg_lbin,
                item_categories=item_categories,
                bazaar=bazaar,
                item_npc_prices=item_npc_prices,
            )
            db.clear_opportunities_older_than_minutes(10, type_filter="AH")
            for opp in ah_opps:
                db.save_opportunity(opp)
            db.record_sightings(ah_opps)
            lbin_hits = sum(1 for o in ah_opps if o.details.get("has_lbin"))
            log.info(f"AH: {len(ah_opps)} opportunities ({lbin_hits} mit LBIN, {len(avg_lbin)} Preise geladen)")

            npc_opps = npc_analyzer.analyze(items_with_limit, bazaar)
            db.clear_opportunities_older_than_minutes(10, type_filter="NPC")
            for opp in npc_opps:
                db.save_opportunity(opp)
            log.info(f"NPC: {len(npc_opps)} insta-buy opportunities")
        except Exception as e:
            log.warning(f"Poll loop error: {e}")
        await asyncio.sleep(60)


async def main():
    cfg = load_config()
    if not cfg.api_key:
        cfg = setup_first_run()

    db = DB()
    hypixel = HypixelClient(api_key=cfg.api_key)

    log.info("Daemon started")
    await run_auction_loop(cfg, db, hypixel)


if __name__ == "__main__":
    asyncio.run(main())
