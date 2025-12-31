# ---------------------------------------------------------------------------
# File: test_commands.py
# ---------------------------------------------------------------------------
# Description:
#   Unit tests for pyezsh command registry.
#
# Notes:
#   - Pure unit tests; no Tkinter dependency.
#
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date			Author						Change
# ---------------------------------------------------------------------------
# 12/30/2025	Paul G. LeDuc				Initial tests
# 12/30/2025	Paul G. LeDuc				Add CommandRegistry coverage
# ---------------------------------------------------------------------------

import pytest

from pyezsh.app.commands import Command, CommandRegistry


def test_register_and_get_command():
	registry = CommandRegistry()

	cmd = Command(
		id="quit",
		name="Quit",
		handler=lambda: "ok",
	)

	registry.register(cmd)

	assert registry.has("quit") is True
	assert registry.get("quit") is cmd
	assert "quit" in registry.ids()


def test_register_duplicate_id_raises():
	registry = CommandRegistry()

	cmd1 = Command(id="x", handler=lambda: 1)
	cmd2 = Command(id="x", handler=lambda: 2)

	registry.register(cmd1)

	with pytest.raises(ValueError):
		registry.register(cmd2)


def test_invoke_calls_handler():
	registry = CommandRegistry()

	calls: list[str] = []

	def handler():
		calls.append("called")
		return 123

	registry.register(Command(id="do", handler=handler))

	result = registry.invoke("do")

	assert result == 123
	assert calls == ["called"]


def test_invoke_unknown_command_raises_key_error():
	registry = CommandRegistry()

	with pytest.raises(KeyError):
		registry.invoke("missing")


def test_invoke_disabled_command_returns_none_and_does_not_call_handler():
	registry = CommandRegistry()

	called = False

	def handler():
		nonlocal called
		called = True
		return "should-not-run"

	registry.register(Command(id="disabled", handler=handler, enabled=False))

	result = registry.invoke("disabled")

	assert result is None
	assert called is False


def test_invoke_enabled_fn_controls_enablement():
	registry = CommandRegistry()

	allow = False
	called = False

	def enabled_fn() -> bool:
		return allow

	def handler():
		nonlocal called
		called = True
		return "ran"

	registry.register(Command(id="dynamic", handler=handler, enabled_fn=enabled_fn))

	# not enabled
	result1 = registry.invoke("dynamic")
	assert result1 is None
	assert called is False

	# enabled
	allow = True
	result2 = registry.invoke("dynamic")
	assert result2 == "ran"
	assert called is True
