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
# 01/03/2026	Paul G. LeDuc				Force visible bar (tk frames/labels + top rule)
# 01/03/2026	Paul G. LeDuc				Grid uniform + nonzero weights so L/R never collapse
# ---------------------------------------------------------------------------

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Literal, Optional

import tkinter as tk

from .component import Component


TkAnchor = Literal["nw", "n", "ne", "w", "center", "e", "sw", "s", "se"]


class StatusBarLogHandler(logging.Handler):
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

		try:
			if self._sb.root is not None:
				self._sb.root.after_idle(lambda: self._sb.set_text(self._section, msg))
			else:
				self._sb.set_text(self._section, msg)
		except Exception:
			pass


@dataclass
class StatusBar(Component):
	sections: tuple[str, ...] = ("left", "middle", "right")
	height_rows: int = 1

	weights: dict[str, int] = field(default_factory=lambda: {"left": 1, "middle": 6, "right": 1})
	text: dict[str, str] = field(default_factory=dict)

	bg: str = "#E6E6E6"
	fg: str = "#000000"
	rule: str = "#C8C8C8"

	# NEW: optional vertical separators so you can *see* the regions
	sep: str = "#D0D0D0"
	show_separators: bool = True

	min_side_px: int = 90
	debug: bool = False

	_section_frames: dict[str, tk.Frame] = field(default_factory=dict, init=False, repr=False)
	_section_labels: dict[str, tk.Label] = field(default_factory=dict, init=False, repr=False)

	# NEW: StringVars make updates deterministic during early startup
	_section_vars: dict[str, tk.StringVar] = field(default_factory=dict, init=False, repr=False)

	_section_components: dict[str, Component] = field(default_factory=dict, init=False, repr=False)

	log_handler: Optional[StatusBarLogHandler] = field(default=None, init=False, repr=False)

	def build(self, parent: tk.Misc) -> tk.Widget:
		height_px = max(18, int(self.height_rows) * 22)

		outer = tk.Frame(parent, height=height_px, bg=self.bg)
		outer.pack_propagate(False)

		# Top rule
		top_rule = tk.Frame(outer, bg=self.rule, height=1)
		top_rule.pack(side="top", fill="x")

		# Grid row
		row = tk.Frame(outer, bg=self.bg)
		row.pack(side="top", fill="both", expand=True)

		row.grid_propagate(False)
		row.rowconfigure(0, weight=1)

		col = 0
		for i, name in enumerate(self.sections):
			weight = int(self.weights.get(name, 1))

			minsize = 0
			if name in ("left", "right"):
				minsize = int(self.min_side_px)

			row.columnconfigure(col, weight=weight, minsize=minsize)

			# Cell frame
			cell = tk.Frame(row, bg=self.bg)
			self._section_frames[name] = cell
			cell.grid(row=0, column=col, sticky="nsew")

			var = tk.StringVar(value=self.text.get(name, ""))
			self._section_vars[name] = var

			lbl = tk.Label(
				cell,
				textvariable=var,
				bg=self.bg,
				fg=self.fg,
				anchor=self._default_anchor_for(name),
			)
			lbl.pack(fill="both", expand=True, padx=(8, 8), pady=self._pady())
			self._section_labels[name] = lbl

			col += 1

			# Separator column
			if self.show_separators and i < len(self.sections) - 1:
				row.columnconfigure(col, weight=0, minsize=1)
				sep = tk.Frame(row, bg=self.sep, width=1)
				sep.grid(row=0, column=col, sticky="ns")
				col += 1

		return outer

	def layout(self) -> None:
		if self.root is None:
			return

		try:
			self.root.pack_propagate(False)
		except Exception:
			pass

		try:
			self.root.pack_forget()
		except Exception:
			pass

		self.root.pack(side="bottom", fill="x")

		if self.debug:
			self._dbg("immediate")
			self._dbg_sections("immediate")
			try:
				self.root.after_idle(lambda: (self._dbg("after_idle"), self._dbg_sections("after_idle")))
				self.root.after(250, lambda: (self._dbg("after_250ms"), self._dbg_sections("after_250ms")))
			except Exception:
				pass

	def _dbg(self, phase: str) -> None:
		try:
			root = self.root
			if root is None:
				print(f"[StatusBar {phase}] root=None")
				return

			parent = root.nametowidget(root.winfo_parent())
			slaves = []
			try:
				slaves = [w.winfo_name() for w in parent.pack_slaves()]
			except Exception:
				pass

			print(
				f"[StatusBar {phase}] mapped={root.winfo_ismapped()} "
				f"height={root.winfo_height()} reqheight={root.winfo_reqheight()} "
				f"parent={type(parent).__name__} pack_slaves={slaves}"
			)
		except Exception as e:
			print(f"[StatusBar {phase}] dbg error: {e}")

	def _dbg_sections(self, phase: str) -> None:
		try:
			if self.root is None:
				print(f"[StatusBar {phase}] root=None")
				return

			root = self.root
			print(
				f"[StatusBar {phase}] root mapped={root.winfo_ismapped()} "
				f"w={root.winfo_width()} h={root.winfo_height()} "
				f"reqw={root.winfo_reqwidth()} reqh={root.winfo_reqheight()}"
			)

			for name in self.sections:
				cell = self._section_frames.get(name)
				lbl = self._section_labels.get(name)

				if cell is None:
					print(f"  - {name}: cell=None")
					continue

				text = ""
				var = self._section_vars.get(name)
				if var is not None:
					try:
						text = var.get()
					except Exception:
						text = ""

				print(
					f"  - {name}: cell mapped={cell.winfo_ismapped()} "
					f"w={cell.winfo_width()} reqw={cell.winfo_reqwidth()} "
					f"lbl={'yes' if lbl is not None else 'no'} "
					f"text={text!r}"
				)
		except Exception as e:
			print(f"[StatusBar {phase}] dbg_sections error: {e}")

	def destroy(self) -> None:
		for _, comp in list(self._section_components.items()):
			try:
				comp.destroy()
			except Exception:
				pass
		self._section_components.clear()

		super().destroy()

	# -----------------------------------------------------------------------
	# Section API
	# -----------------------------------------------------------------------

	def set_text(self, section: str, value: str) -> None:
		self.text[section] = value

		var = self._section_vars.get(section)
		if var is not None:
			try:
				var.set(value)
			except Exception:
				pass
			return

		lbl = self._section_labels.get(section)
		if lbl is None:
			return

		def apply() -> None:
			try:
				if lbl.winfo_exists():
					lbl.config(text=value)
			except Exception:
				pass

		apply()
		try:
			lbl.after_idle(apply)
		except Exception:
			pass

	def set_left(self, value: str) -> None:
		self.set_text("left", value)

	def set_middle(self, value: str) -> None:
		self.set_text("middle", value)

	def set_right(self, value: str) -> None:
		self.set_text("right", value)

	def clear_section(self, section: str) -> None:
		self.set_component(section, None)
		self.set_text(section, "")

	def set_component(self, section: str, component: Optional[Component]) -> None:
		cell = self._section_frames.get(section)
		if cell is None:
			return

		existing = self._section_components.get(section)
		if existing is not None:
			try:
				existing.destroy()
			except Exception:
				pass
			self._section_components.pop(section, None)

		if component is None:
			# Restore label if missing
			lbl = self._section_labels.get(section)
			if lbl is None:
				var = self._section_vars.get(section) or tk.StringVar(value=self.text.get(section, ""))
				self._section_vars[section] = var

				lbl = tk.Label(
					cell,
					textvariable=var,
					bg=self.bg,
					fg=self.fg,
					anchor=self._default_anchor_for(section),
				)
				lbl.pack(fill="both", expand=True, padx=(8, 8), pady=self._pady())
				self._section_labels[section] = lbl
			return

		# Hosting: remove label for that section
		lbl = self._section_labels.get(section)
		if lbl is not None:
			try:
				lbl.destroy()
			except Exception:
				pass
			self._section_labels.pop(section, None)

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

	def _default_anchor_for(self, section: str) -> TkAnchor:
		if section == "left":
			return "w"
		if section == "right":
			return "e"
		return "center"

	def _pady(self) -> int:
		if self.height_rows <= 1:
			return 2
		return 2 + (self.height_rows - 1) * 6
