import pytest
from analyzers.auction import AuctionAnalyzer

MEDIAN_PRICES = {
    "ASPECT_OF_THE_END": 25_000_000,
    "SAND": 500,
}


@pytest.fixture
def analyzer():
    return AuctionAnalyzer(min_profit=500_000, underpriced_threshold=0.25)


def test_underpriced_item_detected(analyzer):
    auctions = [
        {
            "item_name": "Aspect of the End",
            "tag": "ASPECT_OF_THE_END",
            "starting_bid": 18_000_000,
            "bin": True,
            "claimed": False,
            "end": 9999999999999,
            "count": 1,
        }
    ]
    # 18M vs 25M median → 28% below → profit 7M
    results = analyzer.analyze(auctions, MEDIAN_PRICES)
    assert any(r.item_id == "ASPECT_OF_THE_END" for r in results)


def test_fairly_priced_item_ignored(analyzer):
    auctions = [
        {
            "item_name": "Aspect of the End",
            "tag": "ASPECT_OF_THE_END",
            "starting_bid": 24_000_000,
            "bin": True,
            "claimed": False,
            "end": 9999999999999,
            "count": 1,
        }
    ]
    results = analyzer.analyze(auctions, MEDIAN_PRICES)
    assert results == []


def test_stack_arbitrage_detected(analyzer):
    auctions = [
        {
            "item_name": "Sand",
            "tag": "SAND",
            "starting_bid": 5_000,
            "bin": True,
            "claimed": False,
            "end": 9999999999999,
            "count": 64,
        }
    ]
    high_median = {"SAND": 20_000}
    results = analyzer.analyze(auctions, high_median)
    # price_per_unit = 5000/64 ≈ 78, median=20000, profit = (20000-78)*64 ≈ 1.27M > 500k
    assert any(r.item_id == "SAND" for r in results)


def test_non_bin_auction_skipped(analyzer):
    auctions = [
        {
            "item_name": "Aspect of the End",
            "tag": "ASPECT_OF_THE_END",
            "starting_bid": 10_000_000,
            "bin": False,
            "claimed": False,
            "end": 9999999999999,
            "count": 1,
        }
    ]
    results = analyzer.analyze(auctions, MEDIAN_PRICES)
    assert results == []


def test_no_median_data_skipped(analyzer):
    auctions = [
        {
            "item_name": "Unknown",
            "tag": "UNKNOWN_ITEM",
            "starting_bid": 1_000,
            "bin": True,
            "claimed": False,
            "end": 9999999999999,
            "count": 1,
        }
    ]
    results = analyzer.analyze(auctions, MEDIAN_PRICES)
    assert results == []
