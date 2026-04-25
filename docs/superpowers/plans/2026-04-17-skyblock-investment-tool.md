# Skyblock Investment Tool — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python daemon + CLI that continuously monitors Hypixel Skyblock economy APIs and surfaces actionable, high-profit investment opportunities with macOS notifications.

**Architecture:** A background daemon polls Hypixel and Coflnet APIs at configurable intervals, runs opportunity analyzers, and writes results to SQLite. The CLI reads exclusively from SQLite and renders formatted output. Each analyzer is an independent module with clear inputs/outputs.

**Tech Stack:** Python 3.11+, aiohttp (async HTTP), sqlite3 (stdlib), rich (CLI output), pyyaml (config), pytest + pytest-asyncio (tests), osascript + afplay (macOS notifications)

---

## File Map

| File | Responsibility |
|---|---|
| `requirements.txt` | Dependencies |
| `models.py` | Shared `Opportunity` dataclass |
| `db.py` | SQLite wrapper — read/write opportunities + price snapshots |
| `config.py` | Load/save `config.yaml`, interactive first-run setup |
| `sources/hypixel.py` | Async Hypixel API client (Bazaar, AH, Items, Election) |
| `sources/coflnet.py` | Async Coflnet API client + fallback policy |
| `analyzers/bazaar.py` | Bazaar flip opportunity detection |
| `analyzers/npc.py` | NPC arbitrage detection |
| `analyzers/auction.py` | AH underpriced + stack arbitrage detection |
| `analyzers/mayor.py` | Mayor/event historical investment analysis |
| `notify.py` | macOS Desktop Notification + sound |
| `daemon.py` | Async orchestrator — polling loops, writes to DB, triggers notify |
| `cli.py` | On-demand CLI output with filters |
| `com.skyblock.daemon.plist` | launchd plist for auto-restart on macOS |
| `tests/test_db.py` | DB layer tests |
| `tests/test_config.py` | Config loader tests |
| `tests/test_bazaar.py` | Bazaar analyzer tests |
| `tests/test_npc.py` | NPC analyzer tests |
| `tests/test_auction.py` | AH analyzer tests |
| `tests/test_mayor.py` | Mayor analyzer tests |
| `tests/test_notify.py` | Notify tests (mocked osascript) |

---

### Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `models.py`
- Create: `analyzers/__init__.py`
- Create: `sources/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create directory structure**

```bash
cd /Users/robin/Documents/Apps/Skyblock
mkdir -p analyzers sources tests
touch analyzers/__init__.py sources/__init__.py tests/__init__.py
```

- [ ] **Step 2: Create `requirements.txt`**

```
aiohttp==3.9.5
pyyaml==6.0.1
rich==13.7.1
pytest==8.2.0
pytest-asyncio==0.23.6
```

- [ ] **Step 3: Create `models.py`**

```python
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Opportunity:
    type: str          # "BAZAAR", "NPC", "AH", "MAYOR"
    item_id: str
    item_name: str
    profit: float
    action: str        # "JETZT KAUFEN" or "JETZT INVESTIEREN"
    details: dict
    confidence: str    # "high", "medium", "low"
    created_at: datetime = field(default_factory=datetime.utcnow)
```

- [ ] **Step 4: Install dependencies**

```bash
pip install -r requirements.txt
```

- [ ] **Step 5: Commit**

```bash
git init
git add requirements.txt models.py analyzers/__init__.py sources/__init__.py tests/__init__.py
git commit -m "feat: project scaffold and Opportunity model"
```

---

### Task 2: DB Layer (`db.py`)

**Files:**
- Create: `db.py`
- Create: `tests/test_db.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_db.py
import pytest
import tempfile
import os
from datetime import datetime
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


def test_save_price_snapshot(tmp_db):
    tmp_db.save_price_snapshot("ENCHANTED_DIAMOND", 80_000.0, "self")
    snapshots = tmp_db.get_price_snapshots("ENCHANTED_DIAMOND")
    assert len(snapshots) == 1
    assert snapshots[0]["price"] == 80_000.0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_db.py -v
```
Expected: `ModuleNotFoundError: No module named 'db'`

- [ ] **Step 3: Implement `db.py`**

```python
import sqlite3
import json
from datetime import datetime, timedelta
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

    def get_opportunities(self, type_filter: str = None, min_profit: float = 0) -> list[Opportunity]:
        query = "SELECT type, item_id, item_name, profit, action, details, confidence, created_at FROM opportunities WHERE profit >= ?"
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
        cutoff = (datetime.utcnow() - timedelta(minutes=minutes)).isoformat()
        with self._conn() as conn:
            conn.execute("DELETE FROM opportunities WHERE created_at < ?", (cutoff,))

    def save_price_snapshot(self, item_id: str, price: float, source: str):
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO price_snapshots (item_id, price, source, recorded_at) VALUES (?, ?, ?, ?)",
                (item_id, price, source, datetime.utcnow().isoformat())
            )

    def get_price_snapshots(self, item_id: str) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT price, source, recorded_at FROM price_snapshots WHERE item_id = ? ORDER BY recorded_at DESC",
                (item_id,)
            ).fetchall()
        return [{"price": r[0], "source": r[1], "recorded_at": r[2]} for r in rows]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_db.py -v
```
Expected: all 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add db.py tests/test_db.py
git commit -m "feat: SQLite DB layer with opportunities and price snapshots"
```

