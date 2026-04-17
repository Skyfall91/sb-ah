import yaml
from dataclasses import dataclass, asdict

DEFAULT_CONFIG_PATH = "config.yaml"


@dataclass
class Config:
    api_key: str = ""
    bazaar_tax: float = 0.0125
    npc_discount: float = 0.0
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
    print("=== Skyblock Investment Tool — First Run Setup ===\n")
    api_key = input("Hypixel API Key (https://developer.hypixel.net): ").strip()

    print("\nBazaar Tax Rate:")
    print("  0 = 1.25% (default, no upgrades)")
    print("  1 = lower (Community Shop upgraded)")
    tax_choice = input("Bazaar tax rate (0.0125 or lower, e.g. 0.009): ").strip()
    try:
        bazaar_tax = float(tax_choice)
        if not (0.0 <= bazaar_tax <= 0.0125):
            print("  Invalid range, using default 1.25%")
            bazaar_tax = 0.0125
    except ValueError:
        bazaar_tax = 0.0125

    print("\nNPC Discount Talisman:")
    print("  0 = none, 1 = 1%, 2 = 2%, 3 = 3%")
    disc_choice = input("NPC discount level (0/1/2/3): ").strip()
    discount_map = {"0": 0.0, "1": 0.01, "2": 0.02, "3": 0.03}
    npc_discount = discount_map.get(disc_choice, 0.0)

    cfg = Config(
        api_key=api_key,
        bazaar_tax=bazaar_tax,
        npc_discount=npc_discount,
    )
    save_config(cfg, path)
    print(f"\nConfig saved to {path}\n")
    return cfg
