# ---------------------------------------------------------------------------
# File: __init__.py
# ---------------------------------------------------------------------------
# Description:
#	Core package for pyezsh (logging, telemetry, config, etc.).
#
# Notes:
#	Keep this lightweight. Re-export stable public helpers.
#
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date			Author						Change
# ---------------------------------------------------------------------------
# 01/02/2026	Paul G. LeDuc				Initial coding / release
# 01/02/2026	Paul G. LeDuc				Re-export get_app_logger
# 01/03/2026	Paul G. LeDuc				Export telemetry functions
# ---------------------------------------------------------------------------

from __future__ import annotations

from .logging import init_logging, get_logger, get_app_logger
from .telemetry import init_telemetry, get_telemetry

__all__ = [
	"get_logger",
	"get_app_logger",
	"init_logging",
    "init_telemetry",
    "get_telemetry"
]