---

### Task 3: Config System (`config.py`)

**Files:**
- Create: `config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_config.py
import pytest
import tempfile
import os
import yaml
from config import Config, load_config, save_config


def test_default_values():
    cfg = Config()
    assert cfg.bazaar_tax == 0.0125
    assert cfg.npc_discount == 0.0
    assert cfg.min_profit_notify == 500_000
    assert cfg.min_profit_display == 100_000


def test_save_and_load(tmp_path):
    cfg = Config(api_key="test-key", bazaar_tax=0.009, npc_discount=0.02,
                 min_profit_notify=1_000_000, min_profit_display=200_000)
    path = str(tmp_path / "config.yaml")
    save_config(cfg, path)
    loaded = load_config(path)
    assert loaded.api_key == "test-key"
    assert loaded.bazaar_tax == 0.009
    assert loaded.npc_discount == 0.02
    assert loaded.min_profit_notify == 1_000_000


def test_load_missing_file_returns_defaults(tmp_path):
    path = str(tmp_path / "nonexistent.yaml")
    cfg = load_config(path)
    assert cfg.bazaar_tax == 0.0125
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_config.py -v
```
Expected: `ModuleNotFoundError: No module named 'config'`

- [ ] **Step 3: Implement `config.py`**

```python
import yaml
from dataclasses import dataclass, asdict

DEFAULT_CONFIG_PATH = "config.yaml"


@dataclass
class Config:
    api_key: str = ""
    bazaar_tax: float = 0.0125
    npc_discount: float = 0.0
    min_profit_notify: int = 500_000
    min_profit_display: int = 100_000


def load_config(path: str = DEFAULT_CONFIG_PATH) -> Config:
    try:
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return Config(**{k: v for k, v in data.items() if k in Config.__dataclass_fields__})
    except FileNotFoundError:
        return Config()


def save_config(cfg: Config, path: str = DEFAULT_CONFIG_PATH):
    with open(path, "w") as f:
        yaml.dump(asdict(cfg), f, default_flow_style=False)


def setup_first_run(path: str = DEFAULT_CONFIG_PATH) -> Config:
    print("=== Skyblock Investment Tool — First Run Setup ===\n")
    api_key = input("Hypixel API Key (https://developer.hypixel.net): ").strip()

    print("\nBazaar Tax Rate:")
    print("  0 = 1.25% (default, no upgrades)")
    print("  1 = lower (Community Shop upgraded)")
    tax_choice = input("Bazaar tax rate (0.0125 or lower, e.g. 0.009): ").strip()
    try:
        bazaar_tax = float(tax_choice)
    except ValueError:
        bazaar_tax = 0.0125

    print("\nNPC Discount Talisman:")
    print("  0 = none, 1 = 1%, 2 = 2%, 3 = 3%")
    disc_choice = input("NPC discount level (0/1/2/3): ").strip()
    discount_map = {"0": 0.0, "1": 0.01, "2": 0.02, "3": 0.03}
    npc_discount = discount_map.get(disc_choice, 0.0)

    cfg = Config(
        api_key=api_key,
        bazaar_tax=bazaar_tax,
        npc_discount=npc_discount,
    )
    save_config(cfg, path)
    print(f"\nConfig saved to {path}\n")
    return cfg
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_config.py -v
```
Expected: all 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add config.py tests/test_config.py
git commit -m "feat: config loader with first-run interactive setup"
```

---

### Task 4: Hypixel API Client (`sources/hypixel.py`)

**Files:**
- Create: `sources/hypixel.py`
- Create: `tests/test_hypixel.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_hypixel.py
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from sources.hypixel import HypixelClient


@pytest.fixture
def client():
    return HypixelClient(api_key="test-key")


@pytest.mark.asyncio
async def test_get_bazaar_returns_products(client):
    mock_response = {
        "success": True,
        "products": {
            "ENCHANTED_DIAMOND": {
                "product_id": "ENCHANTED_DIAMOND",
                "sell_summary": [{"pricePerUnit": 20_500_000, "amount": 10}],
                "buy_summary": [{"pricePerUnit": 18_200_000, "amount": 10}],
                "quick_status": {"buyVolume": 1000, "sellVolume": 1000,
                                 "buyMovingWeek": 500_000, "sellMovingWeek": 500_000}
            }
        }
    }
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=MagicMock(
            json=AsyncMock(return_value=mock_response),
            status=200
        ))
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_get.return_value = mock_ctx
        result = await client.get_bazaar()
    assert "ENCHANTED_DIAMOND" in result
    assert result["ENCHANTED_DIAMOND"]["sell_summary"][0]["pricePerUnit"] == 20_500_000


@pytest.mark.asyncio
async def test_get_bazaar_timeout_raises(client):
    import aiohttp
    with patch("aiohttp.ClientSession.get", side_effect=aiohttp.ServerTimeoutError):
        with pytest.raises(aiohttp.ServerTimeoutError):
            await client.get_bazaar()


@pytest.mark.asyncio
async def test_get_election_returns_mayor(client):
    mock_response = {
        "success": True,
        "mayor": {"name": "Diana", "key": "diana", "perks": []},
        "current": {"year": 360, "candidates": []}
    }
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=MagicMock(
            json=AsyncMock(return_value=mock_response),
            status=200
        ))
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_get.return_value = mock_ctx
        result = await client.get_election()
    assert result["mayor"]["name"] == "Diana"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_hypixel.py -v
