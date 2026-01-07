# ---------------------------------------------------------------------------
# File: ui/__init__.py
# ---------------------------------------------------------------------------
# Description:
#   Public UI package surface for pyezsh.
#
# Notes:
#   - Uses lazy exports to avoid circular imports (PEP 562).
#   - Do NOT import from pyezsh.ui inside ui modules; import specific modules instead.
# ---------------------------------------------------------------------------

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = [
	# Core component base
	"Component",

	# Menu system
	"MenuBar",
	"MenuDef", "MenuCommand", "MenuSubmenu", "MenuSeparator", "SEP",

	# Other UI components (keep adding as you want to export them)
	"StatusBar",
	"SidebarTreeView",
	"ContentViewer",
	"MainLayout",
]

# Map public name -> (module, attribute)
_EXPORTS: dict[str, tuple[str, str]] = {
	# Core
	"Component": ("pyezsh.ui.component", "Component"),   # <-- adjust module name if needed

	# Menu
	"MenuBar": ("pyezsh.ui.menubar", "MenuBar"),
	"MenuDef": ("pyezsh.ui.menu_defs", "MenuDef"),
	"MenuCommand": ("pyezsh.ui.menu_defs", "MenuCommand"),
	"MenuSubmenu": ("pyezsh.ui.menu_defs", "MenuSubmenu"),
	"MenuSeparator": ("pyezsh.ui.menu_defs", "MenuSeparator"),
	"SEP": ("pyezsh.ui.menu_defs", "SEP"),

	# Other components (adjust module names to match your tree)
	"StatusBar": ("pyezsh.ui.statusbar", "StatusBar"),
	"SidebarTreeView": ("pyezsh.ui.sidebar_treeview", "SidebarTreeView"),
	"ContentViewer": ("pyezsh.ui.content_viewer", "ContentViewer"),
	"MainLayout": ("pyezsh.ui.mainlayout", "MainLayout"),
}

def __getattr__(name: str) -> Any:
	"""
	Lazy attribute resolver for pyezsh.ui exports.
	This avoids import-time circular dependencies.
	"""
	try:
		mod_name, attr_name = _EXPORTS[name]
	except KeyError as ex:
		raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from ex

	import importlib
	mod = importlib.import_module(mod_name)
	return getattr(mod, attr_name)

def __dir__() -> list[str]:
	return sorted(set(list(globals().keys()) + list(__all__)))

if TYPE_CHECKING:
	# Optional: for type checkers / IDEs only (won't execute at runtime)
	from pyezsh.ui.component import Component
	from pyezsh.ui.menubar import MenuBar
	from pyezsh.ui.menu_defs import MenuDef, MenuCommand, MenuSubmenu, MenuSeparator, SEP
	from pyezsh.ui.statusbar import StatusBar
	from pyezsh.ui.sidebar_treeview import SidebarTreeView
	from pyezsh.ui.content_viewer import ContentViewer
	from pyezsh.ui.mainlayout import MainLayout
