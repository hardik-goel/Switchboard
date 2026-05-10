from __future__ import annotations

from pathlib import Path

import pytest

from smart_router.core.config import ConfigEngine, ConfigError


def test_load_valid_config() -> None:
    engine = ConfigEngine(Path("smart_router/configs/default.yaml"))
    config = engine.load()
    assert config.routing.default_provider == "openai"
    assert "openai" in config.providers


def test_load_missing_file_raises() -> None:
    engine = ConfigEngine(Path("missing.yaml"))
    with pytest.raises(ConfigError):
        engine.load()
