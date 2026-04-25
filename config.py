import yaml
from dataclasses import dataclass, asdict

DEFAULT_CONFIG_PATH = "config.yaml"


@dataclass
class Config:
    api_key: str = ""
    min_profit_notify: int = 500_000
    min_profit_display: int = 100_000


def load_config(path: str = DEFAULT_CONFIG_PATH) -> Config:
    try:
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return Config(**{k: v for k, v in data.items() if k in Config.__dataclass_fields__})
    except FileNotFoundError:
        return Config()
    except yaml.YAMLError as e:
        print(f"[warn] config.yaml is malformed ({e}), using defaults")
        return Config()


def save_config(cfg: Config, path: str = DEFAULT_CONFIG_PATH) -> None:
    with open(path, "w") as f:
        yaml.dump(asdict(cfg), f, default_flow_style=False)


def setup_first_run(path: str = DEFAULT_CONFIG_PATH) -> Config:
    print("=== Skyblock Investment Tool ===\n")
    print("Kein API-Key gefunden. Du brauchst einen kostenlosen Hypixel API-Key:")
    print("  → https://developer.hypixel.net/dashboard\n")
    print("1. Einloggen mit deinem Minecraft-Account")
    print("2. 'Create API Key' klicken")
    print("3. Key hier einfügen:\n")

    while True:
        api_key = input("API Key: ").strip()
        if api_key:
            break
        print("  Bitte einen Key eingeben.")

    cfg = Config(api_key=api_key)
    save_config(cfg, path)
    print(f"\nGespeichert. Starte neu um fortzufahren.\n")
    return cfg
