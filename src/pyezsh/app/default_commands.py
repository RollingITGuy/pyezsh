# ---------------------------------------------------------------------------
# File: default_commands.py
# ---------------------------------------------------------------------------
# Description:
#	Default command definitions for pyezsh.
#
# Notes:
#	- Keep this small and safe.
#	- Useful for early UI plumbing (menubar, key routing).
#	- Shortcuts are platform-aware (CMD on macOS, CTRL elsewhere).
#
# TODO (Key routing formalization):
#	We will standardize three related concepts:
#	1) Canonical shortcuts:
#		- Stored on Command.shortcut (e.g., "CMD+Q", "CTRL+Q")
#		- Used by CommandRegistry for shortcut->command resolution
#	2) Display accelerators:
#		- Rendered in the MenuBar UI (e.g., "⌘Q" on macOS)
#		- May differ from canonical shortcut strings
#	3) Tk event keyseq normalization:
#		- Convert Tk events (e.g., "<Command-q>", "<Control-q>") into the
#		  canonical shortcut format so routing is consistent across platforms.
#
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date			Author						Change
# ---------------------------------------------------------------------------
# 12/31/2025	Paul G. LeDuc				Initial coding / release
# 12/31/2025	Paul G. LeDuc				Add platform-aware shortcuts
# 12/31/2025	Paul G. LeDuc				Document key routing formalization plan
# 12/31/2025	Paul G. LeDuc				Improve About/Quit labels + About dialog
# 01/01/2026	Paul G. LeDuc				Add Preferences command (Apple menu friendly)
# ---------------------------------------------------------------------------

from __future__ import annotations

import sys
from tkinter import messagebox

from pyezsh.app.commands import Command, CommandContext, CommandRegistry


def _is_mac() -> bool:
	return sys.platform == "darwin"


def register_default_commands(registry: CommandRegistry) -> None:
	# Canonical shortcut strings (match CommandRegistry.normalize_shortcut expectations)
	quit_shortcut = "CMD+Q" if _is_mac() else "CTRL+Q"
	prefs_shortcut = "CMD+," if _is_mac() else "CTRL+,"

	# Menu-facing labels (especially important for the macOS Apple menu)
	about_label = "About pyezsh" if _is_mac() else "About"
	quit_label = "Quit pyezsh" if _is_mac() else "Quit"
	prefs_label = "Preferences…" if _is_mac() else "Preferences..."

	def _app_quit(ctx: CommandContext) -> None:
		# Route quit through Tk shutdown. Keep it defensive.
		try:
			ctx.app.destroy()
		except Exception:
			pass

	def _app_about(ctx: CommandContext) -> None:
		# Keep it safe and minimal; swap for a real modal later.
		try:
			messagebox.showinfo(
				title="About pyezsh",
				message="pyezsh\n\nA lightweight Python shell UI.\n",
				parent=ctx.app,
			)
		except Exception:
			print("pyezsh - About")

	def _app_preferences(ctx: CommandContext) -> None:
		# Placeholder until a real Preferences window exists.
		try:
			messagebox.showinfo(
				title="Preferences",
				message="Preferences are not implemented yet.\n",
				parent=ctx.app,
			)
		except Exception:
			print("pyezsh - Preferences (not implemented)")

	registry.register(Command(
		id="app.about",
		label=about_label,
		description="Show application information.",
		handler=_app_about,
		order=10,
	))

	registry.register(Command(
		id="app.preferences",
		label=prefs_label,
		description="Open application preferences.",
		shortcut=prefs_shortcut,
		handler=_app_preferences,
		order=15,
	))

	registry.register(Command(
		id="app.quit",
		label=quit_label,
		description="Exit pyezsh.",
		shortcut=quit_shortcut,
		handler=_app_quit,
		order=20,
	))
