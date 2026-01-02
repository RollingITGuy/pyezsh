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
# 01/01/2026	Paul G. LeDuc				Public tk_to_canonical + punctuation key normalization
# 01/01/2026	Paul G. LeDuc				Add KeyMap.resolve_keyseq/normalize_keyseq for KeyRouter
# 01/01/2026	Paul G. LeDuc				Ignore Tk KeyPress/KeyRelease noise in tk_to_canonical
# ---------------------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# Common Tk “named” punctuation keys we want to normalize to symbols so they match
# CommandRegistry.normalize_shortcut usage like "CMD+," (not "CMD+COMMA").
_TK_KEYNAME_TO_SYMBOL: dict[str, str] = {
	"COMMA": ",",
	"PERIOD": ".",
	"DOT": ".",
	"SLASH": "/",
	"BACKSLASH": "\\",
	"MINUS": "-",
	"UNDERSCORE": "_",
	"EQUAL": "=",
	"PLUS": "+",
	"SEMICOLON": ";",
	"COLON": ":",
	"APOSTROPHE": "'",
	"QUOTEDBL": '"',
	"BRACKETLEFT": "[",
	"BRACKETRIGHT": "]",
	"BRACELEFT": "{",
	"BRACERIGHT": "}",
	"GRAVE": "`",
	"ASCIITILDE": "~",
}

# Tk sometimes includes event-type noise inside the <> sequence when menus are posted,
# e.g. "<Command-KeyPress-q>". Treat these tokens as ignorable.
_TK_IGNORED_TOKENS: set[str] = {
	"KEYPRESS",
	"KEYRELEASE",
}


def tk_to_canonical(keyseq: str) -> str:
	"""
	Translate a common Tk key sequence to our canonical shortcut format.

	Examples:
		"<Control-q>"			-> "CTRL+Q"
		"<Control-Shift-p>"		-> "CTRL+SHIFT+P"
		"<Alt-F4>"				-> "ALT+F4"
		"<Command-comma>"		-> "CMD+,"
		"<Command-KeyPress-q>"  -> "CMD+Q"

	Notes:
		- Conservative: if it doesn't match a known pattern, returns original string.
		- Normalizes named punctuation keys (comma/period/etc) to symbols so that
		  key bindings align with Command.shortcut strings like "CMD+,".
		- Ignores Tk KeyPress/KeyRelease noise when present in the sequence.
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

		# Ignore event-type noise tokens like KeyPress/KeyRelease
		if up in _TK_IGNORED_TOKENS:
			continue

		# Modifiers
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

	# Normalize named punctuation keys to symbols (COMMA -> ",", etc)
	key = _TK_KEYNAME_TO_SYMBOL.get(key, key)

	# If the "key" is a single alpha character, force uppercase (q -> Q)
	if len(key) == 1 and key.isalpha():
		key = key.upper()

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

	Stores bindings of key sequences to command ids.

	Stored key strings may be:
	- canonical shortcuts (e.g., "CTRL+Q", "CMD+,")
	- UI strings (e.g., Tk "<Control-q>") which can be translated via tk_to_canonical()
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
		"""
		Direct lookup only (no translation). Useful for exact/raw matches.
		"""
		return self._bindings.get(keyseq)

	def normalize_keyseq(self, keyseq: str) -> str:
		"""
		Normalize a key sequence for routing/lookup:
		- Tk "<...>" form -> canonical (e.g., "<Command-comma>" -> "CMD+,")
		- non-<...> strings pass through unchanged
		"""
		return tk_to_canonical(keyseq)

	def resolve_keyseq(self, keyseq: str) -> Optional[str]:
		"""
		Resolve a key sequence to a command id, trying:
		  1) exact/raw match
		  2) translated canonical match (for Tk "<...>" inputs)
		"""
		if not keyseq:
			return None

		cid = self._bindings.get(keyseq)
		if cid:
			return cid

		canon = tk_to_canonical(keyseq)
		if canon != keyseq:
			return self._bindings.get(canon)

		return None

	# Back-compat alias (older call sites may use this name)
	def resolve_with_translation(self, keyseq: str) -> Optional[str]:
		return self.resolve_keyseq(keyseq)

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
		"""
		bind_fn = getattr(registry, "bind_shortcut", None)
		if bind_fn is None or not callable(bind_fn):
			raise TypeError("registry must provide a callable bind_shortcut(shortcut, command_id, replace=...)")

		for keyseq, command_id in self._bindings.items():
			shortcut = tk_to_canonical(keyseq)
			bind_fn(shortcut, command_id, replace=replace)
