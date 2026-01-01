# ---------------------------------------------------------------------------
# File: menubar.py
# ---------------------------------------------------------------------------
# Description:
#	MenuBar component for pyezsh (Tk Menu renderer driven by command ids).
#
# Notes:
#	- Minimal implementation intended to prove the command spine.
#	- On macOS, ⌘Q is not reliably delivered as a KeyPress while a menu is posted.
#	  The robust fix is to use the native application (Apple) menu via name="apple".
#	- This implementation ensures an Apple menu exists on macOS and can optionally
#	  auto-inject standard items (About, Quit) if they are registered commands.
#
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date			Author						Change
# ---------------------------------------------------------------------------
# 12/31/2025	Paul G. LeDuc				Initial coding / release
# 12/31/2025	Paul G. LeDuc				Use macOS Apple menu for native Quit routing
# 12/31/2025	Paul G. LeDuc				Ensure Apple menu + optional auto standard items
# 12/31/2025	ChatGPT						Type registry as CommandRegistry for Pylance
# ---------------------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, cast, Callable

import sys
import tkinter as tk

from pyezsh.app.commands import CommandContext, CommandRegistry
from pyezsh.ui import Component


@dataclass(frozen=True, slots=True)
class MenuDef:
	"""
	MenuDef

	label:	Top-level menu label (e.g., "File")
	items:	Tuple of command ids or None for separator.
	"""
	label: str
	items: tuple[Optional[str], ...] = field(default_factory=tuple)


class MenuBar(Component):
	"""
	MenuBar

	Tk menubar that renders dropdown menus from command ids.
	On macOS, ensures a native Apple menu exists as the first cascade.
	"""

	def __init__(
		self,
		*,
		id: str | None = None,
		name: str | None = "MenuBar",
		menus: tuple[MenuDef, ...] = (),
		auto_app_menu: bool = True,
	) -> None:
		super().__init__(id=id, name=name)
		self._menus = menus
		self._auto_app_menu = auto_app_menu

		self._app: tk.Misc | None = None
		self._menubar: tk.Menu | None = None

	def mount(self, parent: tk.Misc) -> None:
		"""
		Attach a tk.Menu to the toplevel window.
		"""
		app = parent.winfo_toplevel()
		self._app = app

		menubar = tk.Menu(app, tearoff=0)
		self._menubar = menubar

		app.configure(menu=menubar)

		# macOS: attaching a menu can reset native Quit handling in some builds.
		# Re-install after attaching (your App method is idempotent).
		if sys.platform == "darwin":
			hook = getattr(app, "_install_macos_quit_hook", None)
			if callable(hook):
				try:
					hook()
				except Exception:
					pass

		self._rebuild()

	def layout(self) -> None:
		pass

	def redraw(self) -> None:
		self._rebuild()

	def destroy(self) -> None:
		app = self._app
		if app is not None:
			try:
				if isinstance(app, (tk.Tk, tk.Toplevel)):
					app.configure(menu=tk.Menu(app, tearoff=0))
			except Exception:
				pass

		self._menubar = None
		self._app = None

	# -----------------------------------------------------------------------
	# Internals
	# -----------------------------------------------------------------------

	def _ctx(self) -> CommandContext:
		if self._app is None:
			raise RuntimeError("MenuBar is not mounted")

		build = getattr(self._app, "_build_command_context", None)
		if callable(build):
			fn = cast(Callable[[], CommandContext], build)
			return fn()

		state = getattr(self._app, "state", {})
		services = getattr(self._app, "services", {})
		return CommandContext(app=self._app, state=state, services=services, extra={})

	def _get_registry(self) -> CommandRegistry | None:
		"""
		Return the CommandRegistry from the app (if present), with correct typing.
		"""
		if self._app is None:
			return None
		reg = getattr(self._app, "commands", None)
		return reg if isinstance(reg, CommandRegistry) else None

	def _rebuild(self) -> None:
		if self._app is None or self._menubar is None:
			return

		self._menubar.delete(0, "end")

		ctx = self._ctx()
		registry = self._get_registry()
		is_mac = (sys.platform == "darwin")

		# 1) macOS: ensure an Apple (application) menu exists first.
		if is_mac and self._auto_app_menu:
			self._add_apple_menu(ctx, registry)

		# 2) Render the user-provided menus next.
		for m in self._menus:
			# If caller included an explicit "App"/"Pyezsh" menu, we still render it
			# as a normal menu. The true Apple menu is handled above.
			dropdown = tk.Menu(self._menubar, tearoff=0)
			self._populate_dropdown(dropdown, m.items, ctx, registry)
			self._menubar.add_cascade(label=m.label, menu=dropdown)

	def _add_apple_menu(self, ctx: CommandContext, registry: CommandRegistry | None) -> None:
		"""
		Add the native macOS Apple menu (first cascade) using name="apple".
		The system renders the correct application name/Apple icon.
		"""
		if self._menubar is None:
			return

		apple = tk.Menu(self._menubar, name="apple", tearoff=0)

		# Optionally inject standard items if those commands exist.
		# (No hard dependency: if you haven't registered app.about, it just won't show.)
		items: list[Optional[str]] = []

		if self._command_exists(registry, "app.about"):
			items.append("app.about")
			items.append(None)

		# Future: preferences could go here when you add it.
		# if self._command_exists(registry, "app.preferences"):
		# 	items.append("app.preferences")
		# 	items.append(None)

		if self._command_exists(registry, "app.quit"):
			items.append("app.quit")

		self._populate_dropdown(apple, tuple(items), ctx, registry)

		# Important: do NOT supply a label for the Apple menu.
		self._menubar.add_cascade(menu=apple)

	def _populate_dropdown(
		self,
		dropdown: tk.Menu,
		items: tuple[Optional[str], ...],
		ctx: CommandContext,
		registry: CommandRegistry | None,
	) -> None:
		if registry is None:
			return

		for item in items:
			if item is None:
				dropdown.add_separator()
				continue

			try:
				cmd = registry.get(item)
			except Exception:
				continue
			if cmd is None:
				continue

			# Visible?
			try:
				if not registry.is_visible(cmd.id, ctx):
					continue
			except Exception:
				continue

			# Enabled?
			try:
				enabled = registry.is_enabled(cmd.id, ctx)
			except Exception:
				enabled = False

			label = cmd.label
			accel = cmd.shortcut or ""

			dropdown.add_command(
				label=label,
				accelerator=accel,
				state=("normal" if enabled else "disabled"),
				command=lambda cid=cmd.id: self._invoke(cid),
			)

	def _command_exists(self, registry: CommandRegistry | None, command_id: str) -> bool:
		if registry is None:
			return False
		try:
			return registry.get(command_id) is not None
		except Exception:
			return False

	def _invoke(self, command_id: str) -> None:
		if self._app is None:
			return

		invoke = getattr(self._app, "invoke", None)
		if callable(invoke):
			invoke(command_id)
			return

		registry = self._get_registry()
		if registry is not None:
			registry.execute(command_id, self._ctx(), require_visible=True)
