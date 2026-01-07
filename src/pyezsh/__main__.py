from __future__ import annotations

import os

from pyezsh.app.app import App
from pyezsh.ui.menubar import MenuBar
from pyezsh.ui.menu_defs import MenuDef, MenuSubmenu, SEP


def build_app(app: App) -> None:
	"""
	Compose the initial UI tree.
	"""

	# Dummy menus for MVP
	menus = (
		MenuDef(
			label="File",
			items=(
				"mvp.file.new",
				"mvp.file.open",
				MenuSubmenu(
					label="Open Recent",
					items=(
						"mvp.file.recent.project_a",
						"mvp.file.recent.notes",
						SEP,
						"mvp.file.recent.clear",
					),
				),
				SEP,
				"mvp.file.save",
				"mvp.file.save_as",
			),
		),
		MenuDef(
			label="Edit",
			items=(
				"mvp.edit.cut",
				"mvp.edit.copy",
				"mvp.edit.paste",
				SEP,
				"mvp.edit.find",
			),
		),
		MenuDef(
			label="View",
			items=(
				"mvp.view.toggle_sidebar",
				"mvp.view.toggle_properties",
				"mvp.view.toggle_telemetry",
			),
		),
		MenuDef(
			label="Help",
			items=(
				"mvp.help.docs",
				"mvp.help.shortcuts",
				SEP,
				"app.about",
			),
		),
	)

	# IMPORTANT: use fully-declarative injection so MenuBar doesn’t “guess”
	menubar = MenuBar(
		menus=menus,
		auto_app_menu=True,
		registry=app.commands,
		context_provider=app._build_command_context,  # or a public wrapper if you have one
		invoker=app.invoke,
	)

	app.add_component(menubar)


def _truthy_env(name: str, default: str = "0") -> bool:
	val = os.getenv(name, default).strip().lower()
	return val in ("1", "true", "t", "yes", "y", "on")


def main() -> None:
	app = App()

	if _truthy_env("PYEZSH_DEBUG_KEYS"):
		app.enable_key_debug()

	build_app(app)
	app.run()


if __name__ == "__main__":
	main()