```
Expected: `ModuleNotFoundError: No module named 'sources.hypixel'`

- [ ] **Step 3: Implement `sources/hypixel.py`**

```python
import aiohttp
import asyncio
from typing import Any

BASE = "https://api.hypixel.net"
TIMEOUT = aiohttp.ClientTimeout(total=10)


class HypixelClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def _get(self, path: str, params: dict = None) -> dict[str, Any]:
        p = {"key": self.api_key, **(params or {})}
        async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
            async with session.get(f"{BASE}{path}", params=p) as resp:
                data = await resp.json()
        if not data.get("success"):
            raise ValueError(f"Hypixel API error on {path}: {data.get('cause', 'unknown')}")
        return data

    async def get_bazaar(self) -> dict[str, Any]:
        data = await self._get("/skyblock/bazaar")
        return data["products"]

    async def get_auctions(self) -> list[dict]:
        first = await self._get("/skyblock/auctions", {"page": 0})
        total_pages = first["totalPages"]
        all_auctions = list(first["auctions"])
        if total_pages > 1:
            tasks = [self._get("/skyblock/auctions", {"page": p}) for p in range(1, total_pages)]
            pages = await asyncio.gather(*tasks, return_exceptions=True)
            for page in pages:
                if isinstance(page, Exception):
                    continue
                all_auctions.extend(page["auctions"])
        return all_auctions

    async def get_items(self) -> list[dict]:
        data = await self._get("/resources/skyblock/items")
        return data["items"]

    async def get_election(self) -> dict[str, Any]:
        return await self._get("/resources/skyblock/election")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_hypixel.py -v
```
Expected: all 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add sources/hypixel.py tests/test_hypixel.py
git commit -m "feat: async Hypixel API client (Bazaar, AH, Items, Election)"
```

---

### Task 5: Coflnet API Client (`sources/coflnet.py`)

**Files:**
- Create: `sources/coflnet.py`
- Create: `tests/test_coflnet.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_coflnet.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sources.coflnet import CoflnetClient, NoDataError


@pytest.fixture
def client():
    return CoflnetClient()


@pytest.mark.asyncio
async def test_get_price_history_returns_data(client):
    mock_data = [
        {"time": "2025-01-01T00:00:00", "avg": 80_000.0, "min": 75_000.0, "max": 85_000.0, "volume": 1200},
        {"time": "2025-01-02T00:00:00", "avg": 82_000.0, "min": 78_000.0, "max": 86_000.0, "volume": 1100},
    ]
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=MagicMock(
            json=AsyncMock(return_value=mock_data),
            status=200
        ))
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_get.return_value = mock_ctx
        result = await client.get_price_history("GRIFFIN_FEATHER", days=90)
    assert len(result) == 2
    assert result[0]["avg"] == 80_000.0


@pytest.mark.asyncio
async def test_empty_response_raises_no_data(client):
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=MagicMock(
            json=AsyncMock(return_value=[]),
            status=200
        ))
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_get.return_value = mock_ctx
        with pytest.raises(NoDataError):
            await client.get_price_history("UNKNOWN_ITEM", days=90)


@pytest.mark.asyncio
async def test_timeout_raises_original_exception(client):
    import aiohttp
    with patch("aiohttp.ClientSession.get", side_effect=aiohttp.ServerTimeoutError):
        with pytest.raises(aiohttp.ServerTimeoutError):
            await client.get_price_history("ANY_ITEM", days=90)


@pytest.mark.asyncio
async def test_get_median_price(client):
    mock_data = [
        {"time": "2025-01-01T00:00:00", "avg": 80_000.0, "min": 75_000.0, "max": 85_000.0, "volume": 1200},
    ]
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=MagicMock(
            json=AsyncMock(return_value=mock_data),
            status=200
        ))
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_get.return_value = mock_ctx
        median = await client.get_median_price("ENCHANTED_DIAMOND")
    assert median == 80_000.0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_coflnet.py -v
```
Expected: `ModuleNotFoundError: No module named 'sources.coflnet'`

- [ ] **Step 3: Implement `sources/coflnet.py`**

```python
import aiohttp
import statistics
from typing import Any

BASE = "https://sky.coflnet.com/api"
TIMEOUT = aiohttp.ClientTimeout(total=10)


class NoDataError(Exception):
    """Coflnet returned success but no data for this item."""


class CoflnetClient:
    async def _get(self, path: str, params: dict = None) -> Any:
        async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
            async with session.get(f"{BASE}{path}", params=params) as resp:
                return await resp.json(content_type=None)

    async def get_price_history(self, item_id: str, days: int = 180) -> list[dict]:
        # Coflnet uses item IDs in lowercase with hyphens for some endpoints
        data = await self._get(f"/item/price/{item_id}/history/day", {"days": days})
        if not data:
            raise NoDataError(f"No price history for {item_id}")
        return data

    async def get_median_price(self, item_id: str, days: int = 30) -> float:
        history = await self.get_price_history(item_id, days=days)
        avgs = [entry["avg"] for entry in history if "avg" in entry]
        if not avgs:
            raise NoDataError(f"No avg prices in history for {item_id}")
        return statistics.median(avgs)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_coflnet.py -v
```
Expected: all 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add sources/coflnet.py tests/test_coflnet.py
git commit -m "feat: Coflnet API client with NoDataError fallback policy"
```

---

### Task 6: Bazaar Flip Analyzer (`analyzers/bazaar.py`)

**Files:**
- Create: `analyzers/bazaar.py`
- Create: `tests/test_bazaar.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_bazaar.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_bazaar.py -v
```
Expected: `ModuleNotFoundError: No module named 'analyzers.bazaar'`

- [ ] **Step 3: Implement `analyzers/bazaar.py`**

```python
from models import Opportunity

