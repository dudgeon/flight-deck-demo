"""omnigent-slim Hangar: what people can fly, and building people (``/v1/slim/hangar``).

The Hangar is Product Aviator's builder mode (docs/product/hangar.md, D-39 to
D-47). This first slice only looks: it lists the things other people fly and
how they refer to each other, all read from files that already exist:

- People and agents: ``<workspace>/participants/*.md`` (the roster).
- Workflows: each ``skills/<name>/`` folder with a ``scenario.json``.
- Views: every view spec a workflow lists, plus the standalone artifact
  templates in ``<library>/artifacts/*.html``.
- Scenarios: a workflow's scripted demo (``script.md`` and its fixtures). Until
  D-42 moves them into their own folders there is one per workflow.
- Skills: every ``skills/<name>/SKILL.md``.
- Starters: the Library's canned sessions, ``<library>/sessions/*.md``.
- Frameworks: ``<workspace>/frameworks/*.md``.

Checks and rendering come from the view kit's own ``pa`` command
(``skills/view-kit/scripts/pa.py``), imported, so the Hangar can never disagree
with ``pa check``. Every file is read on each request. The only writes are
drafts, publish and restore of people (slice 2), all done by ``pa`` under
``<workspace>/.hangar/`` and ``<workspace>/participants/``.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import logging
import os
import re
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from omnigent.server.auth import AuthProvider
from omnigent.server.routes._auth_helpers import require_user
from omnigent.server.routes.slim_library import (
    _read_text,
    library_dir,
    parse_artifact_template,
    parse_canned_session,
)
from omnigent.slim_skills import slim_skills_dir

_logger = logging.getLogger(__name__)

WORKSPACE_ENV = "OMNIGENT_SLIM_WORKSPACE"
#: Repo-root ``workspace/`` (the package is installed editable from the checkout).
DEFAULT_WORKSPACE = Path(__file__).resolve().parents[3] / "workspace"
_FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)
_SESSION_CAST = re.compile(r"participants for this session:\s*([^\n]+)", re.IGNORECASE)
_H1 = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_PLACEHOLDER = re.compile(r"\s*·?\s*\{[^}]*\}")
_DATASET_FIELD = re.compile(r"\{dataset\.(\w+)\}")


# ----------------------------------------------------------------- folders


def workspace_dir() -> Path:
    raw = os.environ.get(WORKSPACE_ENV, "").strip()
    return Path(raw).expanduser() if raw else DEFAULT_WORKSPACE


def _templates_dir() -> Path:
    return library_dir() or (workspace_dir() / "templates")


_PA: ModuleType | None = None
_PA_PATH: Path | None = None


def _pa() -> ModuleType:
    """The view kit's ``pa`` module, loaded from the skills folder (once per path)."""
    global _PA, _PA_PATH
    path = slim_skills_dir() / "view-kit" / "scripts" / "pa.py"
    if _PA is not None and path == _PA_PATH:
        return _PA
    if not path.is_file():
        raise HTTPException(status_code=503, detail=f"the view kit is missing ({path})")
    spec = importlib.util.spec_from_file_location("_slim_hangar_pa", path)
    if spec is None or spec.loader is None:
        raise HTTPException(status_code=503, detail="could not load the view kit")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    _PA, _PA_PATH = module, path
    return module


def _json(path: Path) -> Any:
    text = _read_text(path)
    if text is None:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _front_matter(text: str) -> tuple[dict[str, Any], str]:
    match = _FRONT_MATTER.match(text)
    if not match:
        return {}, text
    try:
        loaded = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        loaded = {}
    return (loaded if isinstance(loaded, dict) else {}), match.group(2)


# ------------------------------------------------------------------ people


def _roster(pa: ModuleType) -> dict[str, dict[str, Any]]:
    try:
        return pa._participants(workspace_dir() / "participants")
    except Exception:
        _logger.warning("could not read the roster", exc_info=True)
        return {}


def _person_entry(pa: ModuleType, person: dict[str, Any]) -> dict[str, Any]:
    pid = person["id"]
    skills = person.get("skills")
    if isinstance(skills, str):
        skills = [s.strip() for s in skills.split(",") if s.strip()]
    return {
        "id": pid,
        "name": str(person.get("name", pid)),
        "kind": person.get("kind", "agent"),
        "role": str(person.get("role", "")),
        "initials": str(person.get("initials", "")),
        "stand_in": bool(person.get("stand_in")),
        "backing": person.get("backing", "session"),
        "call_for": str(person.get("call_for", "")),
        # D-47: an optional `skills` line narrows what their session gets.
        "skills": skills if isinstance(skills, list) else None,
        "brief": person.get("brief", ""),
        "path": f"workspace/participants/{pid}.md",
        "problems": pa._check_participants({pid: person}),
        "used_in": {"workflows": [], "starters": []},
    }


