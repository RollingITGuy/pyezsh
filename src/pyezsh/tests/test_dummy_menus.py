# ---------------------------------------------------------------------------
# File: test_dummy_menus.py
# ---------------------------------------------------------------------------
# Description:
#	Tests for MVP dummy menu command registration.
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date			Author						Change
# ---------------------------------------------------------------------------
# 01/06/2026	Paul G. LeDuc				Initial version
# ---------------------------------------------------------------------------

from __future__ import annotations

from pyezsh.app.app import App


def test_dummy_menu_commands_registered() -> None:
	app = App(width=300, height=200, title="test", cfg={"scrollable": False})
	try:
		assert app.commands.has("mvp.file.open")
		assert app.commands.has("mvp.help.docs")
	finally:
		try:
			app.destroy()
		except Exception:
			pass
