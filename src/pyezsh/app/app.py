# ---------------------------------------------------------------------------
# File: app.py
# ---------------------------------------------------------------------------
# Description:
#   Starting point for pyezsh app.
#
# Notes:
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
# ---------------------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import tkinter as tk
from tkinter import ttk

# Keep ttkthemes import for later theme work
import ttkthemes as ttk_themes

from pyezsh.ui import Component
from pyezsh.app.commands import Command, CommandRegistry
from pyezsh.app.keys import KeyMap


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

		# -------------------------------------------------------------------
		# Command + keymap (invocation spine)
		# -------------------------------------------------------------------

		self.commands = CommandRegistry()
		self.keymap = KeyMap()

		# -------------------------------------------------------------------
		# Component registry (explicit ownership)
		# -------------------------------------------------------------------

		self.components: list[Component] = []

		# Component indexes (ids must be unique within the App)
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

	def register_command(self, command: Command) -> None:
		self.commands.register(command)

	def invoke(self, command_id: str) -> Any:
		return self.commands.invoke(command_id)

	def bind_key(self, keyseq: str, command_id: str, *, overwrite: bool = True) -> None:
		self.keymap.bind(keyseq, command_id, overwrite=overwrite)

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
