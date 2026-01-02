# ---------------------------------------------------------------------------
# File: default_keys.py
# ---------------------------------------------------------------------------
# Description:
#	Default key bindings for pyezsh.
#
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date			Author						Change
# ---------------------------------------------------------------------------
# 12/31/2025	Paul G. LeDuc				Initial coding / release
# 01/01/2026	Paul G. LeDuc				Add Preferences bindings (Cmd+, / Ctrl+,)
# ---------------------------------------------------------------------------

from __future__ import annotations

import sys

from pyezsh.app.keys import KeyMap


def build_default_keymap() -> KeyMap:
	km = KeyMap()
	is_mac = sys.platform == "darwin"

	if is_mac:
		# Quit
		km.bind("<Command-q>", "app.quit")
		km.bind("<Command-KeyPress-q>", "app.quit")
		km.bind("<Meta-KeyPress-q>", "app.quit")  # occasional Tk mapping

		# Preferences (Cmd+,)
		km.bind("<Command-comma>", "app.preferences")
		km.bind("<Command-KeyPress-comma>", "app.preferences")
		km.bind("<Meta-KeyPress-comma>", "app.preferences")

		# Compatibility: allow Ctrl variants too
		km.bind("<Control-q>", "app.quit")
		km.bind("<Control-KeyPress-q>", "app.quit")
		km.bind("<Control-comma>", "app.preferences")
		km.bind("<Control-KeyPress-comma>", "app.preferences")
	else:
		# Windows/Linux
		km.bind("<Control-q>", "app.quit")
		km.bind("<Control-KeyPress-q>", "app.quit")
		km.bind("<Control-comma>", "app.preferences")
		km.bind("<Control-KeyPress-comma>", "app.preferences")

	return km
