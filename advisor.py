"""AI advisor: combines player wealth, current opportunities, wiki RAG, and core mechanics."""
from __future__ import annotations
import asyncio
import os
from openai import OpenAI

from config import Config
from db import DB
from sources.hypixel import HypixelClient
from sources import rag
from utils.formatting import format_coins

CORE_MECHANICS_PATH = os.path.join(os.path.dirname(__file__), "data", "core_mechanics.md")
ADVISOR_MODEL = "qwen3-8b"


def _load_core_mechanics() -> str:
    with open(CORE_MECHANICS_PATH) as f:
        return f.read()


async def _fetch_wealth(cfg: Config, full: bool) -> dict:
    from utils.nbt import decode_auction_item

    hypixel = HypixelClient(api_key=cfg.api_key)
    uuid = await HypixelClient.get_uuid(cfg.minecraft_username)
    profile = await hypixel.get_profile(uuid)

    result = {
        "profile_name": profile["profile_name"],
        "bank": profile["bank"],
        "purse": profile["purse"],
        "liquid": profile["bank"] + profile["purse"],
    }

    if full:
        bazaar = await hypixel.get_bazaar()
        lbin_path = os.path.join(os.path.dirname(__file__), ".moulberry_lbin.json")
        avg_lbin: dict = {}
        if os.path.exists(lbin_path):
            import json
            with open(lbin_path) as f:
                avg_lbin = json.load(f)

        def estimate_nbt_value(nbt_data: str) -> float:
            if not nbt_data:
                return 0
            total = 0.0
            try:
                # decode_auction_item returns (count, skyblock_id)
                count, skyblock_id = decode_auction_item(nbt_data)
                if skyblock_id:
                    price = avg_lbin.get(skyblock_id) or 0
                    if not price:
                        bz = bazaar.get(skyblock_id, {}).get("quick_status", {})
                        price = bz.get("sellPrice", 0)
                    total = price * count
            except Exception:
                pass
            return total

        inv_value = estimate_nbt_value(profile["inventory"])
        ec_value = estimate_nbt_value(profile["ender_chest"])

        bp_value = 0.0
        for bp in (profile["backpacks"] or {}).values():
            bp_value += estimate_nbt_value(bp.get("data", ""))

        result["inventory_value"] = inv_value
        result["ender_chest_value"] = ec_value
        result["backpack_value"] = bp_value
        result["estimated_total"] = result["liquid"] + inv_value + ec_value + bp_value

    return result


def _build_prompt(wealth: dict, opportunities: list, wiki_chunks: list[str],
                  core_mechanics: str, full: bool) -> str:
    opp_lines = []
    for o in opportunities[:15]:
        d = o.details
        flags = []
        if d.get("manipulated"):
            flags.append("possibly manipulated")
        if d.get("suspicious"):
            flags.append("suspicious price")
        flag_str = f" [{', '.join(flags)}]" if flags else ""
        opp_lines.append(
            f"- {o.item_name} ({d.get('tier', '?')}): "
            f"buy {d.get('count')}× at {format_coins(d.get('bundle_per_unit', 0))}/ea, "
            f"sell at {format_coins(d.get('single_price', 0))}/ea, "
            f"profit/14 slots: {format_coins(o.profit)}{flag_str}"
        )

    wealth_lines = [
        f"- Profile: {wealth['profile_name']}",
        f"- Purse: {format_coins(wealth['purse'])}",
        f"- Bank: {format_coins(wealth['bank'])}",
        f"- Liquid total: {format_coins(wealth['liquid'])}",
    ]
    if full and "estimated_total" in wealth:
        wealth_lines += [
            f"- Inventory value (estimate): {format_coins(wealth.get('inventory_value', 0))}",
            f"- Ender chest value (estimate): {format_coins(wealth.get('ender_chest_value', 0))}",
            f"- Backpack value (estimate): {format_coins(wealth.get('backpack_value', 0))}",
            f"- Estimated net worth: {format_coins(wealth['estimated_total'])}",
        ]

    wiki_section = "\n\n".join(wiki_chunks) if wiki_chunks else "(no wiki context loaded)"

    return f"""You are an expert Hypixel Skyblock economy advisor. Your job is to give personalized, actionable flip recommendations based on the player's current wealth and the available AH opportunities.

## Core Game Mechanics
{core_mechanics}

## Relevant Wiki Context
{wiki_section}

## Player Wealth
{chr(10).join(wealth_lines)}

## Current AH Opportunities (sorted by profit/14 slots)
{chr(10).join(opp_lines) if opp_lines else "No opportunities available — daemon may not be running."}

## Your Task
Analyze the opportunities above and give the player specific, prioritized recommendations. Consider:
- Which flips they can actually afford given their liquid coins
- Which items have the best risk/reward (flag manipulated or suspicious ones)
- How many slots to dedicate to each flip
- Any game knowledge that affects whether an item is a good flip right now (e.g. upcoming events, mayor effects, item usefulness)

Be direct and specific. Format your answer clearly with the top 3-5 recommendations first, then any caveats."""


def run(cfg: Config, full: bool = False) -> None:
    if not cfg.minecraft_username:
        print("No Minecraft username set. Run: python3 cli.py setup")
        return

    if not rag.index_exists():
        print("[warn] Wiki index not built — advisor will use core mechanics only.")
        print("       Run 'python3 cli.py wiki update' for full wiki knowledge.\n")
        wiki_chunks = []
    else:
        print("Retrieving relevant wiki context...")

    db = DB()
    opportunities = db.get_opportunities(type_filter="AH", min_profit=0)

    if rag.index_exists():
        query = " ".join(set(o.item_name for o in opportunities[:10]))
        wiki_chunks = rag.retrieve(query, k=8)
    else:
        wiki_chunks = []

    print("Fetching player profile...")
    try:
        wealth = asyncio.run(_fetch_wealth(cfg, full=full))
    except Exception as e:
        print(f"[error] Could not fetch player profile: {e}")
        return

    core_mechanics = _load_core_mechanics()
    prompt = _build_prompt(wealth, opportunities, wiki_chunks, core_mechanics, full)

    print(f"Asking {ADVISOR_MODEL}...\n")
    client = OpenAI(base_url=f"{cfg.lm_studio_url}/v1", api_key="lm-studio")
    response = client.chat.completions.create(
        model=ADVISOR_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        stream=True,
    )

    for chunk in response:
        delta = chunk.choices[0].delta.content
        if delta:
            print(delta, end="", flush=True)
    print()
