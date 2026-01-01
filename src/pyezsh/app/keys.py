# ---------------------------------------------------------------------------
# File: keys.py
# ---------------------------------------------------------------------------
# Description:
#	Key mapping for pyezsh (key sequence -> command id).
#
# Notes:
#	This module is key-binding policy/config and is intentionally UI-toolkit-agnostic.
#	The CommandRegistry owns shortcut normalization + execution.
#	This module can:
#	- store default bindings
#	- translate common UI key strings (e.g., Tk "<Control-q>") to canonical shortcuts
#	- apply bindings to a CommandRegistry
#
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date			Author						Change
# ---------------------------------------------------------------------------
# 12/30/2025	Paul G. LeDuc				Initial coding / release
# 12/31/2025	Paul G. LeDuc				Refactor to bind CommandRegistry shortcuts
# ---------------------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


def _tk_to_canonical(keyseq: str) -> str:
	"""
	Translate a common Tk key sequence to our canonical shortcut format.

	Examples:
		"<Control-q>"	-> "CTRL+Q"
		"<Control-Shift-p>" -> "CTRL+SHIFT+P"
		"<Alt-F4>"		-> "ALT+F4"

	Notes:
		- This is intentionally conservative. If it doesn't match a known pattern,
		  we return the original string and let the registry normalization decide.
	"""
	s = (keyseq or "").strip()
	if not s:
		return s

	# Only translate the common <...> form
	if not (s.startswith("<") and s.endswith(">")):
		return s

	inner = s[1:-1].strip()
	if not inner:
		return s

	parts = [p.strip() for p in inner.split("-") if p.strip()]
	if not parts:
		return s

	mods: list[str] = []
	key: Optional[str] = None

	for p in parts:
		up = p.upper()
		if up in ("CONTROL", "CTRL"):
			mods.append("CTRL")
			continue
		if up in ("ALT", "OPTION"):
			mods.append("ALT")
			continue
		if up == "SHIFT":
			mods.append("SHIFT")
			continue
		if up in ("COMMAND", "CMD", "META"):
			mods.append("CMD")
			continue

		# Assume last non-mod token is the key
		key = up

	if key is None:
		return s

	# De-dupe mods, stable order
	order = ("CTRL", "ALT", "SHIFT", "CMD")
	modset = {m for m in mods}
	ordered_mods = [m for m in order if m in modset]

	if ordered_mods:
		return "+".join([*ordered_mods, key])

	return key


@dataclass(slots=True)
class KeyMap:
	"""
	KeyMap

	Stores default bindings of key sequences to command ids.

	Important:
	- KeyMap does not execute commands.
	- KeyMap does not validate command ids.
	- KeyMap applies bindings to CommandRegistry which owns normalization/collisions.

	Stored key strings may be:
	- canonical shortcuts (e.g., "Ctrl+Q")
	- UI strings (e.g., Tk "<Control-q>") which will be translated on apply()
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

	def apply(self, registry: object, *, replace: bool = False) -> None:
		"""
		Apply all bindings to a CommandRegistry-like object.

		The registry is expected to expose:
			bind_shortcut(shortcut: str, command_id: str, replace: bool = False) -> None

		We translate common Tk "<...>" key sequences to canonical shortcuts first.
		"""
		bind_fn = getattr(registry, "bind_shortcut", None)
		if bind_fn is None or not callable(bind_fn):
			raise TypeError("registry must provide a callable bind_shortcut(shortcut, command_id, replace=...)")

		for keyseq, command_id in self._bindings.items():
			shortcut = _tk_to_canonical(keyseq)
			bind_fn(shortcut, command_id, replace=replace)
