# Skyblock AH Flipper

Automatically finds profitable bundle flips in the Hypixel Skyblock Auction House.

The tool detects listings where a bundle of items is cheaper per unit than singles — buy the bundle, sell individually for profit. An optional AI advisor analyzes opportunities based on your wealth and Skyblock wiki knowledge.

## Requirements

- Python 3.10+
- Free Hypixel API key: https://developer.hypixel.net/dashboard
- For the AI advisor: [LM Studio](https://lmstudio.ai) with `Qwen3-8B` (MLX 4-bit) loaded

## Setup

```bash
git clone https://github.com/Skyfall91/sb-ah.git
cd sb-ah
pip3 install -r requirements.txt
python3 cli.py setup
```

During setup you'll be asked for your Hypixel API key and Minecraft username. Both are stored locally in `config.yaml` and never uploaded.

## Usage

**Start the daemon** — fetches new auction data every 60 seconds:
```bash
python3 cli.py daemon start
```

**Show current flips:**
```bash
python3 cli.py
```

**Top flips over the last 24h** (more reliable, based on repeated sightings):
```bash
python3 cli.py top
python3 cli.py top --hours 6
```

**Filter by minimum profit:**
```bash
python3 cli.py --min-profit 1m
```

**Stop the daemon:**
```bash
python3 cli.py daemon stop
```

## AI Advisor

The advisor combines your current wealth, live opportunities, and wiki knowledge to give personalized recommendations.

**One-time setup** — crawl the wiki and build the search index (~5 min):
```bash
python3 cli.py wiki update
```

**Get recommendations** (based on bank + purse):
```bash
python3 cli.py advice
```

**Include full wealth estimate** (inventory, enderchest, backpacks):
```bash
python3 cli.py advice --full
```

Requires LM Studio running locally with `Qwen3-8B` (MLX 4-bit) loaded. Default URL: `http://localhost:1234`.

## Reading the output

| Column | Meaning |
|--------|---------|
| **Buy** | Bundle price per unit |
| **Sell** | Reference sell price (AH average, Bazaar, or NPC) |
| **Bundles** | Number of profitable listings currently available |
| **Profit/14** | Profit if you fill all 14 AH slots with singles from one bundle |

Price badges: `BZ` = Bazaar floor · `NPC` = NPC price · `~` = possible manipulation · `⚠` = suspicious price
