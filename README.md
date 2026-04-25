# Skyblock AH Flipper

Findet automatisch profitable Flip-Möglichkeiten im Hypixel Skyblock Auction House.

## Einrichtung (einmalig)

```bash
pip3 install -r requirements.txt
cp config.yaml.example config.yaml
python3 cli.py setup   # fragt nach deinem API-Key
```

API-Key bekommst du hier: https://developer.hypixel.net/dashboard

## Starten

**Daemon starten** (holt alle 60s neue Daten):
```bash
python3 cli.py daemon start
```

**Opportunities anzeigen:**
```bash
python3 cli.py
```

**Live-Ansicht** (aktualisiert alle 10s):
```bash
python3 cli.py -w
```

**Top-Flips der letzten 24h:**
```bash
python3 cli.py top
```

**Daemon stoppen:**
```bash
python3 cli.py daemon stop
```
