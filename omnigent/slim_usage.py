"""omnigent-slim: the server's side of the usage log (D-122 to D-127).

The log itself (format, privacy rules, files) is one standard-library module
shared with the ``pa`` command: ``skills/view-kit/scripts/usagelog.py``. This
module loads it and adds what only the server sees:

* ``tee_upstream``: every upstream telemetry event (session created, stopped,
  deleted, turn end, token usage, policies), called from
  ``omnigent.telemetry.emit`` before upstream's own opt-out check, so the
  events upstream would send are kept here instead, under ``upstream.*``.
* ``observe_tool``: each tool an agent used, and which skill it loaded,
  called by the runner for every ``PostToolUse`` hook payload. Only the tool
  and skill names are kept, never their input or output.
* ``log``: slim routes' own events (``hangar.publish`` and so on).
* ``route_event``: one line per change made through a slim route.
* ``web_event_to_line``: maps the web app's analytics events for the router in
  ``omnigent/server/routes/slim_usage.py``.

Nothing here may raise into the caller: a broken log never breaks the work.
"""

from __future__ import annotations

import importlib.util
import logging
import re
from dataclasses import asdict, is_dataclass
from functools import lru_cache
from types import ModuleType
from typing import Any

_logger = logging.getLogger(__name__)

_SESSION_PATH_RE = re.compile(r"/c/([A-Za-z0-9_-]{6,80})")
_UPSTREAM_DROP = {"installation_id", "anon_user_id", "host_installation_id", "session_id"}


@lru_cache(maxsize=1)
def _module() -> ModuleType | None:
    from omnigent.slim_skills import DEFAULT_SKILLS_DIR, slim_skills_dir

    for root in (slim_skills_dir(), DEFAULT_SKILLS_DIR):
        path = root / "view-kit" / "scripts" / "usagelog.py"
        if not path.is_file():
            continue
        try:
            spec = importlib.util.spec_from_file_location("omnigent_slim_usagelog", path)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        except Exception:
            _logger.debug("Could not load the usage log from %s", path, exc_info=True)
    return None


def usagelog() -> ModuleType | None:
    """The shared usage-log module, or None when it cannot be found."""
    return _module()


def log(
    event_name: str,
    *,
    source: str = "server",
    params: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
    session_id: str | None = None,
) -> None:
    module = _module()
    if module is None:
        return
    try:
        module.log(event_name, source=source, params=params, context=context, session_id=session_id)
    except Exception:
        _logger.debug("usage log write failed", exc_info=True)


def _snake(name: str) -> str:
    if name.endswith("Event"):
        name = name[: -len("Event")]
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def tee_upstream(event: object) -> None:
    """Keep one upstream telemetry event as ``upstream.<snake_name>``."""
    try:
        if not is_dataclass(event) or isinstance(event, type):
            return
        fields = asdict(event)
        session_id = fields.get("session_id")
        params = {k: v for k, v in fields.items() if k not in _UPSTREAM_DROP}
        params["upstream_event"] = type(event).__name__
        log(
            f"upstream.{_snake(type(event).__name__)}",
            params=params,
            session_id=session_id if isinstance(session_id, str) else None,
        )
    except Exception:
        _logger.debug("usage tee failed", exc_info=True)


def observe_tool(payload: Any, session_id: str | None) -> None:
    """One ``tool.used`` line per tool call: the tool's name, and the skill's."""
    try:
        if not isinstance(payload, dict):
            return
        tool = payload.get("tool_name")
        if not isinstance(tool, str) or not tool:
            return
        params: dict[str, Any] = {"tool": tool}
        tool_input = payload.get("tool_input")
        if tool == "Skill" and isinstance(tool_input, dict):
            skill = tool_input.get("skill") or tool_input.get("command")
            if isinstance(skill, str):
                params["skill"] = skill.split(":")[-1].strip().lstrip("/")
        elif tool == "Task" and isinstance(tool_input, dict):
            agent = tool_input.get("subagent_type")
            if isinstance(agent, str):
                params["agent"] = agent
        response = payload.get("tool_response")
        if isinstance(response, dict) and isinstance(response.get("is_error"), bool):
            params["error"] = response["is_error"]
        log("tool.used", source="tool", params=params, session_id=session_id)
    except Exception:
        _logger.debug("usage tool observe failed", exc_info=True)


