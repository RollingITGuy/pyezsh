# ---------------------------------------------------------------------------
# File: app.py
# ---------------------------------------------------------------------------
# Description:
#   Starting point for pyezsh app.
#
# Notes:
#
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date          Author                      Change
# ---------------------------------------------------------------------------
# 12/17/2025    Paul G. LeDuc               Initial coding / release
# ---------------------------------------------------------------------------

from __future__ import annotations
from typing import Any 
import tkinter as tk
import ttkthemes as ttk


class App:
	"""
	App

	Main application class for pyezsh 
	"""

	# -----------------------------------------------------------------------
	# Class variables (shared across all instances)
	# -----------------------------------------------------------------------
	width: int = 0
	height: int = 0
	title: str = ""
	cfg: dict[str, int] = {}
	
	def __init__(self) -> None:
		"""
		Initialize a new instance of ClassName.
		"""
		pass

	def __str__(self) -> str:
		"""
		User-friendly string representation.
		"""
		return f"{self.__class__.__name__}()"

	def __repr__(self) -> str:
		"""
		Developer-friendly string representation.
		"""
		return f"<{self.__class__.__name__}>"
