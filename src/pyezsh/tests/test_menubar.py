# ---------------------------------------------------------------------------
# File: test_menubar.py
# ---------------------------------------------------------------------------
# Description:
#	Unit tests for MenuBar menu filtering logic (no Tk dependency).
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date			Author						Change
# ---------------------------------------------------------------------------
# 01/01/2026	Paul G. LeDuc				Initial tests for macOS About/Quit filtering
# ---------------------------------------------------------------------------

from pyezsh.ui.menubar import MenuBar, MenuDef


def test_filter_removes_about_quit_and_cleans_separators():
	mb = MenuBar(
		menus=(
			MenuDef("App", items=("app.about", None, "app.quit")),
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

	# About/Quit removed
	assert "app.about" not in file_menu.items
	assert "app.quit" not in file_menu.items
	assert "app.about" not in help_menu.items
	assert "app.quit" not in help_menu.items

	# Separators cleaned: no leading/trailing and no duplicate Nones
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
		MenuDef("App", items=("app.about", None, "app.quit")),
		MenuDef("File", items=("file.open", None, "app.quit", None, "file.close")),
	)

	# macOS + auto_app_menu=True => filtered
	mb1 = MenuBar(menus=menus, auto_app_menu=True)
	eff1 = mb1._get_effective_menus(is_mac=True)
	assert [m.label for m in eff1] == ["File"]
	assert eff1[0].items == ("file.open", None, "file.close")

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
			MenuDef("OnlyReserved", items=(None, "app.about", None, "app.quit", None)),
			MenuDef("Other", items=("x",)),
		),
		auto_app_menu=True,
	)

	out = mb._filter_macos_reserved_items(mb._menus)
	assert [m.label for m in out] == ["Other"]
	assert out[0].items == ("x",)
