# ---------------------------------------------------------------------------
# File: test_commands.py
# ---------------------------------------------------------------------------
# Description:
#	Unit tests for pyezsh command registry.
#
# Notes:
#	- Pure unit tests; no Tkinter dependency.
#
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date			Author						Change
# ---------------------------------------------------------------------------
# 12/30/2025	Paul G. LeDuc				Initial tests
# 12/30/2025	Paul G. LeDuc				Add CommandRegistry coverage
# 01/01/2026	Paul G. LeDuc				Update tests for revised Command/Registry API
# ---------------------------------------------------------------------------

import pytest

from pyezsh.app.commands import (
	Command,
	CommandAlreadyRegistered,
	CommandContext,
	CommandNotEnabled,
	CommandNotFound,
	CommandRegistry,
)


def _ctx() -> CommandContext:
	return CommandContext(app=None, state={}, services={}, extra={})


def test_register_and_get_command():
	registry = CommandRegistry()

	cmd = Command(
		id="quit",
		label="Quit",
		handler=lambda ctx: "ok",
	)

	registry.register(cmd)

	assert registry.has("quit") is True
	assert registry.get("quit") is cmd
	assert "quit" in registry.ids()


def test_register_duplicate_id_raises():
	registry = CommandRegistry()

	cmd1 = Command(id="x", label="X", handler=lambda ctx: 1)
	cmd2 = Command(id="x", label="X2", handler=lambda ctx: 2)

	registry.register(cmd1)

	with pytest.raises(CommandAlreadyRegistered):
		registry.register(cmd2)


def test_execute_calls_handler():
	registry = CommandRegistry()

	calls: list[str] = []

	def handler(ctx: CommandContext):
		calls.append("called")
		return 123

	registry.register(Command(id="do", label="Do", handler=handler))

	result = registry.execute("do", _ctx())

	assert result == 123
	assert calls == ["called"]


def test_execute_unknown_command_raises():
	registry = CommandRegistry()

	with pytest.raises(CommandNotFound):
		registry.execute("missing", _ctx())


def test_execute_disabled_command_raises_and_does_not_call_handler():
	registry = CommandRegistry()

	called = False

	def handler(ctx: CommandContext):
		nonlocal called
		called = True
		return "should-not-run"

	registry.register(Command(id="disabled", label="Disabled", handler=handler, enabled=False))

	with pytest.raises(CommandNotEnabled):
		registry.execute("disabled", _ctx())

	assert called is False


def test_enabled_predicate_controls_enablement():
	registry = CommandRegistry()

	allow = False
	called = False

	def enabled_pred(ctx: CommandContext) -> bool:
		return allow

	def handler(ctx: CommandContext):
		nonlocal called
		called = True
		return "ran"

	registry.register(Command(id="dynamic", label="Dynamic", handler=handler, enabled=enabled_pred))

	# not enabled
	with pytest.raises(CommandNotEnabled):
		registry.execute("dynamic", _ctx())
	assert called is False

	# enabled
	allow = True
	result = registry.execute("dynamic", _ctx())
	assert result == "ran"
	assert called is True
