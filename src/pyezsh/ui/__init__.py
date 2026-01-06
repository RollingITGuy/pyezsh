# ---------------------------------------------------------------------------
# File: __init__.py
# ---------------------------------------------------------------------------
# Description:
#	UI package exports for pyezsh.
#
# Notes:
#	- Re-export commonly used UI components and menu definition types.
#	- Menu definitions live in ui/menu_defs.py (typed items + legacy compatibility).
#
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date			Author						Change
# ---------------------------------------------------------------------------
# 01/01/2026	Paul G. LeDuc				Update exports for menu_defs split
# 01/03/2026	Paul G. LeDuc				Update exports for StatusBar
# 01/05/2026	Paul G. LeDuc				Update exports for MainLayout
# ---------------------------------------------------------------------------

from .component import Component
from .menubar import MenuBar
from .menu_defs import (
	SEP,
	MenuDef,
	MenuItem,
	MenuItemLike,
	MenuSeparator,
	MenuCommand,
	MenuSubmenu,
)
from .statusbar import StatusBar
from .mainlayout import MainLayout

__all__ = [
	"Component",
	"MenuBar",
    "SEP",
	"MenuDef",
	"MenuItem",
	"MenuItemLike",
	"MenuSeparator",
	"MenuCommand",
	"MenuSubmenu",
    "StatusBar",
    "MainLayout",
]
