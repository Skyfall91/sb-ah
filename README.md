# Skyblock AH Flipper

Automatically finds profitable bundle flips in the Hypixel Skyblock Auction House.

The tool detects listings where a bundle of items is cheaper per unit than singles — buy the bundle, sell individually for profit.

## Requirements

- Python 3.10+
- Free Hypixel API key: https://developer.hypixel.net/dashboard

## Setup

```bash
git clone https://github.com/Skyfall91/sb-ah.git
cd sb-ah
pip3 install -r requirements.txt
python3 cli.py setup
```

During setup you'll be asked for your API key. It's stored locally in `config.yaml` and never uploaded.

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

## Reading the output

| Column | Meaning |
|--------|---------|
| **Buy** | Bundle price per unit |
| **Sell** | Reference sell price (AH average, Bazaar, or NPC) |
| **Bundles** | Number of profitable listings currently available |
| **Profit/14** | Profit if you fill all 14 AH slots with singles from one bundle |

Price badges: `BZ` = Bazaar floor · `NPC` = NPC price · `~` = possible manipulation · `⚠` = suspicious price
