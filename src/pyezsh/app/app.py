# ---------------------------------------------------------------------------
# File: app.py
# ---------------------------------------------------------------------------
# Description:
#	Starting point for pyezsh app.
#
# Notes:
#	- App owns CommandRegistry and KeyMap.
#	- Command execution uses CommandContext (app/state/services/extra).
#	- KeyRouter provides contextual key routing:
#		focused component -> mode -> global keymap -> command execution
#
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date			Author						Change
# ---------------------------------------------------------------------------
# 12/17/2025	Paul G. LeDuc				Initial coding / release
# 12/18/2025	Paul G. LeDuc				Add ctor args + geometry guards
# 12/18/2025	Paul G. LeDuc				Add root_frame + optional scrolling
# 12/26/2025	Paul G. LeDuc				Add component management lifecycle
# 12/30/2025	Paul G. LeDuc				Add component id/name indexing + lookup
# 12/30/2025	Paul G. LeDuc				Add command + keymap ownership
# 12/31/2025	Paul G. LeDuc				Wire CommandContext + shortcut execution
# 12/31/2025	Paul G. LeDuc				Add Tk key routing (event -> keyseq -> command)
# 12/31/2025	Paul G. LeDuc				Bind explicit key sequences for routing
# 12/31/2025	Paul G. LeDuc				Hook macOS native Quit (tk::mac::Quit)
# 12/31/2025	Paul G. LeDuc				Make Quit routing single-path + safer Tcl hook
# 12/31/2025	Paul G. LeDuc				Make macOS Quit hook idempotent + re-installable
# 12/31/2025	Paul G. LeDuc				Remove quit-hook rename-debug + make debug hooks safe
# 01/01/2026	Paul G. LeDuc				Adopt KeyRouter for contextual routing (keyseq -> command)
# 01/01/2026	Paul G. LeDuc				Route macOS Quit through KeyRouter single path
# 01/02/2026	Paul G. LeDuc				Add declarative MenuBar wiring (registry/context/invoker)
# 01/02/2026	Paul G. LeDuc				Public macOS quit hook API for MenuBar
# 01/02/2026	Paul G. LeDuc				Added logging to application
# 01/03/2026	Paul G. LeDuc				Added telemetry to application
# 01/03/2026	Paul G. LeDuc				Added statusbar to application
# ---------------------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
import logging
import sys

import tkinter as tk
from tkinter import ttk

# Keep ttkthemes import for later theme work
import ttkthemes as ttk_themes

from pyezsh.core import get_app_logger, init_logging
from pyezsh.core import get_telemetry, init_telemetry

from pyezsh.ui import Component
from pyezsh.app.commands import Command, CommandContext, CommandRegistry
from pyezsh.app.keys import KeyMap
from pyezsh.app.default_commands import register_default_commands
from pyezsh.app.default_keys import build_default_keymap
from pyezsh.app.keyrouter import KeyRouter

# Declarative MenuBar wiring
from pyezsh.ui import MenuBar
from pyezsh.ui import MenuDef

# StatusBar
from pyezsh.ui import StatusBar

from pyezsh.services import StatusService

@dataclass(frozen=True, slots=True)
class AppConfig:
	"""
	Light wrapper for config options.
	We'll evolve this later (e.g., a Configurer class) without breaking App's API.
	"""
	options: dict[str, Any] | None = None

	def get(self, key: str, default: Any = None) -> Any:
		if self.options is None:
			return default
		return self.options.get(key, default)


