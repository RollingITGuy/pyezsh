# ---------------------------------------------------------------------------
# File: commands.py
# ---------------------------------------------------------------------------
# Description:
#   Command definitions + registry for pyezsh.
#
# Notes:
#   Commands provide a single invocation spine for UI actions (menus, keys, buttons).
#
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date			Author						Change
# ---------------------------------------------------------------------------
# 12/30/2025	Paul G. LeDuc				Initial coding / release
# 12/30/2025	Paul G. LeDuc				Add Command + CommandRegistry
# ---------------------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional


CommandHandler = Callable[[], Any]
EnabledCheck = Callable[[], bool]


@dataclass(frozen=True, slots=True)
class Command:
	"""
	Command

	Represents an action that can be invoked by id.

	- id:			Unique identifier (required).
	- handler:		Callable executed on invoke.
	- name:			Optional friendly label.
	- description:	Optional help text.
	- enabled:		Optional bool (static enable/disable).
	- enabled_fn:	Optional callable for dynamic enablement.
	- accelerators:	Optional list of display hints (e.g., "Ctrl+Q").
	"""
	id: str
	handler: CommandHandler

	name: Optional[str] = None
	description: Optional[str] = None

	enabled: bool = True
	enabled_fn: Optional[EnabledCheck] = None

	accelerators: tuple[str, ...] = field(default_factory=tuple)

	def is_enabled(self) -> bool:
		if not self.enabled:
			return False
		if self.enabled_fn is None:
			return True
		return bool(self.enabled_fn())


class CommandRegistry:
	"""
	CommandRegistry

	Stores commands by id and invokes them safely.
	"""

	def __init__(self) -> None:
		self._commands: dict[str, Command] = {}

	def register(self, command: Command) -> None:
		if not command.id:
			raise ValueError("Command id must be a non-empty string")

		if command.id in self._commands:
			raise ValueError(f"Duplicate command id: {command.id!r}")

		self._commands[command.id] = command

	def unregister(self, command_id: str) -> None:
		self._commands.pop(command_id, None)

	def has(self, command_id: str) -> bool:
		return command_id in self._commands

	def get(self, command_id: str) -> Optional[Command]:
		return self._commands.get(command_id)

	def ids(self) -> list[str]:
		return list(self._commands.keys())

	def invoke(self, command_id: str) -> Any:
		command = self._commands.get(command_id)
		if command is None:
			raise KeyError(f"Unknown command id: {command_id!r}")

		if not command.is_enabled():
			return None

		return command.handler()
