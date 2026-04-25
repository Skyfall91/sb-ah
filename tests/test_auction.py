import pytest
from unittest.mock import patch
from analyzers.auction import AuctionAnalyzer

END = 9_999_999_999_999
LBIN = {"ITEM": 1_000_000}


def auction(bid, *, bin=True, claimed=False):
    return {"item_bytes": "fake", "starting_bid": bid, "bin": bin, "claimed": claimed, "end": END}


@pytest.fixture
def analyzer():
    return AuctionAnalyzer(min_profit=500_000)


def test_bundle_arbitrage_detected(analyzer):
    # single at 1M, bundle of 64 at 1000 total → profit per 14 >> 500k
    auctions = [auction(1_000_000), auction(1_000)]
    with patch("analyzers.auction.decode_auction_item", side_effect=[(1, "ITEM"), (64, "ITEM")]):
        results = analyzer.analyze(auctions, LBIN)
    assert any(r.item_id == "ITEM" for r in results)


def test_bundle_near_reference_price_ignored(analyzer):
    # bundle barely below reference → profit_14 < min_profit
    auctions = [auction(1_000_000), auction(985_000 * 64)]
    with patch("analyzers.auction.decode_auction_item", side_effect=[(1, "ITEM"), (64, "ITEM")]):
        results = analyzer.analyze(auctions, LBIN)
    assert results == []


def test_non_bin_auction_skipped(analyzer):
    # non-BIN is ignored, leaving only the single → no bundle → no result
    auctions = [auction(1_000_000), auction(1_000, bin=False)]
    with patch("analyzers.auction.decode_auction_item", side_effect=[(1, "ITEM")]):
        results = analyzer.analyze(auctions, LBIN)
    assert results == []


def test_no_item_bytes_skipped(analyzer):
    auctions = [{"starting_bid": 1_000, "bin": True, "claimed": False, "end": END}]
    results = analyzer.analyze(auctions, LBIN)
    assert results == []


def test_unknown_item_without_lbin_skipped(analyzer):
    # no avg_lbin entry, only one auction → can't form singles+bundles pair
    auctions = [auction(1_000)]
    with patch("analyzers.auction.decode_auction_item", side_effect=[(64, "UNKNOWN")]):
        results = analyzer.analyze(auctions, {})
    assert results == []
