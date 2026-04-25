# Skyblock Investment Tool

Findet automatisch profitable Investitionsmöglichkeiten in Hypixel Skyblock.

## Einrichtung (einmalig)

```bash
pip3 install -r requirements.txt
python3 cli.py setup
```

## Starten

Doppelklick auf **`start.command`** im Finder.

Oder im Terminal:
```bash
python3 menubar.py
```

Das Tool erscheint in der macOS Menüleiste:
- `● SB` — läuft, Opportunities vorhanden
- `○ SB` — läuft, keine Opportunities gerade
- `✕ SB` — Daemon gestoppt

## Menü

Klick auf ein Item kopiert den Namen in die Zwischenablage (direkt im Spiel einfügbar).

## Daemon-Log

```bash
tail -f daemon.log
```
