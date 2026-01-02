# ---------------------------------------------------------------------------
# File: test_keys.py
# ---------------------------------------------------------------------------
# Description:
#   Unit tests for KeyMap (key sequence -> command id mapping).
#
# Notes:
#   - Pure unit tests; no Tkinter dependency.
#   - apply() is tested with a FakeRegistry that captures bind_shortcut calls.
#
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date          Author                      Change
# ---------------------------------------------------------------------------
# 12/30/2025    Paul G. LeDuc               Initial tests
# 12/30/2025    Paul G. LeDuc               Add KeyMap coverage
# 01/01/2026    Paul G. LeDuc               Add apply() + Tk->canonical translation tests
# 01/01/2026    Paul G. LeDuc               Add KeyPress variant + resolve_keyseq tests
# ---------------------------------------------------------------------------

from __future__ import annotations

import pytest

from pyezsh.app.keys import KeyMap


class FakeRegistry:
	"""
	Minimal stand-in for a CommandRegistry-like object.
	Captures bind_shortcut calls made by KeyMap.apply().
	"""
	def __init__(self) -> None:
		self.calls: list[tuple[str, str, bool]] = []

	def bind_shortcut(self, shortcut: str, command_id: str, *, replace: bool = False) -> None:
		self.calls.append((shortcut, command_id, replace))


def test_bind_and_resolve():
	m = KeyMap()

	m.bind("<Control-q>", "quit")

	assert m.resolve("<Control-q>") == "quit"
	assert "<Control-q>" in m.keys()


def test_unbind_removes_binding():
	m = KeyMap()
	m.bind("<Control-q>", "quit")

	m.unbind("<Control-q>")

	assert m.resolve("<Control-q>") is None


def test_bind_overwrite_defaults_to_true():
	m = KeyMap()

	m.bind("<Control-q>", "quit")
	m.bind("<Control-q>", "other")

	assert m.resolve("<Control-q>") == "other"


def test_bind_rejects_existing_when_overwrite_false():
	m = KeyMap()

	m.bind("<Control-q>", "quit")

	with pytest.raises(ValueError):
		m.bind("<Control-q>", "other", overwrite=False)


def test_bind_rejects_empty_inputs():
	m = KeyMap()

	with pytest.raises(ValueError):
		m.bind("", "quit")

	with pytest.raises(ValueError):
		m.bind("<Control-q>", "")


def test_clear_removes_all_bindings():
	m = KeyMap()

	m.bind("<Control-q>", "quit")
	m.bind("<Control-s>", "save")

	assert len(m.keys()) == 2

	m.clear()

	assert m.resolve("<Control-q>") is None
	assert m.resolve("<Control-s>") is None
	assert m.keys() == []


# ---------------------------------------------------------------------------
# apply() / translation tests
# ---------------------------------------------------------------------------

def test_apply_binds_translated_shortcuts_to_registry():
	m = KeyMap()
	reg = FakeRegistry()

	m.bind("<Control-q>", "app.quit")
	m.bind("<Command-comma>", "app.preferences")
	m.bind("<Control-Shift-p>", "palette.open")

	# Non-<...> strings should pass through untouched to the registry
	m.bind("CTRL+K", "other.action")

	m.apply(reg, replace=False)

	# NOTE: <Command-comma> -> CMD+, (key token stays as ","; registry normalizes "CMD+,")
	assert reg.calls == [
		("CTRL+Q", "app.quit", False),
		("CMD+,", "app.preferences", False),
		("CTRL+SHIFT+P", "palette.open", False),
		("CTRL+K", "other.action", False),
	]


def test_apply_keypress_variants_translate_to_same_shortcut():
	"""
	Tk can emit KeyPress variants when menus are posted/open (notably on macOS):
		<Command-KeyPress-q> should translate the same as <Command-q>.
	"""
	m = KeyMap()
	reg = FakeRegistry()

	m.bind("<Command-q>", "app.quit")
	m.bind("<Command-KeyPress-q>", "app.quit")
	m.bind("<Control-KeyPress-q>", "app.quit")  # cross-platform compatibility form

	m.apply(reg, replace=False)

	# KeyPress token is ignored during translation, so these collapse to CMD+Q / CTRL+Q.
	assert reg.calls == [
		("CMD+Q", "app.quit", False),
		("CMD+Q", "app.quit", False),
		("CTRL+Q", "app.quit", False),
	]


def test_apply_passes_replace_flag_through():
	m = KeyMap()
	reg = FakeRegistry()

	m.bind("<Control-q>", "app.quit")

	m.apply(reg, replace=True)

	assert reg.calls == [
		("CTRL+Q", "app.quit", True),
	]


def test_apply_rejects_registry_without_bind_shortcut():
	m = KeyMap()
	m.bind("<Control-q>", "app.quit")

	class BadRegistry:
		pass

	with pytest.raises(TypeError):
		m.apply(BadRegistry())


# ---------------------------------------------------------------------------
# resolve_keyseq / normalize_keyseq tests (KeyRouter support)
# ---------------------------------------------------------------------------

def test_resolve_keyseq_prefers_exact_match_over_translation():
	"""
	If both a raw Tk keyseq and its canonical translation exist, the exact/raw
	binding should win (most-specific wins).
	"""
	m = KeyMap()
	m.bind("<Control-q>", "raw.quit")
	m.bind("CTRL+Q", "canon.quit")

	assert m.resolve_keyseq("<Control-q>") == "raw.quit"


def test_resolve_keyseq_translates_when_only_canonical_is_bound():
	m = KeyMap()
	m.bind("CTRL+Q", "canon.quit")

	assert m.resolve_keyseq("<Control-q>") == "canon.quit"


def test_resolve_keyseq_handles_keypress_variants():
	m = KeyMap()
	m.bind("CMD+Q", "app.quit")

	# When menus are posted/open, Tk may emit this form; it should still resolve.
	assert m.resolve_keyseq("<Command-KeyPress-q>") == "app.quit"


def test_normalize_keyseq_preserves_non_tk_strings():
	m = KeyMap()
	assert m.normalize_keyseq("CTRL+K") == "CTRL+K"


def test_normalize_keyseq_translates_named_punctuation():
	m = KeyMap()
	assert m.normalize_keyseq("<Command-comma>") == "CMD+,"
	assert m.normalize_keyseq("<Command-period>") == "CMD+."
