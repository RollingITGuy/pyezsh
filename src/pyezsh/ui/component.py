# ---------------------------------------------------------------------------
# File: component.py
# ---------------------------------------------------------------------------
# Description:
#   Base UI Component for pyezsh (Tkinter).
#
# Notes:
#   Composite pattern: every component can contain child components.
#
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date			Author						Change
# ---------------------------------------------------------------------------
# 12/26/2025	Paul G. LeDuc				Initial coding / release
# 12/30/2025	Paul G. LeDuc				Add optional id/name for components
# 12/30/2025	Paul G. LeDuc				Use tk.Misc for parent typing (Tk/Toplevel safe)
# ---------------------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
from uuid import uuid4

import tkinter as tk
from tkinter import ttk


@dataclass
class Component:
	"""
	Base UI component.

	- id:	Optional but encouraged stable identifier for routing/debugging/tests.
	- name:	Optional human-friendly label (defaults to class name).

	- Every component can own child components (composite pattern).
	- mount() builds self.root and mounts children into it.
	- layout() applies geometry; default is pack.
	- redraw() is a hook for refreshing; default delegates to children.
	- destroy() destroys children then root.
	"""
	id: Optional[str] = None
	name: Optional[str] = None

	components: list["Component"] = field(default_factory=list)

	# tk.Misc is the common base for Tk, Toplevel, and all widgets.
	parent: Optional[tk.Misc] = field(default=None, init=False)
	root: Optional[tk.Widget] = field(default=None, init=False)

	def __post_init__(self) -> None:
		# Optional but encouraged: auto-generate when not provided.
		if not self.id:
			self.id = str(uuid4())

		# Optional friendly label: defaults to class name when not provided.
		if not self.name:
			self.name = self.__class__.__name__

	def __repr__(self) -> str:
		return f"<{self.__class__.__name__} id={self.id!r} name={self.name!r}>"

	def mount(self, parent: tk.Misc) -> None:
		"""
		Create and attach underlying widget(s) for this component, then mount children.
		"""
		self.parent = parent
		self.root = self.build(parent)

		for child in self.components:
			child.mount(self.get_child_parent())

	def build(self, parent: tk.Misc) -> tk.Widget:
		"""
		Create this component's root widget.
		Default is a Frame so containers work naturally.
		"""
		return ttk.Frame(parent)

	def get_child_parent(self) -> tk.Misc:
		"""
		Where children should be mounted.
		By default: into this component's root widget.
		"""
		if self.root is None:
			raise RuntimeError(f"Component not mounted: id={self.id!r} name={self.name!r}")
		return self.root

	def add_component(self, child: "Component") -> None:
		self.components.append(child)

		if self.root is not None:
			child.mount(self.get_child_parent())
			self.layout()

	def remove_component(self, child: "Component") -> None:
		if child in self.components:
			child.destroy()
			self.components.remove(child)
			self.layout()

	def clear_components(self) -> None:
		for child in list(self.components):
			child.destroy()
		self.components.clear()
		self.layout()

	def layout(self) -> None:
		"""
		Default layout:
		- Root fills available space.
		- Children stacked vertically inside root.
		"""
		if self.root is None:
			return

		self.root.pack(fill="both", expand=True)

		for child in self.components:
			child.layout()

	def redraw(self) -> None:
		for child in self.components:
			child.redraw()

		if self.root is not None:
			self.root.update_idletasks()

	def destroy(self) -> None:
		for child in list(self.components):
			child.destroy()
		self.components.clear()

		if self.root is not None:
			self.root.destroy()
			self.root = None
