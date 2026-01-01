# ---------------------------------------------------------------------------
# File: default_keys.py
# ---------------------------------------------------------------------------
# Description:
#	Default key bindings for pyezsh.
#
# Notes:
#	- This module only declares bindings (policy).
#	- CommandRegistry owns normalization and conflict rules.
#	- Bindings are platform-aware (Cmd on macOS, Ctrl elsewhere).
#	- On macOS, menus often emit shortcuts as KeyPress variants while posted/open.
#
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date			Author						Change
# ---------------------------------------------------------------------------
# 12/31/2025	Paul G. LeDuc				Initial coding / release
# 12/31/2025	Paul G. LeDuc				Add platform-aware quit binding
# 12/31/2025	Paul G. LeDuc				Add compatibility bindings + canonical forms
# 12/31/2025	Paul G. LeDuc				Add KeyPress variants for menu-posted behavior
# ---------------------------------------------------------------------------

from __future__ import annotations

import sys

from pyezsh.app.keys import KeyMap


def build_default_keymap() -> KeyMap:
	km = KeyMap()
	is_mac = sys.platform == "darwin"

	# Keep bindings in Tk keyseq form for now.
	# We'll formalize canonical shortcuts + normalization later.
	if is_mac:
		# Primary: macOS Quit (normal focus path)
		km.bind("<Command-q>", "app.quit")

		# When a Tk menu is posted/open, some builds emit KeyPress variants instead.
		km.bind("<Command-KeyPress-q>", "app.quit")

		# Fallback: some Tk builds map Command to Meta internally.
		km.bind("<Meta-KeyPress-q>", "app.quit")

		# Compatibility: cross-platform muscle memory / environments that still deliver Control-q.
		km.bind("<Control-q>", "app.quit")
		km.bind("<Control-KeyPress-q>", "app.quit")
	else:
		# Primary: Windows/Linux Quit
		km.bind("<Control-q>", "app.quit")
		km.bind("<Control-KeyPress-q>", "app.quit")

	# Optional future: add About if/when you bind it to a key
	# if is_mac:
	# 	km.bind("<Command-KeyPress-?>", "app.about")

	return km
