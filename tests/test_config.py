import yaml
from config import Config, load_config, save_config


def test_default_values():
    cfg = Config()
    assert cfg.api_key == ""
    assert cfg.min_profit_notify == 500_000
    assert cfg.min_profit_display == 100_000


def test_save_and_load(tmp_path):
    cfg = Config(api_key="test-key", min_profit_notify=1_000_000, min_profit_display=200_000)
    path = str(tmp_path / "config.yaml")
    save_config(cfg, path)
    loaded = load_config(path)
    assert loaded.api_key == "test-key"
    assert loaded.min_profit_notify == 1_000_000
    assert loaded.min_profit_display == 200_000


def test_load_missing_file_returns_defaults(tmp_path):
    path = str(tmp_path / "nonexistent.yaml")
    cfg = load_config(path)
    assert cfg.api_key == ""
    assert cfg.min_profit_display == 100_000


def test_load_malformed_yaml_returns_defaults(tmp_path):
    path_obj = tmp_path / "bad.yaml"
    path_obj.write_text(": invalid: yaml: {{{{")
    cfg = load_config(str(path_obj))
    assert cfg.api_key == ""
