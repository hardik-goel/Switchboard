"""Config inspection/validation commands."""

from __future__ import annotations

import json

import typer

from smart_router.cli.bootstrap import AppServices


def config_validate(services: AppServices) -> None:
    cfg = services.config_engine.config
    typer.echo("Configuration valid")
    typer.echo(json.dumps(cfg.model_dump(), indent=2))
