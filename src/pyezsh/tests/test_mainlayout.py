# ---------------------------------------------------------------------------
# File: test_mainlayout.py
# ---------------------------------------------------------------------------
# Description:
#	Unit tests for MainLayout helpers.
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date			Author						Change
# ---------------------------------------------------------------------------
# 01/06/2026	Paul G. LeDuc				Initial tests
# ---------------------------------------------------------------------------

from __future__ import annotations

from pyezsh.ui.mainlayout import MainLayout


def test_clamp_bounds() -> None:
	ml = MainLayout()
	assert ml._clamp(5, 10, 20) == 10
	assert ml._clamp(15, 10, 20) == 15
	assert ml._clamp(25, 10, 20) == 20
