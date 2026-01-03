# ---------------------------------------------------------------------------
# File: status.py
# ---------------------------------------------------------------------------
# Description:
#	Status service for pyezsh.
#
# Notes:
#	- Thin facade over StatusBar (if present).
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

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class StatusService:
	"""
	StatusService

	Small facade for setting status messages.

	If no statusbar is attached, calls become no-ops.
	"""
	statusbar: Optional[object] = None

	def set(self, section: str, message: str) -> None:
		sb = self.statusbar
		if sb is None:
			return
		set_text = getattr(sb, "set_text", None)
		if callable(set_text):
			set_text(section, message)

	def clear(self, section: str) -> None:
		self.set(section, "")

	def set_left(self, message: str) -> None:
		self.set("left", message)

	def set_middle(self, message: str) -> None:
		self.set("middle", message)

	def set_right(self, message: str) -> None:
		self.set("right", message)
