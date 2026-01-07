# ---------------------------------------------------------------------------
# File: test_content_viewer.py
# ---------------------------------------------------------------------------
# Description:
#	Unit tests for ContentViewer rendering decisions.
#
# Notes:
#	- Avoid GUI/Tk event loop tests (flaky in CI).
#	- Validate decision logic via a capture subclass that intercepts _write/_append.
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date			Author						Change
# ---------------------------------------------------------------------------
# 01/06/2026	Paul G. LeDuc				Initial tests
# ---------------------------------------------------------------------------

from __future__ import annotations

from pathlib import Path

from pyezsh.ui.content_viewer import ContentViewer


class _CaptureViewer(ContentViewer):
	def __init__(self, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		self.writes: list[str] = []
		self.appends: list[str] = []

	def _write(self, s: str) -> None:
		self.writes.append(s)

	def _append(self, s: str) -> None:
		self.appends.append(s)


def test_set_path_directory_renders_summary(tmp_path: Path) -> None:
	(tmp_path / "a.txt").write_text("x", encoding="utf-8")
	(tmp_path / "b.txt").write_text("y", encoding="utf-8")

	v = _CaptureViewer()
	v.set_path(tmp_path)

	assert v.writes, "expected _write to be called"
	assert "Directory" in v.writes[-1]
	assert str(tmp_path) in v.writes[-1]
	assert v.appends, "expected _append to be called"
	assert "Items:" in v.appends[-1]


def test_set_path_large_file_shows_size_limit(tmp_path: Path) -> None:
	p = tmp_path / "big.txt"
	p.write_bytes(b"x" * 1024)

	v = _CaptureViewer(max_bytes=10)  # force size rejection
	v.set_path(p)

	assert v.writes
	assert "too large" in v.writes[-1].lower()


def test_set_path_non_utf8_reports_binary(tmp_path: Path) -> None:
	p = tmp_path / "bin.dat"
	p.write_bytes(b"\xff\xfe\xfd\xfc")

	v = _CaptureViewer(max_bytes=1024)
	v.set_path(p)

	assert v.writes
	assert "non-utf-8" in v.writes[-1].lower() or "binary" in v.writes[-1].lower()


def test_set_path_truncates_lines(tmp_path: Path) -> None:
	p = tmp_path / "many.txt"
	p.write_text("a\nb\nc\nd\ne\n", encoding="utf-8")

	v = _CaptureViewer(max_lines=2)
	v.set_path(p)

	assert v.writes
	out = v.writes[-1]
	assert "a\n" in out
	assert "b\n" in out
	assert "truncated" in out.lower()