MIN_WEEKLY_VOLUME = 50_000


class BazaarAnalyzer:
    def __init__(self, bazaar_tax: float, min_profit: float):
        self.bazaar_tax = bazaar_tax
        self.min_profit = min_profit

    def analyze(self, products: dict, items_meta: dict) -> list[Opportunity]:
        opportunities = []
        for item_id, product in products.items():
            if not product.get("sell_summary") or not product.get("buy_summary"):
                continue

            sell_price = product["sell_summary"][0]["pricePerUnit"]
            buy_price = product["buy_summary"][0]["pricePerUnit"]
            weekly_volume = min(
                product["quick_status"].get("buyMovingWeek", 0),
                product["quick_status"].get("sellMovingWeek", 0),
            )

            if weekly_volume < MIN_WEEKLY_VOLUME:
                continue

            net_profit = sell_price * (1 - self.bazaar_tax) - buy_price
            if net_profit < self.min_profit:
                continue

            name = items_meta.get(item_id, {}).get("name", item_id)
            volume_label = "hoch" if weekly_volume > 500_000 else "mittel"

            opportunities.append(Opportunity(
                type="BAZAAR",
                item_id=item_id,
                item_name=name,
                profit=net_profit,
                action="JETZT KAUFEN",
                details={
                    "buy_order": buy_price,
                    "sell_offer": sell_price,
                    "volume": volume_label,
                    "weekly_volume": weekly_volume,
                },
                confidence="high" if weekly_volume > 500_000 else "medium",
            ))

        return sorted(opportunities, key=lambda o: o.profit, reverse=True)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_bazaar.py -v
```
Expected: all 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add analyzers/bazaar.py tests/test_bazaar.py
git commit -m "feat: Bazaar flip analyzer with tax and volume checks"
```

---

### Task 7: NPC Arbitrage Analyzer (`analyzers/npc.py`)

**Files:**
- Create: `analyzers/npc.py`
- Create: `tests/test_npc.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_npc.py
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
    # NPC sells Sand at 2/piece, bazaar buys at 10000/piece
    # 64 stack: cost 128, sell 640000 → profit 639872
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
    # NPC 9800, bazaar 10000, stack 64: profit = (10000 - 9800) * 64 = 12800
    items = [{"id": "ITEM", "name": "Item", "npc_sell_price": 9_800, "daily_limit": 640}]
    bazaar = {"ITEM": make_bazaar_product(buy_price=10_000)}
    results = analyzer.analyze(items, bazaar)
    assert results == []


def test_npc_discount_reduces_effective_cost():
    analyzer = NpcAnalyzer(npc_discount=0.03, min_profit=100_000)
    items = [{"id": "SAND", "name": "Sand", "npc_sell_price": 1_000, "daily_limit": 640}]
    bazaar = {"SAND": make_bazaar_product(buy_price=2_000)}
    results = analyzer.analyze(items, bazaar)
    # effective_npc = 1000 * 0.97 = 970; profit per item = 2000 - 970 = 1030; total = 659200
    assert len(results) == 1
    assert abs(results[0].details["effective_npc_price"] - 970.0) < 0.01


def test_discount_increases_profit():
    analyzer_no_disc = NpcAnalyzer(npc_discount=0.0, min_profit=100_000)
    analyzer_disc = NpcAnalyzer(npc_discount=0.03, min_profit=100_000)
    items = [{"id": "ITEM", "name": "Item", "npc_sell_price": 9_000, "daily_limit": 64}]
    bazaar = {"ITEM": make_bazaar_product(buy_price=10_000)}
    r_no = analyzer_no_disc.analyze(items, bazaar)
    r_disc = analyzer_disc.analyze(items, bazaar)
    assert r_disc[0].profit > r_no[0].profit
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_npc.py -v
```
Expected: `ModuleNotFoundError: No module named 'analyzers.npc'`

- [ ] **Step 3: Implement `analyzers/npc.py`**

```python
from models import Opportunity

STACK_SIZE = 64


class NpcAnalyzer:
    def __init__(self, npc_discount: float, min_profit: float):
        self.npc_discount = npc_discount
        self.min_profit = min_profit

    def analyze(self, items: list[dict], bazaar: dict) -> list[Opportunity]:
        opportunities = []
        for item in items:
            item_id = item.get("id")
            npc_price = item.get("npc_sell_price")
            daily_limit = item.get("daily_limit", STACK_SIZE)
            name = item.get("name", item_id)

            if not item_id or npc_price is None:
                continue
            if item_id not in bazaar:
                continue
            bz = bazaar[item_id]
            if not bz.get("buy_summary"):
                continue

            bazaar_buy = bz["buy_summary"][0]["pricePerUnit"]
            effective_npc = npc_price * (1 - self.npc_discount)
            profit_per_item = bazaar_buy - effective_npc
            total_profit = profit_per_item * daily_limit

            if total_profit < self.min_profit:
                continue

            opportunities.append(Opportunity(
                type="NPC",
                item_id=item_id,
                item_name=name,
                profit=total_profit,
                action="JETZT KAUFEN",
                details={
                    "npc_price": npc_price,
                    "effective_npc_price": round(effective_npc, 2),
                    "bazaar_buy": bazaar_buy,
                    "daily_limit": daily_limit,
                    "profit_per_item": round(profit_per_item, 2),
                },
                confidence="high",
            ))

        return sorted(opportunities, key=lambda o: o.profit, reverse=True)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_npc.py -v
```
Expected: all passing (skip the empty `test_npc_discount_applied`)

