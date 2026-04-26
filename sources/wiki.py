"""Crawl the Hypixel Skyblock wiki and save chunks for RAG."""
from __future__ import annotations
import json
import os
import re
import ssl
import time
import urllib.request
import urllib.parse
from typing import Iterator

import certifi

_SSL_CTX = ssl.create_default_context(cafile=certifi.where())

WIKI_API = "https://hypixelskyblock.minecraft.wiki/api.php"
CACHE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "wiki_chunks.json")

# Categories to crawl — covers items, mechanics, and economy-relevant pages
CRAWL_CATEGORIES = [
    "Items",
    "Weapons",
    "Armor",
    "Accessories",
    "Pets",
    "Enchantments",
    "Mayor",
    "Dungeons",
    "Skills",
]

# Pages with no category membership but important for the advisor
EXTRA_PAGES = ["Bazaar", "Auction House"]

MAX_PAGES_PER_CATEGORY = 150
CHUNK_SIZE = 600  # words per chunk
CHUNK_OVERLAP = 60


def _api_get(params: dict) -> dict:
    params["format"] = "json"
    url = WIKI_API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "sb-ah-flipper/1.0"})
    with urllib.request.urlopen(req, timeout=15, context=_SSL_CTX) as r:
        return json.loads(r.read())


def _pages_in_category(category: str) -> Iterator[str]:
    cmcontinue = None
    seen = 0
    while seen < MAX_PAGES_PER_CATEGORY:
        p: dict = {"action": "query", "list": "categorymembers",
                   "cmtitle": f"Category:{category}", "cmlimit": 50,
                   "cmtype": "page"}
        if cmcontinue:
            p["cmcontinue"] = cmcontinue
        data = _api_get(p)
        for m in data["query"]["categorymembers"]:
            yield m["title"]
            seen += 1
        if "continue" not in data:
            break
        cmcontinue = data["continue"]["cmcontinue"]


def _fetch_page_text(title: str) -> str:
    data = _api_get({"action": "query", "titles": title,
                     "prop": "extracts", "explaintext": True, "exsectionformat": "plain"})
    pages = data["query"]["pages"]
    page = next(iter(pages.values()))
    return page.get("extract", "")


def _chunk_text(title: str, text: str) -> list[dict]:
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk_words = words[i:i + CHUNK_SIZE]
        chunks.append({
            "title": title,
            "text": " ".join(chunk_words),
            "chunk_index": len(chunks),
        })
        i += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


def crawl(verbose: bool = True) -> list[dict]:
    all_chunks: list[dict] = []
    seen_titles: set[str] = set()

    for category in CRAWL_CATEGORIES:
        if verbose:
            print(f"  Crawling category: {category}")
        try:
            titles = list(_pages_in_category(category))
        except Exception as e:
            print(f"  [warn] Could not fetch category {category}: {e}")
            continue

        for title in titles:
            if title in seen_titles:
                continue
            seen_titles.add(title)
            try:
                text = _fetch_page_text(title)
                if len(text.split()) < 30:
                    continue
                chunks = _chunk_text(title, text)
                all_chunks.extend(chunks)
                time.sleep(0.05)  # be polite to the wiki server
            except Exception as e:
                print(f"  [warn] Could not fetch '{title}': {e}")

        if verbose:
            print(f"    {len(seen_titles)} pages so far, {len(all_chunks)} chunks")

    for title in EXTRA_PAGES:
        if title in seen_titles:
            continue
        seen_titles.add(title)
        try:
            text = _fetch_page_text(title)
            if len(text.split()) >= 30:
                all_chunks.extend(_chunk_text(title, text))
        except Exception as e:
            print(f"  [warn] Could not fetch '{title}': {e}")

    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w") as f:
        json.dump(all_chunks, f)

    if verbose:
        print(f"\nSaved {len(all_chunks)} chunks from {len(seen_titles)} pages → {CACHE_PATH}")
    return all_chunks


def load_chunks() -> list[dict]:
    if not os.path.exists(CACHE_PATH):
        raise FileNotFoundError("Wiki not crawled yet. Run: python3 cli.py wiki update")
    with open(CACHE_PATH) as f:
        return json.load(f)


def is_stale(max_age_days: int = 3) -> bool:
    """Returns True if the wiki cache is missing or older than max_age_days."""
    if not os.path.exists(CACHE_PATH):
        return True
    age_seconds = time.time() - os.path.getmtime(CACHE_PATH)
    return age_seconds > max_age_days * 86400
