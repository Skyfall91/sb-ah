import pytest
import tempfile
import os
from datetime import datetime, timedelta, timezone
from models import Opportunity
from db import DB


@pytest.fixture
def tmp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    db = DB(path)
    yield db
    os.unlink(path)


def test_save_and_load_opportunity(tmp_db):
    opp = Opportunity(
        type="BAZAAR",
        item_id="ENCHANTED_DIAMOND",
        item_name="Enchanted Diamond",
        profit=2_300_000,
        action="JETZT KAUFEN",
        details={"buy_order": 18_200_000, "sell_offer": 20_500_000},
        confidence="high",
    )
    tmp_db.save_opportunity(opp)
    results = tmp_db.get_opportunities()
    assert len(results) == 1
    assert results[0].item_id == "ENCHANTED_DIAMOND"
    assert results[0].profit == 2_300_000
    assert results[0].details == {"buy_order": 18_200_000, "sell_offer": 20_500_000}


def test_filter_by_type(tmp_db):
    opp_bazaar = Opportunity("BAZAAR", "A", "A", 600_000, "JETZT KAUFEN", {}, "high")
    opp_npc = Opportunity("NPC", "B", "B", 700_000, "JETZT KAUFEN", {}, "high")
    tmp_db.save_opportunity(opp_bazaar)
    tmp_db.save_opportunity(opp_npc)
    results = tmp_db.get_opportunities(type_filter="BAZAAR")
    assert len(results) == 1
    assert results[0].type == "BAZAAR"


def test_filter_by_min_profit(tmp_db):
    tmp_db.save_opportunity(Opportunity("BAZAAR", "A", "A", 200_000, "JETZT KAUFEN", {}, "high"))
    tmp_db.save_opportunity(Opportunity("BAZAAR", "B", "B", 800_000, "JETZT KAUFEN", {}, "high"))
    results = tmp_db.get_opportunities(min_profit=500_000)
    assert len(results) == 1
    assert results[0].item_id == "B"


def test_clear_old_opportunities(tmp_db):
    opp = Opportunity("BAZAAR", "A", "A", 600_000, "JETZT KAUFEN", {}, "high")
    tmp_db.save_opportunity(opp)
    tmp_db.clear_opportunities_older_than_minutes(0)
    assert tmp_db.get_opportunities() == []


def test_clear_old_opportunities_keeps_recent(tmp_db):
    old_opp = Opportunity("BAZAAR", "OLD", "Old", 600_000, "JETZT KAUFEN", {}, "high")
    old_opp.created_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    recent_opp = Opportunity("BAZAAR", "NEW", "New", 600_000, "JETZT KAUFEN", {}, "high")
    tmp_db.save_opportunity(old_opp)
    tmp_db.save_opportunity(recent_opp)
    tmp_db.clear_opportunities_older_than_minutes(5)
    results = tmp_db.get_opportunities()
    assert len(results) == 1
    assert results[0].item_id == "NEW"


def test_top_sightings_include_prices(tmp_db):
    opp = Opportunity("AH", "ITEM", "Item", 1_000_000, "JETZT KAUFEN",
                      {"tier": "RARE", "bundle_per_unit": 5_000, "single_price": 25_000_000}, "high")
    tmp_db.record_sightings([opp])
    rows = tmp_db.get_top_sightings(hours=1)
    assert len(rows) == 1
    assert rows[0]["avg_buy_price"] == 5_000
    assert rows[0]["avg_sell_price"] == 25_000_000


def test_sightings_kept_for_30_days(tmp_db):
    opp = Opportunity("AH", "ITEM", "Item", 1_000_000, "JETZT KAUFEN", {"tier": "RARE"}, "high")
    # Record a sighting, then manually backdate it to 29 days ago
    tmp_db.record_sightings([opp])
    with tmp_db._conn() as conn:
        conn.execute("UPDATE ah_sightings SET seen_at = datetime('now', '-29 days')")
    # After another record_sightings call (which prunes), 29-day-old entry should survive
    tmp_db.record_sightings([])
    rows = tmp_db.get_top_sightings(hours=24 * 30)
    assert len(rows) == 1


def test_sightings_older_than_30_days_pruned(tmp_db):
    opp = Opportunity("AH", "ITEM", "Item", 1_000_000, "JETZT KAUFEN", {"tier": "RARE"}, "high")
    tmp_db.record_sightings([opp])
    with tmp_db._conn() as conn:
        conn.execute("UPDATE ah_sightings SET seen_at = datetime('now', '-31 days')")
    tmp_db.record_sightings([])
    rows = tmp_db.get_top_sightings(hours=24 * 32)
    assert len(rows) == 0


def test_save_price_snapshot(tmp_db):
    tmp_db.save_price_snapshot("ENCHANTED_DIAMOND", 80_000.0, "self")
    snapshots = tmp_db.get_price_snapshots("ENCHANTED_DIAMOND")
    assert len(snapshots) == 1
    assert snapshots[0]["price"] == 80_000.0