# --------------------------------------------------------------- workflows


def _check_workflow(pa: ModuleType, folder: Path) -> list[str]:
    """Run ``pa check`` on one workflow folder and return its problems."""
    out = io.StringIO()
    args = argparse.Namespace(
        scenario=str(folder), participants=str(workspace_dir() / "participants")
    )
    try:
        with contextlib.redirect_stdout(out):
            pa.cmd_check(args)
    except SystemExit:
        return [
            line.strip()[2:]
            for line in out.getvalue().splitlines()
            if line.strip().startswith("- ")
        ]
    except Exception as err:  # noqa: BLE001 -- PaError and friends: one problem, in its own words
        return [str(err) or type(err).__name__]
    return []


def _script(
    pa: ModuleType, folder: Path, manifest: dict[str, Any], roster: dict[str, Any]
) -> dict[str, Any] | None:
    rel = manifest.get("script")
    if not rel or not (folder / rel).is_file():
        return None
    text = _read_text(folder / rel) or ""
    eligible = {pid: roster[pid] for pid in (manifest.get("participants") or []) if pid in roster}
    try:
        parsed = pa.parse_script(text, eligible, rel)
        steps = parsed.get("steps", [])
        error = None
    except Exception as err:  # noqa: BLE001 -- a script error is shown, not raised
        steps, error = [], str(err)
    title = _H1.search(text)
    hosts: dict[str, str] = {}
    for step in steps:
        if step.get("canvas"):
            hosts.setdefault(step["canvas"], "canvas")
        if step.get("widget"):
            hosts.setdefault(step["widget"], "chat")
    return {
        "path": rel,
        "title": title.group(1).strip() if title else manifest.get("title", folder.name),
        "text": text,
        "steps": len(steps),
        "error": error,
        "hosts": hosts,
    }


