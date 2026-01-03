# ---------------------------------------------------------------------------
# File: statusbar.py
# ---------------------------------------------------------------------------
# Description:
#	StatusBar component for pyezsh.
#
# Notes:
#	- Configurable sections (left/middle/right or N).
#	- Sections can display text or host a child Component.
#	- Optional logging.Handler to mirror log messages into a section.
#	- Intended to evolve (multi-row widgets, telemetry summary, etc.).
#
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date			Author						Change
# ---------------------------------------------------------------------------
# 01/03/2026	Paul G. LeDuc				Initial coding / release
# 01/03/2026	Paul G. LeDuc				Add sections + component hosting + log mirroring
# 01/03/2026	Paul G. LeDuc				Tighten Tk anchor typing for Pylance
# ---------------------------------------------------------------------------

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Literal, Optional

import tkinter as tk
from tkinter import ttk

from .component import Component


TkAnchor = Literal["nw", "n", "ne", "w", "center", "e", "sw", "s", "se"]


# ---------------------------------------------------------------------------
# Logging integration
# ---------------------------------------------------------------------------

class StatusBarLogHandler(logging.Handler):
	"""
	A logging handler that mirrors formatted log records into a StatusBar section.

	Important:
	- Never raise from emit(); UI logging should never crash the app.
	"""

	def __init__(
		self,
		statusbar: "StatusBar",
		*,
		section: str = "middle",
		level: int = logging.INFO,
	) -> None:
		super().__init__(level=level)
		self._sb = statusbar
		self._section = section

	def emit(self, record: logging.LogRecord) -> None:
		try:
			msg = self.format(record)
		except Exception:
			return
		self._sb.set_text(self._section, msg)


# ---------------------------------------------------------------------------
# StatusBar
# ---------------------------------------------------------------------------

@dataclass
class StatusBar(Component):
	"""
	StatusBar

	A simple, configurable status bar.

	Sections:
	- If sections=("left","middle","right"), you get the common 3-region layout.
	- You can pass any tuple of names, e.g. ("a","b","c","d").

	Text vs Component:
	- By default a section is a Label.
	- If you call set_component(section, comp), that section hosts the Component instead.
	"""

	sections: tuple[str, ...] = ("left", "middle", "right")

	# Approximate height in rows (we use padding; true row height is font-dependent in Tk).
	height_rows: int = 1

	# Section weights control stretch. Defaults: middle stretches, others don’t.
	weights: dict[str, int] = field(default_factory=lambda: {"left": 0, "middle": 1, "right": 0})

	# Initial text values
	text: dict[str, str] = field(default_factory=dict)

	# Internal widget refs
	_section_frames: dict[str, ttk.Frame] = field(default_factory=dict, init=False, repr=False)
	_section_labels: dict[str, ttk.Label] = field(default_factory=dict, init=False, repr=False)
	_section_components: dict[str, Component] = field(default_factory=dict, init=False, repr=False)

	# Optional log handler
	log_handler: Optional[StatusBarLogHandler] = field(default=None, init=False, repr=False)

	def build(self, parent: tk.Misc) -> tk.Widget:
		frame = ttk.Frame(parent)

		# Make the bar act like a single-row grid with N columns.
		for col, name in enumerate(self.sections):
			weight = int(self.weights.get(name, 0))
			frame.columnconfigure(col, weight=weight)

			cell = ttk.Frame(frame)
			cell.grid(row=0, column=col, sticky="nsew")
			self._section_frames[name] = cell

			# Default: label section
			lbl = ttk.Label(
				cell,
				text=self.text.get(name, ""),
				anchor=self._default_anchor_for(name),
			)
			lbl.pack(fill="x", expand=True, padx=(8, 8), pady=self._pady())
			self._section_labels[name] = lbl

		return frame

	def layout(self) -> None:
		if self.root is None:
			return
		# StatusBar is typically anchored at bottom.
		self.root.pack(side="bottom", fill="x")

	def destroy(self) -> None:
		# Detach any hosted components first (avoid leaving Tk widgets around).
		for name, comp in list(self._section_components.items()):
			try:
				comp.destroy()
			except Exception:
				pass
			self._section_components.pop(name, None)

		super().destroy()

	# -----------------------------------------------------------------------
	# Section API
	# -----------------------------------------------------------------------

	def set_text(self, section: str, value: str) -> None:
		"""
		Set text in a section.

		If the section currently hosts a Component, this will be ignored.
		"""
		self.text[section] = value

		lbl = self._section_labels.get(section)
		if lbl is None:
			return

		# Tk-safe update (UI loop)
		lbl.after_idle(lambda: lbl.config(text=value))

	# Convenience (3-way)
	def set_left(self, value: str) -> None:
		self.set_text("left", value)

	def set_middle(self, value: str) -> None:
		self.set_text("middle", value)

	def set_right(self, value: str) -> None:
		self.set_text("right", value)

	def clear_section(self, section: str) -> None:
		"""
		Clear a section and remove any hosted component.
		"""
		self.set_component(section, None)
		self.set_text(section, "")

	def set_component(self, section: str, component: Optional[Component]) -> None:
		"""
		Host a Component inside a section.

		If component is None, removes any hosted component and restores label mode.
		"""
		cell = self._section_frames.get(section)
		if cell is None:
			return

		# Remove existing hosted component (if any)
		existing = self._section_components.get(section)
		if existing is not None:
			try:
				existing.destroy()
			except Exception:
				pass
			self._section_components.pop(section, None)

		# If we're removing, restore the label (if missing)
		if component is None:
			lbl = self._section_labels.get(section)
			if lbl is None:
				lbl = ttk.Label(
					cell,
					text=self.text.get(section, ""),
					anchor=self._default_anchor_for(section),
				)
				lbl.pack(fill="x", expand=True, padx=(8, 8), pady=self._pady())
				self._section_labels[section] = lbl
			return

		# If we’re hosting, hide label for that section
		lbl = self._section_labels.get(section)
		if lbl is not None:
			try:
				lbl.destroy()
			except Exception:
				pass
			self._section_labels.pop(section, None)

		# Mount component into the section frame
		component.mount(cell)
		component.layout()
		self._section_components[section] = component

	# -----------------------------------------------------------------------
	# Logging integration
	# -----------------------------------------------------------------------

	def attach_logging(
		self,
		logger: logging.Logger,
		*,
		section: str = "middle",
		level: int = logging.INFO,
		fmt: str = "%(levelname)s: %(message)s",
	) -> StatusBarLogHandler:
		"""
		Attach a handler to mirror log messages into a section.
		"""
		h = StatusBarLogHandler(self, section=section, level=level)
		h.setFormatter(logging.Formatter(fmt))
		logger.addHandler(h)
		self.log_handler = h
		return h

	def detach_logging(self, logger: logging.Logger) -> None:
		if self.log_handler is None:
			return
		try:
			logger.removeHandler(self.log_handler)
		except Exception:
			pass
		self.log_handler = None

	# -----------------------------------------------------------------------
	# Internals
	# -----------------------------------------------------------------------

	def _default_anchor_for(self, section: str) -> TkAnchor:
		if section == "left":
			return "w"
		if section == "right":
			return "e"
		return "center"

	def _pady(self) -> int:
		# crude but effective: “rows” => more padding
		if self.height_rows <= 1:
			return 2
		return 2 + (self.height_rows - 1) * 6
