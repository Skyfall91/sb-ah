import pytest
from analyzers.npc import NpcAnalyzer


def make_bazaar_product(buy_price: float, weekly_volume: int = 500_000) -> dict:
    return {
        "buy_summary": [{"pricePerUnit": buy_price, "amount": 100}],
        "quick_status": {"buyMovingWeek": weekly_volume}
    }


@pytest.fixture
def analyzer():
    return NpcAnalyzer(npc_discount=0.0, min_profit=500_000)


def test_npc_arbitrage_detected(analyzer):
    items = [{"id": "SAND", "name": "Sand", "npc_sell_price": 2, "daily_limit": 640}]
    bazaar = {"SAND": make_bazaar_product(buy_price=10_000)}
    results = analyzer.analyze(items, bazaar)
    assert len(results) == 1
    assert results[0].item_id == "SAND"
    assert results[0].profit > 500_000


def test_no_bazaar_data_skipped(analyzer):
    items = [{"id": "SAND", "name": "Sand", "npc_sell_price": 2, "daily_limit": 640}]
    results = analyzer.analyze(items, {})
    assert results == []


def test_low_profit_ignored(analyzer):
    items = [{"id": "ITEM", "name": "Item", "npc_sell_price": 9_800, "daily_limit": 640}]
    bazaar = {"ITEM": make_bazaar_product(buy_price=10_000)}
    results = analyzer.analyze(items, bazaar)
    assert results == []


def test_discount_increases_profit():
    analyzer_no_disc = NpcAnalyzer(npc_discount=0.0, min_profit=50_000)
    analyzer_disc = NpcAnalyzer(npc_discount=0.03, min_profit=50_000)
    items = [{"id": "ITEM", "name": "Item", "npc_sell_price": 9_000, "daily_limit": 64}]
    bazaar = {"ITEM": make_bazaar_product(buy_price=10_000)}
    r_no = analyzer_no_disc.analyze(items, bazaar)
    r_disc = analyzer_disc.analyze(items, bazaar)
    assert r_disc[0].profit > r_no[0].profit


def test_npc_discount_reduces_effective_cost():
    analyzer = NpcAnalyzer(npc_discount=0.03, min_profit=100_000)
    items = [{"id": "SAND", "name": "Sand", "npc_sell_price": 1_000, "daily_limit": 640}]
    bazaar = {"SAND": make_bazaar_product(buy_price=2_000)}
    results = analyzer.analyze(items, bazaar)
    assert len(results) == 1
    assert abs(results[0].details["effective_npc_price"] - 970.0) < 0.01