def _record_types(folder: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    rel = manifest.get("schemas")
    schemas = _json(folder / rel) if rel else None
    if not isinstance(schemas, dict):
        return []
    types = []
    for name, schema in schemas.items():
        if not isinstance(schema, dict):
            continue
        fields = schema.get("fields") or {}
        types.append(
            {
                "name": name,
                "required": [f for f in schema.get("required", []) if f not in ("id", "type")],
                "fields": [
                    {"name": key, "enum": rule.get("enum"), "note": rule.get("note", "")}
                    for key, rule in fields.items()
                    if isinstance(rule, dict)
                ],
            }
        )
    return types


def _workflow(pa: ModuleType, folder: Path, roster: dict[str, Any]) -> dict[str, Any] | None:
    manifest = _json(folder / "scenario.json")
    if not isinstance(manifest, dict):
        return None
    wid = folder.name
    script = _script(pa, folder, manifest, roster)
    fixture = (manifest.get("fixtures") or {}).get("dataset")
    sample = _json(folder / fixture) if fixture else None
    sample = sample if isinstance(sample, dict) else {}
    hosts = script["hosts"] if script else {}
    views = []
    for name, rel in (manifest.get("views") or {}).items():
        spec = _json(folder / rel)
        spec = spec if isinstance(spec, dict) else {}
        views.append(
            {
                "key": f"{wid}/{name}",
                "name": name,
                "workflow": wid,
                "title": _PLACEHOLDER.sub(
                    "", str(spec.get("eyebrow") or spec.get("view") or name)
                ).strip(" ·")
                or name,
                "heading": _DATASET_FIELD.sub(
                    lambda m: str(sample.get(m.group(1), "")), str(spec.get("title", ""))
                ),
                "layout": spec.get("layout", ""),
                "host": hosts.get(name)
                or ("chat" if spec.get("layout") in ("form", "detail") else "canvas"),
                "actions": len(spec.get("actions", [])) + (1 if spec.get("submit") else 0),
                "path": f"skills/{wid}/{rel}",
            }
        )
    skill_meta, _ = _front_matter(_read_text(folder / "SKILL.md") or "")
    return {
        "id": wid,
        "title": str(manifest.get("title") or wid),
        "summary": str(manifest.get("summary") or ""),
        "description": str(skill_meta.get("description") or ""),
        "steps": [s for s in manifest.get("steps") or [] if isinstance(s, str)],
        "progress": manifest.get("progress"),
        "inputs": manifest.get("inputs") or [],
        "launchers": manifest.get("launchers") or [],
        "work_products": manifest.get("work_products") or [],
        "participants": [p for p in manifest.get("participants") or [] if isinstance(p, str)],
        "records": _record_types(folder, manifest),
        "views": views,
        "script": script,
        "fixtures": manifest.get("fixtures") or {},
        "builtin": True,
        "path": f"skills/{wid}/",
        "problems": _check_workflow(pa, folder),
        "starters": [],
    }


# ------------------------------------------------------------------ others


def _skills(root: Path) -> list[dict[str, Any]]:
    skills = []
    if not root.is_dir():
        return skills
    for folder in sorted(p for p in root.iterdir() if p.is_dir() and (p / "SKILL.md").is_file()):
        text = _read_text(folder / "SKILL.md") or ""
        meta, body = _front_matter(text)
        skills.append(
            {
                "id": folder.name,
                "name": str(meta.get("name") or folder.name),
                "description": str(meta.get("description") or ""),
                "workflow": (folder / "scenario.json").is_file(),
                "files": sorted(
                    p.relative_to(folder).as_posix()
                    for p in folder.rglob("*")
                    if p.is_file() and p.name != ".DS_Store"
                )[:60],
                "text": body,
                "path": f"skills/{folder.name}/SKILL.md",
                "used_by": [],
            }
        )
    return skills


def _frameworks(folder: Path) -> list[dict[str, Any]]:
    out = []
    if not folder.is_dir():
        return out
    for path in sorted(folder.glob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        text = _read_text(path) or ""
        title = _H1.search(text)
        out.append(
            {
                "id": path.stem,
                "title": title.group(1).strip() if title else path.stem,
                "text": text,
                "path": f"workspace/frameworks/{path.name}",
                "used_by": [],
            }
        )
    return out


def _mentions(text: str, word: str) -> bool:
    return re.search(rf"(?<![\w-]){re.escape(word)}(?![\w-])", text) is not None


def load_hangar() -> dict[str, Any]:
    """Read everything the Hangar shows and link what uses what."""
    pa = _pa()
    roster = _roster(pa)
    people = [_person_entry(pa, person) for person in roster.values()]
    for person in people:
        live = workspace_dir() / "participants" / f"{person['id']}.md"
        person["text"] = _read_text(live) or ""
        person["history"] = [
            {k: v for k, v in version.items() if k != "text"}
            for version in pa.person_history(workspace_dir(), person["id"])
        ]
    by_person = {p["id"]: p for p in people}
    skills_root = slim_skills_dir()
    workflows = []
    if skills_root.is_dir():
        for folder in sorted(skills_root.iterdir()):
            if folder.is_dir() and (folder / "scenario.json").is_file():
                entry = _workflow(pa, folder, roster)
                if entry is not None:
                    workflows.append(entry)
    by_workflow = {w["id"]: w for w in workflows}

    templates_root = _templates_dir()
    starters: list[dict[str, Any]] = []
    for path in sorted((templates_root / "sessions").glob("*.md")):
        text = _read_text(path)
        if text is None:
            continue
        entry = parse_canned_session(path.stem, text)
        entry["path"] = f"templates/sessions/{path.name}"
        entry["workflows"] = [w for w in by_workflow if _mentions(entry["prompt"], w)]
        cast = _SESSION_CAST.search(entry["prompt"])
        entry["participants"] = [
            pid.strip().rstrip(".")
            for pid in (cast.group(1).split(",") if cast else [])
            if pid.strip()
        ]
        starters.append(entry)
    templates = []
    for path in sorted((templates_root / "artifacts").glob("*.html")):
        text = _read_text(path)
        if text is not None:
            entry = parse_artifact_template(path.stem, text)
            entry["key"] = f"template/{path.stem}"
            entry["starters"] = [s["id"] for s in starters if s.get("template") == path.stem]
            templates.append(entry)

    skills = _skills(skills_root)
    frameworks = _frameworks(workspace_dir() / "frameworks")

    # Links in both directions, so every inspect page can say what uses it.
    for workflow in workflows:
        for pid in workflow["participants"]:
            if pid in by_person:
                by_person[pid]["used_in"]["workflows"].append(workflow["id"])
    for starter in starters:
        for wid in starter["workflows"]:
            by_workflow[wid]["starters"].append(starter["id"])
        for pid in starter["participants"]:
            if pid in by_person:
                by_person[pid]["used_in"]["starters"].append(starter["id"])
    for skill in skills:
        for other in skills:
            if other["id"] != skill["id"] and _mentions(other["text"], skill["id"]):
                skill["used_by"].append(other["id"])
    for framework in frameworks:
        needle = f"frameworks/{framework['id']}.md"
        framework["used_by"] = [s["id"] for s in skills if needle in s["text"]]

    scenarios = [
        {
            "id": w["id"],
            "workflow": w["id"],
            "title": w["script"]["title"],
            "steps": w["script"]["steps"],
            "error": w["script"]["error"],
            "path": f"skills/{w['id']}/{w['script']['path']}",
            "text": w["script"]["text"],
            "cast": w["participants"],
            "fixtures": [f"skills/{w['id']}/{rel}" for rel in w["fixtures"].values()],
            "problems": w["problems"],
        }
        for w in workflows
        if w["script"]
    ]
    # A real line each person speaks in a scenario, for "how they appear when flying".
    for person in people:
        speech = re.compile(rf"^\*\*{re.escape(person['name'])}:\*\*\s*(.+)$", re.MULTILINE)
        for scenario in scenarios:
            found = speech.search(scenario["text"])
            if found:
                person["sample"] = {"text": found.group(1).strip(), "scenario": scenario["id"]}
                break
        else:
            person["sample"] = None
    for workflow in workflows:
        if workflow["script"]:
            workflow["script"] = {k: v for k, v in workflow["script"].items() if k != "text"}
    for skill in skills:
        skill.pop("text", None)

    return {
        "workspace_dir": str(workspace_dir()),
        "skills_dir": str(skills_root),
        "people": people,
        "workflows": workflows,
        "views": [v for w in workflows for v in w["views"]],
        "templates": templates,
        "scenarios": scenarios,
        "skills": skills,
        "starters": starters,
        "frameworks": frameworks,
        "drafts": _drafts(pa),
    }


# ------------------------------------------------------------------ building
#
# Slice 2: people can be built. Every change is a draft under
# ``<workspace>/.hangar/drafts/``; the work itself is done by ``pa``
# (``draft``, ``publish``, ``history``), the same code the build-person skill
# runs in a guided session, so the app and the agent can never disagree.


def _drafts(pa: ModuleType) -> list[dict[str, Any]]:
    try:
        return pa.list_drafts(workspace_dir(), slim_skills_dir())
    except Exception:
        _logger.warning("could not read the Hangar drafts", exc_info=True)
        return []


def _pa_call(fn: Any, *args: Any, **kwargs: Any) -> Any:
    pa = _pa()
    try:
        return fn(*args, **kwargs)
    except pa.PaError as err:
        raise HTTPException(status_code=409, detail=str(err)) from err


def draft_detail(pid: str) -> dict[str, Any]:
    pa = _pa()
    return _pa_call(pa.draft_info, workspace_dir(), pid, slim_skills_dir())


def start_person_draft(pid: str, remove: bool = False) -> dict[str, Any]:
    pa = _pa()
    _pa_call(pa.start_draft, workspace_dir(), pid=pid, remove=remove)
    return draft_detail(pid)


def publish_person(pid: str, summary: str) -> dict[str, Any]:
    pa = _pa()
    return _pa_call(pa.publish_draft, workspace_dir(), pid, summary, slim_skills_dir())


def discard_person_draft(pid: str) -> dict[str, Any]:
    pa = _pa()
    _pa_call(pa.discard_draft, workspace_dir(), pid)
    return {"id": pid, "discarded": True}


def restore_person(pid: str, version: str) -> dict[str, Any]:
    pa = _pa()
    return _pa_call(pa.restore_version, workspace_dir(), pid, version, slim_skills_dir())


def person_version(pid: str, version: str) -> dict[str, Any]:
    pa = _pa()
    for entry in _pa_call(pa.person_history, workspace_dir(), pid):
        if entry["version"] == version:
            return entry
    raise HTTPException(status_code=404, detail="no such version")


# --------------------------------------------------------------- rendering


def _workflow_folder(workflow: str) -> Path:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,80}", workflow):
        raise HTTPException(status_code=404, detail="no such workflow")
    folder = slim_skills_dir() / workflow
    if not (folder / "scenario.json").is_file():
        raise HTTPException(status_code=404, detail="no such workflow")
    return folder


def render_view(workflow: str, view: str) -> str:
    """One view of a workflow drawn over its scenario's sample data, as ``pa render`` would."""
    pa = _pa()
    folder = _workflow_folder(workflow)
    manifest = _json(folder / "scenario.json") or {}
    rel = (manifest.get("views") or {}).get(view)
    if not rel:
        raise HTTPException(status_code=404, detail="no such view")
    spec = _json(folder / rel)
    if not isinstance(spec, dict):
        raise HTTPException(status_code=422, detail=f"{rel} is not a view spec")
    roster = _roster(pa)
    fixture = (manifest.get("fixtures") or {}).get("dataset")
    data: dict[str, Any] = {"records": []}
    if fixture and (folder / fixture).is_file():
        loaded = _json(folder / fixture)
        if isinstance(loaded, dict):
            data = {k: v for k, v in loaded.items() if k not in ("views", "flow")}
    data["participants"] = {k: pa._card(v) for k, v in roster.items()}
    script = _script(pa, folder, manifest, roster)
    host = (script or {}).get("hosts", {}).get(view) or (
        "chat" if spec.get("layout") in ("form", "detail") else "canvas"
    )
    return pa.page(spec, data, host)


def render_preview(workflow: str) -> str:
    """The scenario's standalone player, as ``pa preview`` builds it."""
    pa = _pa()
    folder = _workflow_folder(workflow)
    out = io.StringIO()
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "preview.html"
        args = argparse.Namespace(
            scenario=str(folder),
            out=str(target),
            participants=str(workspace_dir() / "participants"),
        )
        try:
            with contextlib.redirect_stdout(out):
                pa.cmd_preview(args)
        except Exception as err:
            raise HTTPException(status_code=422, detail=str(err)) from err
        return target.read_text(encoding="utf-8")


def read_template(template: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][\w-]{0,80}", template):
        raise HTTPException(status_code=404, detail="no such template")
    path = _templates_dir() / "artifacts" / f"{template}.html"
    text = _read_text(path) if path.is_file() else None
    if text is None:
        raise HTTPException(status_code=404, detail="no such template")
    return text


def create_slim_hangar_router(*, auth_provider: AuthProvider | None = None) -> APIRouter:
    """Build the Hangar routes under ``/v1/slim/hangar``: the catalog, and drafts of people."""
    router = APIRouter()

    @router.get("/slim/hangar")
    async def get_hangar(request: Request) -> dict[str, Any]:
        require_user(request, auth_provider)
        return load_hangar()

    @router.get("/slim/hangar/views/{workflow}/{view}", response_class=HTMLResponse)
    async def get_view(request: Request, workflow: str, view: str) -> HTMLResponse:
        require_user(request, auth_provider)
        return HTMLResponse(render_view(workflow, view))

    @router.get("/slim/hangar/preview/{workflow}", response_class=HTMLResponse)
    async def get_preview(request: Request, workflow: str) -> HTMLResponse:
        require_user(request, auth_provider)
        return HTMLResponse(render_preview(workflow))

    @router.get("/slim/hangar/templates/{template}", response_class=HTMLResponse)
    async def get_template(request: Request, template: str) -> HTMLResponse:
        require_user(request, auth_provider)
        return HTMLResponse(read_template(template))

    @router.get("/slim/hangar/drafts/person/{pid}")
    async def get_draft(request: Request, pid: str) -> dict[str, Any]:
        require_user(request, auth_provider)
        return draft_detail(pid)

    @router.post("/slim/hangar/drafts/person/{pid}")
    async def post_draft(
        request: Request, pid: str, body: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        require_user(request, auth_provider)
        return start_person_draft(pid, remove=bool((body or {}).get("remove")))

    @router.delete("/slim/hangar/drafts/person/{pid}")
    async def delete_draft(request: Request, pid: str) -> dict[str, Any]:
        require_user(request, auth_provider)
        return discard_person_draft(pid)

    @router.post("/slim/hangar/drafts/person/{pid}/publish")
    async def post_publish(
        request: Request, pid: str, body: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        require_user(request, auth_provider)
        return publish_person(pid, str((body or {}).get("summary") or "")[:200])

    @router.get("/slim/hangar/history/person/{pid}/{version}")
    async def get_version(request: Request, pid: str, version: str) -> dict[str, Any]:
        require_user(request, auth_provider)
        return person_version(pid, version)

    @router.post("/slim/hangar/history/person/{pid}/{version}/restore")
    async def post_restore(request: Request, pid: str, version: str) -> dict[str, Any]:
        require_user(request, auth_provider)
        return restore_person(pid, version)

    return router
