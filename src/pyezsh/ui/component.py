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
# ---------------------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import tkinter as tk
from tkinter import ttk


@dataclass
class Component:
	"""
	Base UI component.

	- Every component can own child components (composite pattern).
	- mount() builds self.root and mounts children into it.
	- layout() applies geometry; default is pack.
	- redraw() is a hook for refreshing; default delegates to children.
	- destroy() destroys children then root.
	"""
	components: list["Component"] = field(default_factory=list)

	parent: Optional[tk.Widget] = field(default=None, init=False)
	root: Optional[tk.Widget] = field(default=None, init=False)

	def mount(self, parent: tk.Widget) -> None:
		"""
		Create and attach underlying widget(s) for this component, then mount children.
		"""
		self.parent = parent
		self.root = self.build(parent)

		for child in self.components:
			child.mount(self.get_child_parent())

	def build(self, parent: tk.Widget) -> tk.Widget:
		"""
		Create this component's root widget.
		Default is a Frame so containers work naturally.
		"""
		return ttk.Frame(parent)

	def get_child_parent(self) -> tk.Widget:
		"""
		Where children should be mounted.
		By default: into this component's root widget.
		"""
		if self.root is None:
			raise RuntimeError("Component is not mounted; root is None")
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
