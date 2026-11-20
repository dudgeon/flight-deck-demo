"""Keep omnigent's own processes off the network beyond this machine.

The slim build runs where the open internet is off-limits. Every omnigent
process (server, host daemon, runner, hooks, MCP bridge) imports the
``omnigent`` package, which installs this guard first. It refuses DNS lookups
and socket connections to anything but loopback and Unix sockets, so a stray
telemetry ping, update check or CDN fetch fails fast instead of leaving the
machine. The ``claude`` CLI is a separate program and is not affected: it
reaches Anthropic exactly as it does when run by hand.

Set ``OMNIGENT_ALLOW_NETWORK=1`` to turn the guard off (for example on a
build machine).
"""

from __future__ import annotations

import importlib.abc
import ipaddress
import logging
import os
import socket
import sys

ALLOW_NETWORK_ENV_VAR = "OMNIGENT_ALLOW_NETWORK"

_logger = logging.getLogger("omnigent.offline_guard")
_LOCAL_NAMES = frozenset({"localhost", "localhost.localdomain", "ip6-localhost", "ip6-loopback"})
_installed = False

# Defaults that switch off features which would call out on their own.
# Each stays overridable from the environment.
OFFLINE_ENV_DEFAULTS = {
    "OMNIGENT_DISABLE_TELEMETRY": "1",
    "DO_NOT_TRACK": "1",
    "OMNIGENT_NO_UPDATE_CHECK": "1",
    "OMNIGENT_DISABLE_CATALOG_LOOKUP": "1",
    "OMNIGENT_HARNESS_INSTALL_ENABLED": "0",
    # Not network, but part of the slim profile: offer only the Claude Code
    # terminal agent (others need vendor CLIs or API keys).
    "OMNIGENT_SEEDED_AGENTS": "claude-native-ui",
}


class OfflineGuardError(ConnectionRefusedError):
    """Raised instead of opening a connection that would leave this machine."""


class _BlockUvloop(importlib.abc.MetaPathFinder):
    """Make ``import uvloop`` fail, as if it were not installed."""

    def find_spec(self, fullname, path=None, target=None):  # type: ignore[no-untyped-def]
        if fullname == "uvloop" or fullname.startswith("uvloop."):
            raise ModuleNotFoundError(f"No module named {fullname!r} (offline guard)", name=fullname)
        return None


def network_allowed() -> bool:
    """Whether the user explicitly allowed off-machine connections."""
    return os.environ.get(ALLOW_NETWORK_ENV_VAR, "").strip().lower() in ("1", "true", "yes")


def is_local_host(host: object) -> bool:
    """Whether ``host`` names this machine: a loopback IP or a localhost name."""
    if host is None:
        return True  # getaddrinfo(None, ...) means the local wildcard/loopback
    if isinstance(host, bytes):
        host = host.decode("idna", errors="replace")
    if not isinstance(host, str):
        return False
    name = host.strip().strip("[]").lower().rstrip(".")
    if name in _LOCAL_NAMES or name.endswith(".localhost"):
        return True
    try:
        address = ipaddress.ip_address(name.split("%", 1)[0])
    except ValueError:
        return False
    return address.is_loopback or address.is_unspecified


def _check_address(family: int, address: object) -> None:
    if family == getattr(socket, "AF_UNIX", None):
        return
    host = address[0] if isinstance(address, tuple) and address else address
    if not is_local_host(host):
        _logger.warning("offline guard blocked a connection to %s", host)
        raise OfflineGuardError(
            f"omnigent-slim offline guard: refused a connection to {host!r}. "
            f"Only this machine is reachable; set {ALLOW_NETWORK_ENV_VAR}=1 to allow it."
        )


def install() -> None:
    """Apply offline env defaults and patch socket connect/DNS once per process."""
    global _installed
    if _installed:
        return
    _installed = True
    for name, value in OFFLINE_ENV_DEFAULTS.items():
        os.environ.setdefault(name, value)
    if network_allowed():
        return

    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex
    original_getaddrinfo = socket.getaddrinfo

    def guarded_connect(self: socket.socket, address: object) -> None:
        _check_address(self.family, address)
        return original_connect(self, address)

    def guarded_connect_ex(self: socket.socket, address: object) -> int:
        _check_address(self.family, address)
        return original_connect_ex(self, address)

    def guarded_getaddrinfo(host: object, *args: object, **kwargs: object):  # type: ignore[no-untyped-def]
        if not is_local_host(host):
            _logger.warning("offline guard blocked a DNS lookup of %s", host)
            raise socket.gaierror(
                socket.EAI_NONAME,
                f"omnigent-slim offline guard: {host!r} is not on this machine",
            )
        return original_getaddrinfo(host, *args, **kwargs)

    # uvloop resolves and connects in C, around the patches below; refuse to
    # load it so uvicorn and asyncio fall back to the patched stdlib loop.
    sys.meta_path.insert(0, _BlockUvloop())
    sys.modules.pop("uvloop", None)

    socket.socket.connect = guarded_connect  # type: ignore[method-assign]
    socket.socket.connect_ex = guarded_connect_ex  # type: ignore[method-assign]
    socket.getaddrinfo = guarded_getaddrinfo  # type: ignore[assignment]
