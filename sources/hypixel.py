import aiohttp
import asyncio
from typing import Any

BASE = "https://api.hypixel.net"
MOJANG_BASE = "https://api.minecraftservices.com"
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

    async def get_mayor(self) -> str:
        data = await self._get("/resources/skyblock/election")
        return data.get("mayor", {}).get("name", "")

    @staticmethod
    async def get_uuid(username: str) -> str:
        url = f"{MOJANG_BASE}/minecraft/profile/lookup/bulk/byname"
        async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
            async with session.post(url, json=[username]) as resp:
                data = await resp.json()
        if not data:
            raise ValueError(f"Player '{username}' not found")
        return data[0]["id"]

    async def get_profile(self, uuid: str) -> dict[str, Any]:
        data = await self._get("/skyblock/profiles", {"uuid": uuid})
        profiles = data.get("profiles") or []
        # Use the most recently played profile
        active = max(profiles, key=lambda p: p.get("last_save", 0), default=None)
        if not active:
            raise ValueError("No Skyblock profile found")
        member = active.get("members", {}).get(uuid, {})
        return {
            "profile_name": active.get("cute_name", "Unknown"),
            "bank": active.get("banking", {}).get("balance", 0),
            "purse": member.get("currencies", {}).get("coin_purse", 0),
            "inventory": member.get("inventory", {}).get("inv_contents", {}).get("data", ""),
            "ender_chest": member.get("inventory", {}).get("ender_chest_contents", {}).get("data", ""),
            "backpacks": member.get("inventory", {}).get("backpack_contents", {}),
            "pets": member.get("pets_data", {}).get("pets", []),
        }

