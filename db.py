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

    def save_opportunity(self, opp: Opportunity):
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO opportunities (type, item_id, item_name, profit, action, details, confidence, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (opp.type, opp.item_id, opp.item_name, opp.profit, opp.action,
                 json.dumps(opp.details), opp.confidence, opp.created_at.isoformat())
            )

    def get_opportunities(self, type_filter: str = None, min_profit: float = 0) -> list:
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

    def clear_opportunities_older_than_minutes(self, minutes: int):
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()
        with self._conn() as conn:
            conn.execute("DELETE FROM opportunities WHERE created_at < ?", (cutoff,))

    def save_price_snapshot(self, item_id: str, price: float, source: str):
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO price_snapshots (item_id, price, source, recorded_at) VALUES (?, ?, ?, ?)",
                (item_id, price, source, datetime.now(timezone.utc).isoformat())
            )

    def get_price_snapshots(self, item_id: str) -> list:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT price, source, recorded_at FROM price_snapshots WHERE item_id = ? ORDER BY recorded_at DESC",
                (item_id,)
            ).fetchall()
        return [{"price": r[0], "source": r[1], "recorded_at": r[2]} for r in rows]
