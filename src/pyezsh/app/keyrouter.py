# ---------------------------------------------------------------------------
# File: keyrouter.py
# ---------------------------------------------------------------------------
# Description:
#	KeyRouter for pyezsh (contextual key routing -> command execution).
#
# Notes:
#	- KeyRouter is UI-toolkit-agnostic: it routes by key sequence strings.
#	- Uses layered resolution:
#		1) Focused component keymap (optional)
#		2) Current mode keymap (optional)
#		3) Global/app keymap
#	- Keymaps map to command ids; execution uses CommandRegistry.
#
# ---------------------------------------------------------------------------
# Revision History
# ---------------------------------------------------------------------------
# Date			Author						Change
# ---------------------------------------------------------------------------
# 01/01/2026	Paul G. LeDuc				Initial coding / release
# 01/01/2026	Paul G. LeDuc				Align with KeyMap API (resolve_keyseq translation)
# 01/01/2026	Paul G. LeDuc				Use Protocol for KeyMapLike (typing-safe decoupling)
# ---------------------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional, Protocol, runtime_checkable

from pyezsh.app.commands import CommandContext, CommandRegistry


FocusProvider = Callable[[], Optional[str]]


@runtime_checkable
class KeyMapLike(Protocol):
	"""
	Minimal interface KeyRouter needs from a keymap.
	This keeps KeyRouter decoupled from a concrete KeyMap implementation.
	"""
	def resolve_keyseq(self, keyseq: str) -> Optional[str]:
		...


@dataclass(slots=True)
class KeyRouter:
	"""
	KeyRouter

	Contextual key routing:
	- keyseq -> command_id using layered KeyMaps
	- command_id -> execute via CommandRegistry
	"""
	registry: CommandRegistry
	global_keymap: KeyMapLike

	# Optional mode routing
	mode_keymaps: dict[str, KeyMapLike] = field(default_factory=dict)
	_mode: Optional[str] = None

	# Optional focus routing
	component_keymaps: dict[str, KeyMapLike] = field(default_factory=dict)
	focus_provider: Optional[FocusProvider] = None

	def set_mode(self, mode: Optional[str]) -> None:
		self._mode = mode

	def get_mode(self) -> Optional[str]:
		return self._mode

	def set_focus_provider(self, provider: Optional[FocusProvider]) -> None:
		self.focus_provider = provider

	def register_mode_keymap(self, mode: str, keymap: KeyMapLike) -> None:
		self.mode_keymaps[mode] = keymap

	def unregister_mode_keymap(self, mode: str) -> None:
		self.mode_keymaps.pop(mode, None)

	def register_component_keymap(self, component_id: str, keymap: KeyMapLike) -> None:
		self.component_keymaps[component_id] = keymap

	def unregister_component_keymap(self, component_id: str) -> None:
		self.component_keymaps.pop(component_id, None)

	def route_keyseq(self, keyseq: str, ctx: CommandContext) -> bool:
		"""
		Route a key sequence string to a command.

		Returns:
			True if handled (a command executed), else False.

		Notes:
			- CommandRegistry enforces visibility/enablement.
			- If the command is not found/enabled/visible, exceptions propagate.
			  App-level Tk handlers should catch and decide whether to swallow.
		"""
		command_id = self.resolve_command_id(keyseq)
		if not command_id:
			return False

		self.registry.execute(command_id, ctx, require_visible=True)
		return True

	def resolve_command_id(self, keyseq: str) -> Optional[str]:
		"""
		Resolve a keyseq to a command id using layered keymaps.

		Resolution order:
			1) Focused component keymap
			2) Current mode keymap
			3) Global/app keymap

		KeyMapLike is responsible for handling both raw matches and
		Tk "<...>" -> canonical translation matches.
		"""
		# 1) Focused component map
		focus_id = self.focus_provider() if self.focus_provider else None
		if focus_id:
			km = self.component_keymaps.get(focus_id)
			if km:
				cid = km.resolve_keyseq(keyseq)
				if cid:
					return cid

		# 2) Mode map
		if self._mode:
			km = self.mode_keymaps.get(self._mode)
			if km:
				cid = km.resolve_keyseq(keyseq)
				if cid:
					return cid

		# 3) Global/app map
		return self.global_keymap.resolve_keyseq(keyseq)
