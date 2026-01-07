# ---------------------------------------------------------------------------
# File: app/__init__.py
# ---------------------------------------------------------------------------
# Description:
#   Public app package surface for pyezsh.
#
# Notes:
#   - Uses lazy exports to avoid circular imports between App <-> UI components.
# ---------------------------------------------------------------------------

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = [
	"App",
]

_EXPORTS: dict[str, tuple[str, str]] = {
	"App": ("pyezsh.app.app", "App"),
}

def __getattr__(name: str) -> Any:
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
	from pyezsh.app.app import App