def web_event_to_line(event: Any) -> tuple[str, dict[str, Any], str | None] | None:
    """Map one upstream web analytics event to (event name, params, session).

    Upstream's analytics events carry stable ids only (``lib/host.ts``): a
    page id, a component id, a value the call site declared PII-free, an
    interaction kind. ``path`` is the page's path, which names a session.
    """
    if not isinstance(event, dict):
        return None
    kind = event.get("type")
    path = event.get("path") if isinstance(event.get("path"), str) else None
    session = None
    if path:
        match = _SESSION_PATH_RE.search(path)
        session = match.group(1) if match else None
    params: dict[str, Any]
    if kind == "page_view":
        params = {"page": event.get("pageId"), "path": path}
        name = "web.page_view"
    elif kind == "click":
        params = {"component": event.get("componentId"), "component_kind": event.get("componentKind")}
        name = "web.click"
    elif kind == "value_change":
        params = {
            "component": event.get("componentId"),
            "component_kind": event.get("componentKind"),
            "value": event.get("value"),
        }
        name = "web.value_change"
    elif kind == "interaction_phase":
        params = {
            "interaction": event.get("interactionKind"),
            "phase": event.get("phase"),
            "status": event.get("status"),
            "name": event.get("name"),
            "duration_ms": event.get("durationMs"),
        }
        name = "web.interaction"
    elif kind == "slim" and isinstance(event.get("event"), str) and event["event"].startswith("web."):
        raw = event.get("params")
        params = dict(raw) if isinstance(raw, dict) else {}
        name = event["event"]
    else:
        return None
    if path and "path" not in params:
        params["path"] = path
    if isinstance(event.get("theme"), str):
        params["theme"] = event["theme"]
    return name, params, session


_HANGAR_ROUTES: list[tuple[str, re.Pattern[str], str]] = [
    ("POST", re.compile(r"^/v1/slim/hangar/repo/send$"), "hangar.send_to_repo"),
    ("POST", re.compile(r"^/v1/slim/hangar/drafts/(?P<kind>[\w-]+)/(?P<id>[\w.-]+)/publish$"), "hangar.publish"),
    ("POST", re.compile(r"^/v1/slim/hangar/history/(?P<kind>[\w-]+)/(?P<id>[\w.-]+)/[\w.-]+/restore$"), "hangar.restore"),
    ("PUT", re.compile(r"^/v1/slim/hangar/drafts/(?P<kind>person)/(?P<id>[\w.-]+)/avatar$"), "hangar.avatar_set"),
    ("DELETE", re.compile(r"^/v1/slim/hangar/drafts/(?P<kind>person)/(?P<id>[\w.-]+)/avatar$"), "hangar.avatar_remove"),
    ("POST", re.compile(r"^/v1/slim/hangar/drafts/(?P<kind>[\w-]+)/(?P<id>[\w.-]+)$"), "hangar.draft_save"),
    ("POST", re.compile(r"^/v1/slim/hangar/drafts/(?P<kind>[\w-]+)$"), "hangar.draft_new"),
    ("DELETE", re.compile(r"^/v1/slim/hangar/drafts/(?P<kind>[\w-]+)/(?P<id>[\w.-]+)$"), "hangar.draft_discard"),
]
_SLIM_AREA_RE = re.compile(r"^/v1/slim/(?P<area>[\w-]+)")


def route_event(method: str, path: str, status: int, duration_ms: int) -> None:
    """One line for each change made through a slim route (D-125).

    Reads are not logged (the app polls them); each write is, by what it did:
    ``hangar.publish``, ``hangar.send_to_repo``, or ``api.slim_write`` for the
    other slim areas. Ids from the path are kept; bodies never are.
    """
    try:
        if method in ("GET", "HEAD", "OPTIONS") or not path.startswith("/v1/slim/"):
            return
        if path == "/v1/slim/usage/events":
            return
        params: dict[str, Any] = {"status": status, "duration_ms": duration_ms}
        for route_method, pattern, name in _HANGAR_ROUTES:
            match = pattern.match(path)
            if route_method == method and match:
                params.update(match.groupdict())
                log(name, params=params, context={"mode": "hangar"})
                return
        area = _SLIM_AREA_RE.match(path)
        params.update({"method": method.lower(), "area": area.group("area") if area else None})
        log("api.slim_write", params=params)
    except Exception:
        _logger.debug("usage route log failed", exc_info=True)
