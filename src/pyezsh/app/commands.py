# ---------------------------------------------------------------------------
# File: commands.py
# ---------------------------------------------------------------------------
# Description:
#	Command model + CommandRegistry for pyezsh.
#
# Notes:
#	Commands provide a single invocation spine for UI actions (menus, keys, buttons).
#	This module is UI/toolkit-agnostic. UI layers should:
#	- define commands (register_commands)
#	- bind keys (bind_keys)
#	- route input to registry.execute / registry.execute_shortcut
#
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date			Author						Change
# ---------------------------------------------------------------------------
# 12/30/2025	Paul G. LeDuc				Initial coding / release
# 12/31/2025	Paul G. LeDuc				Refine API (context, visibility, shortcuts)
# ---------------------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Optional
import re


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------
CommandId = str
Shortcut = str
Tags = tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CommandContext:
	"""
	CommandContext

	Context passed to command handlers and predicates.
	Keep this UI/toolkit-agnostic.
	"""
	app: Any
	state: Any
	services: Mapping[str, Any] = field(default_factory=dict)
	extra: Mapping[str, Any] = field(default_factory=dict)


Predicate = Callable[[CommandContext], bool]
Handler = Callable[[CommandContext], Any]


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
class CommandError(Exception):
	pass


class CommandNotFound(CommandError):
	pass


class CommandAlreadyRegistered(CommandError):
	pass


class ShortcutAlreadyBound(CommandError):
	pass


class CommandNotEnabled(CommandError):
	pass


class CommandNotVisible(CommandError):
	pass


# ---------------------------------------------------------------------------
# Shortcut normalization
# ---------------------------------------------------------------------------
_MOD_ORDER = ("CTRL", "ALT", "SHIFT", "CMD")


