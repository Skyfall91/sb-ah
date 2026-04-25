import pytest
from analyzers.npc import NpcAnalyzer


def make_bazaar_product(insta_buy_price: float, weekly_volume: int = 500_000) -> dict:
    return {
        "buy_summary": [{"pricePerUnit": insta_buy_price * 10, "amount": 100}],  # buy orders are irrelevant
        "quick_status": {"buyPrice": insta_buy_price, "buyMovingWeek": weekly_volume},
    }


@pytest.fixture
def analyzer():
    return NpcAnalyzer(npc_discount=0.0, min_profit=100_000)


def test_npc_arbitrage_detected(analyzer):
    items = [{"id": "SAND", "name": "Sand", "npc_sell_price": 2, "daily_limit": 640_000}]
    bazaar = {"SAND": make_bazaar_product(insta_buy_price=1)}
    results = analyzer.analyze(items, bazaar)
    assert len(results) == 1
    assert results[0].item_id == "SAND"
    assert results[0].profit > 100_000


def test_no_bazaar_data_skipped(analyzer):
    items = [{"id": "SAND", "name": "Sand", "npc_sell_price": 2, "daily_limit": 640}]
    results = analyzer.analyze(items, {})
    assert results == []


def test_no_daily_limit_skipped(analyzer):
    items = [{"id": "WITHER_SHIELD", "name": "Wither Shield", "npc_sell_price": 1}]
    bazaar = {"WITHER_SHIELD": make_bazaar_product(insta_buy_price=1)}
    results = analyzer.analyze(items, bazaar)
    assert results == []


def test_zero_npc_price_skipped(analyzer):
    items = [{"id": "ITEM", "name": "Item", "npc_sell_price": 0, "daily_limit": 640}]
    bazaar = {"ITEM": make_bazaar_product(insta_buy_price=1)}
    results = analyzer.analyze(items, bazaar)
    assert results == []


def test_buy_order_more_expensive_than_npc_skipped(analyzer):
    # Buy order price > NPC price → would lose money
    items = [{"id": "ITEM", "name": "Item", "npc_sell_price": 5, "daily_limit": 640}]
    bazaar = {"ITEM": make_bazaar_product(insta_buy_price=10)}
    results = analyzer.analyze(items, bazaar)
    assert results == []


def test_low_profit_ignored(analyzer):
    items = [{"id": "ITEM", "name": "Item", "npc_sell_price": 2, "daily_limit": 1}]
    bazaar = {"ITEM": make_bazaar_product(insta_buy_price=1)}
    results = analyzer.analyze(items, bazaar)
    assert results == []


def test_low_volume_skipped(analyzer):
    items = [{"id": "MOB_DROP", "name": "Mob Drop", "npc_sell_price": 100, "daily_limit": 640}]
    bazaar = {"MOB_DROP": make_bazaar_product(insta_buy_price=1, weekly_volume=500)}
    results = analyzer.analyze(items, bazaar)
    assert results == []


def test_discount_reduces_effective_npc_price():
    analyzer_no_disc = NpcAnalyzer(npc_discount=0.0, min_profit=100)
    analyzer_disc = NpcAnalyzer(npc_discount=0.03, min_profit=100)
    items = [{"id": "ITEM", "name": "Item", "npc_sell_price": 100, "daily_limit": 64}]
    bazaar = {"ITEM": make_bazaar_product(insta_buy_price=50)}
    r_no = analyzer_no_disc.analyze(items, bazaar)
    r_disc = analyzer_disc.analyze(items, bazaar)
    assert r_no[0].profit > r_disc[0].profit
    assert abs(r_disc[0].details["effective_npc_price"] - 97.0) < 0.01
