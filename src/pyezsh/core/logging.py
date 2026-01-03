# ---------------------------------------------------------------------------
# File: logging.py
# ---------------------------------------------------------------------------
# Description:
#	Core logging helpers for pyezsh (stdlib logging).
#
# Notes:
#	- Uses Python stdlib logging only.
#	- Safe to call before any UI is mounted (no Tk dependencies).
#	- Idempotent initialization (won’t duplicate handlers).
#	- Configuration is intentionally lightweight and cfg-driven.
#
#	Supported cfg keys (first match wins):
#	- Level:
#		"logging.level", "log_level"	(default: "INFO")
#	- Console handler:
#		"logging.console", "log_console" (default: True)
#	- File handler:
#		"logging.file", "log_file"	(default: None)
#	- File mode:
#		"logging.file_mode", "log_file_mode" (default: "a")
#	- Root reset (clear handlers on re-init):
#		"logging.reset_root", "log_reset_root" (default: True)
#	- Format:
#		"logging.format", "log_format" (default: standard format)
#	- Date format:
#		"logging.datefmt", "log_datefmt" (default: "%Y-%m-%d %H:%M:%S")
#
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date			Author						Change
# ---------------------------------------------------------------------------
# 01/02/2026	Paul G. LeDuc				Initial coding / release
# 01/02/2026	Paul G. LeDuc				Add get_app_logger + reset_root + file_mode
# ---------------------------------------------------------------------------

from __future__ import annotations

from typing import Any
import logging
import os


# ---------------------------------------------------------------------------
# Module-scoped state (idempotent init)
# ---------------------------------------------------------------------------

_INITIALIZED: bool = False
_CONFIG_SIGNATURE: tuple[Any, ...] | None = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_logger(name: str) -> logging.Logger:
	"""
	Return a logger by explicit name.
	"""
	return logging.getLogger(name)


def get_app_logger(component: str | None = None) -> logging.Logger:
	"""
	Return an application-scoped logger.

	Examples:
		get_app_logger()              -> pyezsh.app
		get_app_logger("keys")        -> pyezsh.app.keys
		get_app_logger("filesystem") -> pyezsh.app.filesystem
	"""
	base = "pyezsh.app"
	if component:
		return logging.getLogger(f"{base}.{component}")
	return logging.getLogger(base)


def init_logging(cfg: Any | None = None) -> None:
	"""
	Initialize stdlib logging for pyezsh.

	This is safe to call multiple times. Reconfiguration occurs only if the
	configuration signature changes (to prevent duplicate handlers).

	Args:
		cfg:
			Any object that supports cfg.get(key, default) (e.g., AppConfig) or a dict-like.
	"""
	global _INITIALIZED, _CONFIG_SIGNATURE

	# Pull config values (minimal + flexible)
	level_raw = _cfg_get(cfg, "logging.level", None)
	if level_raw is None:
		level_raw = _cfg_get(cfg, "log_level", "INFO")

	console_enabled = _cfg_get(cfg, "logging.console", None)
	if console_enabled is None:
		console_enabled = _cfg_get(cfg, "log_console", True)

	log_file = _cfg_get(cfg, "logging.file", None)
	if log_file is None:
		log_file = _cfg_get(cfg, "log_file", None)

	file_mode = _cfg_get(cfg, "logging.file_mode", None)
	if file_mode is None:
		file_mode = _cfg_get(cfg, "log_file_mode", "a")

	reset_root = _cfg_get(cfg, "logging.reset_root", None)
	if reset_root is None:
		reset_root = _cfg_get(cfg, "log_reset_root", True)

	fmt = _cfg_get(cfg, "logging.format", None)
	if fmt is None:
		fmt = _cfg_get(cfg, "log_format", None)

	datefmt = _cfg_get(cfg, "logging.datefmt", None)
	if datefmt is None:
		datefmt = _cfg_get(cfg, "log_datefmt", "%Y-%m-%d %H:%M:%S")

	level = _coerce_level(level_raw)

	if fmt is None:
		fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

	file_mode = _coerce_file_mode(file_mode)

	# Signature used to avoid duplicating handlers on repeated init calls
	signature: tuple[Any, ...] = (
		level,
		bool(console_enabled),
		str(log_file) if log_file else None,
		file_mode,
		bool(reset_root),
		str(fmt),
		str(datefmt),
	)

	if _INITIALIZED and _CONFIG_SIGNATURE == signature:
		return

	_configure_root_logger(
		level=level,
		console_enabled=bool(console_enabled),
		log_file=str(log_file) if log_file else None,
		file_mode=file_mode,
		fmt=str(fmt),
		datefmt=str(datefmt),
		reset_root=bool(reset_root),
	)

	_INITIALIZED = True
	_CONFIG_SIGNATURE = signature


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _cfg_get(cfg: Any | None, key: str, default: Any = None) -> Any:
	"""
	Best-effort config getter.

	Supports:
	- cfg.get(key, default)
	- dict-like objects
	"""
	if cfg is None:
		return default

	getter = getattr(cfg, "get", None)
	if callable(getter):
		try:
			return getter(key, default)
		except Exception:
			return default

	try:
		# dict-like fallback
		return cfg[key]  # type: ignore[index]
	except Exception:
		return default


def _coerce_level(level: Any) -> int:
	"""
	Convert common representations of logging levels to an int.
	"""
	if isinstance(level, int):
		return level

	if isinstance(level, str):
		val = level.strip().upper()
		if val.isdigit():
			try:
				return int(val)
			except Exception:
				return logging.INFO
		return getattr(logging, val, logging.INFO)

	return logging.INFO


def _coerce_file_mode(mode: Any) -> str:
	"""
	Normalize file mode for FileHandler.
	Only allow "a" or "w" to keep this simple/safe.
	"""
	if isinstance(mode, str):
		val = mode.strip().lower()
		if val in ("a", "w"):
			return val
	return "a"


def _configure_root_logger(
	*,
	level: int,
	console_enabled: bool,
	log_file: str | None,
	file_mode: str,
	fmt: str,
	datefmt: str,
	reset_root: bool,
) -> None:
	"""
	Configure the root logger in a safe, idempotent way.

	If reset_root=True, clear existing handlers to prevent duplicates.
	"""
	root = logging.getLogger()
	root.setLevel(level)

	if reset_root:
		for h in list(root.handlers):
			try:
				root.removeHandler(h)
			except Exception:
				pass

	formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)

	if console_enabled:
		ch = logging.StreamHandler()
		ch.setLevel(level)
		ch.setFormatter(formatter)
		root.addHandler(ch)

	if log_file:
		_ensure_parent_dir(log_file)
		fh = logging.FileHandler(log_file, mode=file_mode, encoding="utf-8")
		fh.setLevel(level)
		fh.setFormatter(formatter)
		root.addHandler(fh)


def _ensure_parent_dir(path: str) -> None:
	"""
	Create parent directory for a log file if needed.
	"""
	parent = os.path.dirname(os.path.abspath(path))
	if not parent:
		return
	try:
		os.makedirs(parent, exist_ok=True)
	except Exception:
		# If we can't create the directory, don't crash the app here.
		pass


# ---------------------------------------------------------------------------
# Test helper
# ---------------------------------------------------------------------------

def _reset_logging_for_tests() -> None:
	"""
	Reset module-scoped init state (intended for unit tests only).
	"""
	global _INITIALIZED, _CONFIG_SIGNATURE
	_INITIALIZED = False
	_CONFIG_SIGNATURE = None
