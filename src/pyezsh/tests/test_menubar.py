# ---------------------------------------------------------------------------
# File: test_menubar.py
# ---------------------------------------------------------------------------
# Description:
#	Unit tests for MenuBar logic.
#
# Notes:
#	- These tests intentionally avoid Tkinter rendering. They use a FakeMenu to capture
#	  MenuBar output from _populate_dropdown().
#	- Submenu support requires FakeMenu.add_cascade().
#
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date			Author						Change
# ---------------------------------------------------------------------------
# 01/01/2026	Paul G. LeDuc				Initial tests for MenuBar filtering + dropdown rendering
# 01/01/2026	Paul G. LeDuc				Add submenu + recursive filtering tests (MenuDef expressiveness)
# 01/01/2026	Paul G. LeDuc				Use pyezsh.ui public exports + loosen legacy item typing
# ---------------------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import tkinter as tk

from pyezsh.app.commands import Command, CommandContext, CommandRegistry
from pyezsh.ui import (
	MenuBar,
	MenuDef,
	MenuCommand,
	MenuSeparator,
	MenuSubmenu,
)


def _ctx() -> CommandContext:
	return CommandContext(app=None, state={}, services={}, extra={})


@dataclass
class _FakeMenuEntry:
	kind: str
	attrs: dict[str, Any]


class FakeMenu:
	"""
	Minimal stand-in for tk.Menu used by MenuBar._populate_dropdown() tests.
	"""
	def __init__(self) -> None:
		self.entries: list[_FakeMenuEntry] = []

	def add_separator(self) -> None:
		self.entries.append(_FakeMenuEntry(kind="sep", attrs={}))

	def add_command(self, **kwargs: Any) -> None:
		self.entries.append(_FakeMenuEntry(kind="cmd", attrs=dict(kwargs)))

	def add_cascade(self, **kwargs: Any) -> None:
		self.entries.append(_FakeMenuEntry(kind="cascade", attrs=dict(kwargs)))


# ---------------------------------------------------------------------------
# 1) Filtering tests (macOS duplication prevention)
# ---------------------------------------------------------------------------

def test_filter_removes_about_quit_preferences_and_cleans_separators():
	mb = MenuBar(
		menus=(
			MenuDef("App", items=("app.about", None, "app.preferences", None, "app.quit")),
			MenuDef("File", items=(None, "file.open", None, None, "app.quit", None, "file.close", None)),
			MenuDef("Help", items=("help.docs", None, "app.about", None, "help.support")),
		),
		auto_app_menu=True,
	)

	out = mb._filter_macos_reserved_items(mb._menus)

	# "App" menu becomes empty and should be dropped
	assert [m.label for m in out] == ["File", "Help"]

	file_menu = next(m for m in out if m.label == "File")
	help_menu = next(m for m in out if m.label == "Help")

	# Reserved items removed (legacy tuple form)
	assert "app.about" not in file_menu.items
	assert "app.quit" not in file_menu.items
	assert "app.preferences" not in file_menu.items

	# Separator cleanup: no leading/trailing, no duplicates
	assert file_menu.items[0] is not None
	assert file_menu.items[-1] is not None
	for a, b in zip(file_menu.items, file_menu.items[1:]):
		assert not (a is None and b is None)

	assert help_menu.items[0] is not None
	assert help_menu.items[-1] is not None
	for a, b in zip(help_menu.items, help_menu.items[1:]):
		assert not (a is None and b is None)


def test_get_effective_menus_filters_only_on_macos_with_auto_app_menu_true():
	menus = (
		MenuDef("App", items=("app.about", None, "app.preferences", None, "app.quit")),
		MenuDef("File", items=("file.open", None, "app.quit", None, "file.close")),
	)

	# macOS + auto_app_menu=True => filtered
	mb1 = MenuBar(menus=menus, auto_app_menu=True)
	eff1 = mb1._get_effective_menus(is_mac=True)
	assert [m.label for m in eff1] == ["File"]
	assert eff1[0].items == (MenuCommand("file.open"), MenuSeparator(), MenuCommand("file.close"))

	# macOS + auto_app_menu=False => unchanged
	mb2 = MenuBar(menus=menus, auto_app_menu=False)
	eff2 = mb2._get_effective_menus(is_mac=True)
	assert eff2 == menus

	# non-mac => unchanged regardless
	mb3 = MenuBar(menus=menus, auto_app_menu=True)
	eff3 = mb3._get_effective_menus(is_mac=False)
	assert eff3 == menus


def test_filter_drops_menu_when_only_reserved_items_present():
	mb = MenuBar(
		menus=(
			MenuDef("OnlyReserved", items=(None, "app.about", None, "app.preferences", None, "app.quit", None)),
			MenuDef("Other", items=("x",)),
		),
		auto_app_menu=True,
	)

	out = mb._filter_macos_reserved_items(mb._menus)
	assert [m.label for m in out] == ["Other"]
	assert out[0].items == (MenuCommand("x"),)

