from __future__ import annotations
import sqlite3
import json
from datetime import datetime, timedelta, timezone
from models import Opportunity


class DB:
    def __init__(self, path: str = "skyblock.db"):
        self.path = path
        self._init_schema()

    def _conn(self):
        return sqlite3.connect(self.path)

    def _init_schema(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS opportunities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    item_name TEXT NOT NULL,
                    profit REAL NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT NOT NULL,
                    confidence TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS price_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id TEXT NOT NULL,
                    price REAL NOT NULL,
                    source TEXT NOT NULL,
                    recorded_at TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_opp_created_at ON opportunities(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_snap_item_id ON price_snapshots(item_id)")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ah_sightings (
                    item_id TEXT NOT NULL,
                    item_name TEXT NOT NULL,
                    profit_per_14 REAL NOT NULL,
                    tier TEXT NOT NULL,
                    seen_at TEXT NOT NULL,
                    buy_price REAL,
                    sell_price REAL
                )
            """)
            # Migrate: add missing columns
            cols = {r[1] for r in conn.execute("PRAGMA table_info(ah_sightings)").fetchall()}
            if "profit_per_14" not in cols:
                conn.execute("DROP TABLE ah_sightings")
                conn.execute("""
                    CREATE TABLE ah_sightings (
                        item_id TEXT NOT NULL,
                        item_name TEXT NOT NULL,
                        profit_per_14 REAL NOT NULL,
                        tier TEXT NOT NULL,
                        seen_at TEXT NOT NULL,
                        buy_price REAL,
                        sell_price REAL
                    )
                """)
            if "buy_price" not in cols:
                conn.execute("ALTER TABLE ah_sightings ADD COLUMN buy_price REAL")
                conn.execute("ALTER TABLE ah_sightings ADD COLUMN sell_price REAL")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sightings_item ON ah_sightings(item_id, seen_at)")
            # Deduplicate existing rows before adding unique constraint
            conn.execute("""
                DELETE FROM opportunities WHERE id NOT IN (
                    SELECT MAX(id) FROM opportunities GROUP BY type, item_id
                )
            """)
            conn.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_opp_type_item ON opportunities(type, item_id)
            """)

    def save_opportunity(self, opp: Opportunity):
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO opportunities "
                "(type, item_id, item_name, profit, action, details, confidence, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (opp.type, opp.item_id, opp.item_name, opp.profit, opp.action,
                 json.dumps(opp.details), opp.confidence, opp.created_at.isoformat())
            )

    def get_opportunities(self, type_filter: str = None, min_profit: float = 0) -> list[Opportunity]:
        query = (
            "SELECT type, item_id, item_name, profit, action, details, confidence, created_at "
            "FROM opportunities WHERE profit >= ?"
        )
        params: list = [min_profit]
        if type_filter:
            query += " AND type = ?"
            params.append(type_filter)
        query += " ORDER BY profit DESC"
        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            Opportunity(
                type=r[0], item_id=r[1], item_name=r[2], profit=r[3],
                action=r[4], details=json.loads(r[5]), confidence=r[6],
                created_at=datetime.fromisoformat(r[7])
            )
            for r in rows
        ]

    def clear_opportunities_older_than_minutes(self, minutes: int, type_filter: str = None):
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()
        with self._conn() as conn:
            if type_filter:
                conn.execute("DELETE FROM opportunities WHERE created_at < ? AND type = ?", (cutoff, type_filter))
            else:
                conn.execute("DELETE FROM opportunities WHERE created_at < ?", (cutoff,))

    def record_sightings(self, opps: list) -> None:
        now_dt = datetime.now(timezone.utc)
        now = now_dt.isoformat()
        cutoff = (now_dt - timedelta(days=30)).isoformat()
        with self._conn() as conn:
            conn.executemany(
                "INSERT INTO ah_sightings (item_id, item_name, profit_per_14, tier, seen_at, buy_price, sell_price) VALUES (?,?,?,?,?,?,?)",
                [(o.item_id, o.item_name, o.profit, o.details.get("tier", ""), now,
                  o.details.get("bundle_per_unit"), o.details.get("single_price")) for o in opps],
            )
            conn.execute("DELETE FROM ah_sightings WHERE seen_at < ?", (cutoff,))

    def get_top_sightings(self, hours: int = 2) -> list[dict]:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        with self._conn() as conn:
            rows = conn.execute("""
                WITH filtered AS (
                    SELECT * FROM ah_sightings WHERE seen_at >= ?
                )
                SELECT item_id, item_name, tier,
                       COUNT(*) as seen,
                       (SELECT COUNT(DISTINCT seen_at) FROM filtered) as rounds,
                       AVG(profit_per_14) as avg_profit,
                       AVG(buy_price) as avg_buy_price,
                       AVG(sell_price) as avg_sell_price
                FROM filtered
                GROUP BY item_id
                ORDER BY AVG(profit_per_14) * COUNT(*) DESC
            """, (cutoff,)).fetchall()
        if not rows:
            return []
        return [
            {
                "item_id": r[0], "item_name": r[1], "tier": r[2],
                "seen": r[3], "rounds": r[4],
                "avg_profit": r[5],
                "avg_buy_price": r[6], "avg_sell_price": r[7],
            }
            for r in rows
        ]

    def save_price_snapshot(self, item_id: str, price: float, source: str):
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO price_snapshots (item_id, price, source, recorded_at) VALUES (?, ?, ?, ?)",
                (item_id, price, source, datetime.now(timezone.utc).isoformat())
            )

    def get_price_snapshots(self, item_id: str) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT price, source, recorded_at FROM price_snapshots WHERE item_id = ? ORDER BY recorded_at DESC",
                (item_id,)
            ).fetchall()
        return [{"price": r[0], "source": r[1], "recorded_at": r[2]} for r in rows]
