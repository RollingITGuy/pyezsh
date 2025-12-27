from __future__ import annotations

from tkinter import ttk
import tkinter as tk

from .component import Component


class Label(Component):
	def __init__(self, text: str) -> None:
		super().__init__()
		self.text = text

	def build(self, parent: tk.Widget) -> tk.Widget:
		return ttk.Label(parent, text=self.text)