class App(tk.Tk):
	"""
	App

	Main application class for pyezsh.
	Acts as the root container for all UI components.
	"""

	def __init__(
		self,
		width: int | None = None,
		height: int | None = None,
		title: str | None = None,
		cfg: dict[str, Any] | None = None,
	) -> None:
		"""
		Initialize a new instance of App.
		"""
		super().__init__()

		self.cfg = AppConfig(cfg)
		init_logging(self.cfg)
		self.log = get_app_logger()
		#self.log.info("Welcome to pyezsh")

		init_telemetry(self.cfg.options or {}, logger=self.log)
		self.telemetry = get_telemetry()
		self.telemetry.event("app.init", {"title": title or "pyezsh"})

		self.title_text = title or "pyezsh"
		self.title(self.title_text)

		# macOS Quit hook installation guard (idempotent)
		self._mac_quit_hook_installed: bool = False

		# -------------------------------------------------------------------
		# State/services placeholders (for CommandContext)
		# -------------------------------------------------------------------

		self.state: dict[str, Any] = {}
		self.services: dict[str, Any] = {}

		# Optional: a single place to track mode (KeyRouter can consult this later).
		self.state.setdefault("mode", None)

		# -------------------------------------------------------------------
		# Command + keymap (invocation spine)
		# -------------------------------------------------------------------

		self.commands = CommandRegistry()
		self.keymap = build_default_keymap()

		register_default_commands(self.commands)
		self.apply_keymap(replace=True)

		# -------------------------------------------------------------------
		# KeyRouter (contextual routing layer)
		# -------------------------------------------------------------------

		self.keyrouter = KeyRouter(
			registry=self.commands,
			global_keymap=self.keymap,
			telemetry=self.telemetry,
		)

		# Wire the focus provider now (safe: returns None if nothing focused).
		self.keyrouter.set_focus_provider(self._get_focused_component_id)

		# Route window-close through the command spine as well.
		self.protocol("WM_DELETE_WINDOW", lambda: self.invoke("app.quit"))

		# -------------------------------------------------------------------
		# Key routing (explicit Tk keyseq bindings + platform hooks)
		# -------------------------------------------------------------------

		# Install key routing + macOS quit hook early.
		# If/when a menubar is attached, MenuBar can call install_macos_quit_hook()
		# again safely (it is idempotent).
		self._enable_key_routing()

		# -------------------------------------------------------------------
		# Component registry (explicit ownership)
		# -------------------------------------------------------------------

		self.components: list[Component] = []
		self._components_by_id: dict[str, Component] = {}
		self._components_by_name: dict[str, list[Component]] = {}

		# Ensure Tk has computed screen dimensions
		self.update_idletasks()

		# Apply geometry (with screen-size guard)
		self._apply_geometry(width, height)

		# Single container for all UI (prevents root-level pack conflicts)
		self.app_frame = ttk.Frame(self)
		self.app_frame.pack(fill="both", expand=True)

		# Create a single root container for all UI
		if bool(self.cfg.get("scrollable", False)):
			self._build_scrollable_root()
			if bool(self.cfg.get("mousewheel", True)):
				self._bind_mousewheel()
		else:
			self.root_frame = ttk.Frame(self.app_frame)

		# -------------------------------------------------------------------
		# Root frame layout
		# -------------------------------------------------------------------

		# NOTE: pack root_frame AFTER statusbar so the statusbar always wins the bottom edge.
		# In scrollable mode, _build_scrollable_root() already packed the container/canvas.

		# -------------------------------------------------------------------
		# StatusBar 
		# -------------------------------------------------------------------

		self.statusbar = StatusBar(height_rows=int(self.cfg.get("statusbar_rows", 1)), debug=False)
		self.statusbar.mount(self.app_frame)
		self.statusbar.layout()

		# Now pack root_frame (non-scrollable mode)
		if not bool(self.cfg.get("scrollable", False)):
			self.root_frame.pack(fill="both", expand=True)		

		# Mirror app logs into the StatusBar (middle section by default)
		if bool(self.cfg.get("statusbar_log_enabled", True)):

			self.statusbar.attach_logging(
				#logging.getLogger(),  # root logger
				self.log,
				section=str(self.cfg.get("statusbar_log_section", "middle")),
				level=int(self.cfg.get("statusbar_log_level", logging.INFO)),
				fmt=str(self.cfg.get("statusbar_log_fmt", "%(levelname)s: %(message)s")),
			)

			self.log.info("Welcome to pyezsh!")
			
		# -------------------------------------------------------------------
		# Services
		# -------------------------------------------------------------------

		status = StatusService()
		self.services["status"] = status	
		status.attach_sink(self.statusbar)
		status.set_left("Ready")
		status.set_right(self.title_text)

	# -----------------------------------------------------------------------
	# Command / keymap wrappers
	# -----------------------------------------------------------------------

	def _build_command_context(self, *, extra: dict[str, Any] | None = None) -> CommandContext:
		"""
		Build the CommandContext used for enabled/visible evaluation + command execution.
		"""
		return CommandContext(
			app=self,
			state=self.state,
			services=self.services,
			extra=extra or {},
		)

	def build_command_context(self, *, extra: dict[str, Any] | None = None) -> CommandContext:
		"""
		Public wrapper for building CommandContext.

		This exists so declarative components (e.g., MenuBar) can depend on a stable
		public API rather than calling a private helper.
		"""
		return self._build_command_context(extra=extra)

	def register_command(self, command: Command, *, replace: bool = False) -> None:
		self.commands.register(command, replace=replace)

	def invoke(
		self,
		command_id: str,
		*,
		extra: dict[str, Any] | None = None,
		require_visible: bool = True,
	) -> Any:
		if hasattr(self, "telemetry") and self.telemetry:
			self.telemetry.event(
				"command.invoke",
				{
					"command_id": command_id,
					"require_visible": require_visible,
				},
			)

		ctx = self._build_command_context(extra=extra)

		if hasattr(self, "telemetry") and self.telemetry:
			with self.telemetry.timer("command.duration", {"command_id": command_id}):
				return self.commands.execute(command_id, ctx, require_visible=require_visible)

		return self.commands.execute(command_id, ctx, require_visible=require_visible)

	def invoke_shortcut(self, shortcut: str, *, extra: dict[str, Any] | None = None) -> Any:
		"""
		Invoke a command by shortcut (canonical like "Ctrl+S" or Tk style like "<Control-s>").
		"""
		if hasattr(self, "telemetry") and self.telemetry:
			self.telemetry.event("shortcut.invoke", {"shortcut": shortcut})

		ctx = self._build_command_context(extra=extra)

		if hasattr(self, "telemetry") and self.telemetry:
			with self.telemetry.timer("shortcut.duration", {"shortcut": shortcut}):
				return self.commands.execute_shortcut(shortcut, ctx)

		return self.commands.execute_shortcut(shortcut, ctx)

	def bind_key(self, keyseq: str, command_id: str, *, overwrite: bool = True) -> None:
		"""
		Store a key binding in the KeyMap (policy/config layer).
		Use keymap.apply(self.commands) to bind into the registry when ready.
		"""
		self.keymap.bind(keyseq, command_id, overwrite=overwrite)

	def apply_keymap(self, *, replace: bool = False) -> None:
		"""
		Bind all KeyMap entries into the CommandRegistry.
		"""
		self.keymap.apply(self.commands, replace=replace)

	# -----------------------------------------------------------------------
	# Declarative component helpers (MenuBar)
	# -----------------------------------------------------------------------

	def create_menubar(
		self,
		*,
		menus: tuple[MenuDef, ...] = (),
		auto_app_menu: bool = True,
		id: str | None = None,
		name: str | None = "MenuBar",
	) -> MenuBar:
		"""
		Create a fully-declarative MenuBar wired to this App's command spine.

		The MenuBar will NOT need to introspect the App for:
			- registry
			- context construction
			- invocation
		"""
		return MenuBar(
			id=id,
			name=name,
			menus=menus,
			auto_app_menu=auto_app_menu,
			registry=self.commands,
			context_provider=self.build_command_context,
			invoker=lambda cid: self.invoke(cid),
		)

	def install_macos_quit_hook(self) -> None:
		"""
		Public wrapper for installing the macOS quit hook (idempotent).

		Declarative components may call this after attaching a menubar if needed.
		"""
		self._install_macos_quit_hook()

	# -----------------------------------------------------------------------
	# Key routing (KeyRouter)
	# -----------------------------------------------------------------------

	def _enable_key_routing(self) -> None:
		"""
		Bind explicit Tk key sequences and route them via KeyRouter.

		Also bind on the "Menu" class so shortcuts work even when a menu
		is currently posted/open (macOS in particular).
		"""
		if sys.platform == "darwin":
			self._install_macos_quit_hook()

		for keyseq, _command_id in self.keymap.items():
			# Bind by keyseq, not command id, so routing can be contextual later.
			handler = lambda _event, ks=keyseq: self._route_keyseq(ks)

			# Normal: works when focus is in regular widgets.
			self.bind_all(keyseq, handler, add="+")

			# Attempt to catch posted-menu paths too (best-effort).
			try:
				self.bind_class("Menu", keyseq, handler, add="+")
			except tk.TclError:
				pass

	def _route_keyseq(self, keyseq: str) -> str:
		"""
		Route a keyseq through KeyRouter and return Tk event disposition.

		Returns:
			"break" if handled, "" otherwise.
		"""
		try:
			# Keep router's idea of mode aligned with app state (single source of truth).
			# (If you later want KeyRouter to consult state directly, remove this.)
			self.keyrouter.set_mode(self.state.get("mode"))

			ctx = self._build_command_context()
			handled = self.keyrouter.route_keyseq(keyseq, ctx)
			return "break" if handled else ""
		except Exception as e:
			if hasattr(self, "telemetry") and self.telemetry:
				self.telemetry.event(
					"keyrouter.error",
					{
						"keyseq": keyseq,
						"error": type(e).__name__,
					},
				)

			# Don't raise into Tk event loop.
			return ""

	def _install_macos_quit_hook(self) -> None:
		"""
		Route macOS native Quit through our KeyRouter (idempotent).

		Key points:
		- Safe to call multiple times (including after attaching a menubar).
		- Avoids renaming tk::mac::Quit (rename conflicts are common).
		- Installs/overwrites the Tcl proc body to call our Python callback.
		"""
		if sys.platform != "darwin":
			return

		try:
			self.deletecommand("pyezsh::mac_quit")
		except Exception:
			pass

		self.createcommand("pyezsh::mac_quit", self._mac_quit)

		for quit_cmd in ("tk::mac::Quit", "::tk::mac::Quit"):
			try:
				self.tk.eval(f"""
					proc {quit_cmd} {{}} {{
						pyezsh::mac_quit
					}}
				""")
			except tk.TclError:
				continue

		self._mac_quit_hook_installed = True

	def _mac_quit(self) -> None:
		"""
		macOS native Quit hook.

		IMPORTANT:
		Do NOT call destroy() directly here.
		Route through the same key routing path so behavior is consistent.
		"""
		# Single path: go through KeyRouter using the actual bound key sequence.
		# (This keeps macOS Quit aligned with your default_keys policy.)
		self._route_keyseq("<Command-q>")

	# -----------------------------------------------------------------------
	# Focus/mode integration helpers (for contextual routing)
	# -----------------------------------------------------------------------

	def _get_focused_component_id(self) -> Optional[str | None]:
		"""
		Return the currently focused component id (if any).

		Right now, this is conservative and returns None until components
		explicitly participate in focus tracking.

		Planned evolution:
		- Components can call app.set_focused_component_id(component.id)
		- Or implement a Focusable protocol so App can query focus state.
		"""
		return self.state.get("focused_component_id")

	def set_focused_component_id(self, component_id: Optional[str | None]) -> None:
		"""
		Set the current focused component id used by KeyRouter.
		Components/features should call this when focus changes.
		"""
		self.state["focused_component_id"] = component_id

	def set_mode(self, mode: Optional[str | None]) -> None:
		"""
		Set the current app mode and keep KeyRouter aligned.
		"""
		self.state["mode"] = mode
		self.keyrouter.set_mode(mode)

	# -----------------------------------------------------------------------
	# Component lifecycle management
	# -----------------------------------------------------------------------

	def add_component(self, component: Component) -> None:
		"""
		Add a top-level component to the app.

		Component IDs must be unique within the App.
		"""
		if component.id is None:
			raise ValueError("Component id must not be None (Component should auto-generate one)")

		if component.id in self._components_by_id:
			existing = self._components_by_id[component.id]
			raise ValueError(
				f"Duplicate component id {component.id!r}: "
				f"existing={existing.__class__.__name__} name={existing.name!r}, "
				f"new={component.__class__.__name__} name={component.name!r}"
			)

		self.components.append(component)
		self._components_by_id[component.id] = component

		if component.name is not None:
			self._components_by_name.setdefault(component.name, []).append(component)

		component.mount(self.root_frame)
		component.layout()

	def remove_component(self, component: Component) -> None:
		"""
		Remove a component from the app and destroy it.
		"""
		if component not in self.components:
			return

		component.destroy()
		self.components.remove(component)

		if component.id is not None:
			self._components_by_id.pop(component.id, None)

		if component.name is not None:
			items = self._components_by_name.get(component.name, [])
			if component in items:
				items.remove(component)
				if not items:
					self._components_by_name.pop(component.name, None)

		self.layout_components()

	def clear_components(self) -> None:
		"""
		Remove and destroy all components.
		"""
		for component in list(self.components):
			component.destroy()

		self.components.clear()
		self._components_by_id.clear()
		self._components_by_name.clear()

	def layout_components(self) -> None:
		"""
		Re-apply layout to all components.
		"""
		for component in self.components:
			component.layout()

	def redraw_components(self) -> None:
		"""
		Trigger redraw/refresh on all components.
		"""
		for component in self.components:
			component.redraw()

		self.update_idletasks()

	# -----------------------------------------------------------------------
	# Component lookup
	# -----------------------------------------------------------------------

	def get_component(self, component_id: str) -> Optional[Component]:
		"""
		Get a top-level component by id.
		"""
		return self._components_by_id.get(component_id)

	def find_components_by_name(self, name: str) -> list[Component]:
		"""
		Get all top-level components with a given name.
		Names are not required to be unique.
		"""
		return list(self._components_by_name.get(name, []))

	def find_component_by_name(self, name: str) -> Optional[Component]:
		"""
		Get the first top-level component with a given name (if any).
		"""
		items = self._components_by_name.get(name, [])
		return items[0] if items else None

	# -----------------------------------------------------------------------
	# Window & root setup
	# -----------------------------------------------------------------------

	def _apply_geometry(self, width: int | None, height: int | None) -> None:
		screen_w = self.winfo_screenwidth()
		screen_h = self.winfo_screenheight()

		if width is None and height is None:
			win_w = screen_w
			win_h = screen_h
		else:
			req_w = width if width is not None else screen_w
			req_h = height if height is not None else screen_h

			win_w = max(1, min(req_w, screen_w))
			win_h = max(1, min(req_h, screen_h))

		x = max(0, (screen_w - win_w) // 2)
		y = max(0, (screen_h - win_h) // 2)

		self.geometry(f"{win_w}x{win_h}+{x}+{y}")

	def _build_scrollable_root(self) -> None:
		"""
		Build a scrollable root container using Canvas + inner Frame + Scrollbar.
		"""
		#container = ttk.Frame(self)
		#container.pack(fill="both", expand=True)
		container = ttk.Frame(self.app_frame)
		container.pack(fill="both", expand=True)
		self.canvas = tk.Canvas(container, highlightthickness=0)
		self.v_scroll = ttk.Scrollbar(
			container,
			orient="vertical",
			command=self.canvas.yview,
		)

		self.root_frame = ttk.Frame(self.canvas)

		self.root_frame.bind("<Configure>", self._on_root_configure)

		self.canvas.create_window((0, 0), window=self.root_frame, anchor="nw")
		self.canvas.configure(yscrollcommand=self.v_scroll.set)

		self.canvas.pack(side="left", fill="both", expand=True)
		self.v_scroll.pack(side="right", fill="y")

	def _on_root_configure(self, event: tk.Event) -> None:
		if hasattr(self, "canvas"):
			self.canvas.configure(scrollregion=self.canvas.bbox("all"))

	def _bind_mousewheel(self) -> None:
		"""
		Bind mousewheel scrolling for the canvas.
		"""
		def _on_mousewheel(event: tk.Event) -> None:
			if not hasattr(self, "canvas"):
				return
			delta = getattr(event, "delta", 0)
			if delta:
				self.canvas.yview_scroll(int(-1 * (delta / 120)), "units")

		self.bind_all("<MouseWheel>", _on_mousewheel)

	# -----------------------------------------------------------------------
	# Runtime
	# -----------------------------------------------------------------------

	def run(self) -> None:
		"""
		Run the Tk event loop.
		"""
		if hasattr(self, "telemetry") and self.telemetry:
			self.telemetry.event("app.start", {"title": self.title_text})

		try:
			self.mainloop()
		finally:
			if hasattr(self, "telemetry") and self.telemetry:
				self.telemetry.event("app.stop", {"title": self.title_text})

	def __str__(self) -> str:
		return f"{self.__class__.__name__}(title={self.title_text!r})"

	def __repr__(self) -> str:
		return f"<{self.__class__.__name__} title={self.title_text!r}>"

	# -----------------------------------------------------------------------
	# Debug: key routing diagnostics
	# -----------------------------------------------------------------------

	def enable_key_debug(self) -> None:
		"""
		Enable verbose logging to understand what happens on the FIRST ⌘Q.

		This is meant for one-off local debugging runs.
		"""
		self._install_debug_key_traps()
		self._dump_quit_bindings()

	def _install_debug_key_traps(self) -> None:
		# Tcl callback to python print
		try:
			self.deletecommand("pyezsh::dbg")
		except Exception:
			pass
		self.createcommand("pyezsh::dbg", lambda msg: print(msg))

		# Tcl-level binds (all + Menu class)
		try:
			self.tk.eval(r'''
				bind all <KeyPress> {
					pyezsh::dbg [format "TCL KeyPress  keysym=%s keycode=%s state=%s char=%s widget=%s" %K %k %s %A %W]
				}
				bind all <KeyRelease> {
					pyezsh::dbg [format "TCL KeyRelease keysym=%s keycode=%s state=%s char=%s widget=%s" %K %k %s %A %W]
				}
				bind Menu <KeyPress> {
					pyezsh::dbg [format "TCL(Menu) KeyPress  keysym=%s keycode=%s state=%s char=%s widget=%s" %K %k %s %A %W]
				}
				bind Menu <KeyRelease> {
					pyezsh::dbg [format "TCL(Menu) KeyRelease keysym=%s keycode=%s state=%s char=%s widget=%s" %K %k %s %A %W]
				}
			''')
		except tk.TclError as e:
			print(f"[dbg] Tcl bind install failed: {e}")

		# Python-level binds
		self.bind_all("<KeyPress>", self._py_dbg_keypress, add="+")
		self.bind_all("<KeyRelease>", self._py_dbg_keyrelease, add="+")

		# Debug-only wrapper for tk::mac::Quit that DOES NOT rename.
		if sys.platform == "darwin":
			self._install_debug_macos_quit_proc()

	def _py_dbg_keypress(self, event: tk.Event) -> None:
		ks = getattr(event, "keysym", "")
		kc = getattr(event, "keycode", "")
		st = getattr(event, "state", "")
		ch = getattr(event, "char", "")
		w = getattr(event, "widget", None)
		print(
			f"PY  KeyPress  keysym={ks!r} keycode={kc!r} state={st!r} char={ch!r} "
			f"widget={type(w).__name__ if w else None}"
		)

	def _py_dbg_keyrelease(self, event: tk.Event) -> None:
		ks = getattr(event, "keysym", "")
		kc = getattr(event, "keycode", "")
		st = getattr(event, "state", "")
		ch = getattr(event, "char", "")
		w = getattr(event, "widget", None)
		print(
			f"PY  KeyRelease keysym={ks!r} keycode={kc!r} state={st!r} char={ch!r} "
			f"widget={type(w).__name__ if w else None}"
		)

	def _install_debug_macos_quit_proc(self) -> None:
		try:
			self.deletecommand("pyezsh::dbg_mac_quit")
		except Exception:
			pass

		def _dbg_quit() -> None:
			print("PY  macOS Quit hook fired (debug proc)")
			self._route_keyseq("<Command-q>")

		self.createcommand("pyezsh::dbg_mac_quit", _dbg_quit)

		for quit_cmd in ("tk::mac::Quit", "::tk::mac::Quit"):
			try:
				self.tk.eval(f"""
					proc {quit_cmd} {{}} {{
						pyezsh::dbg "TCL macOS Quit invoked via {quit_cmd}"
						pyezsh::dbg_mac_quit
					}}
				""")
			except tk.TclError:
				continue

	def _dump_quit_bindings(self) -> None:
		seqs = ("<Command-q>", "<Command-Q>", "<Control-q>", "<Control-Q>")

		print("---- BINDING DUMP (all / Menu class / toplevel) ----")
		for s in seqs:
			try:
				a = self.bind_all(s) or ""
			except Exception:
				a = ""
			try:
				m = self.bind_class("Menu", s) or ""
			except Exception:
				m = ""
			try:
				t = self.bind(s) or ""
			except Exception:
				t = ""

			print(f"{s}:")
			print(f"  all : {a!r}")
			print(f"  Menu: {m!r}")
			print(f"  self: {t!r}")

		print("---- TCL COMMAND PRESENCE ----")
		for name in ("tk::mac::Quit", "::tk::mac::Quit"):
			try:
				exists = bool(int(self.tk.eval(f"llength [info commands {name}]")))
			except Exception:
				exists = False
			print(f"{name} exists: {exists}")
