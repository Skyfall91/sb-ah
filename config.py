import yaml
from dataclasses import dataclass, asdict

DEFAULT_CONFIG_PATH = "config.yaml"


@dataclass
class Config:
    api_key: str = ""
    min_profit_notify: int = 500_000
    min_profit_display: int = 100_000
    minecraft_username: str = ""
    lm_studio_url: str = "http://localhost:1234"


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
    print("=== Skyblock AH Flipper ===\n")
    print("No API key found. You need a free Hypixel API key:")
    print("  → https://developer.hypixel.net/dashboard\n")
    print("1. Log in with your Minecraft account")
    print("2. Click 'Create API Key'")
    print("3. Paste it here:\n")

    while True:
        api_key = input("API Key: ").strip()
        if api_key:
            break
        print("  Please enter a key.")

    print()
    minecraft_username = input("Minecraft username (for the advisor feature, leave blank to skip): ").strip()

    print()
    lm_studio_url = input(f"LM Studio URL (leave blank for default {Config.__dataclass_fields__['lm_studio_url'].default}): ").strip()
    if not lm_studio_url:
        lm_studio_url = Config.__dataclass_fields__["lm_studio_url"].default

    cfg = Config(api_key=api_key, minecraft_username=minecraft_username, lm_studio_url=lm_studio_url)
    save_config(cfg, path)
    print(f"\nSaved. Restart to continue.\n")
    return cfg
