# ---------------------------------------------------------------------------
# File: __init__.py
# Description:
#	Public service exports for pyezsh.
#
#	This module defines the supported service API surface that can be accessed
#	via CommandContext.services. Services are UI-agnostic capabilities intended
#	to be shared across commands, components, and application logic.
#
# Notes:
#	- Services should not depend directly on Tk widgets where possible.
#	- App is responsible for constructing and wiring service instances.
#
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date			Author						Change
# ---------------------------------------------------------------------------
# 01/03/2026	Paul G. LeDuc				Initial coding / release
# ---------------------------------------------------------------------------

from .status import StatusService

__all__ = [
	"StatusService",
]