def normalize_shortcut(value: str) -> str:
	"""
	Normalize shortcut to a canonical form.

	Examples:
		"ctrl+o" -> "CTRL+O"
		"Ctrl + Shift + p" -> "CTRL+SHIFT+P"
		"cmd+k" -> "CMD+K"
	"""
	if value is None:
		raise ValueError("Shortcut cannot be None")

	s = value.strip()
	if not s:
		raise ValueError("Shortcut cannot be empty")

	parts = [p.strip() for p in re.split(r"\s*\+\s*", s) if p.strip()]
	if not parts:
		raise ValueError(f"Invalid shortcut: {value!r}")

	mods: list[str] = []
	keys: list[str] = []

	for p in parts:
		up = p.upper()

		if up in ("CONTROL", "CTRL"):
			mods.append("CTRL")
			continue
		if up in ("OPTION", "ALT"):
			mods.append("ALT")
			continue
		if up == "SHIFT":
			mods.append("SHIFT")
			continue
		if up in ("COMMAND", "CMD", "META"):
			mods.append("CMD")
			continue

		keys.append(up)

	modset = {m for m in mods}
	ordered_mods = [m for m in _MOD_ORDER if m in modset]

	if len(keys) != 1:
		raise ValueError(f"Shortcut must include exactly one key: {value!r}")

	return "+".join([*ordered_mods, keys[0]])


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class Command:
	"""
	Command

	Represents an action that can be invoked by id.

	- id:			Unique identifier (required).
	- label:		User-facing label (required).
	- handler:		Callable executed on invoke (handler(ctx)).
	- description:	Optional help text.
	- tags:			Optional tags for search/palette.
	- shortcut:		Optional default shortcut (can be overridden via bind_shortcut).

	- enabled:		Bool or predicate(ctx)->bool.
	- visible:		Bool or predicate(ctx)->bool.

	- order:		Used for palette/menu ordering when needed.
	"""
	id: CommandId
	label: str
	handler: Handler

	description: str = ""
	tags: Tags = ()

	shortcut: Optional[Shortcut] = None

	enabled: bool | Predicate = True
	visible: bool | Predicate = True

	order: int = 1000


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
class CommandRegistry:
	"""
	CommandRegistry

	Stores commands by id, binds shortcuts, and invokes them safely.
	"""

	def __init__(self) -> None:
		self._commands: dict[CommandId, Command] = {}
		self._shortcuts: dict[Shortcut, CommandId] = {}

	# ----------------------------
	# Registration
	# ----------------------------
	def register(self, command: Command, *, replace: bool = False) -> None:
		if not command.id:
			raise ValueError("Command id must be a non-empty string")

		if command.id in self._commands and not replace:
			raise CommandAlreadyRegistered(f"Duplicate command id: {command.id!r}")

		if replace and command.id in self._commands:
			self._remove_shortcut_bindings_for_command(command.id)

		self._commands[command.id] = command

		if command.shortcut:
			self.bind_shortcut(command.shortcut, command.id, replace=replace)

	def unregister(self, command_id: CommandId) -> None:
		if command_id not in self._commands:
			raise CommandNotFound(f"Unknown command id: {command_id!r}")

		self._remove_shortcut_bindings_for_command(command_id)
		del self._commands[command_id]

	def has(self, command_id: CommandId) -> bool:
		return command_id in self._commands

	def get(self, command_id: CommandId) -> Command:
		try:
			return self._commands[command_id]
		except KeyError as ex:
			raise CommandNotFound(f"Unknown command id: {command_id!r}") from ex

	def ids(self) -> list[CommandId]:
		return list(self._commands.keys())

	def all(self) -> tuple[Command, ...]:
		return tuple(sorted(self._commands.values(), key=lambda c: (c.order, c.label.lower(), c.id)))

	# ----------------------------
	# Shortcuts
	# ----------------------------
	def bind_shortcut(self, shortcut: Shortcut, command_id: CommandId, *, replace: bool = False) -> None:
		if command_id not in self._commands:
			raise CommandNotFound(f"Unknown command id: {command_id!r}")

		key = normalize_shortcut(shortcut)

		if key in self._shortcuts and not replace:
			raise ShortcutAlreadyBound(f"Shortcut already bound: {key} -> {self._shortcuts[key]}")

		self._shortcuts[key] = command_id

	def unbind_shortcut(self, shortcut: Shortcut) -> None:
		key = normalize_shortcut(shortcut)
		self._shortcuts.pop(key, None)

	def resolve_shortcut(self, shortcut: Shortcut) -> Optional[CommandId]:
		key = normalize_shortcut(shortcut)
		return self._shortcuts.get(key)

	# ----------------------------
	# Evaluation
	# ----------------------------
	def is_visible(self, command_id: CommandId, ctx: CommandContext) -> bool:
		cmd = self.get(command_id)
		return self._eval_predicate(cmd.visible, ctx)

	def is_enabled(self, command_id: CommandId, ctx: CommandContext) -> bool:
		cmd = self.get(command_id)
		return self._eval_predicate(cmd.enabled, ctx)

	def can_execute(self, command_id: CommandId, ctx: CommandContext) -> bool:
		return self.is_visible(command_id, ctx) and self.is_enabled(command_id, ctx)

	# ----------------------------
	# Invocation
	# ----------------------------
	def execute(self, command_id: CommandId, ctx: CommandContext, *, require_visible: bool = True) -> Any:
		cmd = self.get(command_id)

		if require_visible and not self._eval_predicate(cmd.visible, ctx):
			raise CommandNotVisible(f"Command not visible: {command_id!r}")

		if not self._eval_predicate(cmd.enabled, ctx):
			raise CommandNotEnabled(f"Command not enabled: {command_id!r}")

		return cmd.handler(ctx)

	def execute_shortcut(self, shortcut: Shortcut, ctx: CommandContext) -> Any:
		command_id = self.resolve_shortcut(shortcut)
		if not command_id:
			raise CommandNotFound(f"Shortcut not bound: {shortcut!r}")
		return self.execute(command_id, ctx, require_visible=True)

	# ----------------------------
	# UI helpers
	# ----------------------------
	def list_for_menu(self, ids: list[CommandId], ctx: CommandContext) -> list[Command]:
		out: list[Command] = []
		for cid in ids:
			cmd = self.get(cid)
			if self._eval_predicate(cmd.visible, ctx):
				out.append(cmd)
		return out

	def search(self, query: str, ctx: CommandContext, *, limit: int = 25) -> list[Command]:
		q = (query or "").strip().lower()
		if not q:
			return []

		candidates: list[tuple[int, Command]] = []
		for cmd in self._commands.values():
			if not self._eval_predicate(cmd.visible, ctx):
				continue
			score = self._score(cmd, q)
			if score > 0:
				candidates.append((score, cmd))

		candidates.sort(key=lambda t: (-t[0], t[1].order, t[1].label.lower(), t[1].id))
		return [cmd for _, cmd in candidates[:max(0, limit)]]

	# ----------------------------
	# Internals
	# ----------------------------
	def _remove_shortcut_bindings_for_command(self, command_id: CommandId) -> None:
		to_remove = [k for k, v in self._shortcuts.items() if v == command_id]
		for k in to_remove:
			del self._shortcuts[k]

	def _eval_predicate(self, value: bool | Predicate, ctx: CommandContext) -> bool:
		if isinstance(value, bool):
			return value
		return bool(value(ctx))

	def _score(self, cmd: Command, q: str) -> int:
		id_l = cmd.id.lower()
		label_l = cmd.label.lower()
		desc_l = (cmd.description or "").lower()
		tags_l = " ".join(cmd.tags).lower()

		if id_l == q:
			return 100
		if label_l == q:
			return 95
		if id_l.startswith(q):
			return 85
		if label_l.startswith(q):
			return 80
		if q in id_l:
			return 60
		if q in label_l:
			return 55
		if q in desc_l:
			return 30
		if q in tags_l:
			return 25
		return 0
