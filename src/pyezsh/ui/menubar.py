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
#	  auto-inject standard items (About, Preferences, Quit) if they are registered commands.
#	- When auto_app_menu=True on macOS, About/Preferences/Quit are filtered from explicit menus
#	  (including submenus) to avoid duplication while keeping menus=(...) cross-platform.
#	- Menu item definitions live in pyezsh.ui.menu_defs (typed items + legacy compatibility).
#	- Fully-declarative mode:
#		Pass registry/context_provider/invoker so MenuBar does not introspect the app.
#
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date			Author						Change
# ---------------------------------------------------------------------------
# 12/31/2025	Paul G. LeDuc				Initial coding / release
# 12/31/2025	Paul G. LeDuc				Use macOS Apple menu for native Quit routing
# 12/31/2025	Paul G. LeDuc				Ensure Apple menu + optional auto standard items
# 12/31/2025	Paul G. LeDuc				Type registry as CommandRegistry for Pylance
# 01/01/2026	Paul G. LeDuc				Filter About/Quit from explicit menus on macOS when auto_app_menu=True
# 01/01/2026	Paul G. LeDuc				Add Preferences to Apple menu + filter from explicit menus on macOS
# 01/01/2026	Paul G. LeDuc				Add typed menu items + submenu support (menu_defs.py)
# 01/01/2026	Paul G. LeDuc				Make submenu rendering test-friendly (FakeMenu support)
# 01/02/2026	Paul G. LeDuc				Add fully-declarative dependency injection (registry/context/invoker)
# 01/02/2026	Paul G. LeDuc				Prefer public install_macos_quit_hook if present
# 01/03/2026	Paul G. LeDuc				Add minimal telemetry for menu selection
# ---------------------------------------------------------------------------

from __future__ import annotations

from typing import cast, Callable, Any, Optional

import sys
import tkinter as tk

from pyezsh.app.commands import CommandContext, CommandRegistry
from pyezsh.core.telemetry import Telemetry
from pyezsh.ui import Component
from pyezsh.ui.menu_defs import (
	MenuDef,
	MenuItem,
	MenuItemLike,
	MenuSeparator,
	MenuCommand,
	MenuSubmenu,
)