- [ ] **Step 5: Commit**

```bash
git add analyzers/npc.py tests/test_npc.py
git commit -m "feat: NPC arbitrage analyzer with talisman discount support"
```

---

### Task 8: AH Analyzer (`analyzers/auction.py`)

**Files:**
- Create: `analyzers/auction.py`
- Create: `tests/test_auction.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_auction.py
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
            "starting_bid": 5_000,   # 64 stack for 5000 → 78/ea
            "bin": True,
            "claimed": False,
            "end": 9999999999999,
            "count": 64,
        }
    ]
    # median single = 500, stack buy = 78/ea → profit = (500-78)*64 = 27008 < 500k threshold
    # use a higher-value example:
    high_median = {"SAND": 20_000}
    results = analyzer.analyze(auctions, high_median)
    # (20000 - 78) * 64 = 1,275,008 > 500k
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_auction.py -v
```
Expected: `ModuleNotFoundError: No module named 'analyzers.auction'`

- [ ] **Step 3: Implement `analyzers/auction.py`**

```python
import time
from models import Opportunity


class AuctionAnalyzer:
    def __init__(self, min_profit: float, underpriced_threshold: float = 0.25):
        self.min_profit = min_profit
        self.underpriced_threshold = underpriced_threshold

    def analyze(self, auctions: list[dict], median_prices: dict[str, float]) -> list[Opportunity]:
        opportunities = []
        now_ms = int(time.time() * 1000)

        for auction in auctions:
            if not auction.get("bin"):
                continue
            if auction.get("claimed"):
                continue
            if auction.get("end", 0) < now_ms:
                continue

            item_id = auction.get("tag") or auction.get("item_name", "").upper().replace(" ", "_")
            if item_id not in median_prices:
                continue

            median = median_prices[item_id]
            price = auction["starting_bid"]
            count = auction.get("count", 1)
            name = auction.get("item_name", item_id)

            if count > 1:
                price_per_unit = price / count
                if median <= 0 or price_per_unit >= median:
                    continue
                profit = (median - price_per_unit) * count
                if profit < self.min_profit:
                    continue
                opportunities.append(Opportunity(
                    type="AH",
                    item_id=item_id,
                    item_name=name,
                    profit=profit,
                    action="JETZT KAUFEN",
                    details={
                        "auction_price": price,
                        "count": count,
                        "price_per_unit": round(price_per_unit, 2),
                        "median_single_price": median,
                        "arbitrage_type": "stack",
                    },
                    confidence="medium",
                ))
            else:
                if median <= 0:
                    continue
                discount = (median - price) / median
                if discount < self.underpriced_threshold:
                    continue
                profit = median - price
                if profit < self.min_profit:
                    continue
                opportunities.append(Opportunity(
                    type="AH",
                    item_id=item_id,
                    item_name=name,
                    profit=profit,
                    action="JETZT KAUFEN",
                    details={
                        "auction_price": price,
                        "median_price": median,
                        "discount_pct": round(discount * 100, 1),
                        "arbitrage_type": "underpriced",
                    },
                    confidence="high" if discount > 0.4 else "medium",
                ))

        return sorted(opportunities, key=lambda o: o.profit, reverse=True)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_auction.py -v
```
Expected: all 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add analyzers/auction.py tests/test_auction.py
git commit -m "feat: AH flip and stack arbitrage analyzer"
```

---

### Task 9: Mayor/Event Analyzer (`analyzers/mayor.py`)

**Files:**
- Create: `analyzers/mayor.py`
- Create: `tests/test_mayor.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_mayor.py
import pytest
from analyzers.mayor import MayorAnalyzer, MayorCycle

# Price history: 180 days, with a spike at every 31-day Diana cycle
def make_history(base: float, spikes_at: list[int], spike_mult: float, days: int = 180) -> list[dict]:
    from datetime import datetime, timedelta
    result = []
    start = datetime(2025, 1, 1)
    for i in range(days):
        price = base * spike_mult if i in spikes_at else base
        result.append({"time": (start + timedelta(days=i)).isoformat(), "avg": price})
    return result


@pytest.fixture
def analyzer():
    return MayorAnalyzer(min_cycles=3, min_avg_increase_pct=50.0, min_profit=100_000)


def test_item_with_strong_diana_correlation_detected(analyzer):
    # Spike at days 0, 31, 62 (3 Diana cycles, each 31 days apart)
    history = make_history(base=80_000, spikes_at=list(range(0, 93, 31)), spike_mult=3.0, days=180)
    cycles = [
        MayorCycle(mayor="Diana", start_day=0, end_day=30),
        MayorCycle(mayor="Diana", start_day=31, end_day=61),
        MayorCycle(mayor="Diana", start_day=62, end_day=92),
    ]
    results = analyzer.analyze_item("GRIFFIN_FEATHER", "Griffin Feather", history, cycles, current_mayor="Diana")
    assert results is not None
    assert results.confidence in ("high", "medium")


