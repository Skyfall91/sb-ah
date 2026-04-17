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
