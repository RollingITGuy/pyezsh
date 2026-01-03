# ---------------------------------------------------------------------------
# File: telemetry.py
# Description:
#   Lightweight telemetry subsystem for pyezsh.
#
#   Provides a small, stable facade for emitting:
#     - events
#     - counters
#     - timers
#
#   Telemetry is intentionally decoupled from any backend implementation.
#   Backends are implemented as "sinks".
#
# Notes:
#   - Telemetry is optional and safe to call even when disabled.
#   - Default sink is NullSink (no-op).
#   - LogSink is provided for immediate visibility and demos.
#
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date			Author						Change
# ---------------------------------------------------------------------------
# 01/02/2026	Paul G. LeDuc				Initial coding / release
# ---------------------------------------------------------------------------

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol


# ---------------------------------------------------------------------------
# Telemetry data models
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class TelemetryEvent:
	name: str
	timestamp: float
	attrs: Dict[str, Any]


@dataclass(frozen=True, slots=True)
class TelemetryMetric:
	name: str
	value: float
	attrs: Dict[str, Any]


# ---------------------------------------------------------------------------
# Sink protocol
# ---------------------------------------------------------------------------

class TelemetrySink(Protocol):
	def emit_event(self, event: TelemetryEvent) -> None: ...
	def emit_metric(self, metric: TelemetryMetric) -> None: ...


# ---------------------------------------------------------------------------
# Sink implementations
# ---------------------------------------------------------------------------

class NullSink:
	"""
	No-op telemetry sink.
	Used when telemetry is disabled.
	"""

	def emit_event(self, event: TelemetryEvent) -> None:
		return

	def emit_metric(self, metric: TelemetryMetric) -> None:
		return


class LogSink:
	"""
	Telemetry sink that emits events and metrics via Python logging.
	"""

	def __init__(self, logger) -> None:
		self._log = logger

	def emit_event(self, event: TelemetryEvent) -> None:
		self._log.info(
			"telemetry.event name=%s attrs=%s",
			event.name,
			event.attrs,
		)

	def emit_metric(self, metric: TelemetryMetric) -> None:
		self._log.info(
			"telemetry.metric name=%s value=%s attrs=%s",
			metric.name,
			metric.value,
			metric.attrs,
		)

# ---------------------------------------------------------------------------
# Telemetry test sink
# ---------------------------------------------------------------------------

class MemorySink:
	"""
	In-memory telemetry sink for testing.

	Stores emitted events and metrics for inspection.
	"""

	def __init__(self) -> None:
		self.events: list[TelemetryEvent] = []
		self.metrics: list[TelemetryMetric] = []

	def emit_event(self, event: TelemetryEvent) -> None:
		self.events.append(event)

	def emit_metric(self, metric: TelemetryMetric) -> None:
		self.metrics.append(metric)

	def clear(self) -> None:
		self.events.clear()
		self.metrics.clear()


# ---------------------------------------------------------------------------
# Telemetry facade
# ---------------------------------------------------------------------------

class Telemetry:
	"""
	Telemetry facade used throughout the application.

	All methods are safe to call even when telemetry is disabled.
	"""

	def __init__(self, enabled: bool, sink: TelemetrySink) -> None:
		self._enabled = enabled
		self._sink = sink

	def event(self, name: str, attrs: Optional[Dict[str, Any]] = None) -> None:
		if not self._enabled:
			return

		event = TelemetryEvent(
			name=name,
			timestamp=time.time(),
			attrs=attrs or {},
		)
		self._sink.emit_event(event)

	def counter(
		self,
		name: str,
		value: int = 1,
		attrs: Optional[Dict[str, Any]] = None,
	) -> None:
		if not self._enabled:
			return

		metric = TelemetryMetric(
			name=name,
			value=float(value),
			attrs=attrs or {},
		)
		self._sink.emit_metric(metric)

	def timer(self, name: str, attrs: Optional[Dict[str, Any]] = None):
		return _TelemetryTimer(self, name, attrs or {})


class _TelemetryTimer:
	"""
	Context manager for timing operations.
	"""

	def __init__(
		self,
		telemetry: Telemetry,
		name: str,
		attrs: Dict[str, Any],
	) -> None:
		self._telemetry = telemetry
		self._name = name
		self._attrs = attrs
		self._start: float = 0.0

	def __enter__(self):
		self._start = time.perf_counter()
		return self

	def __exit__(self, exc_type, exc, tb):
		elapsed_ms = (time.perf_counter() - self._start) * 1000.0
		self._telemetry.counter(
			self._name,
			value=int(elapsed_ms),
			attrs=self._attrs,
		)


# ---------------------------------------------------------------------------
# Global helpers 
# ---------------------------------------------------------------------------

_telemetry: Optional[Telemetry] = None


def init_telemetry(cfg: Dict[str, Any], logger=None) -> None:
	"""
	Initialize global telemetry instance.

	Expected cfg keys:
		telemetry_enabled: bool
		telemetry_sink: "null" | "log"
	"""
	global _telemetry

	enabled = bool(cfg.get("telemetry_enabled", False))
	sink_name = cfg.get("telemetry_sink", "null")

	if not enabled:
		_telemetry = Telemetry(False, NullSink())
		return

	if sink_name == "log" and logger is not None:
		sink = LogSink(logger)
	else:
		sink = NullSink()

	_telemetry = Telemetry(enabled=True, sink=sink)


def get_telemetry() -> Telemetry:
	"""
	Return the global telemetry instance.
	Safe to call before init; returns a disabled telemetry instance.
	"""
	global _telemetry

	if _telemetry is None:
		_telemetry = Telemetry(False, NullSink())

	return _telemetry

