# Skyblock AH Flipper — AI Advisor

AI-powered flip recommendations for the Hypixel Skyblock Auction House. The advisor knows your current wealth, live opportunities, and has deep Skyblock knowledge from the wiki.

## Requirements

- Python 3.10+
- Hypixel API key (free): https://developer.hypixel.net/dashboard
- [LM Studio](https://lmstudio.ai) with `mlx-community/Qwen3.5-9B-MLX-4bit` loaded and Local Server running

## LM Studio setup

1. Download [LM Studio](https://lmstudio.ai)
2. Search for `Qwen3.5-9B-MLX-4bit` and download it (~5.6 GB, fits on 16 GB RAM)
3. Load the model and set **Context Length to at least 8192** (recommended: 24576) — the default is too small and will cause an error
4. Go to **Local Server** and click **Start Server**
5. Default URL `http://localhost:1234` is used automatically — to change it: `python3 cli.py config lm_studio_url <url>`

## Setup

```bash
git clone https://github.com/Skyfall91/sb-ah.git
cd sb-ah
pip3 install -r requirements.txt
python3 cli.py setup
```

During setup you'll be asked for your Hypixel API key, Minecraft username, and LM Studio URL.

**Build the wiki index** (once, takes ~5 minutes):
```bash
python3 cli.py wiki update
```

## Usage

**Start the daemon** so there's live data to analyze:
```bash
python3 cli.py daemon start
```

**Get AI recommendations** based on your bank + purse:
```bash
python3 cli.py advice
```

**Include full wealth estimate** (inventory, enderchest, backpacks):
```bash
python3 cli.py advice --full
```

The advisor will:
- Fetch your current coin balance from the Hypixel API
- Retrieve relevant wiki knowledge for the items in the current opportunities
- Always include core mechanics (AH fees, mayor effects, etc.) as context
- Ask the local AI model which flips are best for your budget right now

## Other commands

```bash
python3 cli.py              # show current opportunities
python3 cli.py top          # top flips of the last 24h
python3 cli.py daemon stop  # stop the daemon
python3 cli.py config       # show all settings
python3 cli.py config lm_studio_url http://192.168.1.50:1234  # change AI URL
```

## How it works

1. The **daemon** fetches live AH data every 60 seconds
2. **`wiki update`** crawls the Hypixel Skyblock wiki and builds a local search index
3. **`advice`** combines your player wealth, current opportunities, and relevant wiki knowledge into a prompt for a local AI model — which then gives you personalized, prioritized recommendations
