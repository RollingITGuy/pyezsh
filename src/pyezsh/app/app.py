# ---------------------------------------------------------------------------
# File: app.py
# ---------------------------------------------------------------------------
# Description:
#	Starting point for pyezsh app.
#
# Notes:
#	- App owns CommandRegistry and KeyMap.
#	- Command execution uses CommandContext (app/state/services/extra).
#	- UI key events can later route to:
#		self.invoke_shortcut("Ctrl+S") or self.commands.execute_shortcut(...)
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
# ---------------------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
import sys

import tkinter as tk
from tkinter import ttk

# Keep ttkthemes import for later theme work
import ttkthemes as ttk_themes

from pyezsh.ui import Component
from pyezsh.app.commands import Command, CommandContext, CommandRegistry
from pyezsh.app.keys import KeyMap
from pyezsh.app.default_commands import register_default_commands
from pyezsh.app.default_keys import build_default_keymap


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
		self.title_text = title or "pyezsh"
		self.title(self.title_text)

		# macOS Quit hook installation guard (idempotent)
		self._mac_quit_hook_installed: bool = False

		# -------------------------------------------------------------------
		# Command + keymap (invocation spine)
		# -------------------------------------------------------------------

		self.commands = CommandRegistry()
		self.keymap = build_default_keymap()

		register_default_commands(self.commands)
		self.apply_keymap(replace=True)

		# Route window-close through the command spine as well.
		self.protocol("WM_DELETE_WINDOW", lambda: self.invoke("app.quit"))

		# -------------------------------------------------------------------
		# State/services placeholders (for CommandContext)
		# -------------------------------------------------------------------

		self.state: dict[str, Any] = {}
		self.services: dict[str, Any] = {}

		# -------------------------------------------------------------------
		# Key routing (explicit Tk keyseq bindings + platform hooks)
		# -------------------------------------------------------------------

		# Install key routing + macOS quit hook early.
		# If/when a menubar is attached, MenuBar can call _install_macos_quit_hook()
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

		# Create a single root container for all UI
		if bool(self.cfg.get("scrollable", False)):
			self._build_scrollable_root()
			if bool(self.cfg.get("mousewheel", True)):
				self._bind_mousewheel()
		else:
			self.root_frame = ttk.Frame(self)
			self.root_frame.pack(fill="both", expand=True)

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

	def register_command(self, command: Command, *, replace: bool = False) -> None:
		self.commands.register(command, replace=replace)

	def invoke(
		self,
		command_id: str,
		*,
		extra: dict[str, Any] | None = None,
		require_visible: bool = True,
	) -> Any:
		ctx = self._build_command_context(extra=extra)
		return self.commands.execute(command_id, ctx, require_visible=require_visible)

	def invoke_shortcut(self, shortcut: str, *, extra: dict[str, Any] | None = None) -> Any:
		"""
		Invoke a command by shortcut (canonical like "Ctrl+S" or Tk style like "<Control-s>").
		"""
		ctx = self._build_command_context(extra=extra)
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
	# Key routing
	# -----------------------------------------------------------------------

	def _enable_key_routing(self) -> None:
		"""
		Route selected key bindings through the KeyMap/CommandRegistry.

		Also bind on the "Menu" class so shortcuts work even when a menu
		is currently posted/open (macOS in particular).
		"""
		if sys.platform == "darwin":
			self._install_macos_quit_hook()

		for keyseq, command_id in self.keymap.items():
			handler = lambda _event, cid=command_id: self._invoke_bound_command(cid)

			# Normal: works when focus is in regular widgets.
			self.bind_all(keyseq, handler, add="+")

			# Attempt to catch posted-menu paths too (best-effort).
			try:
				self.bind_class("Menu", keyseq, handler, add="+")
			except tk.TclError:
				pass

	def _install_macos_quit_hook(self) -> None:
		"""
		Route macOS native Quit through our command spine (idempotent).

		Key points:
		- Safe to call multiple times (including after attaching a menubar).
		- Avoids renaming tk::mac::Quit (rename conflicts are common).
		- Installs/overwrites the Tcl proc body to call our Python callback.
		"""
		if sys.platform != "darwin":
			return

		# Always (re)bind the Python callback name in Tcl. On some builds,
		# creating the same command twice errors; delete then create.
		try:
			self.deletecommand("pyezsh::mac_quit")
		except Exception:
			pass

		self.createcommand("pyezsh::mac_quit", self._mac_quit)

		# Install/overwrite the Tcl procs (best-effort, repeatable).
		# We do NOT rename the existing procs; we simply replace their bodies.
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
		macOS native Quit hook (Command-Q).

		IMPORTANT:
		Do NOT call destroy() directly here.
		Route through the command spine to keep behavior consistent.
		"""
		self._invoke_bound_command("app.quit")

	def _invoke_bound_command(self, command_id: str) -> str:
		try:
			self.invoke(command_id)
			return "break"
		except Exception:
			# Don't raise into Tk event loop.
			return ""

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
		container = ttk.Frame(self)
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
		self.mainloop()

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
		# We simply overwrite the proc body temporarily to log then call our callback.
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
		# python callback used by the debug Tcl proc
		try:
			self.deletecommand("pyezsh::dbg_mac_quit")
		except Exception:
			pass

		def _dbg_quit() -> None:
			print("PY  macOS Quit hook fired (debug proc)")
			self._invoke_bound_command("app.quit")

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
