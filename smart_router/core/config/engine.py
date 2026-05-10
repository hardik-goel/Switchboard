"""YAML-backed config loader and access engine."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from smart_router.schemas.config import AppConfig

logger = logging.getLogger("smart_router.config")


class ConfigError(RuntimeError):
    """Raised when configuration cannot be loaded or validated."""


class ConfigEngine:
    """Load and provide validated config for the routing system."""

    def __init__(self, config_path: Path) -> None:
        self._config_path = config_path
        self._config: AppConfig | None = None

    @property
    def config(self) -> AppConfig:
        """Return loaded configuration, raising if not loaded."""
        if self._config is None:
            raise ConfigError("Configuration is not loaded. Call load() first.")
        return self._config

    def load(self) -> AppConfig:
        """Load and validate YAML config into typed schema."""
        if not self._config_path.exists():
            raise ConfigError(f"Config file not found: {self._config_path}")

        try:
            raw = yaml.safe_load(self._config_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise ConfigError(f"Invalid YAML in {self._config_path}") from exc

        if not isinstance(raw, dict):
            raise ConfigError("Top-level config must be a mapping.")

        self._config = AppConfig.model_validate(raw)
        logger.info(
            "config_loaded",
            extra={
                "path": str(self._config_path),
                "provider_count": len(self._config.providers),
            },
        )
        return self._config

    def reload(self) -> AppConfig:
        """Reload configuration from disk."""
        self._config = None
        return self.load()

    def as_dict(self) -> dict[str, Any]:
        """Expose loaded config as a plain dictionary."""
        return self.config.model_dump()
