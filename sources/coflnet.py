import aiohttp
import statistics
from typing import Any

BASE = "https://sky.coflnet.com/api"
TIMEOUT = aiohttp.ClientTimeout(total=10)


class NoDataError(Exception):
    """Coflnet returned success but no data for this item."""


class CoflnetClient:
    async def _get(self, path: str, params: dict | None = None) -> Any:
        async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
            async with session.get(f"{BASE}{path}", params=params) as resp:
                return await resp.json(content_type=None)

    async def get_price_history(self, item_id: str, days: int = 180) -> list[dict]:
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
