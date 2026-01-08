# ---------------------------------------------------------------------------
# File: sidebar_treeview.py
# ---------------------------------------------------------------------------
# Description:
#	SidebarTreeView component (ttk.Treeview) for the pyezsh MVP.
#
# Notes:
#	- Rooted filesystem tree (configurable; defaults to Path.home()).
#	- Lazy loads directories for fast startup.
#	- Depth-limited expansion (max_depth).
#	- Directory click behavior: select + expand/collapse.
#	- Emits on_select(Path) when selection changes.
#	- Read-only: no file operations, no rename, no drag/drop.
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date			Author						Change
# ---------------------------------------------------------------------------
# 01/05/2026	Paul G. LeDuc				Initial version
# 01/07/2026	Paul G. LeDuc				Component integration + max_depth + click-to-expand
# ---------------------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import tkinter as tk
from tkinter import ttk

from pyezsh.ui.component import Component


@dataclass(slots=True)
class SidebarTreeView(Component):
	"""
	Read-only filesystem TreeView for the MVP sidebar.

	MVP Contract:
	- base_path configurable, default Path.home()
	- max_depth defaults to 3
	- single selection
	- directory click selects + expands/collapses
	- show dirs + files
	- hide dotfiles by default
	"""

	base_path: Path | None = None
	max_depth: int = 3
	hide_dotfiles: bool = True
	max_children_per_dir: int = 500  # safety for huge dirs

	# Optional internal title/header (generally False if parent pane has a title)
	show_title: bool = False
	title: str = "Sidebar"

	on_select: Optional[Callable[[Path], None]] = None

	tree: ttk.Treeview | None = field(default=None, init=False, repr=False)

	# Tree item id -> filesystem Path
	_item_to_path: dict[str, Path] = field(default_factory=dict, init=False, repr=False)

	# Tree item id -> depth relative to base (root=0)
	_item_depth: dict[str, int] = field(default_factory=dict, init=False, repr=False)

	def build(self, parent: tk.Misc) -> tk.Widget:
		root = ttk.Frame(parent)

		base = self._resolve_base_path()
		self.base_path = base

		row = 0
		if self.show_title:
			header = ttk.Frame(root)
			header.grid(row=row, column=0, columnspan=2, sticky="ew")
			ttk.Label(header, text=self.title).pack(side="left", padx=8, pady=4)

			sep = ttk.Separator(root, orient="horizontal")
			sep.grid(row=row + 1, column=0, columnspan=2, sticky="ew")
			row = 2

		self.tree = ttk.Treeview(root, show="tree", selectmode="browse")
		vsb = ttk.Scrollbar(root, orient="vertical", command=self.tree.yview)
		self.tree.configure(yscrollcommand=vsb.set)

		self.tree.grid(row=row, column=0, sticky="nsew")
		vsb.grid(row=row, column=1, sticky="ns")

		root.rowconfigure(row, weight=1)
		root.columnconfigure(0, weight=1)

		# Bindings
		self.tree.bind("<<TreeviewOpen>>", self._on_open)
		self.tree.bind("<<TreeviewSelect>>", self._on_select)
		self.tree.bind("<ButtonRelease-1>", self._on_click)

		# Root node
		root_id = self.tree.insert("", "end", text=self._format_root_label(base), open=True)
		self._item_to_path[root_id] = base
		self._item_depth[root_id] = 0

		# Populate first level immediately for usability
		self._populate_dir(root_id, base, parent_depth=0)

		return root

	# -----------------------------------------------------------------------
	# Internals
	# -----------------------------------------------------------------------

	def _resolve_base_path(self) -> Path:
		if self.base_path is not None:
			return Path(self.base_path).expanduser().resolve()

		# MVP default: home (fallback to cwd if needed)
		try:
			return Path.home().resolve()
		except Exception:
			try:
				return Path.cwd().resolve()
			except Exception:
				return Path(".")

	def _is_dotfile(self, p: Path) -> bool:
		return p.name.startswith(".")

	def _safe_iterdir(self, p: Path) -> list[Path]:
		try:
			items = list(p.iterdir())
		except Exception:
			return []

		if self.hide_dotfiles:
			items = [x for x in items if not self._is_dotfile(x)]

		# Sort: dirs first, then files; case-insensitive
		items.sort(key=lambda x: (not x.is_dir(), x.name.lower()))

		if self.max_children_per_dir and len(items) > self.max_children_per_dir:
			return items[: self.max_children_per_dir]

		return items

	def _has_placeholder(self, item_id: str) -> bool:
		if self.tree is None:
			return False
		children = self.tree.get_children(item_id)
		if len(children) != 1:
			return False
		return self.tree.item(children[0], "text") == "..."

	def _add_placeholder(self, item_id: str) -> None:
		if self.tree is None:
			return
		self.tree.insert(item_id, "end", text="...")

	def _clear_children(self, item_id: str) -> None:
		if self.tree is None:
			return
		for child in self.tree.get_children(item_id):
			self.tree.delete(child)

	def _populate_dir(self, parent_item: str, dir_path: Path, parent_depth: int) -> None:
		if self.tree is None:
			return

		# At/over max depth: do not expand further
		if parent_depth >= self.max_depth:
			return

		self._clear_children(parent_item)

		for p in self._safe_iterdir(dir_path):
			try:
				is_dir = p.is_dir()
			except Exception:
				is_dir = False

			node_id = self.tree.insert(parent_item, "end", text=p.name, open=False)
			self._item_to_path[node_id] = p
			self._item_depth[node_id] = parent_depth + 1

			# Add placeholder only if expandable under max_depth
			if is_dir and (parent_depth + 1) < self.max_depth:
				self._add_placeholder(node_id)

	def _toggle_open(self, item_id: str) -> None:
		if self.tree is None:
			return

		path = self._item_to_path.get(item_id)
		if path is None:
			return

		try:
			if not path.is_dir():
				return
		except Exception:
			return

		current_open = bool(self.tree.item(item_id, "open"))
		new_open = not current_open
		self.tree.item(item_id, open=new_open)

		# If opening and placeholder exists, lazy load
		if new_open and self._has_placeholder(item_id):
			depth = int(self._item_depth.get(item_id, 0))
			self._populate_dir(item_id, path, parent_depth=depth)

	def _on_open(self, _event: tk.Event) -> None:
		"""
		User expanded via disclosure icon / keyboard.
		If placeholder exists, populate directory.
		"""
		if self.tree is None:
			return

		focus = self.tree.focus()
		if not focus:
			return

		if not self._has_placeholder(focus):
			return

		path = self._item_to_path.get(focus)
		if path is None:
			return

		try:
			if not path.is_dir():
				return
		except Exception:
			return

		depth = int(self._item_depth.get(focus, 0))
		self._populate_dir(focus, path, parent_depth=depth)

	def _on_click(self, event: tk.Event) -> None:
		"""
		Directory click behavior: select + toggle expand/collapse.

		Robust behavior across Tk builds:
		- Only toggle when clicking the item *text*.
		- Let Tk handle open/close when clicking the disclosure indicator.
		"""
		if self.tree is None:
			return

		try:
			region = self.tree.identify_region(event.x, event.y)
		except Exception:
			region = ""

		# Only respond to clicks on the actual item area.
		# ("tree" is where the item label/indent is; "cell" can appear in some themes.)
		if region not in ("tree", "cell"):
			return

		try:
			element = self.tree.identify_element(event.x, event.y)
		except Exception:
			element = ""

		# Only toggle when the user clicks the label text.
		# Indicator clicks will *not* be "text" on most Tk builds.
		if element != "text":
			return

		item_id = self.tree.identify_row(event.y)
		if not item_id:
			return

		# Ensure single selection
		try:
			self.tree.selection_set(item_id)
			self.tree.focus(item_id)
		except Exception:
			pass

		self._toggle_open(item_id)

	def _on_select(self, _event: tk.Event) -> None:
		if self.tree is None:
			return

		sel = self.tree.selection()
		if not sel:
			return

		item_id = sel[0]
		path = self._item_to_path.get(item_id)
		if path is None:
			return

		if self.on_select:
			self.on_select(path)

	def _format_root_label(self, p: Path) -> str:
		try:
			home = Path.home().resolve()
			rp = p.resolve()
			try:
				rel = rp.relative_to(home)
				return f"~/{rel}"
			except Exception:
				pass
		except Exception:
			pass

		try:
			return str(p)
		except Exception:
			return p.name or "root"
