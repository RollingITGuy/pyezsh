from __future__ import annotations

import os

from pyezsh.app import App
from pyezsh.ui.menubar import MenuBar, MenuDef


def build_app(app: App) -> None:
	"""
	Compose the initial UI tree.

	This function is intentionally small and declarative.
	"""
	app.add_component(MenuBar(
		menus=(
			MenuDef("Pyezsh", items=("app.about", None, "app.quit")),
		),
	))


def _truthy_env(name: str, default: str = "0") -> bool:
	val = os.getenv(name, default).strip().lower()
	return val in ("1", "true", "t", "yes", "y", "on")


def main() -> None:
	app = App()

	# Enable key diagnostics only when requested.
	# Example:
	#   PYEZSH_DEBUG_KEYS=1 uv run ./src/pyezsh/__main__.py
	if _truthy_env("PYEZSH_DEBUG_KEYS"):
		app.enable_key_debug()

	build_app(app)
	app.run()


if __name__ == "__main__":
	main()
