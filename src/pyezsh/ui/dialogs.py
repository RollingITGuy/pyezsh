# ---------------------------------------------------------------------------
# File: dialogs.py
# ---------------------------------------------------------------------------
# Description:
#	Dialog helpers for pyezsh.
#
# Notes:
#	- MVP: thin wrappers around tkinter.messagebox.
#	- Future: may evolve into proper component-based dialogs.
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date			Author						Change
# ---------------------------------------------------------------------------
# 01/06/2026	Paul G. LeDuc				Initial version
# ---------------------------------------------------------------------------

from __future__ import annotations

from typing import Any, Optional
import tkinter as tk
from tkinter import messagebox

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_showinfo(*, title: str, message: str, parent: tk.Misc | None) -> None:
	"""
	Show an info dialog, passing parent only when it is safe and non-None.

	This keeps mypy/pylance happy and avoids Tk edge-path errors.
	"""
	try:
		if parent is not None:
			# Some edge paths can hand us a widget that exists but isn't usable as a parent.
			# winfo_exists() is a cheap sanity check.
			try:
				if int(parent.winfo_exists()) == 1:
					messagebox.showinfo(title, message, parent=parent)
					return
			except Exception:
				# Fall through to parent-less messagebox
				pass

		messagebox.showinfo(title, message)
	except Exception:
		# Last-resort: don't crash the app over a dialog
		pass


def show_not_implemented(
	feature: str,
	*,
	parent: tk.Misc | None = None,
	logger: Any | None = None,
	telemetry: Any | None = None,
) -> None:
	"""
	Show a simple MVP 'Not Yet Implemented' message.
	"""
	msg = f"{feature}\n\nNot yet implemented."

	if telemetry is not None:
		try:
			telemetry.event("ui.not_implemented", {"feature": feature})
		except Exception:
			pass

	if logger is not None:
		try:
			logger.info("Not implemented: %s", feature)
		except Exception:
			pass

	_safe_showinfo(title="Not Yet Implemented", message=msg, parent=parent)
