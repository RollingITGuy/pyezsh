# ---------------------------------------------------------------------------
# File: mainlayout.py
# ---------------------------------------------------------------------------
# Description:
#	MainLayout container for pyezsh MVP.
#
# Notes:
#	- Three-pane layout: Sidebar | Content | RightArea
#	- RightArea is stacked: Properties (top) | splitter | Telemetry (bottom)
#	- Splitters are draggable:
#		- Left vertical adjusts sidebar width
#		- Right vertical adjusts right width
#		- Horizontal adjusts properties/telemetry split
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date			Author						Change
# ---------------------------------------------------------------------------
# 01/05/2026	Paul G. LeDuc				Initial coding / release
# ---------------------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass, field
import tkinter as tk
from tkinter import ttk


@dataclass(slots=True)
class MainLayout:
	sidebar_width: int = 240
	right_width: int = 320
	props_height: int = 260

	splitter_width: int = 2
	h_splitter_height: int = 2

	bg: str = "#FFFFFF"
	splitter_color: str = "#C8C8C8"

	# Clamp ranges (tweak as desired)
	min_sidebar_width: int = 160
	max_sidebar_width: int = 520

	min_right_width: int = 220
	max_right_width: int = 720

	min_props_height: int = 120
	min_telemetry_height: int = 120

	# Internal widgets
	root: ttk.Frame | None = field(default=None, init=False, repr=False)

	sidebar_frame: ttk.Frame | None = field(default=None, init=False, repr=False)
	content_frame: ttk.Frame | None = field(default=None, init=False, repr=False)

	right_container: ttk.Frame | None = field(default=None, init=False, repr=False)
	props_frame: ttk.Frame | None = field(default=None, init=False, repr=False)
	telemetry_frame: ttk.Frame | None = field(default=None, init=False, repr=False)

	# Splitters
	_splitter_left: tk.Frame | None = field(default=None, init=False, repr=False)
	_splitter_right: tk.Frame | None = field(default=None, init=False, repr=False)
	_splitter_h: tk.Frame | None = field(default=None, init=False, repr=False)

	# Drag state
	_dragging: str | None = field(default=None, init=False, repr=False)
	_drag_start_x: int = field(default=0, init=False, repr=False)
	_drag_start_y: int = field(default=0, init=False, repr=False)
	_drag_start_sidebar: int = field(default=0, init=False, repr=False)
	_drag_start_right: int = field(default=0, init=False, repr=False)
	_drag_start_props_h: int = field(default=0, init=False, repr=False)

	def mount(self, parent: tk.Misc) -> ttk.Frame:
		root = ttk.Frame(parent)
		self.root = root

		# Main row: Sidebar | vsplit | Content | vsplit | Right
		root.rowconfigure(0, weight=1)

		root.columnconfigure(0, weight=0, minsize=int(self.sidebar_width))
		root.columnconfigure(1, weight=0, minsize=int(self.splitter_width))
		root.columnconfigure(2, weight=1, minsize=200)
		root.columnconfigure(3, weight=0, minsize=int(self.splitter_width))
		root.columnconfigure(4, weight=0, minsize=int(self.right_width))

		# Sidebar
		self.sidebar_frame = ttk.Frame(root)
		self.sidebar_frame.grid(row=0, column=0, sticky="nsew")

		# Vertical splitter (left)
		self._splitter_left = tk.Frame(root, bg=self.splitter_color, width=int(self.splitter_width), cursor="sb_h_double_arrow")
		self._splitter_left.grid(row=0, column=1, sticky="ns")

		# Content
		self.content_frame = ttk.Frame(root)
		self.content_frame.grid(row=0, column=2, sticky="nsew")

		# Vertical splitter (right)
		self._splitter_right = tk.Frame(root, bg=self.splitter_color, width=int(self.splitter_width), cursor="sb_h_double_arrow")
		self._splitter_right.grid(row=0, column=3, sticky="ns")

		# Right container (Properties / Telemetry stack)
		self.right_container = ttk.Frame(root)
		self.right_container.grid(row=0, column=4, sticky="nsew")

		# Right stack grid: props | hsplit | telemetry
		# Props is “fixed-ish”, telemetry grows
		initial_props = max(int(self.min_props_height), int(self.props_height))

		self.right_container.rowconfigure(0, weight=0, minsize=initial_props)
		self.right_container.rowconfigure(1, weight=0, minsize=int(self.h_splitter_height))
		self.right_container.rowconfigure(2, weight=1, minsize=int(self.min_telemetry_height))
		self.right_container.columnconfigure(0, weight=1)

		self.props_frame = ttk.Frame(self.right_container)
		self.props_frame.grid(row=0, column=0, sticky="nsew")

		self._splitter_h = tk.Frame(self.right_container, bg=self.splitter_color, height=int(self.h_splitter_height), cursor="sb_v_double_arrow")
		self._splitter_h.grid(row=1, column=0, sticky="ew")

		self.telemetry_frame = ttk.Frame(self.right_container)
		self.telemetry_frame.grid(row=2, column=0, sticky="nsew")

		# Install drag handlers
		self._bind_splitters()

		# Ensure geometry is computed before first drag
		root.after_idle(self._prime_geometry)


		root.pack(fill="both", expand=True)
		return root

	def _prime_geometry(self) -> None:
		"""
		Force Tk to compute widget sizes so the first drag doesn't "jump".
		"""
		try:
			if self.root is not None:
				self.root.update_idletasks()
			if self.right_container is not None:
				self.right_container.update_idletasks()
		except Exception:
			pass

	# -----------------------------------------------------------------------
	# Public setters
	# -----------------------------------------------------------------------

	def set_sidebar_width(self, px: int) -> None:
		if self.root is None:
			return
		self.sidebar_width = int(px)
		self.root.columnconfigure(0, minsize=self.sidebar_width)

	def set_right_width(self, px: int) -> None:
		if self.root is None:
			return
		self.right_width = int(px)
		self.root.columnconfigure(4, minsize=self.right_width)

	def set_splitter_color(self, color: str) -> None:
		self.splitter_color = str(color)
		for w in (self._splitter_left, self._splitter_right, self._splitter_h):
			if w is not None:
				w.configure(bg=self.splitter_color)

	# -----------------------------------------------------------------------
	# Drag handling
	# -----------------------------------------------------------------------

	def _bind_splitters(self) -> None:
		if self._splitter_left is not None:
			self._splitter_left.bind("<Button-1>", lambda e: self._start_drag("left", e))
			self._splitter_left.bind("<B1-Motion>", self._on_drag)
			self._splitter_left.bind("<ButtonRelease-1>", self._stop_drag)

		if self._splitter_right is not None:
			self._splitter_right.bind("<Button-1>", lambda e: self._start_drag("right", e))
			self._splitter_right.bind("<B1-Motion>", self._on_drag)
			self._splitter_right.bind("<ButtonRelease-1>", self._stop_drag)

		if self._splitter_h is not None:
			self._splitter_h.bind("<Button-1>", lambda e: self._start_drag("h", e))
			self._splitter_h.bind("<B1-Motion>", self._on_drag)
			self._splitter_h.bind("<ButtonRelease-1>", self._stop_drag)

	def _start_drag(self, which: str, event: tk.Event) -> None:
		self._dragging = which
		self._drag_start_x = int(getattr(event, "x_root", 0))
		self._drag_start_y = int(getattr(event, "y_root", 0))

		self._drag_start_sidebar = int(self.sidebar_width)
		self._drag_start_right = int(self.right_width)

		# IMPORTANT: geometry must be real before capturing start heights
		try:
			if self.right_container is not None:
				self.right_container.update_idletasks()
		except Exception:
			pass

		self._drag_start_props_h = self._get_props_height()

		# Visual feedback while dragging
		self._set_splitter_active(which, True)

	def _stop_drag(self, _event: tk.Event) -> None:
		if self._dragging is None:
			return
		self._set_splitter_active(self._dragging, False)
		self._dragging = None

	def _on_drag(self, event: tk.Event) -> None:
		if self.root is None or self._dragging is None:
			return

		x = int(getattr(event, "x_root", 0))
		y = int(getattr(event, "y_root", 0))

		if self._dragging == "left":
			dx = x - self._drag_start_x
			new_w = self._drag_start_sidebar + dx
			new_w = self._clamp(new_w, self.min_sidebar_width, self.max_sidebar_width)
			self.set_sidebar_width(new_w)
			return

		if self._dragging == "right":
			dx = x - self._drag_start_x
			new_w = self._drag_start_right - dx
			new_w = self._clamp(new_w, self.min_right_width, self.max_right_width)
			self.set_right_width(new_w)
			return

		if self._dragging == "h":
			if self.right_container is None:
				return

			dy = y - self._drag_start_y
			new_props_h = self._drag_start_props_h + dy

			# Clamp based on available height and minimums
			total_h = self.right_container.winfo_height()
			if total_h <= 1:
				return

			max_props_h = max(self.min_props_height, total_h - self.min_telemetry_height - self.h_splitter_height)
			new_props_h = self._clamp(new_props_h, self.min_props_height, max_props_h)

			# Apply by setting minsize for row 0; row 2 will naturally take remainder
			self.right_container.rowconfigure(0, minsize=int(new_props_h))
			return

	def _get_props_height(self) -> int:
		# Prefer the configured/current grid minsize (stable), then fallback to widget height.
		if self.right_container is not None:
			try:
				info = self.right_container.grid_rowconfigure(0)
				ms = int(info.get("minsize", 0) or 0)
				if ms > 0:
					return ms
			except Exception:
				pass

		if self.props_frame is None:
			return int(self.min_props_height)

		try:
			self.props_frame.update_idletasks()
		except Exception:
			pass

		h = int(self.props_frame.winfo_height())
		if h <= 1:
			return int(self.min_props_height)
		return h

	def _set_splitter_active(self, which: str, active: bool) -> None:
		# Optional: slightly darken the splitter while dragging
		color = self.splitter_color if not active else "#9E9E9E"

		if which == "left" and self._splitter_left is not None:
			self._splitter_left.configure(bg=color)
		elif which == "right" and self._splitter_right is not None:
			self._splitter_right.configure(bg=color)
		elif which == "h" and self._splitter_h is not None:
			self._splitter_h.configure(bg=color)

	def _clamp(self, v: int, lo: int, hi: int) -> int:
		if v < lo:
			return lo
		if v > hi:
			return hi
		return v
