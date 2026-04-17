import pytest
from analyzers.bazaar import BazaarAnalyzer


def make_product(sell_price: float, buy_price: float, weekly_volume: int) -> dict:
    return {
        "product_id": "TEST_ITEM",
        "sell_summary": [{"pricePerUnit": sell_price, "amount": 100}],
        "buy_summary": [{"pricePerUnit": buy_price, "amount": 100}],
        "quick_status": {
            "buyMovingWeek": weekly_volume,
            "sellMovingWeek": weekly_volume,
        }
    }


@pytest.fixture
def analyzer():
    return BazaarAnalyzer(bazaar_tax=0.0125, min_profit=500_000)


def test_high_profit_opportunity_detected(analyzer):
    products = {
        "ENCHANTED_DIAMOND": make_product(
            sell_price=20_500_000,
            buy_price=18_200_000,
            weekly_volume=1_000_000
        )
    }
    items_meta = {"ENCHANTED_DIAMOND": {"name": "Enchanted Diamond"}}
    results = analyzer.analyze(products, items_meta)
    assert len(results) == 1
    assert results[0].item_id == "ENCHANTED_DIAMOND"
    assert results[0].profit > 500_000


def test_low_profit_below_threshold_ignored(analyzer):
    products = {
        "CHEAP_ITEM": make_product(
            sell_price=1_100_000,
            buy_price=1_000_000,
            weekly_volume=1_000_000
        )
    }
    items_meta = {"CHEAP_ITEM": {"name": "Cheap Item"}}
    results = analyzer.analyze(products, items_meta)
    # profit = 1_100_000 * (1 - 0.0125) - 1_000_000 = 86_250 < 500_000
    assert results == []


def test_low_volume_ignored(analyzer):
    products = {
        "RARE_ITEM": make_product(
            sell_price=20_500_000,
            buy_price=18_200_000,
            weekly_volume=100  # too thin
        )
    }
    items_meta = {"RARE_ITEM": {"name": "Rare Item"}}
    results = analyzer.analyze(products, items_meta)
    assert results == []


def test_profit_calculation_accounts_for_tax(analyzer):
    # sell 10M, buy 9M, tax 1.25%: net = 10M * 0.9875 - 9M = 875k
    products = {
        "TAX_ITEM": make_product(
            sell_price=10_000_000,
            buy_price=9_000_000,
            weekly_volume=500_000
        )
    }
    items_meta = {"TAX_ITEM": {"name": "Tax Item"}}
    results = analyzer.analyze(products, items_meta)
    assert len(results) == 1
    assert abs(results[0].profit - 875_000) < 1


def test_missing_sell_or_buy_summary_skipped(analyzer):
    products = {
        "EMPTY_ITEM": {
            "product_id": "EMPTY_ITEM",
            "sell_summary": [],
            "buy_summary": [],
            "quick_status": {"buyMovingWeek": 1_000_000, "sellMovingWeek": 1_000_000}
        }
    }
    items_meta = {"EMPTY_ITEM": {"name": "Empty"}}
    results = analyzer.analyze(products, items_meta)
    assert results == []
