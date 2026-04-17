import pytest
import tempfile
import os
import yaml
from config import Config, load_config, save_config


def test_default_values():
    cfg = Config()
    assert cfg.bazaar_tax == 0.0125
    assert cfg.npc_discount == 0.0
    assert cfg.min_profit_notify == 500_000
    assert cfg.min_profit_display == 100_000


def test_save_and_load(tmp_path):
    cfg = Config(api_key="test-key", bazaar_tax=0.009, npc_discount=0.02,
                 min_profit_notify=1_000_000, min_profit_display=200_000)
    path = str(tmp_path / "config.yaml")
    save_config(cfg, path)
    loaded = load_config(path)
    assert loaded.api_key == "test-key"
    assert loaded.bazaar_tax == 0.009
    assert loaded.npc_discount == 0.02
    assert loaded.min_profit_notify == 1_000_000


def test_load_missing_file_returns_defaults(tmp_path):
    path = str(tmp_path / "nonexistent.yaml")
    cfg = load_config(path)
    assert cfg.bazaar_tax == 0.0125
