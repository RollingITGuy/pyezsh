# ---------------------------------------------------------------------------
# File: test_default_commands.py
# ---------------------------------------------------------------------------
# Description:
#	Unit tests for default command registration.
#
# Notes:
#	- Verifies that register_default_commands() registers core app commands:
#	  About, Preferences, Quit.
#	- Ensures platform-aware labels and shortcuts behave correctly.
#	- Does not invoke Tk UI elements or handlers.
#
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date			Author						Change
# ---------------------------------------------------------------------------
# 01/01/2026	Paul G. LeDuc				Initial tests for default command registration
# ---------------------------------------------------------------------------

def test_register_default_commands_registers_about_preferences_quit(monkeypatch):
	from pyezsh.app.default_commands import register_default_commands
	from pyezsh.app.commands import CommandRegistry

	# -----------------------------------------------------------------------
	# macOS behavior
	# -----------------------------------------------------------------------
	monkeypatch.setattr("pyezsh.app.default_commands.sys.platform", "darwin")

	registry = CommandRegistry()
	register_default_commands(registry)

	assert registry.has("app.about")
	assert registry.has("app.preferences")
	assert registry.has("app.quit")

	about = registry.get("app.about")
	prefs = registry.get("app.preferences")
	quit_cmd = registry.get("app.quit")

	assert about is not None
	assert prefs is not None
	assert quit_cmd is not None

	assert about.label == "About pyezsh"
	assert prefs.label == "Preferences…"
	assert quit_cmd.label == "Quit pyezsh"

	assert prefs.shortcut == "CMD+,"
	assert quit_cmd.shortcut == "CMD+Q"

	# -----------------------------------------------------------------------
	# non-mac behavior (Linux / Windows)
	# -----------------------------------------------------------------------
	monkeypatch.setattr("pyezsh.app.default_commands.sys.platform", "linux")

	registry2 = CommandRegistry()
	register_default_commands(registry2)

	about2 = registry2.get("app.about")
	prefs2 = registry2.get("app.preferences")
	quit2 = registry2.get("app.quit")

	assert about2 is not None
	assert prefs2 is not None
	assert quit2 is not None

	assert about2.label == "About"
	assert prefs2.label == "Preferences..."
	assert quit2.label == "Quit"

	assert prefs2.shortcut == "CTRL+,"
	assert quit2.shortcut == "CTRL+Q"
