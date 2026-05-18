from __future__ import annotations

import pytest
from typer.testing import CliRunner

from smart_router.cli.main import app
from smart_router.cli.rendering.console import render_stream_event
from smart_router.core.streaming import StreamEvent


class _DummyServices:
    pass


def test_cli_run_command_wiring(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()
    called = {"ok": False}

    async def fake_run_once(services, *, prompt: str, session_id: str | None, stream: bool) -> None:
        _ = services
        called["ok"] = prompt == "fix auth bug" and stream is True

    monkeypatch.setattr("smart_router.cli.main._services", lambda data_dir=None: _DummyServices())
    monkeypatch.setattr("smart_router.cli.main.run_once", fake_run_once)

    result = runner.invoke(app, ["run", "fix auth bug"])
    assert result.exit_code == 0
    assert called["ok"] is True


def test_cli_resume_command_wiring(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()
    called = {"sid": None}

    async def fake_resume(services, sid: str) -> None:
        _ = services
        called["sid"] = sid

    monkeypatch.setattr("smart_router.cli.main._services", lambda data_dir=None: _DummyServices())
    monkeypatch.setattr("smart_router.cli.main.resume_session", fake_resume)

    result = runner.invoke(app, ["resume", "sess-123"])
    assert result.exit_code == 0
    assert called["sid"] == "sess-123"


def test_cli_routes_explain_wiring(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()
    called = {"prompt": None}

    async def fake_explain(services, prompt: str) -> None:
        _ = services
        called["prompt"] = prompt

    monkeypatch.setattr("smart_router.cli.main._services", lambda data_dir=None: _DummyServices())
    monkeypatch.setattr("smart_router.cli.main.explain_route", fake_explain)

    result = runner.invoke(app, ["routes", "explain", "large refactor"])
    assert result.exit_code == 0
    assert called["prompt"] == "large refactor"


def test_cli_telemetry_and_providers_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()
    telemetry_called = {"ok": False}
    provider_called = {"ok": False}

    async def fake_telemetry(services) -> None:
        _ = services
        telemetry_called["ok"] = True

    async def fake_health(services) -> None:
        _ = services
        provider_called["ok"] = True

    monkeypatch.setattr("smart_router.cli.main._services", lambda data_dir=None: _DummyServices())
    monkeypatch.setattr("smart_router.cli.main.telemetry_summary", fake_telemetry)
    monkeypatch.setattr("smart_router.cli.main.providers_health", fake_health)

    telemetry_result = runner.invoke(app, ["telemetry", "summary"])
    providers_result = runner.invoke(app, ["providers", "health"])

    assert telemetry_result.exit_code == 0
    assert providers_result.exit_code == 0
    assert telemetry_called["ok"] is True
    assert provider_called["ok"] is True


def test_stream_renderer_outputs_chunks(capsys: pytest.CaptureFixture[str]) -> None:
    render_stream_event(
        StreamEvent(
            event_type="token_chunk",
            request_id="r1",
            provider="openai",
            model="gpt-5.4",
            content="abc",
        )
    )
    out = capsys.readouterr().out
    assert "abc" in out
