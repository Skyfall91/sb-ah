"""Fetch average LBIN prices from Moulberry's community API."""
from __future__ import annotations
import json
import os
import ssl
import time
import urllib.request

import certifi

_SSL_CTX = ssl.create_default_context(cafile=certifi.where())

LBIN_URL = "https://moulberry.codes/auction_averages_lbin/1day.json"
CACHE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".moulberry_lbin.json")
CACHE_TTL = 3600  # 1 hour


def get_avg_lbin() -> dict[str, float]:
    """Return {skyblock_id: avg_lbin_price} for all items. Cached 1h."""
    if os.path.exists(CACHE_PATH):
        if time.time() - os.path.getmtime(CACHE_PATH) < CACHE_TTL:
            try:
                with open(CACHE_PATH) as f:
                    return json.load(f)
            except Exception:
                pass
    try:
        req = urllib.request.Request(LBIN_URL, headers={"User-Agent": "SkyblockTool/1.0"})
        with urllib.request.urlopen(req, timeout=10, context=_SSL_CTX) as r:
            data = json.loads(r.read())
        if isinstance(data, dict):
            with open(CACHE_PATH, "w") as f:
                json.dump(data, f)
            return data
    except Exception:
        pass
    return {}
