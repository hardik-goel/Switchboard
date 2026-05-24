"""Packaging sanity smoke checks."""

from __future__ import annotations

import importlib.metadata as md


def test_distribution_and_console_scripts_exist() -> None:
    dist = md.distribution("smart-router")
    assert dist.metadata["Name"] == "smart-router"

    scripts = md.entry_points(group="console_scripts")
    script_map = {ep.name: ep.value for ep in scripts}
    assert script_map.get("smart-router") == "smart_router.cli.main:app"
    assert script_map.get("switchboard") == "smart_router.cli.main:app"

