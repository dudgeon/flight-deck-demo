"""omnigent-slim: the runs in flight in a project (``GET /v1/slim/runs``, D-96).

A *run* is one workflow working on one subject. ``pa flow`` (the view kit's
command) keeps a small JSON file per run in the workspace's ``progress/``
folder: the steps, the current step, the state (working, needs-you, waiting,
paused, finished, stopped), the note left at a pause and the session it runs
in. A run outlives its session, so the project page reads them here instead of
from any one session.

Read-only, and read on every request: the files are the record, there is no
table. A project is matched to its folder by its ``config.workspace``. The
Workspace and Hangar projects share one folder, so a run that names a session
is listed only in that session's project, and a run that names none is listed
in the default project (``OMNIGENT_SLIM_PROJECT``).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request

from omnigent.server.auth import AuthProvider
from omnigent.server.routes._auth_helpers import require_user
from omnigent.stores.conversation_store import ConversationStore
from omnigent.stores.project_store import ProjectStore

_logger = logging.getLogger(__name__)

WORKSPACE_ENV = "OMNIGENT_SLIM_WORKSPACE"
PROJECT_ENV = "OMNIGENT_SLIM_PROJECT"
PROGRESS_FOLDER = "progress"
RUN_STATES = ("working", "needs-you", "waiting", "paused", "finished", "stopped")
# Needs the person first, then what they set aside, then what is moving.
_ORDER = {state: i for i, state in enumerate(("needs-you", "paused", "waiting", "working", "stopped", "finished"))}
_MAX_FILES = 200
_MAX_FILE_BYTES = 256 * 1024
# A progress file's name: no separators, no dots at the start.
_RUN_ID = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,160}$")


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


REPORT_KINDS = ("milestone", "progress", "blocker", "done")
_MAX_REPORTS = 20


def _reports(raw: Any) -> list[dict[str, Any]]:
    """The one-line reports a run has sent its director, oldest first."""
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw[-_MAX_REPORTS:]:
        if not isinstance(item, dict) or not _text(item.get("text")):
            continue
        kind = _text(item.get("kind"))
        out.append({
            "at": _text(item.get("at")),
            "kind": kind if kind in REPORT_KINDS else "milestone",
            "text": _text(item.get("text"))[:280],
        })
    return out


def parse_run(run_id: str, raw: Any) -> dict[str, Any] | None:
    """One ``progress/*.json`` file as a run, or ``None`` if it is not one."""
    if not isinstance(raw, dict):
        return None
    steps = [s for s in raw.get("steps") or [] if isinstance(s, str)] if isinstance(raw.get("steps"), list) else []
    if not steps:
        return None
    current = raw.get("current")
    current = current if isinstance(current, int) and not isinstance(current, bool) and current >= 1 else 1
    finished = current > len(steps)
    state = _text(raw.get("state"))
    if state not in RUN_STATES:
        # Written before runs had a state.
        state = "finished" if finished else "working"
    counts = raw.get("counts") if isinstance(raw.get("counts"), dict) else None
    return {
        "id": run_id,
        "workflow": _text(raw.get("workflow")) or "Workflow",
        "scenario": _text(raw.get("scenario")),
        "subject": _text(raw.get("subject")),
        "steps": steps,
        "current": current,
        "state": state,
        "note": _text(raw.get("note")),
        "left_off": _text(raw.get("left_off")),
        "counts": counts,
        "data": _text(raw.get("data")),
        "session": _text(raw.get("session")) or None,
        "started": _text(raw.get("started")),
        "paused_at": _text(raw.get("paused_at")),
        "updated": _text(raw.get("updated")),
        # Threads (D-89, D-118): who directs the run and what it has reported.
        "director": _text(raw.get("director")) or None,
        "brief": _text(raw.get("brief")),
        "reports": _reports(raw.get("reports")),
    }


def load_runs(workspace: Path | None) -> list[dict[str, Any]]:
    """Every run recorded in ``workspace/progress``, the ones needing the person first."""
    if workspace is None:
        return []
    folder = workspace / PROGRESS_FOLDER
    if not folder.is_dir():
        return []
    runs: list[dict[str, Any]] = []
    for path in sorted(folder.glob("*.json"))[:_MAX_FILES]:
        try:
            if path.stat().st_size > _MAX_FILE_BYTES:
                continue
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            _logger.warning("could not read run file %s", path, exc_info=True)
            continue
        run = parse_run(path.stem, raw)
        if run is not None:
            runs.append(run)
    # Within a state, the most recently touched first.
    runs.sort(key=lambda r: r["updated"], reverse=True)
    runs.sort(key=lambda r: _ORDER[r["state"]])
    return runs


def _default_workspace() -> Path | None:
    raw = os.environ.get(WORKSPACE_ENV, "").strip()
    if not raw:
        return None
    path = Path(raw).expanduser()
    return path if path.is_dir() else None


def create_slim_runs_router(
    *,
    project_store: ProjectStore | None = None,
    conversation_store: ConversationStore | None = None,
    auth_provider: AuthProvider | None = None,
) -> APIRouter:
    """Build the router for ``GET /v1/slim/runs?project=<name>`` and ``GET /v1/slim/runs/{id}?session=``."""
    router = APIRouter()

    def _runs_for(project_name: str, user_id: str | None) -> dict[str, Any]:
        default_name = os.environ.get(PROJECT_ENV, "").strip() or "Workspace"
        is_default = project_name == default_name
        project = None
        if project_store is not None:
            project = next((p for p in project_store.list(user_id=user_id) if p.name == project_name), None)
        workspace: Path | None = None
        raw = (project.config or {}).get("workspace") if project is not None else None
        if isinstance(raw, str) and raw.strip():
            candidate = Path(raw).expanduser()
            workspace = candidate if candidate.is_dir() else None
        elif is_default:
            workspace = _default_workspace()

        def _project_of(conversation: Any) -> str | None:
            # A thread is a child session; it belongs to its director's project.
            for _ in range(4):
                if getattr(conversation, "project_id", None) or conversation_store is None:
                    break
                parent = getattr(conversation, "parent_conversation_id", None)
                parent_conversation = conversation_store.get_conversation(parent) if parent else None
                if parent_conversation is None:
                    break
                conversation = parent_conversation
            return getattr(conversation, "project_id", None)

        runs: list[dict[str, Any]] = []
        for run in load_runs(workspace):
            conversation = None
            if run["session"] and conversation_store is not None:
                conversation = conversation_store.get_conversation(run["session"])
            if conversation is None:
                # No session to go back to: Resume starts a new one. Shown once,
                # in the default project, when several projects share the folder.
                if not is_default:
                    continue
                run["session"] = None
                run["session_title"] = None
            else:
                if project is not None and _project_of(conversation) != project.id:
                    continue
                run["session_title"] = conversation.title
            runs.append(run)
        return {
            "project": project_name,
            "runs": runs,
            "needs_you": sum(1 for r in runs if r["state"] == "needs-you"),
        }

    @router.get("/slim/runs")
    async def get_runs(request: Request, project: str = "") -> dict[str, Any]:
        user_id = require_user(request, auth_provider)
        name = project.strip() or os.environ.get(PROJECT_ENV, "").strip() or "Workspace"
        return await asyncio.to_thread(_runs_for, name, user_id)

    def _run_for_session(run_id: str, session_id: str, user_id: str | None) -> dict[str, Any]:
        """One run, found through the session whose chat shows its card.

        Read from disk, so the card still fills in when that session has no
        runner bound (an old session opened to look back).
        """
        if not _RUN_ID.match(run_id) or conversation_store is None or project_store is None:
            return {"run": None}
        conversation = conversation_store.get_conversation(session_id)
        project_id = None
        for _ in range(4):
            if conversation is None:
                break
            project_id = getattr(conversation, "project_id", None)
            parent = getattr(conversation, "parent_conversation_id", None)
            if project_id or not parent:
                break
            conversation = conversation_store.get_conversation(parent)
        project = project_store.get(project_id, user_id=user_id) if project_id else None
        raw = (project.config or {}).get("workspace") if project is not None else None
        if not isinstance(raw, str) or not raw.strip():
            return {"run": None}
        path = Path(raw).expanduser() / PROGRESS_FOLDER / f"{run_id}.json"
        try:
            if path.stat().st_size > _MAX_FILE_BYTES:
                return {"run": None}
            run = parse_run(run_id, json.loads(path.read_text(encoding="utf-8")))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return {"run": None}
        if run is not None and run["session"] and conversation_store.get_conversation(run["session"]) is None:
            run["session"] = None
        return {"run": run}

    @router.get("/slim/runs/{run_id}")
    async def get_run(request: Request, run_id: str, session: str = "") -> dict[str, Any]:
        user_id = require_user(request, auth_provider)
        return await asyncio.to_thread(_run_for_session, run_id, session.strip(), user_id)

    return router