def test_filter_removes_reserved_items_inside_submenus():
	mb = MenuBar(
		menus=(
			MenuDef(
				"Top",
				items=(
					MenuSubmenu(
						label="App",
						items=(
							MenuCommand("app.about"),
							MenuSeparator(),
							MenuCommand("app.preferences"),
							MenuSeparator(),
							MenuCommand("app.quit"),
						),
					),
					MenuSubmenu(
						label="File",
						items=(
							MenuCommand("file.open"),
							MenuSeparator(),
							MenuCommand("app.quit"),
							MenuSeparator(),
							MenuCommand("file.close"),
						),
					),
				),
			),
		),
		auto_app_menu=True,
	)

	out = mb._filter_macos_reserved_items(mb._menus)

	assert len(out) == 1
	assert out[0].label == "Top"

	# After filtering, "App" submenu should be dropped; "File" should remain.
	top_items = list(mb._normalize_items(out[0].items))
	submenus = [it for it in top_items if isinstance(it, MenuSubmenu)]
	labels = [s.label for s in submenus]

	assert "App" not in labels
	assert "File" in labels


# ---------------------------------------------------------------------------
# 5) Headless dropdown rendering tests (FakeMenu)
# ---------------------------------------------------------------------------

def test_populate_dropdown_renders_commands_and_separators_and_state():
	registry = CommandRegistry()

	# Commands used by populate
	open_cmd = Command(id="file.open", label="Open", handler=lambda ctx: None, shortcut="Ctrl+O")
	close_cmd = Command(id="file.close", label="Close", handler=lambda ctx: None)
	hidden_cmd = Command(id="file.hidden", label="Hidden", handler=lambda ctx: None)
	disabled_cmd = Command(id="file.disabled", label="Disabled", handler=lambda ctx: None)

	registry.register(open_cmd)
	registry.register(close_cmd)
	registry.register(hidden_cmd)
	registry.register(disabled_cmd)

	# Force visibility/enablement deterministically without relying on Command internals
	visible: dict[str, bool] = {
		"file.open": True,
		"file.close": True,
		"file.hidden": False,		# should not render
		"file.disabled": True,
	}
	enabled: dict[str, bool] = {
		"file.open": True,
		"file.close": True,
		"file.hidden": True,
		"file.disabled": False,		# should render disabled
	}

	registry.is_visible = lambda cid, ctx: visible.get(cid, True)	# type: ignore[method-assign]
	registry.is_enabled = lambda cid, ctx: enabled.get(cid, True)	# type: ignore[method-assign]

	mb = MenuBar()
	fake = FakeMenu()

	items = (
		"file.open",
		None,
		"file.hidden",
		"file.disabled",
		"file.close",
		"missing.command",	# should be ignored
	)

	mb._populate_dropdown(cast(tk.Menu, fake), items, _ctx(), registry)

	# Expect: Open, sep, Disabled (disabled), Close
	kinds = [e.kind for e in fake.entries]
	assert kinds == ["cmd", "sep", "cmd", "cmd"]

	labels = [e.attrs.get("label") for e in fake.entries if e.kind == "cmd"]
	assert labels == ["Open", "Disabled", "Close"]

	# Accelerator shown for Open
	open_entry = next(e for e in fake.entries if e.kind == "cmd" and e.attrs.get("label") == "Open")
	assert open_entry.attrs.get("accelerator") == "Ctrl+O"
	assert open_entry.attrs.get("state") == "normal"

	disabled_entry = next(e for e in fake.entries if e.kind == "cmd" and e.attrs.get("label") == "Disabled")
	assert disabled_entry.attrs.get("state") == "disabled"


def test_populate_dropdown_supports_submenus():
	registry = CommandRegistry()
	registry.register(Command(id="file.open", label="Open", handler=lambda ctx: None))
	registry.register(Command(id="file.close", label="Close", handler=lambda ctx: None))

	mb = MenuBar()
	root = FakeMenu()

	items = (
		MenuSubmenu(
			label="File",
			items=(
				MenuCommand("file.open"),
				MenuSeparator(),
				MenuCommand("file.close"),
			),
		),
	)

	mb._populate_dropdown(cast(tk.Menu, root), items, _ctx(), registry)

	# One cascade at top level
	assert len(root.entries) == 1
	assert root.entries[0].kind == "cascade"
	assert root.entries[0].attrs.get("label") == "File"
	assert root.entries[0].attrs.get("menu") is not None


def test_populate_dropdown_no_registry_no_output():
	mb = MenuBar()
	fake = FakeMenu()

	mb._populate_dropdown(cast(tk.Menu, fake), ("x", None, "y"), _ctx(), None)

	assert fake.entries == []
