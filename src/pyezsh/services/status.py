# ---------------------------------------------------------------------------
# File: status.py
# ---------------------------------------------------------------------------
# Description:
#	Status service for pyezsh.
#
# Notes:
#	- StatusService owns status state (sections + last key/command).
#	- UI widgets (e.g., StatusBar) may be attached as a sink.
#	- Commands should prefer this service vs importing UI components.
#	- Safe to call even if no StatusBar is attached.
#
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date			Author						Change
# ---------------------------------------------------------------------------
# 01/03/2026	Paul G. LeDuc				Initial coding / release
# ---------------------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Optional, Protocol, runtime_checkable


@runtime_checkable
class StatusSink(Protocol):
	"""
	Minimal interface implemented by UI status widgets.
	"""

	def set_text(self, section: str, value: str) -> None: ...


@dataclass(frozen=True, slots=True)
class StatusSnapshot:
	"""
	Immutable snapshot of status state.
	"""

	sections: Dict[str, str]
	last_keyseq: str = ""
	last_command_id: str = ""


@dataclass(slots=True)
class StatusService:
	"""
	StatusService

	Owns status state and optionally publishes updates to a UI sink.
	"""

	# Core state
	sections: Dict[str, str] = field(
		default_factory=lambda: {"left": "", "middle": "", "right": ""}
	)
	last_keyseq: str = ""
	last_command_id: str = ""

	# Optional UI sink and change callback
	sink: Optional[StatusSink] = None
	on_change: Optional[Callable[[StatusSnapshot], None]] = None

	# -----------------------------------------------------------------------
	# Wiring
	# -----------------------------------------------------------------------

	def attach_sink(self, sink: Optional[StatusSink]) -> None:
		"""
		Attach or detach a UI sink (e.g., StatusBar).
		"""
		self.sink = sink
		self._publish()

	def set_on_change(self, cb: Optional[Callable[[StatusSnapshot], None]]) -> None:
		"""
		Register a callback invoked whenever state changes.
		"""
		self.on_change = cb
		if cb:
			cb(self.snapshot())

	def snapshot(self) -> StatusSnapshot:
		"""
		Return an immutable snapshot of current status state.
		"""
		return StatusSnapshot(
			sections=dict(self.sections),
			last_keyseq=self.last_keyseq,
			last_command_id=self.last_command_id,
		)

	# -----------------------------------------------------------------------
	# Mutators
	# -----------------------------------------------------------------------

	def set(self, section: str, message: str) -> None:
		self.sections[section] = message
		if self.sink:
			self.sink.set_text(section, message)
		self._notify()

	def clear(self, section: str) -> None:
		self.set(section, "")

	def set_left(self, message: str) -> None:
		self.set("left", message)

	def set_middle(self, message: str) -> None:
		self.set("middle", message)

	def set_right(self, message: str) -> None:
		self.set("right", message)

	def set_last_keyseq(self, keyseq: str) -> None:
		self.last_keyseq = keyseq
		self._notify()

	def set_last_command_id(self, command_id: str) -> None:
		self.last_command_id = command_id
		self._notify()

	# -----------------------------------------------------------------------
	# Internal helpers
	# -----------------------------------------------------------------------

	def _publish(self) -> None:
		"""
		Push current section state into the sink (if attached).

		Do not clobber UI defaults with empty service values.
		"""
		if not self.sink:
			return

		for section, value in self.sections.items():
			if value == "":
				continue
			self.sink.set_text(section, value)

	def _notify(self) -> None:
		"""
		Notify registered change callback.
		"""
		if self.on_change:
			self.on_change(self.snapshot())