class MenuBar(Component):
	"""
	MenuBar

	Tk menubar that renders dropdown menus from command ids.

	Declarative inputs:
		- menus: Menu model to render
		- registry: CommandRegistry to resolve and execute command ids
		- context_provider: Callable returning a CommandContext
		- invoker: Optional callable to invoke a command id

	On macOS, ensures a native Apple menu exists as the first cascade when auto_app_menu=True.
	"""

	def __init__(
		self,
		*,
		id: str | None = None,
		name: str | None = "MenuBar",
		menus: tuple[MenuDef, ...] = (),
		auto_app_menu: bool = True,
		registry: CommandRegistry | None = None,
		context_provider: Callable[[], CommandContext] | None = None,
		invoker: Callable[[str], None] | None = None,
	) -> None:
		super().__init__(id=id, name=name)
		self._menus = menus
		self._auto_app_menu = auto_app_menu

		# Fully-declarative dependencies (preferred).
		# If not provided, we fall back to legacy app introspection for compatibility.
		self._registry = registry
		self._context_provider = context_provider
		self._invoker = invoker

		# Optional telemetry (injected or discovered from app)
		self._telemetry: Optional[Telemetry] = None

		self._app: tk.Misc | None = None
		self._menubar: tk.Menu | None = None

	def mount(self, parent: tk.Misc) -> None:
		"""
		Attach a tk.Menu to the toplevel window.
		"""
		app = parent.winfo_toplevel()
		self._app = app

		# Best-effort telemetry discovery from app (keeps MenuBar declarative).
		self._telemetry = getattr(app, "telemetry", None)

		menubar = tk.Menu(app, tearoff=0)
		self._menubar = menubar

		app.configure(menu=menubar)

		# macOS: attaching a menu can reset native Quit handling in some builds.
		# Re-install after attaching (your App method is idempotent).
		if sys.platform == "darwin":
			hook = getattr(app, "install_macos_quit_hook", None)
			if not callable(hook):
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
		self._telemetry = None

	# -----------------------------------------------------------------------
	# Declarative surface
	# -----------------------------------------------------------------------

	def normalized_menus(self, *, platform: str | None = None) -> tuple[MenuDef, ...]:
		"""
		Return the menu model that will be rendered after platform normalization.

		This is intentionally test-friendly (no Tk required).
		"""
		plat = platform if platform is not None else sys.platform
		is_mac = (plat == "darwin")
		return self._get_effective_menus(is_mac=is_mac)

	# -----------------------------------------------------------------------
	# Internals
	# -----------------------------------------------------------------------

	def _ctx(self) -> CommandContext:
		# Fully-declarative path
		if self._context_provider is not None:
			return self._context_provider()

		# Back-compat path (legacy: discover from the Tk app)
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
		Return the CommandRegistry to use.

		Prefer injected registry (fully-declarative). Fall back to app.commands (back-compat).
		"""
		if self._registry is not None:
			return self._registry

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

		# 2) Render the user-provided menus next (filtered on macOS when auto_app_menu=True).
		menus = self._get_effective_menus(is_mac=is_mac)
		for m in menus:
			dropdown = tk.Menu(self._menubar, tearoff=0)
			self._populate_dropdown(dropdown, m.items, ctx, registry, parent_path=(m.label,))
			self._menubar.add_cascade(label=m.label, menu=dropdown)

	def _add_apple_menu(self, ctx: CommandContext, registry: CommandRegistry | None) -> None:
		"""
		Add the native macOS Apple menu (first cascade) using name="apple".
		The system renders the correct application name/Apple icon.
		"""
		if self._menubar is None:
			return

		apple = tk.Menu(self._menubar, name="apple", tearoff=0)

		# Standard macOS ordering:
		#	About
		#	---
		#	Preferences...
		#	---
		#	Quit
		items: list[Optional[str]] = []

		if self._command_exists(registry, "app.about"):
			items.append("app.about")

		if self._command_exists(registry, "app.preferences"):
			if items:
				items.append(None)
			items.append("app.preferences")

		if self._command_exists(registry, "app.quit"):
			if items:
				items.append(None)
			items.append("app.quit")

		self._populate_dropdown(apple, tuple(items), ctx, registry, parent_path=("Apple",))

		# Important: do NOT supply a label for the Apple menu.
		self._menubar.add_cascade(menu=apple)

	def _normalize_items(self, items: tuple[MenuItemLike, ...]) -> tuple[MenuItem, ...]:
		"""
		Normalize legacy menu item representations into typed MenuItem objects.

		Legacy:
			- "cmd.id" -> MenuCommand("cmd.id")
			- None -> MenuSeparator()
		"""
		out: list[MenuItem] = []
		for it in items:
			if it is None:
				out.append(MenuSeparator())
				continue
			if isinstance(it, str):
				out.append(MenuCommand(it))
				continue
			out.append(it)
		return tuple(out)

	def _cleanup_separators(self, items: list[MenuItem]) -> tuple[MenuItem, ...]:
		"""
		Remove leading/trailing and duplicate separators.
		"""
		out: list[MenuItem] = []
		prev_sep = True
		for it in items:
			is_sep = isinstance(it, MenuSeparator)
			if is_sep:
				if prev_sep:
					continue
				out.append(it)
				prev_sep = True
				continue
			out.append(it)
			prev_sep = False

		while out and isinstance(out[-1], MenuSeparator):
			out.pop()

		return tuple(out)

	def _populate_dropdown(
		self,
		dropdown: Any,
		items: tuple[MenuItemLike, ...],
		ctx: CommandContext,
		registry: CommandRegistry | None,
		*,
		parent_path: tuple[str, ...] = (),
	) -> None:
		if registry is None:
			return

		typed_items = self._normalize_items(items)

		for item in typed_items:
			if isinstance(item, MenuSeparator):
				dropdown.add_separator()
				continue

			if isinstance(item, MenuSubmenu):
				# Runtime: use real tk.Menu
				# Tests: use FakeMenu.__class__ so we remain headless
				if isinstance(dropdown, tk.Menu):
					submenu = tk.Menu(dropdown, tearoff=0)
				else:
					submenu = dropdown.__class__()

				self._populate_dropdown(
					submenu,
					item.items,
					ctx,
					registry,
					parent_path=parent_path + (item.label,),
				)
				dropdown.add_cascade(label=item.label, menu=submenu)
				continue

			# MenuCommand
			command_id = item.id

			try:
				cmd = registry.get(command_id)
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

			label = item.label if item.label is not None else cmd.label
			accel = item.accelerator if item.accelerator is not None else (cmd.shortcut or "")

			menu_path = " > ".join(parent_path + (label,))

			dropdown.add_command(
				label=label,
				accelerator=accel,
				state=("normal" if enabled else "disabled"),
				command=lambda cid=cmd.id, mp=menu_path: self._invoke(cid, menu_path=mp),
			)

	def _command_exists(self, registry: CommandRegistry | None, command_id: str) -> bool:
		if registry is None:
			return False
		try:
			return registry.get(command_id) is not None
		except Exception:
			return False

	def _invoke(self, command_id: str, *, menu_path: str | None = None) -> None:
		if self._telemetry:
			attrs: dict[str, Any] = {"command_id": command_id}
			if menu_path:
				attrs["menu_path"] = menu_path
			self._telemetry.event("menu.select", attrs)

		# Fully-declarative path
		if self._invoker is not None:
			self._invoker(command_id)
			return

		# Back-compat path (legacy: invoke on the Tk app if present)
		if self._app is None:
			return

		invoke = getattr(self._app, "invoke", None)
		if callable(invoke):
			invoke(command_id)
			return

		registry = self._get_registry()
		if registry is not None:
			registry.execute(command_id, self._ctx(), require_visible=True)

	# -----------------------------------------------------------------------
	# Menu filtering (macOS duplication prevention)
	# -----------------------------------------------------------------------

	def _get_effective_menus(self, *, is_mac: bool) -> tuple[MenuDef, ...]:
		"""
		Return menus to render for this platform.

		On macOS, when auto_app_menu=True, About/Preferences/Quit are rendered in the native
		Apple menu, so we filter them out of explicit menus to avoid duplication.
		"""
		if is_mac and self._auto_app_menu:
			return self._filter_macos_reserved_items(self._menus)
		return self._menus

	def _filter_macos_reserved_items(self, menus: tuple[MenuDef, ...]) -> tuple[MenuDef, ...]:
		"""
		Remove reserved macOS App-menu items from explicit menus (including submenus).

		- Removes "app.about", "app.preferences", and "app.quit" wherever they appear.
		- Cleans up separators (no leading/trailing/double).
		- Drops menus/submenus that become empty after filtering.
		"""
		reserved: set[str] = {"app.about", "app.preferences", "app.quit"}

		def filter_items(items: tuple[MenuItemLike, ...]) -> tuple[MenuItem, ...]:
			typed = list(self._normalize_items(items))
			out: list[MenuItem] = []

			for it in typed:
				if isinstance(it, MenuSeparator):
					out.append(it)
					continue

				if isinstance(it, MenuSubmenu):
					sub = filter_items(it.items)
					sub_list = list(sub)
					sub_clean = self._cleanup_separators(sub_list)
					if not sub_clean:
						continue
					out.append(MenuSubmenu(label=it.label, items=sub_clean))
					continue

				# MenuCommand
				if it.id in reserved:
					continue
				out.append(it)

			return self._cleanup_separators(out)

		filtered: list[MenuDef] = []
		for m in menus:
			items = filter_items(m.items)
			if not items:
				continue
			filtered.append(MenuDef(label=m.label, items=items))

		return tuple(filtered)
