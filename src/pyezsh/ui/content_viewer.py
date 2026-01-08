# ---------------------------------------------------------------------------
# File: content_viewer.py
# ---------------------------------------------------------------------------
# Description:
#	Read-only content viewer for the MVP Content pane.
#
# Notes:
#	- Safe rendering rules:
#		- Directories: summary
#		- Files: UTF-8 preview up to MAX_BYTES / MAX_LINES
#		- Non-UTF8/binary: friendly message
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date			Author						Change
# ---------------------------------------------------------------------------
# 01/06/2026	Paul G. LeDuc				Initial version
# ---------------------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import tkinter as tk
from tkinter import ttk


@dataclass(slots=True)
class ContentViewer:
	max_bytes: int = 256 * 1024
	max_lines: int = 200

	root: ttk.Frame | None = field(default=None, init=False, repr=False)
	_text: tk.Text | None = field(default=None, init=False, repr=False)
	_vsb: ttk.Scrollbar | None = field(default=None, init=False, repr=False)

	def mount(self, parent: tk.Misc) -> ttk.Frame:
		root = ttk.Frame(parent)
		self.root = root

		self._text = tk.Text(root, wrap="none")
		self._vsb = ttk.Scrollbar(root, orient="vertical", command=self._text.yview)
		self._text.configure(yscrollcommand=self._vsb.set)

		self._text.grid(row=0, column=0, sticky="nsew")
		self._vsb.grid(row=0, column=1, sticky="ns")

		root.rowconfigure(0, weight=1)
		root.columnconfigure(0, weight=1)

		# Start read-only
		self._text.configure(state="disabled")

		return root

	def layout(self) -> None:
		if self.root is None:
			return
		try:
			if not self.root.winfo_manager():
				self.root.pack(fill="both", expand=True)
			self.root.update_idletasks()
		except Exception:
			pass

	# -----------------------------------------------------------------------
	# Public API
	# -----------------------------------------------------------------------

	def set_path(self, p: Path) -> None:
		"""
		Render the selected path into the viewer.
		"""
		# NOTE:
		# We intentionally do not require Tk widgets to be mounted here.
		# _write/_append guard against missing widgets, and tests can override
		# them to validate decision logic without a GUI.

		try:
			is_dir = p.is_dir()
		except Exception:
			is_dir = False

		if is_dir:
			self._write(f"Directory:\n{p}\n\n")
			try:
				count = sum(1 for _ in p.iterdir())
			except Exception:
				count = "?"
			self._append(f"Items: {count}\n")
			return

		try:
			size = p.stat().st_size
		except Exception:
			size = None

		if size is not None and size > self.max_bytes:
			self._write(f"File too large to preview ({size} bytes)\n\n{p}\n")
			return

		lines: list[str] = []
		try:
			with p.open("r", encoding="utf-8") as f:
				for i, line in enumerate(f):
					if i >= self.max_lines:
						lines.append("\n… (truncated)\n")
						break
					lines.append(line)
		except UnicodeDecodeError:
			self._write("Binary or non-UTF-8 file (preview not supported)\n\n" + str(p) + "\n")
			return
		except Exception as e:
			self._write(f"Error reading file:\n{e}\n\n{p}\n")
			return

		self._write("".join(lines))

	# -----------------------------------------------------------------------
	# Internals
	# -----------------------------------------------------------------------

	def _write(self, s: str) -> None:
		if self._text is None:
			return
		self._text.configure(state="normal")
		self._text.delete("1.0", "end")
		self._text.insert("1.0", s)
		self._text.configure(state="disabled")

	def _append(self, s: str) -> None:
		if self._text is None:
			return
		self._text.configure(state="normal")
		self._text.insert("end", s)
		self._text.configure(state="disabled")
