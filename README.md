# Skyblock AH Flipper

Automatically finds profitable bundle flips in the Hypixel Skyblock Auction House.

The tool detects listings where buying multiple items in a bundle is cheaper per unit than buying singles — buy the bundle, sell individually.

---

## How it works

1. The **daemon** fetches all active AH auctions from the Hypixel API every 60 seconds
2. The **analyzer** compares bundle prices against single prices, cross-referenced with Moulberry LBIN data and Bazaar prices as a price floor
3. Profitable opportunities are stored in a local database
4. The **CLI** displays the best flips sorted by profit

---

## Requirements

- Python 3.10+
- Hypixel API key (free): https://developer.hypixel.net/dashboard

---

## Installation

```bash
git clone https://github.com/Skyfall91/sb-ah.git
cd sb-ah
pip3 install -r requirements.txt
```

---

## Setup (once)

```bash
python3 cli.py setup
```

Enter your Hypixel API key when prompted. It is stored locally in `config.yaml` and never uploaded.

---

## Usage

### 1. Start the daemon

```bash
python3 cli.py daemon start
```

Runs in the background and refreshes data every 60 seconds. Logs are written to `daemon.log`.

### 2. Show current flips

```bash
python3 cli.py
```

Displays all current opportunities sorted by profit per 14 days (maximum AH listing duration).

### 3. Top flips over time

```bash
python3 cli.py top
python3 cli.py top --hours 6
```

Shows items that appeared repeatedly — more reliable flips since they aren't just a one-time snapshot.

### 4. Filter by minimum profit

```bash
python3 cli.py --min-profit 1m
python3 cli.py --min-profit 500k
```

### 5. Stop the daemon

```bash
python3 cli.py daemon stop
```

---

## Column reference

| Column | Meaning |
|--------|---------|
| **Item** | Item name (clickable → Hypixel Wiki) |
| **Kaufen** | Bundle quantity × price per unit |
| **Einzeln** | Reference sell price per unit |
| **Bundles** | Number of profitable listings currently available |
| **Profit/14** | Estimated profit buying and reselling 1 bundle per day for 14 days |

#### Price indicators

| Badge | Meaning |
|-------|---------|
| `BZ` | Reference price from Bazaar instant sell |
| `NPC` | Reference price is the NPC sell price |
| `~` | Price deviates significantly from LBIN — possibly manipulated |
| `⚠` | Price looks unrealistically high — treat with caution |

---

## Configuration

`config.yaml` (created automatically during setup):

```yaml
api_key: YOUR_KEY
min_profit_display: 100000   # minimum profit to show (default: 100k)
min_profit_notify: 500000    # minimum profit for notifications (default: 500k)
```
