# ---------------------------------------------------------------------------
# File: test_component.py
# ---------------------------------------------------------------------------
# Description:
#   Unit tests for the base Component class.
#
# Notes:
#   - Validates component identity (id/name).
#   - Validates mount / destroy lifecycle.
#   - Validates composite (child component) behavior.
#
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date			Author						Change
# ---------------------------------------------------------------------------
# 12/30/2025	Paul G. LeDuc				Initial Component tests
# 12/30/2025	Paul G. LeDuc				Update for tk.Misc parent typing
# ---------------------------------------------------------------------------

import tkinter as tk
from tkinter import ttk

from pyezsh.ui.component import Component


class _TestComponent(Component):
	"""
	Minimal concrete Component used for testing.
	"""
	def build(self, parent: tk.Misc) -> tk.Widget:
		return ttk.Frame(parent)


def test_component_auto_generates_id_and_name():
	component = _TestComponent()

	assert component.id is not None
	assert isinstance(component.id, str)
	assert component.name == "_TestComponent"


def test_component_mount_sets_parent_and_root():
	root = tk.Tk()
	try:
		component = _TestComponent()
		component.mount(root)

		assert component.parent is root
		assert component.root is not None
		assert isinstance(component.root, tk.Widget)
	finally:
		root.destroy()


def test_component_destroy_cleans_up_root():
	root = tk.Tk()
	try:
		component = _TestComponent()
		component.mount(root)

		widget = component.root
		assert widget is not None
		assert widget.winfo_exists() == 1

		component.destroy()

		assert component.root is None
		assert widget.winfo_exists() == 0
	finally:
		root.destroy()


def test_component_add_child_mounts_child_when_parent_is_mounted():
	root = tk.Tk()
	try:
		parent = _TestComponent()
		child = _TestComponent()

		parent.mount(root)
		parent.add_component(child)

		assert child in parent.components
		assert child.parent is parent.root
		assert child.root is not None
	finally:
		root.destroy()


def test_component_remove_child_destroys_child():
	root = tk.Tk()
	try:
		parent = _TestComponent()
		child = _TestComponent()

		parent.mount(root)
		parent.add_component(child)

		child_root = child.root
		assert child_root is not None
		assert child_root.winfo_exists() == 1

		parent.remove_component(child)

		assert child not in parent.components
		assert child_root.winfo_exists() == 0
	finally:
		root.destroy()


def test_component_clear_components_destroys_all_children():
	root = tk.Tk()
	try:
		parent = _TestComponent()
		children = [_TestComponent(), _TestComponent()]

		parent.mount(root)

		# Explicitly mount children to avoid depending on add_component side effects
		for child in children:
			child.mount(parent.get_child_parent())
			parent.components.append(child)

		child_roots: list[tk.Widget] = []
		for child in children:
			assert child.root is not None
			child_roots.append(child.root)

		parent.clear_components()

		assert parent.components == []
		for root_widget in child_roots:
			assert root_widget.winfo_exists() == 0
	finally:
		root.destroy()
