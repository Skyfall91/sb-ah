# Skyblock AH Flipper

Finds profitable bundle flips in the Hypixel Skyblock Auction House — buy bundles cheap, sell singles for more.

## Setup

```bash
git clone https://github.com/Skyfall91/sb-ah.git
cd sb-ah
pip3 install -r requirements.txt
python3 cli.py setup
```

You'll need a free Hypixel API key: https://developer.hypixel.net/dashboard

## Usage

```bash
python3 cli.py daemon start   # start fetching data (every 60s)
python3 cli.py                # show current flips
python3 cli.py top            # best flips of the last 24h
python3 cli.py daemon stop    # stop the daemon
```

## Columns

| | |
|---|---|
| **Buy** | Bundle price per unit |
| **Sell** | Reference price per unit (AH / Bazaar / NPC) |
| **Profit/14** | Profit if you fill all 14 AH slots from one bundle |

`~` = price may be manipulated · `⚠` = suspiciously high price
