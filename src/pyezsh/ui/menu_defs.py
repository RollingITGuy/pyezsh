# ---------------------------------------------------------------------------
# File: menu_defs.py
# ---------------------------------------------------------------------------
# Description:
#	Menu definition types for pyezsh.
#
# Notes:
#	- Provides a typed structure for menus and menu items.
#	- Back-compat: MenuItemLike supports legacy "cmd.id" strings and None separators.
#
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date			Author						Change
# ---------------------------------------------------------------------------
# 01/01/2026	Paul G. LeDuc				Initial coding / release
# 01/01/2026	Paul G. LeDuc				Clarify submenu item docs + add SEP convenience constant
# ---------------------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Union, TypeAlias


# Convenience alias for legacy separators in menu item tuples (optional).
SEP: None = None


@dataclass(frozen=True, slots=True)
class MenuSeparator:
	"""
	Explicit separator token for menu items.
	"""
	pass


@dataclass(frozen=True, slots=True)
class MenuCommand:
	"""
	MenuCommand

	id:				Command id to render/execute (required)
	label:			Optional label override (rare; normally use Command.label)
	accelerator:	Optional accelerator override (rare; normally use Command.shortcut)
	"""
	id: str
	label: Optional[str] = None
	accelerator: Optional[str] = None


@dataclass(frozen=True, slots=True)
class MenuSubmenu:
	"""
	MenuSubmenu

	label:	Submenu label
	items:	Submenu items (MenuItemLike supports typed items plus legacy str/None).
	"""
	label: str
	items: tuple["MenuItemLike", ...] = field(default_factory=tuple)


MenuItem: TypeAlias = Union[MenuCommand, MenuSeparator, MenuSubmenu]
MenuItemLike: TypeAlias = Union[MenuItem, Optional[str]]	# Back-compat: str=command id, None=separator


@dataclass(frozen=True, slots=True)
class MenuDef:
	"""
	MenuDef

	label:	Top-level menu label (e.g., "File")
	items:	Tuple of MenuItemLike.
			Back-compat supported: str=command id, None=separator.
	"""
	label: str
	items: tuple[MenuItemLike, ...] = field(default_factory=tuple)
