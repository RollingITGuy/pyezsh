# ---------------------------------------------------------------------------
# File: test_dialogs.py
# ---------------------------------------------------------------------------
# Description:
#	Tests for dialog helpers.
#
# Notes:
#	- We monkeypatch tkinter.messagebox so tests never show real UI.
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date			Author						Change
# ---------------------------------------------------------------------------
# 01/06/2026	Paul G. LeDuc				Initial version
# ---------------------------------------------------------------------------

from __future__ import annotations

from typing import Any

from pyezsh.ui import dialogs


class _Telemetry:
	def __init__(self) -> None:
		self.events: list[tuple[str, dict[str, Any]]] = []

	def event(self, name: str, data: dict[str, Any]) -> None:
		self.events.append((name, data))


class _Logger:
	def __init__(self) -> None:
		self.lines: list[str] = []

	def info(self, fmt: str, *args: Any) -> None:
		# Keep this intentionally simple.
		try:
			self.lines.append(fmt % args)
		except Exception:
			self.lines.append(fmt)


def test_show_not_implemented_calls_messagebox_without_parent(monkeypatch: Any) -> None:
	calls: list[tuple[str, str, bool]] = []

	def _fake_showinfo(title: str, message: str, **kwargs: Any) -> None:
		calls.append((title, message, "parent" in kwargs))

	# Patch the exact object used by dialogs.py
	monkeypatch.setattr(dialogs.messagebox, "showinfo", _fake_showinfo)

	dialogs.show_not_implemented("File → Open", parent=None)

	assert calls, "expected messagebox.showinfo to be called"
	title, message, has_parent = calls[0]
	assert title == "Not Yet Implemented"
	assert "File → Open" in message
	assert has_parent is False


def test_show_not_implemented_emits_telemetry_and_logs(monkeypatch: Any) -> None:
	calls: list[tuple[str, str, bool]] = []

	def _fake_showinfo(title: str, message: str, **kwargs: Any) -> None:
		calls.append((title, message, "parent" in kwargs))

	monkeypatch.setattr(dialogs.messagebox, "showinfo", _fake_showinfo)

	t = _Telemetry()
	l = _Logger()

	dialogs.show_not_implemented("Help → Docs", telemetry=t, logger=l)

	assert calls, "expected messagebox.showinfo to be called"
	assert t.events == [("ui.not_implemented", {"feature": "Help → Docs"})]
	assert any("Not implemented: Help → Docs" in s for s in l.lines)
