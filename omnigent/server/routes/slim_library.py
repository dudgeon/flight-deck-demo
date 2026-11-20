"""omnigent-slim library: canned sessions and artifact templates (``/v1/slim/library``).

Both live as plain files in one folder, ``OMNIGENT_SLIM_LIBRARY_DIR``
(``workspace/templates`` when started with ``./start.sh``):

- ``sessions/*.md`` -- a canned session. YAML front matter gives ``title``,
  ``description`` and optional ``template`` (an artifact template id); the body
  is the prompt. ``{{name}}`` or ``{{name: hint}}`` in the body becomes an input
  field the user fills in before the prompt goes to the composer.
- ``artifacts/*.html`` -- an artifact template. Its ``<title>`` and
  ``<meta name="description">`` describe it in the library.

The files are read on every request, so edits show up on the next page load.
"""

from __future__ import annotations

import html
import logging
import os
import re
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Request

from omnigent.server.auth import AuthProvider
from omnigent.server.routes._auth_helpers import require_user

_logger = logging.getLogger(__name__)

LIBRARY_DIR_ENV = "OMNIGENT_SLIM_LIBRARY_DIR"
PROJECT_ENV = "OMNIGENT_SLIM_PROJECT"

_FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)
_FIELD = re.compile(r"\{\{\s*([A-Za-z][\w-]*)\s*(?::\s*([^}]*?))?\s*\}\}")
_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_DESCRIPTION = re.compile(
    r"<meta\s+[^>]*name=[\"']description[\"'][^>]*content=[\"']([^\"']*)[\"']",
    re.IGNORECASE,
)
_MAX_FILE_BYTES = 512 * 1024


def library_dir() -> Path | None:
    """The configured library folder, or ``None`` when unset or missing."""
    raw = os.environ.get(LIBRARY_DIR_ENV, "").strip()
    if not raw:
        return None
    path = Path(raw).expanduser()
    return path if path.is_dir() else None


def _read_text(path: Path) -> str | None:
    try:
        if path.stat().st_size > _MAX_FILE_BYTES:
            _logger.warning("skipping %s: larger than %d bytes", path, _MAX_FILE_BYTES)
            return None
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        _logger.warning("could not read library file %s", path, exc_info=True)
        return None


def parse_canned_session(item_id: str, text: str) -> dict[str, Any]:
    """Parse one ``sessions/*.md`` file into its library entry."""
    meta: dict[str, Any] = {}
    body = text
    match = _FRONT_MATTER.match(text)
    if match:
        try:
            loaded = yaml.safe_load(match.group(1)) or {}
            meta = loaded if isinstance(loaded, dict) else {}
        except yaml.YAMLError:
            _logger.warning("bad front matter in canned session %s", item_id)
        body = match.group(2)
    fields: list[dict[str, str]] = []
    seen: set[str] = set()
    for field in _FIELD.finditer(body):
        name = field.group(1)
        if name in seen:
            continue
        seen.add(name)
        fields.append({"name": name, "hint": (field.group(2) or "").strip()})
    return {
        "id": item_id,
        "title": str(meta.get("title") or item_id.replace("-", " ").capitalize()),
        "description": str(meta.get("description") or ""),
        "template": str(meta["template"]) if meta.get("template") else None,
        "prompt": body.strip(),
        "fields": fields,
    }


def parse_artifact_template(item_id: str, text: str) -> dict[str, Any]:
    """Describe one ``artifacts/*.html`` template from its title and meta description."""
    title = _TITLE.search(text)
    description = _DESCRIPTION.search(text)
    return {
        "id": item_id,
        "title": html.unescape(title.group(1).strip()) if title else item_id,
        "description": html.unescape(description.group(1).strip()) if description else "",
        "path": f"templates/artifacts/{item_id}.html",
    }


def load_library(root: Path | None) -> dict[str, Any]:
    """Read every canned session and artifact template under ``root``."""
    sessions: list[dict[str, Any]] = []
    templates: list[dict[str, Any]] = []
    if root is not None:
        for path in sorted((root / "sessions").glob("*.md")):
            text = _read_text(path)
            if text is not None:
                sessions.append(parse_canned_session(path.stem, text))
        for path in sorted((root / "artifacts").glob("*.html")):
            text = _read_text(path)
            if text is not None:
                templates.append(parse_artifact_template(path.stem, text))
    return {
        "library_dir": str(root) if root is not None else None,
        "project": os.environ.get(PROJECT_ENV, "").strip() or None,
        "sessions": sessions,
        "templates": templates,
    }


def create_slim_library_router(*, auth_provider: AuthProvider | None = None) -> APIRouter:
    """Build the router for ``GET /v1/slim/library``."""
    router = APIRouter()

    @router.get("/slim/library")
    async def get_library(request: Request) -> dict[str, Any]:
        require_user(request, auth_provider)
        return load_library(library_dir())

    return router