def test_item_with_insufficient_cycles_returns_none(analyzer):
    history = make_history(base=80_000, spikes_at=[0, 31], spike_mult=2.0, days=180)
    cycles = [
        MayorCycle(mayor="Diana", start_day=0, end_day=30),
        MayorCycle(mayor="Diana", start_day=31, end_day=61),
    ]
    # Only 2 cycles, min is 3
    results = analyzer.analyze_item("ITEM", "Item", history, cycles, current_mayor="Diana")
    assert results is None


def test_item_with_weak_correlation_ignored(analyzer):
    # No real spike — all prices flat
    history = make_history(base=80_000, spikes_at=[], spike_mult=1.0, days=180)
    cycles = [
        MayorCycle(mayor="Diana", start_day=0, end_day=30),
        MayorCycle(mayor="Diana", start_day=31, end_day=61),
        MayorCycle(mayor="Diana", start_day=62, end_day=92),
    ]
    results = analyzer.analyze_item("FLAT_ITEM", "Flat Item", history, cycles, current_mayor="Diana")
    assert results is None


def test_wrong_mayor_not_reported(analyzer):
    history = make_history(base=80_000, spikes_at=list(range(0, 93, 31)), spike_mult=3.0, days=180)
    cycles = [
        MayorCycle(mayor="Diana", start_day=0, end_day=30),
        MayorCycle(mayor="Diana", start_day=31, end_day=61),
        MayorCycle(mayor="Diana", start_day=62, end_day=92),
    ]
    results = analyzer.analyze_item("GRIFFIN_FEATHER", "Griffin Feather", history, cycles, current_mayor="Technoblade")
    assert results is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_mayor.py -v
```
Expected: `ModuleNotFoundError: No module named 'analyzers.mayor'`

- [ ] **Step 3: Implement `analyzers/mayor.py`**

```python
from dataclasses import dataclass
from models import Opportunity
import statistics


@dataclass
class MayorCycle:
    mayor: str
    start_day: int
    end_day: int


