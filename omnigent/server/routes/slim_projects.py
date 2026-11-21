"""omnigent-slim: what a project is and what it touches (``GET /v1/slim/projects/connections``).

A project is one in-market goal inside an area (D-97). Its meaning lives in a
small file of our own, ``projects/<slug>.json`` in the workspace, written by
``pa project``; nothing is added to upstream's project table. That file may
describe a project that is not in this app at all, such as another team's.

A project's connections are typed links that hang from specific records
(D-119). ``pa link`` stores each one once, as a line on the record it hangs
from, and a dataset names the project it belongs to. This route reads those
lines and groups them for one project, reading each link the other way from
its far end: a requirement *handed to* project B is where B *came from*.

Read-only, and assembled on every request from the files: there is no graph
store (D-98).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request

from omnigent.server.auth import AuthProvider
from omnigent.server.routes._auth_helpers import require_user
from omnigent.stores.project_store import ProjectStore

_logger = logging.getLogger(__name__)

WORKSPACE_ENV = "OMNIGENT_SLIM_WORKSPACE"
PROJECT_ENV = "OMNIGENT_SLIM_PROJECT"
PROJECTS_FOLDER = "projects"
DATA_FOLDER = "data"
LINK_TYPES = ("handed-to", "started", "relies-on")
PROJECT_STATES = ("shaping", "in-delivery", "shipped", "slipped", "paused", "stopped")
_CARD_KEYS = ("goal", "area", "team", "state_note")
_MAX_FILES = 200
_MAX_FILE_BYTES = 2 * 1024 * 1024


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _read(path: Path) -> Any:
    try:
        if path.stat().st_size > _MAX_FILE_BYTES:
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        _logger.warning("could not read %s", path, exc_info=True)
        return None


def load_project_cards(workspace: Path) -> dict[str, dict[str, Any]]:
    """Every project with a file in ``workspace/projects``, by name."""
    cards: dict[str, dict[str, Any]] = {}
    folder = workspace / PROJECTS_FOLDER
    for path in sorted(folder.glob("*.json"))[:_MAX_FILES] if folder.is_dir() else []:
        raw = _read(path)
        name = _text(raw.get("name")) if isinstance(raw, dict) else ""
        if not name:
            continue
        state = _text(raw.get("state"))
        cards[name] = {
            "name": name,
            **{key: _text(raw.get(key)) for key in _CARD_KEYS},
            "state": state if state in PROJECT_STATES else "",
        }
    return cards


def connections_for(workspace: Path | None, name: str) -> dict[str, Any]:
    """One project's file and its links, grouped by what each link means."""
    empty: dict[str, Any] = {
        "project": None, "lives_in": None,
        "came_from": [], "handed_to": [], "relies_on": [], "relied_on_by": [],
    }
    if workspace is None or not name:
        return empty
    cards = load_project_cards(workspace)

    def card(project: str) -> dict[str, Any] | None:
        # A link may name a project nobody has described yet.
        return cards.get(project) or ({"name": project} if project else None)

    out = dict(empty, project=cards.get(name), lives_in=(cards.get(name) or {}).get("area") or None)
    folder = workspace / DATA_FOLDER
    for path in sorted(folder.glob("*.json"))[:_MAX_FILES] if folder.is_dir() else []:
        raw = _read(path)
        if not isinstance(raw, dict) or not isinstance(raw.get("records"), list):
            continue
        owner = _text(raw.get("project"))
        for record in raw["records"]:
            if not isinstance(record, dict) or not isinstance(record.get("links"), list):
                continue
            item = {
                "id": _text(record.get("id")),
                "title": _text(record.get("title")) or _text(record.get("name")),
                "data": f"{DATA_FOLDER}/{path.name}",
            }
            for link in record["links"]:
                if not isinstance(link, dict):
                    continue
                kind, other = _text(link.get("type")), _text(link.get("project"))
                if kind not in LINK_TYPES or not other:
                    continue
                if owner == name and other != name:
                    group = "relies_on" if kind == "relies-on" else "handed_to"
                    out[group].append({"item": item, "project": card(other), "type": kind})
                elif other == name:
                    # The same line, read from the far end.
                    group = "relied_on_by" if kind == "relies-on" else "came_from"
                    out[group].append({"item": item, "project": card(owner), "type": kind})
    return out


def create_slim_projects_router(
    *,
    project_store: ProjectStore | None = None,
    auth_provider: AuthProvider | None = None,
) -> APIRouter:
    """Build the router for ``GET /v1/slim/projects/connections?project=<name>``."""
    router = APIRouter()

    def _workspace_of(project_name: str, user_id: str | None) -> Path | None:
        project = None
        if project_store is not None:
            project = next((p for p in project_store.list(user_id=user_id) if p.name == project_name), None)
        raw = (project.config or {}).get("workspace") if project is not None else None
        if not isinstance(raw, str) or not raw.strip():
            raw = os.environ.get(WORKSPACE_ENV, "")
        path = Path(raw).expanduser() if raw.strip() else None
        return path if path is not None and path.is_dir() else None

    @router.get("/slim/projects/connections")
    async def get_connections(request: Request, project: str = "") -> dict[str, Any]:
        user_id = require_user(request, auth_provider)
        name = project.strip() or os.environ.get(PROJECT_ENV, "").strip() or "Workspace"

        def _work() -> dict[str, Any]:
            return connections_for(_workspace_of(name, user_id), name)

        return await asyncio.to_thread(_work)

    return router
