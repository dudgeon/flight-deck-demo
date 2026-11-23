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
#: Model for sessions in a flown demo (D-175): demos are scripted, so the faster
#: Sonnet tells the story; "" leaves the default above.
DEMO_CLAUDE_MODEL = _env_default("OMNIGENT_SLIM_DEMO_MODEL", "claude-sonnet-5-5")


def is_demo_workspace(workspace: str | None) -> bool:
    """Whether ``workspace`` is a flown demo's folder (``<workspace>/demos/<id>``)."""
    if not workspace:
        return False
    from pathlib import PurePath

    parts = PurePath(workspace).parts
    return len(parts) >= 2 and parts[-2] == "demos"


def slim_new_session_model(workspace: str | None) -> str | None:
    """The model a new Claude Code session starts on when it names none.

    ``None`` means the slim default (``DEFAULT_CLAUDE_MODEL``) applies at launch.
    """
    if is_demo_workspace(workspace) and DEMO_CLAUDE_MODEL:
        return DEMO_CLAUDE_MODEL
    return None

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


# --- Claude Code through its structured messages (D-172, D-173) -------------
#
# Every Flight Deck session runs the ``claude-code`` agent
# (``omnigent/slim_agents/claude-code``) on the claude-sdk harness: the
# person's installed ``claude`` driven over stream-json instead of in a
# terminal, because company managed settings can refuse plugins, hooks and
# extra tool servers. These rules keep it Claude Code: its own tools, its own
# permission checks, no plugin flags.

#: Claude Code's own tools, offered in place of upstream's ``sys_os_*``
#: stand-ins, so Claude Code's permission checks (Auto's classifier, Manual's
#: questions) decide every file change and command. No web tools: Flight Deck
#: runs offline.
CLAUDE_CODE_TOOLS: tuple[str, ...] = (
    "Bash",
    "Read",
    "Edit",
    "Write",
    "Glob",
    "Grep",
    "NotebookEdit",
    "TodoWrite",
    "Task",
)


def slim_sdk_tools(base_tools: list[str]) -> list[str]:
    """Return ``base_tools`` with Claude Code's own tools added, once each."""
    return list(dict.fromkeys([*base_tools, *CLAUDE_CODE_TOOLS]))


def slim_sdk_permission_mode(mode: str | None) -> str:
    """The permission mode a structured-message session runs in: allowed, Auto if unset."""
    return allowed_claude_permission_mode(mode)


def slim_sdk_model(model: str | None) -> str | None:
    """The model a session names, else the slim default (``None``: Claude's own)."""
    return model or DEFAULT_CLAUDE_MODEL or None


def slim_sdk_effort(effort: str | None) -> str | None:
    """The effort a session names, else the slim default (``None``: Claude's own)."""
    return effort or DEFAULT_CLAUDE_EFFORT or None


#: The one Omnigent tool sessions may use without asking: opening a file in the viewer.
SDK_PREAPPROVED_TOOLS = ("mcp__omnigent__ui_open_file",)


def slim_sdk_preapproved(allowed_tools: Iterable[str]) -> list[str]:
    """Keep only the tools the slim build pre-approves; the rest go through Claude's checks."""
    return [t for t in allowed_tools if t in SDK_PREAPPROVED_TOOLS]


#: Upstream opens an Omnigent REPL terminal beside every non-native session, which
#: shows as a "Terminal" tab next to the chat. Sessions here are Claude Code in the
#: chat, so that tab would only confuse (D-174); the runner and the session create
#: path both check this.
SLIM_REPL_TERMINAL = False
