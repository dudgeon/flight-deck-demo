"""omnigent-slim's permission rules for the Claude Code terminal.

The slim build must never launch Claude Code in a mode that skips the
user's own approval. Every launch path (web UI, ``omnigent claude``,
automations) passes its final ``claude`` args through
:func:`enforce_claude_permission_args`, which:

- removes ``--dangerously-skip-permissions`` and
  ``--allow-dangerously-skip-permissions``;
- replaces any ``--permission-mode`` outside :data:`ALLOWED_CLAUDE_PERMISSION_MODES`
  with ``default``;
- adds ``--permission-mode default`` when no mode is given, so a user-level
  ``defaultMode`` such as ``auto`` or ``bypassPermissions`` never applies.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable

_logger = logging.getLogger("omnigent.slim_policy")

#: Modes that keep a human approval step for commands. ``default`` is the
#: one Claude Code labels "Manual".
ALLOWED_CLAUDE_PERMISSION_MODES: tuple[str, ...] = ("default", "acceptEdits", "plan")
DEFAULT_CLAUDE_PERMISSION_MODE = "default"

_BYPASS_FLAGS = frozenset(
    {"--dangerously-skip-permissions", "--allow-dangerously-skip-permissions"}
)


def allowed_claude_permission_mode(mode: str | None) -> str:
    """Return ``mode`` if the slim build allows it, else the Manual default."""
    if mode in ALLOWED_CLAUDE_PERMISSION_MODES:
        return mode
    if mode:
        _logger.warning("refusing Claude permission mode %r; using %r", mode, "default")
    return DEFAULT_CLAUDE_PERMISSION_MODE


def enforce_claude_permission_args(args: Iterable[str]) -> list[str]:
    """Return ``args`` with bypass flags removed and an allowed permission mode set."""
    result: list[str] = []
    seen_mode = False
    items = list(args)
    index = 0
    while index < len(items):
        arg = items[index]
        if arg in _BYPASS_FLAGS:
            _logger.warning("dropping %s from the Claude launch", arg)
            index += 1
            continue
        if arg == "--permission-mode":
            value = items[index + 1] if index + 1 < len(items) else None
            result.extend(("--permission-mode", allowed_claude_permission_mode(value)))
            seen_mode = True
            index += 2
            continue
        if arg.startswith("--permission-mode="):
            value = arg.split("=", 1)[1]
            result.append(f"--permission-mode={allowed_claude_permission_mode(value)}")
            seen_mode = True
            index += 1
            continue
        result.append(arg)
        index += 1
    if not seen_mode:
        # In front, so it never lands after a positional prompt or a ``--``.
        result[:0] = ["--permission-mode", DEFAULT_CLAUDE_PERMISSION_MODE]
    return result


#: The embedded-browser tools (``browser_navigate`` and friends) drive a browser
#: pane that only the Omnigent desktop app has. omnigent-slim ships without it,
#: and the tools could otherwise load internet pages, so they are not offered.
EMBEDDED_BROWSER_TOOLS_ENABLED = False