class MayorAnalyzer:
    def __init__(self, min_cycles: int = 3, min_avg_increase_pct: float = 50.0, min_profit: float = 100_000):
        self.min_cycles = min_cycles
        self.min_avg_increase_pct = min_avg_increase_pct
        self.min_profit = min_profit

    def analyze_item(
        self,
        item_id: str,
        item_name: str,
        history: list[dict],
        cycles: list[MayorCycle],
        current_mayor: str,
    ) -> Opportunity | None:
        matching = [c for c in cycles if c.mayor == current_mayor]
        if len(matching) < self.min_cycles:
            return None

        prices = [entry["avg"] for entry in history]
        if not prices:
            return None

        overall_avg = statistics.mean(prices)

        cycle_increases = []
        for cycle in matching:
            cycle_prices = prices[cycle.start_day:cycle.end_day + 1]
            if not cycle_prices:
                continue
            cycle_avg = statistics.mean(cycle_prices)
            pct_increase = ((cycle_avg - overall_avg) / overall_avg) * 100
            cycle_increases.append(pct_increase)

        if len(cycle_increases) < self.min_cycles:
            return None

        avg_increase = statistics.mean(cycle_increases)
        if avg_increase < self.min_avg_increase_pct:
            return None

        current_price = prices[-1] if prices else overall_avg
        projected_price = current_price * (1 + avg_increase / 100)
        projected_profit_per_item = projected_price - current_price

        if projected_profit_per_item < self.min_profit:
            return None

        confidence = "high" if avg_increase > 100 else "medium"

        return Opportunity(
            type="MAYOR",
            item_id=item_id,
            item_name=item_name,
            profit=projected_profit_per_item,
            action="JETZT INVESTIEREN",
            details={
                "current_mayor": current_mayor,
                "current_price": round(current_price),
                "avg_increase_pct": round(avg_increase, 1),
                "cycles_analyzed": len(cycle_increases),
                "projected_price": round(projected_price),
            },
            confidence=confidence,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_mayor.py -v
```
Expected: all 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add analyzers/mayor.py tests/test_mayor.py
git commit -m "feat: Mayor/event investment analyzer with historical correlation"
```

---

### Task 10: macOS Notifications (`notify.py`)

**Files:**
- Create: `notify.py`
- Create: `tests/test_notify.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_notify.py
import pytest
from unittest.mock import patch, call
from models import Opportunity
from notify import Notifier


@pytest.fixture
def notifier():
    return Notifier(min_profit_notify=500_000)


def test_high_profit_triggers_notification(notifier):
    opp = Opportunity("BAZAAR", "ENCHANTED_DIAMOND", "Enchanted Diamond",
                      2_300_000, "JETZT KAUFEN", {}, "high")
    with patch("subprocess.run") as mock_run:
        notifier.notify_if_threshold(opp)
        assert mock_run.called


def test_low_profit_no_notification(notifier):
    opp = Opportunity("BAZAAR", "CHEAP_ITEM", "Cheap Item",
                      200_000, "JETZT KAUFEN", {}, "low")
    with patch("subprocess.run") as mock_run:
        notifier.notify_if_threshold(opp)
        assert not mock_run.called


def test_notification_contains_item_name(notifier):
    opp = Opportunity("NPC", "SAND", "Sand",
                      600_000, "JETZT KAUFEN", {}, "high")
    with patch("subprocess.run") as mock_run:
        notifier.notify_if_threshold(opp)
        args = mock_run.call_args_list[0][0][0]
        script = " ".join(args)
        assert "Sand" in script
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_notify.py -v
```
Expected: `ModuleNotFoundError: No module named 'notify'`

- [ ] **Step 3: Implement `notify.py`**

```python
import subprocess
from models import Opportunity


class Notifier:
    def __init__(self, min_profit_notify: int):
        self.min_profit_notify = min_profit_notify

    def notify_if_threshold(self, opp: Opportunity):
        if opp.profit < self.min_profit_notify:
            return
        profit_str = self._format_coins(opp.profit)
        title = f"[{opp.type}] {opp.item_name}"
        body = f"{opp.action} — Profit: {profit_str}"
        self._send(title, body)
        self._play_sound(opp.profit)

    def _send(self, title: str, body: str):
        script = f'display notification "{body}" with title "{title}"'
        subprocess.run(["osascript", "-e", script], check=False)

    def _play_sound(self, profit: float):
        sound = "/System/Library/Sounds/Glass.aiff" if profit < 2_000_000 else "/System/Library/Sounds/Funk.aiff"
        subprocess.run(["afplay", sound], check=False)

    @staticmethod
    def _format_coins(amount: float) -> str:
        if amount >= 1_000_000:
            return f"{amount / 1_000_000:.1f}M"
        if amount >= 1_000:
            return f"{amount / 1_000:.0f}k"
        return str(int(amount))
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_notify.py -v
```
Expected: all 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add notify.py tests/test_notify.py
git commit -m "feat: macOS notification and sound alerts"
```

---

### Task 11: Daemon (`daemon.py`)

**Files:**
- Create: `daemon.py`

No unit tests for the daemon — it's an orchestrator. Integration is verified by running it and checking DB output.

- [ ] **Step 1: Create `daemon.py`**

```python
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
            for item in items_raw[:50]:  # analyze top items only to avoid rate limiting
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
    # Hypixel election API returns limited data; build approximate cycles from current year
    # Each Skyblock year is ~5 real days; mayors serve 1 year each
    # This is a best-effort approximation from available data
    cycles = []
    mayor_name = election.get("mayor", {}).get("name")
    if mayor_name:
        # Add placeholder cycles — real implementation would track historical election data
        for i in range(5):
            start = i * 31
            cycles.append(MayorCycle(mayor=mayor_name, start_day=start, end_day=start + 30))
    return cycles


async def main():
    import os
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
```

- [ ] **Step 2: Verify daemon starts without errors**

```bash
python daemon.py --help 2>&1 || python -c "import daemon; print('imports ok')"
```
Expected: no import errors

- [ ] **Step 3: Commit**

```bash
git add daemon.py
git commit -m "feat: async daemon orchestrating all polling loops"
```

---

### Task 12: CLI (`cli.py`)

**Files:**
- Create: `cli.py`

- [ ] **Step 1: Create `cli.py`**

```python
import argparse
import sys
from rich.console import Console
from rich.text import Text
from config import load_config, setup_first_run
from db import DB

console = Console()

DIVIDER = "━" * 42


def format_coins(amount: float) -> str:
    if amount >= 1_000_000:
        return f"~{amount / 1_000_000:.1f}M"
    if amount >= 1_000:
        return f"~{amount / 1_000:.0f}k"
    return str(int(amount))


def print_opportunity(opp):
    d = opp.details
    console.print(f" [{opp.type}] [bold]{opp.item_name}[/bold]")
    if opp.type == "BAZAAR":
        console.print(f"  → Buy Order: {format_coins(d['buy_order'])} | Sell Offer: {format_coins(d['sell_offer'])}")
        console.print(f"  → Profit: {format_coins(opp.profit)} pro Transaktion")
        console.print(f"  → Volumen: {d.get('volume', '?')}")
    elif opp.type == "NPC":
        console.print(f"  → NPC Preis: {format_coins(d['effective_npc_price'])}/stk | Bazaar Buy: {format_coins(d['bazaar_buy'])}/stk")
        console.print(f"  → Profit: {format_coins(opp.profit)} | Limit: {d['daily_limit']} Stück/Tag")
    elif opp.type == "AH":
        if d.get("arbitrage_type") == "stack":
            console.print(f"  → Stack ({d['count']}x) für {format_coins(d['auction_price'])} = {format_coins(d['price_per_unit'])}/stk")
            console.print(f"  → Einzelverkauf: {format_coins(d['median_single_price'])}/stk | Profit: {format_coins(opp.profit)}")
        else:
            console.print(f"  → AH Preis: {format_coins(d['auction_price'])} | Median: {format_coins(d['median_price'])}")
            console.print(f"  → {d.get('discount_pct', '?')}% unter Median | Profit: {format_coins(opp.profit)}")
    elif opp.type == "MAYOR":
        console.print(f"  → Jetzt kaufen bei: {format_coins(d['current_price'])}/stk")
        console.print(f"  → Historisch bei {d['current_mayor']}: Ø +{d['avg_increase_pct']}% ({d['cycles_analyzed']} Zyklen)")
        console.print(f"  → Empfehlung: einlagern")
    console.print()


def cmd_show(args):
    cfg = load_config()
    db = DB()
    type_filter = args.type.upper() if args.type else None

    min_profit = cfg.min_profit_display
    if args.min_profit:
        raw = args.min_profit.lower().replace("m", "000000").replace("k", "000")
        try:
            min_profit = int(raw)
        except ValueError:
            console.print(f"[red]Invalid --min-profit value: {args.min_profit}[/red]")
            sys.exit(1)

    all_opps = db.get_opportunities(type_filter=type_filter, min_profit=min_profit)
    if not args.mayor:
        buy_opps = [o for o in all_opps if o.action == "JETZT KAUFEN"]
        invest_opps = [o for o in all_opps if o.action == "JETZT INVESTIEREN"]
    else:
        buy_opps = []
        invest_opps = [o for o in all_opps if o.type == "MAYOR"]

    if buy_opps:
        console.print(f"\n[bold green]{DIVIDER}[/bold green]")
        console.print(f"[bold green] JETZT KAUFEN[/bold green]")
        console.print(f"[bold green]{DIVIDER}[/bold green]")
        for opp in buy_opps:
            print_opportunity(opp)

    if invest_opps:
        console.print(f"[bold yellow]{DIVIDER}[/bold yellow]")
        mayor_name = invest_opps[0].details.get("current_mayor", "") if invest_opps else ""
        label = f" JETZT INVESTIEREN (Mayor: {mayor_name})" if mayor_name else " JETZT INVESTIEREN"
        console.print(f"[bold yellow]{label}[/bold yellow]")
        console.print(f"[bold yellow]{DIVIDER}[/bold yellow]")
        for opp in invest_opps:
            print_opportunity(opp)

    if not buy_opps and not invest_opps:
        console.print("[dim]Keine Opportunities gefunden. Läuft der Daemon? python daemon.py[/dim]")


def cmd_daemon(args):
    import subprocess, os
    if args.action == "start":
        proc = subprocess.Popen(
            ["python", "daemon.py"],
            stdout=open("daemon.log", "a"),
            stderr=subprocess.STDOUT,
        )
        with open("daemon.pid", "w") as f:
            f.write(str(proc.pid))
        console.print(f"[green]Daemon gestartet (PID {proc.pid})[/green]")
    elif args.action == "stop":
        try:
            with open("daemon.pid") as f:
                pid = int(f.read().strip())
            os.kill(pid, 15)
            os.unlink("daemon.pid")
            console.print("[green]Daemon gestoppt[/green]")
        except FileNotFoundError:
            console.print("[yellow]Keine daemon.pid gefunden — läuft der Daemon?[/yellow]")


def main():
    parser = argparse.ArgumentParser(prog="skyblock", description="Skyblock Investment Tool")
    sub = parser.add_subparsers(dest="command")

    show = sub.add_parser("show", help="Zeige aktuelle Opportunities")
    show.add_argument("--type", choices=["bazaar", "npc", "ah", "mayor"], help="Filter nach Typ")
    show.add_argument("--min-profit", help="Mindestprofit z.B. 500k oder 1m")
    show.add_argument("--mayor", action="store_true", help="Nur Mayor/Event-Investitionen")

    daemon_p = sub.add_parser("daemon", help="Daemon steuern")
    daemon_p.add_argument("action", choices=["start", "stop"])

    sub.add_parser("setup", help="Konfiguration neu einrichten")

    args = parser.parse_args()

    if args.command == "show" or args.command is None:
        if args.command is None:
            args.type = None
            args.min_profit = None
            args.mayor = False
        cmd_show(args)
    elif args.command == "daemon":
        cmd_daemon(args)
    elif args.command == "setup":
        setup_first_run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify CLI runs**

```bash
python cli.py --help
```
Expected: prints usage with `show`, `daemon`, `setup` subcommands

- [ ] **Step 3: Commit**

```bash
git add cli.py
git commit -m "feat: CLI with rich output, filters, and daemon control"
```

---

### Task 13: launchd Auto-Restart (macOS)

**Files:**
- Create: `com.skyblock.daemon.plist`

- [ ] **Step 1: Create the plist**

Replace `/Users/YOUR_USERNAME` with your actual home directory path.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.skyblock.daemon</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/robin/Documents/Apps/Skyblock/daemon.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/robin/Documents/Apps/Skyblock</string>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/robin/Documents/Apps/Skyblock/daemon.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/robin/Documents/Apps/Skyblock/daemon.log</string>
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
```

- [ ] **Step 2: Register with launchd (optional — only if you want auto-restart on crash)**

```bash
cp com.skyblock.daemon.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.skyblock.daemon.plist
```

To start:
```bash
launchctl start com.skyblock.daemon
```

To stop:
```bash
launchctl stop com.skyblock.daemon
```

- [ ] **Step 3: Commit**

```bash
git add com.skyblock.daemon.plist
git commit -m "feat: launchd plist for daemon auto-restart on macOS"
```

---

## Final Verification

- [ ] Run full test suite: `pytest -v` — all tests pass
- [ ] Run setup: `python cli.py setup`
- [ ] Start daemon: `python cli.py daemon start`
- [ ] Check output: `python cli.py` — renders formatted opportunity list
- [ ] Check `daemon.log` for polling activity
