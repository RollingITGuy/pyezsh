# ---------------------------------------------------------------------------
# File: test_sidebar_treeview.py
# ---------------------------------------------------------------------------
# Description:
#	Unit tests for SidebarTreeView filesystem behavior.
#
# Notes:
#	- Avoid GUI/Tk event loop tests (flaky in CI).
#	- Focus on deterministic filesystem logic: filtering, ordering, truncation.
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date			Author						Change
# ---------------------------------------------------------------------------
# 01/06/2026	Paul G. LeDuc				Initial tests
# ---------------------------------------------------------------------------

from __future__ import annotations

from pathlib import Path

from pyezsh.ui.sidebar_treeview import SidebarTreeView


def _touch(p: Path, *, text: str = "") -> None:
	p.parent.mkdir(parents=True, exist_ok=True)
	p.write_text(text, encoding="utf-8")


def test_safe_iterdir_filters_dotfiles(tmp_path: Path) -> None:
	(tmp_path / "adir").mkdir()
	_touch(tmp_path / "afile.txt", text="x")
	(tmp_path / ".hidden_dir").mkdir()
	_touch(tmp_path / ".hidden_file", text="x")

	stv = SidebarTreeView(base_path=tmp_path, hide_dotfiles=True)
	items = stv._safe_iterdir(tmp_path)

	names = [p.name for p in items]
	assert "adir" in names
	assert "afile.txt" in names
	assert ".hidden_dir" not in names
	assert ".hidden_file" not in names


def test_safe_iterdir_sorts_dirs_first_then_files(tmp_path: Path) -> None:
	(tmp_path / "bdir").mkdir()
	(tmp_path / "adir").mkdir()
	_touch(tmp_path / "bfile.txt", text="x")
	_touch(tmp_path / "afile.txt", text="x")

	stv = SidebarTreeView(base_path=tmp_path, hide_dotfiles=False)
	items = stv._safe_iterdir(tmp_path)

	names = [p.name for p in items]
	assert names == ["adir", "bdir", "afile.txt", "bfile.txt"]


def test_safe_iterdir_truncates_max_children(tmp_path: Path) -> None:
	for i in range(20):
		_touch(tmp_path / f"f{i:02d}.txt", text="x")

	stv = SidebarTreeView(base_path=tmp_path, hide_dotfiles=False, max_children_per_dir=5)
	items = stv._safe_iterdir(tmp_path)

	assert len(items) == 5
