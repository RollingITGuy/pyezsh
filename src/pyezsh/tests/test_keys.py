# ---------------------------------------------------------------------------
# File: test_keys.py
# ---------------------------------------------------------------------------
# Description:
#   Unit tests for KeyMap (key sequence -> command id mapping).
#
# Notes:
#   - Pure unit tests; no Tkinter dependency.
#
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date			Author						Change
# ---------------------------------------------------------------------------
# 12/30/2025	Paul G. LeDuc				Initial tests
# 12/30/2025	ChatGPT						Add KeyMap coverage
# ---------------------------------------------------------------------------

import pytest

from pyezsh.app.keys import KeyMap


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
