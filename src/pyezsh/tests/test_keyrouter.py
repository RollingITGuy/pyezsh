# ---------------------------------------------------------------------------
# File: test_keyrouter.py
# ---------------------------------------------------------------------------
# Description:
#	Unit tests for KeyRouter (contextual key routing).
#
# Notes:
#	- Pure unit tests; no Tkinter dependency.
#
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date			Author						Change
# ---------------------------------------------------------------------------
# 01/01/2026	Paul G. LeDuc				Initial tests
# ---------------------------------------------------------------------------

from __future__ import annotations

from pyezsh.app.commands import Command, CommandContext, CommandRegistry
from pyezsh.app.keys import KeyMap
from pyezsh.app.keyrouter import KeyRouter


def _ctx() -> CommandContext:
	return CommandContext(app=None, state={}, services={}, extra={})


def test_keyrouter_global_routing_executes_command():
	reg = CommandRegistry()
	calls: list[str] = []

	reg.register(Command(id="app.quit", label="Quit", handler=lambda ctx: calls.append("app.quit")))
	km = KeyMap()
	km.bind("<Control-q>", "app.quit")

	r = KeyRouter(registry=reg, global_keymap=km)

	assert r.route_keyseq("<Control-q>", _ctx()) is True
	assert calls == ["app.quit"]


def test_keyrouter_mode_overrides_global():
	reg = CommandRegistry()
	calls: list[str] = []

	reg.register(Command(id="a", label="A", handler=lambda ctx: calls.append("a")))
	reg.register(Command(id="b", label="B", handler=lambda ctx: calls.append("b")))

	global_km = KeyMap()
	global_km.bind("<Control-p>", "a")

	mode_km = KeyMap()
	mode_km.bind("<Control-p>", "b")

	r = KeyRouter(registry=reg, global_keymap=global_km)
	r.register_mode_keymap("palette", mode_km)
	r.set_mode("palette")

	assert r.route_keyseq("<Control-p>", _ctx()) is True
	assert calls == ["b"]


def test_keyrouter_focus_overrides_mode_and_global():
	reg = CommandRegistry()
	calls: list[str] = []

	reg.register(Command(id="global", label="G", handler=lambda ctx: calls.append("global")))
	reg.register(Command(id="mode", label="M", handler=lambda ctx: calls.append("mode")))
	reg.register(Command(id="focus", label="F", handler=lambda ctx: calls.append("focus")))

	global_km = KeyMap()
	global_km.bind("<Control-k>", "global")

	mode_km = KeyMap()
	mode_km.bind("<Control-k>", "mode")

	focus_km = KeyMap()
	focus_km.bind("<Control-k>", "focus")

	focus_id: str | None = "editor"

	r = KeyRouter(registry=reg, global_keymap=global_km, focus_provider=lambda: focus_id)
	r.register_mode_keymap("edit", mode_km)
	r.register_component_keymap("editor", focus_km)
	r.set_mode("edit")

	assert r.route_keyseq("<Control-k>", _ctx()) is True
	assert calls == ["focus"]


def test_keyrouter_unhandled_returns_false():
	reg = CommandRegistry()
	reg.register(Command(id="x", label="X", handler=lambda ctx: None))

	global_km = KeyMap()
	r = KeyRouter(registry=reg, global_keymap=global_km)

	assert r.route_keyseq("<Control-q>", _ctx()) is False
