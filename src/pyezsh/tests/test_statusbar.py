# ---------------------------------------------------------------------------
# File: test_statusbar.py
# ---------------------------------------------------------------------------
# Description:
#	Unit tests for StatusBar logic.
#
# Notes:
#	- Headless-safe: does NOT create any Tk widgets.
#	- Focuses on pure logic + logging handler behavior.
#
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date			Author						Change
# ---------------------------------------------------------------------------
# 01/03/2026	Paul G. LeDuc				Initial tests
# ---------------------------------------------------------------------------

from __future__ import annotations

import logging

from pyezsh.ui.statusbar import StatusBar, StatusBarLogHandler


def test_statusbar_default_anchor_for_left_middle_right():
	sb = StatusBar()

	assert sb._default_anchor_for("left") == "w"
	assert sb._default_anchor_for("right") == "e"
	assert sb._default_anchor_for("middle") == "center"
	assert sb._default_anchor_for("anything_else") == "center"


def test_statusbar_pady_scales_with_height_rows():
	sb1 = StatusBar(height_rows=1)
	assert sb1._pady() == 2

	sb2 = StatusBar(height_rows=2)
	assert sb2._pady() == 8

	sb3 = StatusBar(height_rows=3)
	assert sb3._pady() == 14


def test_statusbar_log_handler_emits_to_section_with_formatter():
	sb = StatusBar()
	calls: list[tuple[str, str]] = []

	# Patch set_text so we don't depend on Tk widgets
	sb.set_text = lambda section, value: calls.append((section, value))  # type: ignore[method-assign]

	h = StatusBarLogHandler(sb, section="middle", level=logging.INFO)
	h.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

	logger = logging.getLogger("pyezsh.tests.statusbar")
	logger.setLevel(logging.DEBUG)
	logger.propagate = False

	# Isolate this logger so the handler count is deterministic
	for existing in list(logger.handlers):
		logger.removeHandler(existing)

	logger.addHandler(h)

	logger.info("hello")

	assert calls == [("middle", "INFO: hello")]


def test_statusbar_log_handler_never_raises_on_bad_format():
	sb = StatusBar()
	calls: list[tuple[str, str]] = []

	# Patch set_text so we don't depend on Tk widgets
	sb.set_text = lambda section, value: calls.append((section, value))  # type: ignore[method-assign]

	h = StatusBarLogHandler(sb, section="middle", level=logging.INFO)

	# Force formatter to explode
	class _BadFormatter(logging.Formatter):
		def format(self, record: logging.LogRecord) -> str:
			raise RuntimeError("boom")

	h.setFormatter(_BadFormatter())

	logger = logging.getLogger("pyezsh.tests.statusbar.badfmt")
	logger.setLevel(logging.DEBUG)
	logger.propagate = False

	for existing in list(logger.handlers):
		logger.removeHandler(existing)
	logger.addHandler(h)

	# Should not raise, and should not call set_text
	logger.info("hello")

	assert calls == []
