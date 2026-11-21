"""omnigent-slim's launch rules for the Claude Code terminal.

The slim build must never launch Claude Code in a mode that skips safety
checks entirely. Every launch path (web UI, ``omnigent claude``,
automations) passes its final ``claude`` args through
:func:`enforce_claude_permission_args`, which:

- removes ``--dangerously-skip-permissions`` and
  ``--allow-dangerously-skip-permissions``;
- replaces any ``--permission-mode`` outside :data:`ALLOWED_CLAUDE_PERMISSION_MODES`
  (``bypassPermissions``, ``dontAsk``) with Manual (``default``);
- adds ``--permission-mode auto`` when no mode is given, so a user-level
  ``defaultMode`` such as ``bypassPermissions`` never applies;
- adds ``--model`` and ``--effort`` defaults when the launch names none.

The defaults can be changed without code via ``OMNIGENT_SLIM_CLAUDE_MODEL``,
``OMNIGENT_SLIM_CLAUDE_EFFORT`` and ``OMNIGENT_SLIM_CLAUDE_PERMISSION_MODE``
(an empty model or effort leaves Claude Code's own default).
"""

from __future__ import annotations

import logging
import os
from collections.abc import Iterable

_logger = logging.getLogger("omnigent.slim_policy")

#: Modes Claude Code may launch in. ``default`` is the one Claude Code labels
#: "Manual"; ``auto`` runs tools but a classifier blocks risky actions.
ALLOWED_CLAUDE_PERMISSION_MODES: tuple[str, ...] = ("default", "auto", "acceptEdits", "plan")
#: Where a refused mode (bypass, don't ask) lands: the one that always asks.
REFUSED_CLAUDE_PERMISSION_MODE_FALLBACK = "default"


def _env_default(name: str, fallback: str) -> str:
    value = os.environ.get(name)
    return fallback if value is None else value.strip()


#: Mode for launches that name none.
DEFAULT_CLAUDE_PERMISSION_MODE = _env_default("OMNIGENT_SLIM_CLAUDE_PERMISSION_MODE", "auto")
if DEFAULT_CLAUDE_PERMISSION_MODE not in ALLOWED_CLAUDE_PERMISSION_MODES:
    DEFAULT_CLAUDE_PERMISSION_MODE = "auto"
#: Model and effort for launches that name none ("" leaves Claude's default).
DEFAULT_CLAUDE_MODEL = _env_default("OMNIGENT_SLIM_CLAUDE_MODEL", "claude-opus-5-5")
DEFAULT_CLAUDE_EFFORT = _env_default("OMNIGENT_SLIM_CLAUDE_EFFORT", "medium")

_BYPASS_FLAGS = frozenset(
    {"--dangerously-skip-permissions", "--allow-dangerously-skip-permissions"}
)


def allowed_claude_permission_mode(mode: str | None) -> str:
    """Return ``mode`` if the slim build allows it; Manual if refused, Auto if unset."""
    if mode in ALLOWED_CLAUDE_PERMISSION_MODES:
        return mode
    if mode:
        _logger.warning(
            "refusing Claude permission mode %r; using %r",
            mode,
            REFUSED_CLAUDE_PERMISSION_MODE_FALLBACK,
        )
        return REFUSED_CLAUDE_PERMISSION_MODE_FALLBACK
    return DEFAULT_CLAUDE_PERMISSION_MODE


def enforce_claude_permission_args(args: Iterable[str]) -> list[str]:
    """Return ``args`` with bypass flags removed, an allowed mode, and model/effort defaults."""
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
    # Defaults go in front, so they never land after a positional prompt or ``--``.
    defaults: list[str] = []
    if not seen_mode:
        defaults += ["--permission-mode", DEFAULT_CLAUDE_PERMISSION_MODE]
    if DEFAULT_CLAUDE_MODEL and not _has_flag(result, "--model"):
        defaults += ["--model", DEFAULT_CLAUDE_MODEL]
    if DEFAULT_CLAUDE_EFFORT and not _has_flag(result, "--effort"):
        defaults += ["--effort", DEFAULT_CLAUDE_EFFORT]
    result[:0] = defaults
    return result


def _has_flag(args: list[str], flag: str) -> bool:
    return any(arg == flag or arg.startswith(flag + "=") for arg in args)


#: The embedded-browser tools (``browser_navigate`` and friends) drive a browser
#: pane that only the Omnigent desktop app has. omnigent-slim ships without it,
#: and the tools could otherwise load internet pages, so they are not offered.
EMBEDDED_BROWSER_TOOLS_ENABLED = False
