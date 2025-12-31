# ---------------------------------------------------------------------------
# File: test_app.py
# ---------------------------------------------------------------------------
# Description:
#   Unit tests for the App class.
#
# Notes:
#   - Validates App lifecycle and component management.
#   - Uses a minimal test Component for isolation.
#
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date			Author						Change
# ---------------------------------------------------------------------------
# 12/26/2025	Paul G. LeDuc				Initial tests
# 12/30/2025	Paul G. LeDuc				Update for component id/name support
# 12/30/2025	Paul G. LeDuc				Update for tk.Misc parent typing
# ---------------------------------------------------------------------------

import tkinter as tk
from tkinter import ttk

from pyezsh.app import App
from pyezsh.ui import Component


class _TestComponent(Component):
	"""
	Minimal concrete Component used for App tests.
	"""
	def build(self, parent: tk.Misc) -> tk.Widget:
		return ttk.Frame(parent)


def test_app_default_title():
	app = App(title=None)
	try:
		# Validate window title via Tk
		assert app.wm_title() == "pyezsh"
	finally:
		app.destroy()


def test_app_has_components_list():
	app = App()
	try:
		assert hasattr(app, "components")
		assert isinstance(app.components, list)
		assert len(app.components) == 0
	finally:
		app.destroy()


def test_app_add_component_mounts_component():
	app = App()
	try:
		component = _TestComponent()
		app.add_component(component)

		assert len(app.components) == 1
		assert app.components[0] is component
		assert component.root is not None
		assert component.parent is app.root_frame
	finally:
		app.destroy()


def test_app_remove_component_destroys_component():
	app = App()
	try:
		component = _TestComponent()
		app.add_component(component)

		root_widget = component.root
		assert root_widget is not None
		assert root_widget.winfo_exists() == 1

		app.remove_component(component)

		assert component not in app.components
		assert root_widget.winfo_exists() == 0
	finally:
		app.destroy()
