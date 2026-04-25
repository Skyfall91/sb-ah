# Skyblock Investment Tool — Design Spec
**Date:** 2026-04-17

## Overview

A Python-based tool that continuously monitors the Hypixel Skyblock economy and surfaces actionable investment and trading opportunities. Runs as a background daemon with macOS notifications; a CLI provides on-demand output.

---

## Investment Types

### 1. Bazaar Flipping
- Computes `sell_offer - buy_order - bazaar_tax` per item
- Only reports opportunities with net profit ≥ configurable minimum (default: 500k coins)
- Requires sufficient weekly volume to ensure the trade is realistically executable
- Bazaar tax is configurable per player (default: 1.25% free tier; lower values set in `config.yaml`)

### 2. NPC Arbitrage
- Compares NPC sell prices (from Hypixel Items API) against Bazaar buy orders
- Reports when `bazaar_buy_order - npc_price > threshold`
- Accounts for player NPC discount talisman (0%, 1%, 2%, or 3% — set in `config.yaml`)
- Respects daily NPC purchase limits per item

### 3. AH Flipping & Stack Arbitrage
- **Underpriced items:** Compares active AH listings against Coflnet median price; reports when listing is significantly below median
- **Stack arbitrage:** Detects when `stack_price / stack_size < single_item_price` — profit from buying stacks and reselling individually

### 4. Mayor/Event-Based Investing
- Reads current and upcoming Mayor from Hypixel Election API
- Cross-references against Coflnet historical price data to find items with statistically significant price increases during this Mayor (minimum 3 cycles as data basis)
- No guessing — only reports patterns backed by data
- If data is insufficient, reports `"unzureichende Datenbasis"` rather than speculating

---

## Architecture

```
skyblock/
├── daemon.py          # Main process, orchestrates all analyzers
├── cli.py             # On-demand output
├── db.py              # SQLite wrapper
├── notify.py          # macOS notification + sound
├── config.yaml        # Thresholds, API keys, player modifiers
├── analyzers/
│   ├── bazaar.py      # Bazaar flip logic
│   ├── npc.py         # NPC arbitrage logic
│   ├── auction.py     # AH flip + stack arbitrage logic
│   └── mayor.py       # Mayor/event investment logic
└── sources/
    ├── hypixel.py     # Hypixel Skyblock API client
    └── coflnet.py     # Coflnet historical price client
```

The daemon polls APIs on configurable intervals, passes raw data to analyzers, and writes found opportunities to SQLite. The CLI reads exclusively from the DB — no direct API calls.

---

## Data Sources

| Source | Purpose | Interval |
|---|---|---|
| Hypixel Bazaar API | Live prices, order book | ~60s |
| Hypixel AH API | Active auctions | ~5min |
| Hypixel Items API | Item metadata, NPC prices | daily |
| Hypixel Election API | Current/upcoming Mayor | ~10min |
| Coflnet API | Price history (primary) | on-demand |
| Local SQLite DB | Opportunities, fallback price history | continuous |

### Coflnet Fallback Policy
- Fallback to self-collected price data **only** if Coflnet returns a successful response but has no data for a specific item
- On timeout, error, or partial data: skip the analysis for that item, mark as `"keine Datenbasis"`
- Never estimate or interpolate missing data

---

## Player Configuration (`config.yaml`)

Set once at setup; prompted interactively on first run:

```yaml
api_key: ""                  # Hypixel API key
bazaar_tax: 0.0125           # 1.25% default; lower if Community Shop upgraded
npc_discount: 0.00           # 0%, 0.01, 0.02, or 0.03 depending on talisman
min_profit_notify: 500000    # Minimum profit to trigger notification (coins)
min_profit_display: 100000   # Minimum profit to show in CLI
```

---

## CLI Interface

```
python cli.py                    # All current opportunities
python cli.py --type bazaar      # Bazaar only
python cli.py --type npc         # NPC arbitrage only
python cli.py --type ah          # AH flipping only
python cli.py --min-profit 1m    # Filter by minimum profit
python cli.py --mayor            # Mayor/event investment analysis
python cli.py daemon start       # Start background daemon
python cli.py daemon stop        # Stop background daemon
```

---

## Output Format

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 JETZT KAUFEN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 [BAZAAR] Enchanted Diamond
  → Buy Order: 18.2M | Sell Offer: 20.5M
  → Profit: ~2.3M pro Transaktion
  → Volumen: hoch (sicher handelbar)

 [NPC] Sand — 64er Stack beim NPC kaufen
  → Kosten: 1.280 | Bazaar-Verkauf: 541k
  → Profit: ~540k | Limit: 640 Stück/Tag

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 JETZT INVESTIEREN (Mayor: Diana aktiv)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 [MAYOR] Griffin Feather
  → Jetzt kaufen bei: ~80k/stk
  → Historisch bei Diana: Ø +180% (5 Zyklen)
  → Empfehlung: 100–500 Stück einlagern
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Clear separation between **"act now"** and **"invest for later"**. Every recommendation states what to buy, where, expected profit, and why.

---

## Notifications

- macOS Desktop Notification fires when an opportunity exceeds `min_profit_notify`
- Sound alert accompanies the notification (configurable; higher profit = distinct sound)
- Notification body: item name, profit, type (BAZAAR / NPC / AH / MAYOR)

---

## Error Handling

- API timeouts: log, skip this cycle, retry next interval
- Missing item data: mark as `"keine Datenbasis"`, never estimate
- Coflnet unavailable: skip Mayor/AH analysis for affected items, log clearly
- Daemon crash: systemd-style restart via launchd plist (macOS)
