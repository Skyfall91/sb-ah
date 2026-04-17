import asyncio
import logging
from config import load_config, setup_first_run
from db import DB
from notify import Notifier
from sources.hypixel import HypixelClient
from sources.coflnet import CoflnetClient, NoDataError
from analyzers.bazaar import BazaarAnalyzer
from analyzers.npc import NpcAnalyzer
from analyzers.auction import AuctionAnalyzer
from analyzers.mayor import MayorAnalyzer, MayorCycle

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


async def run_bazaar_loop(cfg, db: DB, hypixel: HypixelClient, notifier: Notifier):
    analyzer = BazaarAnalyzer(bazaar_tax=cfg.bazaar_tax, min_profit=cfg.min_profit_display)
    while True:
        try:
            products = await hypixel.get_bazaar()
            items_raw = await hypixel.get_items()
            items_meta = {item["id"]: item for item in items_raw}
            opps = analyzer.analyze(products, items_meta)
            db.clear_opportunities_older_than_minutes(5)
            for opp in opps:
                db.save_opportunity(opp)
                notifier.notify_if_threshold(opp)
            log.info(f"Bazaar: {len(opps)} opportunities found")
        except Exception as e:
            log.warning(f"Bazaar loop error: {e}")
        await asyncio.sleep(60)


async def run_npc_loop(cfg, db: DB, hypixel: HypixelClient, notifier: Notifier):
    analyzer = NpcAnalyzer(npc_discount=cfg.npc_discount, min_profit=cfg.min_profit_display)
    while True:
        try:
            items_raw = await hypixel.get_items()
            npc_items = [i for i in items_raw if i.get("npc_sell_price")]
            bazaar = await hypixel.get_bazaar()
            opps = analyzer.analyze(npc_items, bazaar)
            for opp in opps:
                db.save_opportunity(opp)
                notifier.notify_if_threshold(opp)
            log.info(f"NPC: {len(opps)} opportunities found")
        except Exception as e:
            log.warning(f"NPC loop error: {e}")
        await asyncio.sleep(300)


async def run_auction_loop(cfg, db: DB, hypixel: HypixelClient, coflnet: CoflnetClient, notifier: Notifier):
    analyzer = AuctionAnalyzer(min_profit=cfg.min_profit_display)
    while True:
        try:
            auctions = await hypixel.get_auctions()
            bin_auctions = [a for a in auctions if a.get("bin") and not a.get("claimed")]
            item_ids = list({a.get("tag") for a in bin_auctions if a.get("tag")})

            median_prices = {}
            for item_id in item_ids:
                try:
                    median_prices[item_id] = await coflnet.get_median_price(item_id)
                except NoDataError:
                    pass
                except Exception:
                    pass

            opps = analyzer.analyze(bin_auctions, median_prices)
            for opp in opps:
                db.save_opportunity(opp)
                notifier.notify_if_threshold(opp)
            log.info(f"AH: {len(opps)} opportunities found")
        except Exception as e:
            log.warning(f"AH loop error: {e}")
        await asyncio.sleep(300)


async def run_mayor_loop(cfg, db: DB, hypixel: HypixelClient, coflnet: CoflnetClient, notifier: Notifier):
    analyzer = MayorAnalyzer(min_cycles=3, min_avg_increase_pct=50.0, min_profit=cfg.min_profit_display)
    while True:
        try:
            election = await hypixel.get_election()
            current_mayor = election.get("mayor", {}).get("name")
            if not current_mayor:
                await asyncio.sleep(600)
                continue

            items_raw = await hypixel.get_items()
            for item in items_raw[:50]:
                item_id = item.get("id")
                name = item.get("name", item_id)
                try:
                    history = await coflnet.get_price_history(item_id, days=365)
                    cycles = _build_mayor_cycles(election)
                    opp = analyzer.analyze_item(item_id, name, history, cycles, current_mayor)
                    if opp:
                        db.save_opportunity(opp)
                        notifier.notify_if_threshold(opp)
                except NoDataError:
                    pass
                except Exception as e:
                    log.debug(f"Mayor analysis skipped for {item_id}: {e}")

            log.info(f"Mayor loop complete (current: {current_mayor})")
        except Exception as e:
            log.warning(f"Mayor loop error: {e}")
        await asyncio.sleep(600)


def _build_mayor_cycles(election: dict) -> list[MayorCycle]:
    # Hypixel election API doesn't expose full historical mayor data.
    # Build approximate cycles from available data — each Skyblock year ~5 real days.
    cycles = []
    mayor_name = election.get("mayor", {}).get("name")
    if mayor_name:
        for i in range(5):
            start = i * 31
            cycles.append(MayorCycle(mayor=mayor_name, start_day=start, end_day=start + 30))
    return cycles


async def main():
    cfg = load_config()
    if not cfg.api_key:
        cfg = setup_first_run()

    db = DB()
    notifier = Notifier(min_profit_notify=cfg.min_profit_notify)
    hypixel = HypixelClient(api_key=cfg.api_key)
    coflnet = CoflnetClient()

    log.info("Daemon started")
    await asyncio.gather(
        run_bazaar_loop(cfg, db, hypixel, notifier),
        run_npc_loop(cfg, db, hypixel, notifier),
        run_auction_loop(cfg, db, hypixel, coflnet, notifier),
        run_mayor_loop(cfg, db, hypixel, coflnet, notifier),
    )


if __name__ == "__main__":
    asyncio.run(main())
