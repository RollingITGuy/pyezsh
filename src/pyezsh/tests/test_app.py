# ---------------------------------------------------------------------------
# File: test_app.py
# ---------------------------------------------------------------------------
# Description:
#   Unit tests for the App class.
#
# Notes:
#   - App.add_component() registers only (no mount/layout side effects).
#   - Tests explicitly mount components when widget existence is required.
#
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date          Author                      Change
# ---------------------------------------------------------------------------
# 12/26/2025    Paul G. LeDuc               Initial tests
# 12/30/2025    Paul G. LeDuc               Update for component id/name support
# 01/07/2026    Paul G. LeDuc               Update: add_component is registration-only
# ---------------------------------------------------------------------------

import tkinter as tk
from tkinter import ttk

from pyezsh.app.app import App
from pyezsh.ui.component import Component


class _TestComponent(Component):
	"""
	Minimal concrete Component used for App tests.
	"""
	def build(self, parent: tk.Misc) -> tk.Widget:
		return ttk.Frame(parent)


def test_app_default_title():
	app = App(title=None)
	try:
		assert app.wm_title() == "pyezsh"
	finally:
		app.destroy()


def test_app_has_components_list():
	app = App()
	try:
		assert isinstance(app.components, list)
		assert len(app.components) == 0
	finally:
		app.destroy()


def test_app_add_component_registers_component_only():
	app = App()
	try:
		component = _TestComponent()
		app.add_component(component)

		assert len(app.components) == 1
		assert app.components[0] is component

		# Registration-only: no mount/layout side effects.
		assert component.root is None
		assert component.parent is None
	finally:
		app.destroy()


def test_app_remove_component_destroys_component_if_mounted():
	app = App()
	try:
		component = _TestComponent()
		app.add_component(component)

		# Explicitly mount to create the widget tree
		component.mount(app.root_frame)
		assert component.root is not None
		assert component.root.winfo_exists() == 1

		root_widget = component.root

		app.remove_component(component)

		assert component not in app.components
		assert root_widget.winfo_exists() == 0
	finally:
		app.destroy()
