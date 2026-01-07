# ---------------------------------------------------------------------------
# File: sidebar_treeview.py
# ---------------------------------------------------------------------------
# Description:
#	Read-only filesystem TreeView for the MVP sidebar.
#
# Notes:
#	- Rooted at a base path (cwd/home).
#	- Lazy loads directories for fast startup.
#	- Emits on_select(Path) for selection changes.
#	- Title/header is optional (App/MainLayout may provide pane titles).
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date			Author						Change
# ---------------------------------------------------------------------------
# 01/05/2026	Paul G. LeDuc       		Initial version
# 01/06/2026	Paul G. LeDuc				Optional title + parent-controlled layout
# ---------------------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import tkinter as tk
from tkinter import ttk


@dataclass(slots=True)
class SidebarTreeView:
	base_path: Path | None = None
	hide_dotfiles: bool = True
	max_children_per_dir: int = 500  # safety for huge dirs

	# Optional internal header (leave False when parent already provides titles)
	show_title: bool = False
	title: str = "Sidebar"

	on_select: Optional[Callable[[Path], None]] = None

	root: ttk.Frame | None = field(default=None, init=False, repr=False)
	tree: ttk.Treeview | None = field(default=None, init=False, repr=False)

	# Maps Treeview item ids -> filesystem paths
	_item_to_path: dict[str, Path] = field(default_factory=dict, init=False, repr=False)

	def mount(self, parent: tk.Misc) -> ttk.Frame:
		root = ttk.Frame(parent)
		self.root = root

		base = self._resolve_base_path()
		self.base_path = base

		# Optional header row (title)
		row = 0
		if self.show_title:
			header = ttk.Frame(root)
			header.grid(row=row, column=0, columnspan=2, sticky="ew")

			ttk.Label(header, text=self.title).pack(side="left", anchor="w", padx=8, pady=4)

			sep = ttk.Separator(root, orient="horizontal")
			sep.grid(row=row + 1, column=0, columnspan=2, sticky="ew")

			row = 2

		# Tree + scrollbar
		self.tree = ttk.Treeview(root, show="tree")
		vsb = ttk.Scrollbar(root, orient="vertical", command=self.tree.yview)
		self.tree.configure(yscrollcommand=vsb.set)

		self.tree.grid(row=row, column=0, sticky="nsew")
		vsb.grid(row=row, column=1, sticky="ns")

		root.rowconfigure(row, weight=1)
		root.columnconfigure(0, weight=1)

		# Root node
		display_root = self._format_root_label(base)
		root_id = self.tree.insert("", "end", text=display_root, open=True)
		self._item_to_path[root_id] = base

		# Populate root children and add lazy placeholders for dirs
		self._populate_dir(root_id, base)

		# Events
		self.tree.bind("<<TreeviewOpen>>", self._on_open, add="+")
		self.tree.bind("<<TreeviewSelect>>", self._on_select, add="+")

		return root

	def layout(self) -> None:
		"""
		Layout hook.

		Important:
		- If the parent already manages geometry, we don't fight it.
		- If nobody has placed our root yet, we pack it so the TreeView is visible.
		"""
		if self.root is None:
			return

		try:
			# Only pack if we are not already managed by pack/grid/place.
			if not self.root.winfo_manager():
				self.root.pack(fill="both", expand=True)
			self.root.update_idletasks()
		except Exception:
			pass

	# -----------------------------------------------------------------------
	# Internals
	# -----------------------------------------------------------------------

	def _resolve_base_path(self) -> Path:
		if self.base_path is not None:
			return Path(self.base_path).expanduser().resolve()

		try:
			return Path.cwd().resolve()
		except Exception:
			return Path.home().resolve()

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

	def _populate_dir(self, parent_item: str, dir_path: Path) -> None:
		if self.tree is None:
			return

		self._clear_children(parent_item)

		for p in self._safe_iterdir(dir_path):
			try:
				is_dir = p.is_dir()
			except Exception:
				is_dir = False

			node_id = self.tree.insert(parent_item, "end", text=p.name, open=False)
			self._item_to_path[node_id] = p

			if is_dir:
				# Lazy-load marker
				self._add_placeholder(node_id)

	def _on_open(self, _event: tk.Event) -> None:
		if self.tree is None:
			return

		focus = self.tree.focus()
		if not focus:
			return

		path = self._item_to_path.get(focus)
		if path is None:
			return

		if not path.is_dir():
			return

		# Only populate if we still have the placeholder
		if self._has_placeholder(focus):
			self._populate_dir(focus, path)

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
		"""
		Return a friendly display label for the root path.
		"""
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

		# Fallback: show the resolved path (or name if it exists)
		try:
			return str(p)
		except Exception:
			return p.name or "root"
