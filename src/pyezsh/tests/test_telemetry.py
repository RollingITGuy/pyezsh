# ---------------------------------------------------------------------------
# File: test_telemetry.py
# ---------------------------------------------------------------------------
# Description:
#	Unit tests for pyezsh.core.telemetry.
#
# Notes:
#	- Pure unit tests; no Tkinter dependency.
#	- Uses MemorySink for deterministic assertions.
#
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date			Author						Change
# ---------------------------------------------------------------------------
# 01/03/2026	Paul G. LeDuc				Initial tests
# ---------------------------------------------------------------------------

from __future__ import annotations

from pyezsh.core.telemetry import (
	MemorySink,
	NullSink,
	Telemetry,
	get_telemetry,
	init_telemetry,
)


def test_telemetry_disabled_is_noop():
	sink = MemorySink()
	t = Telemetry(enabled=False, sink=sink)

	t.event("app.start", {"x": 1})
	t.counter("keys.pressed", 3, {"k": "v"})

	with t.timer("command.duration_ms", {"command_id": "x"}):
		pass

	assert sink.events == []
	assert sink.metrics == []


def test_telemetry_event_emits_to_sink():
	sink = MemorySink()
	t = Telemetry(enabled=True, sink=sink)

	t.event("app.start", {"foo": "bar"})

	assert len(sink.events) == 1
	ev = sink.events[0]
	assert ev.name == "app.start"

	# slots=True dataclasses don't have __dict__
	assert hasattr(ev, "timestamp")
	assert isinstance(ev.timestamp, float)
	assert ev.timestamp > 0.0


def test_telemetry_counter_emits_metric_to_sink():
	sink = MemorySink()
	t = Telemetry(enabled=True, sink=sink)

	t.counter("keys.pressed", 2, {"keyseq": "<Control-q>"})

	assert len(sink.metrics) == 1
	m = sink.metrics[0]
	assert m.name == "keys.pressed"
	assert m.value == 2.0
	assert m.attrs["keyseq"] == "<Control-q>"


def test_telemetry_timer_emits_metric():
	sink = MemorySink()
	t = Telemetry(enabled=True, sink=sink)

	with t.timer("command.duration_ms", {"command_id": "app.quit"}):
		pass

	assert len(sink.metrics) == 1
	m = sink.metrics[0]
	assert m.name == "command.duration_ms"
	assert m.value >= 0.0
	assert m.attrs["command_id"] == "app.quit"


def test_memorysink_clear():
	sink = MemorySink()
	t = Telemetry(enabled=True, sink=sink)

	t.event("x")
	t.counter("y")

	assert len(sink.events) == 1
	assert len(sink.metrics) == 1

	sink.clear()

	assert sink.events == []
	assert sink.metrics == []


def test_get_telemetry_safe_before_init_returns_disabled():
	# get_telemetry() is safe before init_telemetry()
	t = get_telemetry()

	# We can't access private fields directly; this checks behavior:
	# emitting should not raise and should be a no-op by default.
	t.event("should.not.raise")
	t.counter("should.not.raise", 1)

	# If get_telemetry() returned an enabled instance by default, this would be surprising.
	# We can at least assert it is a Telemetry instance and doesn't error.
	assert isinstance(t, Telemetry)


def test_init_telemetry_disabled_sets_global_noop():
	init_telemetry({"telemetry_enabled": False})

	t = get_telemetry()
	assert isinstance(t, Telemetry)

	# Should not raise; default sink is NullSink inside Telemetry(False,...)
	t.event("disabled.noop")
	t.counter("disabled.noop", 1)


def test_init_telemetry_enabled_without_logger_uses_nullsink():
	# sink_name log, but no logger -> falls back to NullSink
	init_telemetry({"telemetry_enabled": True, "telemetry_sink": "log"}, logger=None)

	t = get_telemetry()
	assert isinstance(t, Telemetry)

	# Behavior check: should not raise.
	t.event("enabled.nullsink")
	t.counter("enabled.nullsink", 1)


def test_init_telemetry_enabled_unknown_sink_uses_nullsink():
	# unknown sink -> falls back to NullSink
	init_telemetry({"telemetry_enabled": True, "telemetry_sink": "nope"}, logger=None)

	t = get_telemetry()
	assert isinstance(t, Telemetry)

	# Should not raise.
	t.event("enabled.unknownsink")
	t.counter("enabled.unknownsink", 1)
