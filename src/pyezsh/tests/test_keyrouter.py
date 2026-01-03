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
# 01/03/2026	Paul G. LeDuc				Add telemetry assertions (MemorySink)
# ---------------------------------------------------------------------------

from __future__ import annotations

from pyezsh.app.commands import Command, CommandContext, CommandRegistry
from pyezsh.app.keys import KeyMap
from pyezsh.app.keyrouter import KeyRouter
from pyezsh.core.telemetry import MemorySink, Telemetry


def _ctx() -> CommandContext:
	return CommandContext(app=None, state={}, services={}, extra={})


def _telemetry() -> tuple[Telemetry, MemorySink]:
	sink = MemorySink()
	return Telemetry(enabled=True, sink=sink), sink


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

	r = KeyRouter(registry=reg, global_keymap=global_km)
	r.set_focus_provider(lambda: focus_id)

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


def test_keyrouter_telemetry_global_dispatch():
	reg = CommandRegistry()
	calls: list[str] = []

	reg.register(Command(id="app.quit", label="Quit", handler=lambda ctx: calls.append("app.quit")))
	km = KeyMap()
	km.bind("<Control-q>", "app.quit")

	telemetry, sink = _telemetry()
	r = KeyRouter(registry=reg, global_keymap=km, telemetry=telemetry)

	assert r.route_keyseq("<Control-q>", _ctx()) is True
	assert calls == ["app.quit"]

	# keys.pressed metric emitted
	assert len(sink.metrics) == 1
	assert sink.metrics[0].name == "keys.pressed"
	assert sink.metrics[0].value == 1.0
	assert sink.metrics[0].attrs["keyseq"] == "<Control-q>"

	# command.dispatched event emitted (global layer)
	assert any(e.name == "command.dispatched" for e in sink.events)
	ev = next(e for e in sink.events if e.name == "command.dispatched")
	assert ev.attrs["command_id"] == "app.quit"
	assert ev.attrs["keyseq"] == "<Control-q>"
	assert ev.attrs["layer"] == "global"


def test_keyrouter_telemetry_mode_dispatch_layer():
	reg = CommandRegistry()
	calls: list[str] = []

	reg.register(Command(id="a", label="A", handler=lambda ctx: calls.append("a")))
	reg.register(Command(id="b", label="B", handler=lambda ctx: calls.append("b")))

	global_km = KeyMap()
	global_km.bind("<Control-p>", "a")

	mode_km = KeyMap()
	mode_km.bind("<Control-p>", "b")

	telemetry, sink = _telemetry()
	r = KeyRouter(registry=reg, global_keymap=global_km, telemetry=telemetry)
	r.register_mode_keymap("palette", mode_km)
	r.set_mode("palette")

	assert r.route_keyseq("<Control-p>", _ctx()) is True
	assert calls == ["b"]

	ev = next(e for e in sink.events if e.name == "command.dispatched")
	assert ev.attrs["command_id"] == "b"
	assert ev.attrs["layer"] == "mode"


def test_keyrouter_telemetry_component_dispatch_layer():
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

	telemetry, sink = _telemetry()
	r = KeyRouter(registry=reg, global_keymap=global_km, telemetry=telemetry)
	r.set_focus_provider(lambda: focus_id)

	r.register_mode_keymap("edit", mode_km)
	r.register_component_keymap("editor", focus_km)
	r.set_mode("edit")

	assert r.route_keyseq("<Control-k>", _ctx()) is True
	assert calls == ["focus"]

	ev = next(e for e in sink.events if e.name == "command.dispatched")
	assert ev.attrs["command_id"] == "focus"
	assert ev.attrs["layer"] == "component"


def test_keyrouter_telemetry_unhandled_key_emits_event():
	reg = CommandRegistry()
	reg.register(Command(id="x", label="X", handler=lambda ctx: None))

	global_km = KeyMap()

	telemetry, sink = _telemetry()
	r = KeyRouter(registry=reg, global_keymap=global_km, telemetry=telemetry)

	assert r.route_keyseq("<Control-q>", _ctx()) is False

	# keys.pressed metric emitted even for unhandled
	assert len(sink.metrics) == 1
	assert sink.metrics[0].name == "keys.pressed"
	assert sink.metrics[0].attrs["keyseq"] == "<Control-q>"

	# key.unhandled event emitted
	assert any(e.name == "key.unhandled" for e in sink.events)
	ev = next(e for e in sink.events if e.name == "key.unhandled")
	assert ev.attrs["keyseq"] == "<Control-q>"
