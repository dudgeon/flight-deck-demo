"""omnigent-slim: the director's notes, readable and editable (``/v1/slim/director/notes``).

A director runs for days, across compactions and new sessions (D-128). What
it must not lose it writes to two files in the workspace, ``director/state.md``
(where the project stands, rewritten at checkpoints) and ``director/memory.md``
(lasting facts, one dated line each); ``pa recap`` reads them back after a
compaction. The project page shows them as "Director's notes", and the person
can edit either one: their edit wins, because the director re-reads the files.

A save names the version it was editing (the file's modification time). If
the director rewrote the file in the meantime, the save is refused with 409 and
the current text, so nobody's words are lost silently.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from omnigent.server.auth import AuthProvider
from omnigent.server.routes._auth_helpers import require_user
from omnigent.stores.project_store import ProjectStore

WORKSPACE_ENV = "OMNIGENT_SLIM_WORKSPACE"
PROJECT_ENV = "OMNIGENT_SLIM_PROJECT"
DIRECTOR_FOLDER = "director"
NOTE_FILES = {"state": "state.md", "memory": "memory.md"}
MAX_NOTE_BYTES = 64 * 1024


class NoteSave(BaseModel):
    project: str = ""
    note: Literal["state", "memory"]
    text: str = Field(max_length=MAX_NOTE_BYTES)
    # The `updated` the editor started from; None for a file that did not exist.
    base: float | None = None


def _stamp(path: Path) -> float | None:
    try:
        return path.stat().st_mtime
    except OSError:
        return None


def read_notes(workspace: Path | None) -> dict[str, Any]:
    """Both notes, each with its text and when it was last written (None when missing)."""
    out: dict[str, Any] = {}
    for key, name in NOTE_FILES.items():
        path = workspace / DIRECTOR_FOLDER / name if workspace is not None else None
        text, updated = "", None
        if path is not None and path.is_file():
            try:
                text = path.read_text(encoding="utf-8")[:MAX_NOTE_BYTES]
                updated = _stamp(path)
            except (OSError, UnicodeDecodeError):
                text, updated = "", None
        out[key] = {"file": f"{DIRECTOR_FOLDER}/{name}", "text": text, "updated": updated}
    out["exists"] = any(out[key]["updated"] is not None for key in NOTE_FILES)
    return out


def save_note(workspace: Path, note: str, text: str, base: float | None) -> dict[str, Any]:
    """Write one note atomically, unless it changed since ``base``."""
    path = workspace / DIRECTOR_FOLDER / NOTE_FILES[note]
    current = _stamp(path)
    if current is not None and (base is None or abs(current - base) > 1e-6):
        raise HTTPException(status_code=409, detail={"message": "The director changed this note while you were editing.", **read_notes(workspace)})
    path.parent.mkdir(parents=True, exist_ok=True)
    body = text.replace("\r\n", "\n")
    if body and not body.endswith("\n"):
        body += "\n"
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(body)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return read_notes(workspace)


def create_slim_director_router(
    *,
    project_store: ProjectStore | None = None,
    auth_provider: AuthProvider | None = None,
) -> APIRouter:
    """Build the router for ``GET`` and ``PUT /v1/slim/director/notes``."""
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

    def _name(project: str) -> str:
        return project.strip() or os.environ.get(PROJECT_ENV, "").strip() or "Workspace"

    @router.get("/slim/director/notes")
    async def get_notes(request: Request, project: str = "") -> dict[str, Any]:
        user_id = require_user(request, auth_provider)
        return await asyncio.to_thread(lambda: read_notes(_workspace_of(_name(project), user_id)))

    @router.put("/slim/director/notes")
    async def put_note(request: Request, body: NoteSave) -> dict[str, Any]:
        user_id = require_user(request, auth_provider)

        def _work() -> dict[str, Any]:
            workspace = _workspace_of(_name(body.project), user_id)
            if workspace is None:
                raise HTTPException(status_code=404, detail="This project has no workspace folder.")
            return save_note(workspace, body.note, body.text, body.base)

        return await asyncio.to_thread(_work)

    return router
