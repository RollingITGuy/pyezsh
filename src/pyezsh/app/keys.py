# ---------------------------------------------------------------------------
# File: keys.py
# ---------------------------------------------------------------------------
# Description:
#   Key mapping for pyezsh (key sequence -> command id).
#
# Notes:
#   This module is pure mapping and is intentionally UI-toolkit-agnostic.
#   Tkinter integration (binding events) will be added later.
#
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date			Author						Change
# ---------------------------------------------------------------------------
# 12/30/2025	Paul G. LeDuc				Initial coding / release
# 12/30/2025	Paul G. LeDuc				Add KeyMap
# ---------------------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class KeyMap:
	"""
	KeyMap

	Stores bindings of key sequences (e.g., "<Control-q>") to command ids (e.g., "quit").
	"""
	_bindings: dict[str, str] = field(default_factory=dict)

	def bind(self, keyseq: str, command_id: str, *, overwrite: bool = True) -> None:
		if not keyseq:
			raise ValueError("keyseq must be a non-empty string")
		if not command_id:
			raise ValueError("command_id must be a non-empty string")

		if not overwrite and keyseq in self._bindings:
			raise ValueError(f"Key binding already exists for {keyseq!r}")

		self._bindings[keyseq] = command_id

	def unbind(self, keyseq: str) -> None:
		self._bindings.pop(keyseq, None)

	def resolve(self, keyseq: str) -> Optional[str]:
		return self._bindings.get(keyseq)

	def keys(self) -> list[str]:
		return list(self._bindings.keys())

	def items(self) -> list[tuple[str, str]]:
		return list(self._bindings.items())

	def clear(self) -> None:
		self._bindings.clear()
