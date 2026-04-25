# tests/test_menubar_helpers.py
import pytest
from models import Opportunity


def test_format_coins_millions():
    from utils.formatting import format_coins
    assert format_coins(2_300_000) == "~2.3M"


def test_format_coins_thousands():
    from utils.formatting import format_coins
    assert format_coins(540_000) == "~540k"


def test_format_coins_small():
    from utils.formatting import format_coins
    assert format_coins(999) == "999"


def test_opportunity_title_bazaar():
    from menubar import opportunity_title
    opp = Opportunity("BAZAAR", "ENCHANTED_DIAMOND", "Enchanted Diamond",
                      2_300_000, "JETZT KAUFEN", {"volume": "hoch"}, "high")
    assert opportunity_title(opp) == "[BAZAAR] Enchanted Diamond"


def test_opportunity_title_mayor_has_star():
    from menubar import opportunity_title
    opp = Opportunity("MAYOR", "GRIFFIN_FEATHER", "Griffin Feather",
                      900_000, "JETZT INVESTIEREN", {}, "high")
    assert "★" in opportunity_title(opp)


def test_opportunity_subtitle_bazaar():
    from menubar import opportunity_subtitle
    opp = Opportunity("BAZAAR", "ENCHANTED_DIAMOND", "Enchanted Diamond",
                      2_300_000, "JETZT KAUFEN",
                      {"buy_order": 18_200_000, "sell_offer": 20_500_000, "volume": "hoch"},
                      "high")
    subtitle = opportunity_subtitle(opp)
    assert "2.3M" in subtitle
    assert "hoch" in subtitle


def test_opportunity_subtitle_npc():
    from menubar import opportunity_subtitle
    opp = Opportunity("NPC", "SAND", "Sand", 540_000, "JETZT KAUFEN",
                      {"daily_limit": 640}, "high")
    subtitle = opportunity_subtitle(opp)
    assert "540k" in subtitle
    assert "640" in subtitle


def test_opportunity_subtitle_ah_underpriced():
    from menubar import opportunity_subtitle
    opp = Opportunity("AH", "ASPECT_OF_THE_END", "Aspect of the End",
                      7_000_000, "JETZT KAUFEN",
                      {"discount_pct": 28.0, "arbitrage_type": "underpriced"},
                      "high")
    subtitle = opportunity_subtitle(opp)
    assert "28" in subtitle


def test_opportunity_subtitle_mayor():
    from menubar import opportunity_subtitle
    opp = Opportunity("MAYOR", "GRIFFIN_FEATHER", "Griffin Feather",
                      900_000, "JETZT INVESTIEREN",
                      {"current_mayor": "Diana", "avg_increase_pct": 180.0, "cycles_analyzed": 5},
                      "high")
    subtitle = opportunity_subtitle(opp)
    assert "Diana" in subtitle
    assert "180" in subtitle


def test_needs_setup_true_when_no_api_key():
    from menubar import needs_setup
    from config import Config
    assert needs_setup(Config(api_key="")) is True


def test_needs_setup_false_when_api_key_present():
    from menubar import needs_setup
    from config import Config
    assert needs_setup(Config(api_key="abc-123")) is False


def test_opportunity_subtitle_ah_stack():
    from menubar import opportunity_subtitle
    opp = Opportunity("AH", "ENCHANTED_DIAMOND", "Enchanted Diamond",
                      3_000_000, "JETZT KAUFEN",
                      {"discount_pct": 0.0, "arbitrage_type": "stack", "count": 64},
                      "high")
    subtitle = opportunity_subtitle(opp)
    assert "Stack" in subtitle
    assert "64" in subtitle
