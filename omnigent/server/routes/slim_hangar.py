"""omnigent-slim Hangar: what people can fly, and building people (``/v1/slim/hangar``).

The Hangar is Product Aviator's builder mode (docs/product/hangar.md, D-39 to
D-47). This first slice only looks: it lists the things other people fly and
how they refer to each other, all read from files that already exist:

- People and agents: ``<workspace>/participants/*.md`` (the roster).
- Workflows: each ``skills/<name>/`` folder with a ``workflow.json`` (shipped,
  locked), and ones built in the Hangar under ``<workspace>/.claude/skills/``.
- Views: every view spec a workflow lists, plus the standalone artifact
  templates in ``<library>/artifacts/*.html``.
- Scenarios: ``<workspace>/scenarios/<name>/``, a scripted run of a workflow
  with its cast, invented data and ``script.md`` (D-42).
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

import asyncio
import contextlib
import importlib.util
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse

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


def _avatar_url(pa: ModuleType, pid: str) -> str | None:
    path = pa.live_avatar(workspace_dir(), pid)
    return f"/v1/slim/hangar/avatars/{pid}?v={int(path.stat().st_mtime)}" if path else None


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
        "avatar": _avatar_url(pa, pid),
        "brief": person.get("brief", ""),
        "path": f"workspace/participants/{pid}.md",
        "problems": pa._check_participants({pid: person}),
        "used_in": {"workflows": [], "starters": []},
    }


# --------------------------------------------------------------- workflows


def _check(pa: ModuleType, folder: Path) -> list[str]:
    """``pa check`` on a workflow or scenario folder: its problems, in pa's words."""
    try:
        _, problems, _ = pa.check_run(
            folder, str(workspace_dir() / "participants"), workspace_dir()
        )
    except Exception as err:  # noqa: BLE001 -- PaError and friends: one problem, in its own words
        return [str(err) or type(err).__name__]
    return list(problems)


def _script(
    pa: ModuleType, folder: Path | None, manifest: dict[str, Any], roster: dict[str, Any]
) -> dict[str, Any] | None:
    rel = manifest.get("script")
    if folder is None or not rel or not (folder / rel).is_file():
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


def _shown(path: Path) -> str:
    """A path as the Hangar shows it: from the repo or the workspace."""
    for base, label in ((workspace_dir(), "workspace"), (slim_skills_dir(), "skills")):
        with contextlib.suppress(ValueError):
            return f"{label}/{path.resolve().relative_to(base.resolve()).as_posix()}"
    return path.as_posix()


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


# Where a view is shown (D-112). A workflow's instructions say it: a line like
# ``$PA render SKILL_DIR/views/card.json --host chat`` puts the card in the
# chat as a widget. The scenario's script ([widget card]) says it too. A view
# neither mentions goes by its layout: a form or one record's card in the chat,
# anything bigger in the canvas, as the view-kit skill teaches.
_SKILL_RENDER = re.compile(r"views/([A-Za-z0-9_.-]+?)\.json\b([^\n`]*)")


def skill_hosts(folder: Path, manifest: dict[str, Any]) -> dict[str, str]:
    """Each view's place as the workflow's SKILL.md renders it: ``chat`` or ``canvas``."""
    text = _read_text(folder / "SKILL.md") or ""
    by_file = {Path(str(rel)).stem: name for name, rel in (manifest.get("views") or {}).items()}
    hosts: dict[str, str] = {}
    for m in _SKILL_RENDER.finditer(text):
        name = by_file.get(m.group(1))
        if name is None or "render" not in text[max(0, m.start() - 80) : m.start()]:
            continue
        if "--host chat" in m.group(2):
            hosts[name] = "chat"
        else:
            hosts.setdefault(name, "canvas")
    return hosts


def view_host(
    name: str, spec: dict[str, Any], script: dict[str, Any] | None, skill: dict[str, str]
) -> str:
    return (
        (script or {}).get("hosts", {}).get(name)
        or skill.get(name)
        or ("chat" if spec.get("layout") in ("form", "detail") else "canvas")
    )


def _views_of(
    folder: Path,
    manifest: dict[str, Any],
    sample: dict[str, Any],
    script: dict[str, Any] | None,
    wid: str,
) -> list[dict[str, Any]]:
    skill = skill_hosts(folder, manifest)
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
                "host": view_host(name, spec, script, skill),
                "actions": len(spec.get("actions", [])) + (1 if spec.get("submit") else 0),
                "path": _shown(folder / rel),
                "file": str(rel),
            }
        )
    return views


def _workflow(pa: ModuleType, folder: Path, roster: dict[str, Any]) -> dict[str, Any] | None:
    try:
        run = pa.resolve_run(folder, workspace_dir())
    except Exception:  # noqa: BLE001 -- an unreadable workflow is left off the shelf
        return None
    manifest, wid, sdir = run["manifest"], run["workflow_id"], run["scenario_dir"]
    wid = folder.name
    script = _script(pa, sdir, manifest, roster)
    fixture = (manifest.get("fixtures") or {}).get("dataset")
    sample = _json(sdir / fixture) if fixture and sdir is not None else None
    sample = sample if isinstance(sample, dict) else {}
    views = _views_of(folder, manifest, sample, script, wid)
    skill_meta, _ = _front_matter(_read_text(folder / "SKILL.md") or "")
    builtin = not folder.resolve().is_relative_to(workspace_dir().resolve())
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
        "participants": [
            p for p in run["workflow"].get("participants") or [] if isinstance(p, str)
        ],
        "records": _record_types(folder, manifest),
        "views": views,
        "script": script,
        "scenarios": [s.name for s in pa.scenarios_of(wid, workspace_dir())],
        "builtin": builtin,
        "shipped": pa.shipped_workflow(workspace_dir(), wid) is not None,
        "history": pa.folder_history(workspace_dir(), "workflow", wid),
        "path": _shown(folder) + "/",
        "problems": _check(pa, folder),
        "starters": [],
    }


def _scenario_entry(pa: ModuleType, folder: Path, roster: dict[str, Any]) -> dict[str, Any]:
    entry: dict[str, Any] = {"id": folder.name, "path": _shown(folder) + "/"}
    try:
        run = pa.resolve_run(folder, workspace_dir())
    except Exception as err:  # noqa: BLE001 -- a broken scenario is listed with its problem
        raw = _json(folder / "scenario.json") or {}
        return {
            **entry,
            "workflow": str(raw.get("workflow") or ""),
            "title": str(raw.get("title") or folder.name),
            "summary": str(raw.get("summary") or ""),
            "steps": 0,
            "error": None,
            "text": "",
            "cast": [],
            "fixtures": [],
            "problems": [str(err)],
        }
    scenario, manifest = run["scenario"] or {}, run["manifest"]
    script = _script(pa, folder, manifest, roster)
    return {
        **entry,
        "workflow": run["workflow_id"],
        "title": str(scenario.get("title") or (script or {}).get("title") or folder.name),
        "summary": str(scenario.get("summary") or ""),
        "steps": (script or {}).get("steps", 0),
        "error": (script or {}).get("error"),
        "script_path": _shown(folder / str(manifest.get("script") or "script.md")),
        "text": (script or {}).get("text", ""),
        "cast": [p for p in manifest.get("participants") or [] if isinstance(p, str)],
        "fixtures": [
            _shown(folder / str(rel)) for rel in (manifest.get("fixtures") or {}).values()
        ],
        "opening": pa.scenario_opening(folder, scenario),
        "demo": demo_of(pa, folder.name),
        "history": pa.folder_history(workspace_dir(), "scenario", folder.name),
        "problems": _check(pa, folder),
    }


# ------------------------------------------------------------------- demos
#
# "Scenario you build, demo you fly" (D-76). Flying a scenario makes a folder
# under <workspace>/demos/<id>/ (pa.fly_demo) and a project for it named
# "◆ Demo · <title>", so the demo's sessions are listed together and run there.

DEMO_PREFIX = "◆ Demo · "
DEMO_ICON = "✈️"


def demo_project_name(title: str) -> str:
    return f"{DEMO_PREFIX}{title}"


def demo_of(pa: ModuleType, sid: str) -> dict[str, Any] | None:
    """Where the demo of a scenario is, if it has been flown: turn, turns, project name."""
    folder = pa.demo_dir(workspace_dir(), sid)
    state = pa.demo_state(folder)
    if state is None:
        return None
    return {
        **pa._demo_summary(folder, state),
        "project": demo_project_name(str(state.get("title") or sid)),
    }


def _ensure_demo_project(
    project_store: Any, user_id: str | None, name: str, folder: Path
) -> str | None:
    """Create the demo's project, or point an existing one at its folder; its id.

    Its settings (host, agent) follow the Workspace project.
    """
    if project_store is None:
        return None
    projects = project_store.list(user_id=user_id)
    base = next(
        (p for p in projects if p.name == os.environ.get("OMNIGENT_SLIM_PROJECT", "Workspace")),
        None,
    )
    config: dict[str, Any] = dict((base.config if base is not None else None) or {})
    config.update({"workspace": str(folder), "use_worktree": False, "icon": DEMO_ICON})
    existing = next((p for p in projects if p.name == name), None)
    if existing is not None:
        if (existing.config or {}).get("workspace") != str(folder):
            project_store.update(
                existing.id, user_id=user_id, config={**(existing.config or {}), **config}
            )
        return str(existing.id)
    import uuid

    return str(project_store.create(uuid.uuid4().hex, name, user_id, config).id)


def fly_scenario(
    sid: str,
    mode: str | None,
    project_store: Any = None,
    user_id: str | None = None,
    live_turns: bool | None = None,
) -> dict[str, Any]:
    """Fly a scenario as a demo. ``mode`` is None (ask if one exists), "reset" or "keep".

    ``live_turns`` False plays every turn canned (the Library's switch, D-85).
    """
    pa = _pa()
    folder = pa.list_scenarios(workspace_dir()).get(sid)
    if folder is None:
        raise HTTPException(status_code=404, detail=f"no published scenario {sid!r}")
    if mode not in (None, "reset", "keep"):
        raise HTTPException(status_code=400, detail="mode is reset or keep")
    existing = demo_of(pa, sid)
    if existing and mode is None:
        return {"state": "exists", "demo": existing}
    info = _pa_call(
        pa.fly_demo, folder, workspace_dir(), reset=mode != "keep", live_turns=live_turns
    )
    title = str(info.get("title") or sid)
    name = demo_project_name(title)
    project_id = _ensure_demo_project(project_store, user_id, name, Path(info["folder"]))
    fresh = bool(info.get("created")) or not info.get("turn")
    return {
        "state": "created" if info.get("created") else "kept",
        "demo": {**info, "project": name},
        "project": {"id": project_id, "name": name},
        # The composer starts with the opening line only at the start of the story.
        "prompt": info.get("opening", "") if fresh else "",
    }


# ------------------------------------------------------------------ others


def _skills(roots: list[Path], workspace: Path) -> list[dict[str, Any]]:
    """Every skill, first root wins: one built here takes over a shipped id (D-72, D-167)."""
    skills: list[dict[str, Any]] = []
    seen: set[str] = set()
    shipped: set[str] = set()
    for root in roots:
        if not root.is_dir():
            continue
        builtin = not root.resolve().is_relative_to(workspace.resolve())
        names = {p.name for p in root.iterdir() if p.is_dir() and (p / "SKILL.md").is_file()}
        if builtin:
            shipped |= names
        for name in sorted(names - seen):
            seen.add(name)
            skills.append(_skill_entry(root / name, builtin))
    for skill in skills:
        skill["shipped"] = skill["id"] in shipped
    return sorted(skills, key=lambda s: s["id"])


def _skill_entry(folder: Path, builtin: bool) -> dict[str, Any]:
    text = _read_text(folder / "SKILL.md") or ""
    meta, body = _front_matter(text)
    where = "skills" if builtin else "workspace/.claude/skills"
    return {
        "id": folder.name,
        "name": str(meta.get("name") or folder.name),
        "description": str(meta.get("description") or ""),
        "workflow": (folder / "workflow.json").is_file() or (folder / "scenario.json").is_file(),
        "files": sorted(
            p.relative_to(folder).as_posix()
            for p in folder.rglob("*")
            if p.is_file() and p.name != ".DS_Store"
        )[:60],
        "text": body,
        "path": f"{where}/{folder.name}/SKILL.md",
        "builtin": builtin,
        "used_by": [],
    }


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
    for folder in pa.list_workflows(workspace_dir()).values():
        entry = _workflow(pa, folder, roster)
        if entry is not None:
            workflows.append(entry)
    by_workflow = {w["id"]: w for w in workflows}
    scenarios = [
        _scenario_entry(pa, folder, roster)
        for folder in pa.list_scenarios(workspace_dir()).values()
    ]

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

    skills = _skills(pa.skill_roots(workspace_dir()), workspace_dir())
    frameworks = _frameworks(workspace_dir() / "frameworks")

    # Links in both directions, so every inspect page can say what uses it.
    for workflow in workflows:
        for pid in workflow["participants"]:
            if pid in by_person:
                by_person[pid]["used_in"]["workflows"].append(workflow["id"])
    for scenario in scenarios:
        for pid in scenario["cast"]:
            if pid in by_person:
                by_person[pid]["used_in"].setdefault("scenarios", []).append(scenario["id"])
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
        skill["history"] = (
            [] if skill["workflow"] else pa.folder_history(workspace_dir(), "skill", skill["id"])
        )

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
        "repo": repo_status(),
    }


# Published config travels with the repo (D-75): people, avatars, scenarios,
# workflows built in the workspace and starters are plain files in the
# checkout. The Hangar says when some are not committed yet, so they are not
# lost when the folder is replaced by a fresh download.
_TRAVELS = ("participants", "scenarios", ".claude/skills", "templates")


def repo_status() -> dict[str, Any]:
    root = workspace_dir()
    try:
        inside = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        if inside.returncode != 0:
            return {"git": False, "uncommitted": []}
        status = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all", "--", *_TRAVELS],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return {"git": False, "uncommitted": []}
    top = Path(inside.stdout.strip())
    files = []
    for line in status.stdout.splitlines():
        path = line[3:].strip().strip('"')
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        with contextlib.suppress(ValueError):
            path = (top / path).resolve().relative_to(root.resolve()).as_posix()
        files.append(path)
    return {
        "git": True,
        "uncommitted": files[:100],
        "count": len(files),
        "sent": _last_send(root),
    }


# ------------------------------------------------------------ send to repo
#
# D-113: on a git copy of the app (the Mac mini), "Send to repo" commits the
# published configuration to a new branch and pushes it, then opens a pull
# request with `gh` when it is installed (otherwise it hands back the link to
# open one). The commit is built in a throwaway index from HEAD, so the
# checkout, its branch and anything else in the working tree are left as they
# are; once the pull request merges, pulling main brings the same files back.
# Only a person's press does this: nothing is sent on its own, and a ZIP copy
# (no git, the work Mac) never shows the button.

_SENT = ".hangar/sent.json"


def _last_send(root: Path) -> dict[str, Any] | None:
    sent = _json(root / _SENT)
    return sent if isinstance(sent, dict) else None


def _git(args: list[str], cwd: Path, env: dict[str, str], timeout: int = 20) -> str:
    try:
        done = subprocess.run(
            ["git", *args],
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as err:
        raise HTTPException(
            status_code=422, detail=f"git {args[0]} took too long; nothing was sent"
        ) from err
    except OSError as err:
        raise HTTPException(status_code=422, detail="git is not installed here") from err
    if done.returncode != 0:
        lines = (done.stderr or done.stdout).strip().splitlines() or ["no reason given"]
        raise HTTPException(status_code=422, detail=f"git {args[0]} failed: {lines[-1]}")
    return done.stdout.strip()


def _compare_url(remote: str, base: str, branch: str) -> str | None:
    """The page that opens a pull request, for a GitHub remote."""
    m = re.fullmatch(
        r"(?:https://(?:[^@/]+@)?github\.com/|git@github\.com:)([^/]+/[^/]+?)(?:\.git)?/?", remote
    )
    return f"https://github.com/{m.group(1)}/compare/{base}...{branch}?expand=1" if m else None


def send_to_repo(summary: str = "") -> dict[str, Any]:
    root = workspace_dir()
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    top = Path(_git(["rev-parse", "--show-toplevel"], root, env))
    head = _git(["rev-parse", "HEAD"], top, env)
    rel = root.resolve().relative_to(top.resolve()).as_posix()
    specs = [
        spec
        for spec in (f"{rel}/{t}" if rel != "." else t for t in _TRAVELS)
        # A folder git has never seen and that is not on disk would fail `git add`.
        if (top / spec).exists() or _git(["ls-tree", "--name-only", "HEAD", spec], top, env)
    ]
    with tempfile.TemporaryDirectory() as tmp:
        index = {**env, "GIT_INDEX_FILE": str(Path(tmp) / "index")}
        _git(["read-tree", "HEAD"], top, index)
        _git(["add", "-A", "--", *specs], top, index, timeout=60)
        tree = _git(["write-tree"], top, index)
        if tree == _git(["rev-parse", "HEAD^{tree}"], top, env):
            raise HTTPException(
                status_code=422, detail="every published file is already in the repo"
            )
        last = _last_send(root) or {}
        if last.get("tree") == tree:
            raise HTTPException(
                status_code=422,
                detail=f"already sent as {last.get('branch')}; merge that first",
            )
        changed = _git(["diff-tree", "-r", "--name-status", "HEAD", tree], top, env).splitlines()
        who = {}
        if not _git_config(top, env, "user.email"):
            who = {
                "GIT_AUTHOR_NAME": "Flight Deck Hangar",
                "GIT_AUTHOR_EMAIL": "hangar@flight-deck.local",
                "GIT_COMMITTER_NAME": "Flight Deck Hangar",
                "GIT_COMMITTER_EMAIL": "hangar@flight-deck.local",
            }
        title = f"Hangar: {summary.strip()}" if summary.strip() else "Hangar: published changes"
        body = "Published in the Hangar and sent with Send to repo (D-113).\n\n" + "\n".join(
            f"- {line.replace(chr(9), ' ')}" for line in changed[:200]
        )
        commit = _git(
            ["commit-tree", tree, "-p", head, "-m", f"{title}\n\n{body}"], top, {**env, **who}
        )
    stamp = datetime.now().astimezone().strftime("%Y-%m-%d-%H%M%S")
    branch = f"hangar/{stamp}"
    remote = _git(["remote"], top, env).splitlines()
    name = "origin" if "origin" in remote else (remote[0] if remote else "")
    if not name:
        raise HTTPException(status_code=422, detail="this copy has no remote to send to")
    _git(["push", name, f"{commit}:refs/heads/{branch}"], top, env, timeout=120)
    base = "main"
    with contextlib.suppress(HTTPException):
        base = _git(["symbolic-ref", "--short", f"refs/remotes/{name}/HEAD"], top, env).split(
            "/", 1
        )[-1]
    url = None
    if shutil.which("gh"):
        with contextlib.suppress(OSError, subprocess.SubprocessError):
            made = subprocess.run(
                [
                    "gh",
                    "pr",
                    "create",
                    "--head",
                    branch,
                    "--base",
                    base,
                    "--title",
                    title,
                    "--body",
                    body,
                ],
                cwd=top,
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            if made.returncode == 0 and made.stdout.strip().startswith("https://"):
                url = made.stdout.strip().splitlines()[-1]
    remote_url = ""
    with contextlib.suppress(HTTPException):
        remote_url = _git(["remote", "get-url", name], top, env)
    sent = {
        "branch": branch,
        "commit": commit,
        "tree": tree,
        "files": len(changed),
        "at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "pull_request": url,
        "open_pr": None if url else _compare_url(remote_url, base, branch),
        "summary": summary.strip(),
    }
    target = root / _SENT
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(sent, indent=1) + "\n", encoding="utf-8")
    return sent


def _git_config(top: Path, env: dict[str, str], key: str) -> str:
    try:
        return _git(["config", key], top, env)
    except HTTPException:
        return ""


# ------------------------------------------------------------------ building
#
# Slice 2: people can be built. Every change is a draft under
# ``<workspace>/.hangar/drafts/``; the work itself is done by ``pa``
# (``draft``, ``publish``, ``history``), the same code the build-person skill
# runs in a guided session, so the app and the agent can never disagree.


def _drafts(pa: ModuleType) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    try:
        out += pa.list_drafts(workspace_dir(), slim_skills_dir())
    except Exception:
        _logger.warning("could not read the Hangar drafts", exc_info=True)
    try:
        # Folder drafts are listed without file contents; the editor fetches those.
        for draft in pa.list_folder_drafts(workspace_dir()):
            draft["files"] = [
                {k: v for k, v in f.items() if k not in ("text", "live")} for f in draft["files"]
            ]
            out.append(draft)
    except Exception:
        _logger.warning("could not read the Hangar folder drafts", exc_info=True)
    return out


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


_EDITABLE = ("name", "kind", "role", "initials", "backing", "call_for", "skills")
_AVATAR_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def set_person_avatar(pid: str, filename: str, data: bytes | None) -> dict[str, Any]:
    """Copy a picked picture into the draft (D-74); it reaches the roster on publish."""
    pa = _pa()
    _pa_call(pa.set_draft_avatar, workspace_dir(), pid, filename, data)
    return draft_detail(pid)


def avatar_file(pid: str, draft: bool) -> Path:
    pa = _pa()
    if not _NAME.fullmatch(pid):
        raise HTTPException(status_code=404, detail="no such avatar")
    path = pa.avatar_of(workspace_dir(), pid, draft)
    if path is None or path.suffix not in _AVATAR_TYPES:
        raise HTTPException(status_code=404, detail="no such avatar")
    return path


def avatars() -> dict[str, str]:
    """Every live avatar, by participant id, as a URL that changes when the picture does."""
    pa = _pa()
    out: dict[str, str] = {}
    for pid in _roster(pa):
        path = pa.live_avatar(workspace_dir(), pid)
        if path is not None:
            out[pid] = f"/v1/slim/hangar/avatars/{pid}?v={int(path.stat().st_mtime)}"
    return out


def edit_person_draft(pid: str, body: dict[str, Any]) -> dict[str, Any]:
    """Save edits made on the Hangar page into the draft (fields, brief, cast)."""
    pa = _pa()
    fields = {k: body["fields"][k] for k in _EDITABLE if k in (body.get("fields") or {})}
    brief = body.get("brief")
    cast = body.get("cast")
    if brief is not None and not isinstance(brief, str):
        raise HTTPException(status_code=422, detail="brief must be text")
    if cast is not None and not (
        isinstance(cast, dict)
        and all(isinstance(v, list) and all(isinstance(i, str) for i in v) for v in cast.values())
    ):
        raise HTTPException(status_code=422, detail="cast must map a kind to a list of ids")
    aviator = body.get("aviator")
    _pa_call(
        pa.edit_draft,
        workspace_dir(),
        pid,
        fields,
        brief,
        None,
        cast,
        str(aviator) if aviator else None,
    )
    return draft_detail(pid)


def new_person_draft(name: str, duplicate_of: str | None = None) -> dict[str, Any]:
    pa = _pa()
    pid = _pa_call(pa.start_draft, workspace_dir(), name=name, duplicate_of=duplicate_of)
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


# Slice 3: scenarios and workflows. A draft is a whole folder; the same
# ``pa`` functions back ``pa draft scenario|workflow`` for the builder skills.

_FOLDER_KINDS = ("scenario", "workflow", "skill")


def _folder_kind(kind: str) -> str:
    if kind not in _FOLDER_KINDS:
        raise HTTPException(status_code=404, detail="no such kind of draft")
    return kind


def folder_draft_detail(kind: str, fid: str) -> dict[str, Any]:
    pa = _pa()
    info = _pa_call(pa.folder_draft_info, workspace_dir(), _folder_kind(kind), fid)
    if info.get("kind") == "workflow" and info.get("action") != "remove":
        info["views"] = _draft_views(pa, fid)
    return info


def _draft_views(pa: ModuleType, fid: str) -> list[dict[str, Any]]:
    """The widgets and views of a workflow draft, placed as they would be when flying."""
    folder, _ = pa._fd_paths(workspace_dir(), "workflow", fid)
    try:
        run = pa.resolve_run(folder, workspace_dir())
    except Exception:  # noqa: BLE001 -- the checks already say what is wrong
        return []
    manifest, sdir = run["manifest"], run["scenario_dir"]
    script = _script(pa, sdir, manifest, _roster(pa))
    fixture = (manifest.get("fixtures") or {}).get("dataset")
    sample = _json(sdir / fixture) if fixture and sdir is not None else None
    return _views_of(folder, manifest, sample if isinstance(sample, dict) else {}, script, fid)


def start_folder_draft(kind: str, fid: str, remove: bool = False) -> dict[str, Any]:
    pa = _pa()
    _pa_call(pa.start_folder_draft, workspace_dir(), _folder_kind(kind), fid=fid, remove=remove)
    return folder_draft_detail(kind, fid)


def new_folder_draft(kind: str, body: dict[str, Any]) -> dict[str, Any]:
    pa = _pa()
    name = str(body.get("name") or "").strip()[:80]
    if not name:
        raise HTTPException(status_code=422, detail=f"a new {kind} needs a name")
    duplicate = body.get("duplicate_of")
    workflow = body.get("workflow")
    fid = _pa_call(
        pa.start_folder_draft,
        workspace_dir(),
        _folder_kind(kind),
        name=name,
        duplicate_of=str(duplicate) if duplicate else None,
        workflow=str(workflow) if workflow else None,
    )
    return folder_draft_detail(kind, fid)


def edit_folder_draft(kind: str, fid: str, body: dict[str, Any]) -> dict[str, Any]:
    """Save edits made on the Hangar page: manifest fields and whole text files."""
    pa = _pa()
    manifest = body.get("manifest")
    files = body.get("files")
    if manifest is not None and not isinstance(manifest, dict):
        raise HTTPException(status_code=422, detail="manifest must be an object")
    if files is not None and not (
        isinstance(files, dict)
        and all(isinstance(k, str) and (v is None or isinstance(v, str)) for k, v in files.items())
    ):
        raise HTTPException(status_code=422, detail="files must map a path to text (or null)")
    aviator = body.get("aviator")
    _pa_call(
        pa.edit_folder_draft,
        workspace_dir(),
        _folder_kind(kind),
        fid,
        manifest or None,
        files or None,
        None,
        str(aviator) if aviator else None,
    )
    return folder_draft_detail(kind, fid)


def publish_folder(kind: str, fid: str, summary: str) -> dict[str, Any]:
    pa = _pa()
    return _pa_call(pa.publish_folder_draft, workspace_dir(), _folder_kind(kind), fid, summary)


def discard_folder(kind: str, fid: str) -> dict[str, Any]:
    pa = _pa()
    _pa_call(pa.discard_folder_draft, workspace_dir(), _folder_kind(kind), fid)
    return {"id": fid, "discarded": True}


def restore_folder(kind: str, fid: str, version: str) -> dict[str, Any]:
    pa = _pa()
    return _pa_call(pa.restore_folder_version, workspace_dir(), _folder_kind(kind), fid, version)


def render_draft_preview(kind: str, fid: str) -> str:
    """The player for a draft scenario (or a draft workflow's first scenario)."""
    pa = _pa()
    folder, meta = pa._fd_paths(workspace_dir(), _folder_kind(kind), fid)
    if not meta.is_file() or not folder.is_dir():
        raise HTTPException(status_code=404, detail="no such draft")
    try:
        return pa.preview_html(folder, str(workspace_dir() / "participants"), workspace_dir())
    except Exception as err:
        raise HTTPException(status_code=422, detail=str(err)) from err


def aviator_home(session_id: str) -> dict[str, Any]:
    """The Hangar page whose Aviator pop-over holds this session, if a draft still has it.

    Hangar chats belong on their draft's page, not in flying mode: the web UI
    asks here when a session opens and, if the answer has a path, goes there.
    """
    pa = _pa()
    base = workspace_dir() / pa.HANGAR_DIR / "drafts"
    kinds = {"people": "person", **{v: k for k, v in pa.FOLDER_KINDS.items()}}
    for folder, kind in kinds.items():
        for meta in sorted((base / folder).glob("*.json")) if (base / folder).is_dir() else []:
            data = _json(meta)
            if isinstance(data, dict) and data.get("aviator") == session_id:
                return {
                    "kind": kind,
                    "id": meta.stem,
                    "path": f"/hangar/drafts/{kind}/{meta.stem}",
                }
    return {"kind": None, "id": None, "path": None}


# --------------------------------------------------------------- rendering


_NAME = re.compile(r"[a-z0-9][a-z0-9-]{0,80}")


def _workflow_folder(workflow: str) -> Path:
    if not _NAME.fullmatch(workflow):
        raise HTTPException(status_code=404, detail="no such workflow")
    folder = _pa().find_workflow(workflow, workspace_dir())
    if folder is None:
        raise HTTPException(status_code=404, detail="no such workflow")
    return folder


def render_view(workflow: str, view: str) -> str:
    """One view of a workflow over its first scenario's sample data, as ``pa render`` draws it."""
    return _render_view_in(_workflow_folder(workflow), view)


def render_draft_view(fid: str, view: str) -> str:
    """One view of a workflow draft, so the widget editor shows the change as it is typed."""
    pa = _pa()
    if not _NAME.fullmatch(fid):
        raise HTTPException(status_code=404, detail="no such draft")
    folder, meta = pa._fd_paths(workspace_dir(), "workflow", fid)
    if not meta.is_file() or not folder.is_dir():
        raise HTTPException(status_code=404, detail="no such draft")
    return _render_view_in(folder, view)


def _render_view_in(folder: Path, view: str) -> str:
    pa = _pa()
    try:
        run = pa.resolve_run(folder, workspace_dir())
    except Exception as err:  # noqa: BLE001 -- shown in the frame, not raised
        raise HTTPException(status_code=422, detail=str(err)) from err
    manifest, sdir = run["manifest"], run["scenario_dir"]
    rel = (manifest.get("views") or {}).get(view)
    if not rel:
        raise HTTPException(status_code=404, detail="no such view")
    spec = _json(folder / rel)
    if not isinstance(spec, dict):
        raise HTTPException(status_code=422, detail=f"{rel} is not a view spec")
    roster = _roster(pa)
    fixture = (manifest.get("fixtures") or {}).get("dataset")
    data: dict[str, Any] = {"records": []}
    if fixture and sdir is not None and (sdir / fixture).is_file():
        loaded = _json(sdir / fixture)
        if isinstance(loaded, dict):
            data = {k: v for k, v in loaded.items() if k not in ("views", "flow")}
    data["participants"] = {k: pa._card(v) for k, v in roster.items()}
    script = _script(pa, sdir, manifest, roster)
    host = view_host(view, spec, script, skill_hosts(folder, manifest))
    try:
        return pa.page(spec, data, host)
    except Exception as err:  # noqa: BLE001 -- a half-typed spec is shown as a problem
        raise HTTPException(status_code=422, detail=f"{rel}: {err}") from err


def render_preview(name: str) -> str:
    """A scenario's player (or a workflow's first scenario's), as ``pa preview`` builds it."""
    pa = _pa()
    if not _NAME.fullmatch(name):
        raise HTTPException(status_code=404, detail="no such scenario")
    folder = pa.list_scenarios(workspace_dir()).get(name) or pa.find_workflow(
        name, workspace_dir()
    )
    if folder is None:
        raise HTTPException(status_code=404, detail="no such scenario")
    try:
        return pa.preview_html(folder, str(workspace_dir() / "participants"), workspace_dir())
    except Exception as err:
        raise HTTPException(status_code=422, detail=str(err)) from err


def read_template(template: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][\w-]{0,80}", template):
        raise HTTPException(status_code=404, detail="no such template")
    path = _templates_dir() / "artifacts" / f"{template}.html"
    text = _read_text(path) if path.is_file() else None
    if text is None:
        raise HTTPException(status_code=404, detail="no such template")
    return text


def create_slim_hangar_router(
    *, auth_provider: AuthProvider | None = None, project_store: Any = None
) -> APIRouter:
    """Build the Hangar routes under ``/v1/slim/hangar``: the catalog, and drafts of people."""
    router = APIRouter()

    @router.post("/slim/scenarios/{sid}/fly")
    async def post_fly(request: Request, sid: str) -> dict[str, Any]:
        """Fly a scenario as a demo: make its folder and its "◆ Demo" project.

        Body (optional): ``{"mode": "reset" | "keep", "live_turns": bool}``.
        ``live_turns`` false plays every turn canned. Without a mode, an
        existing demo is reported (``state: "exists"``) so the caller can offer
        "Reset to the start" or "Keep going". Otherwise returns ``state``
        ("created" or "kept"), ``project`` ({id, name}) and ``prompt``, the
        opening line for the new session's composer.
        """
        user_id = require_user(request, auth_provider)
        body: dict[str, Any] = {}
        with contextlib.suppress(Exception):
            body = await request.json() or {}
        if not isinstance(body, dict):
            body = {}
        mode = body.get("mode")
        live = body.get("live_turns")
        live_turns = live if isinstance(live, bool) else None
        result = await asyncio.to_thread(
            fly_scenario, sid, mode, project_store, user_id, live_turns
        )
        if result.get("project"):
            from omnigent.server.routes.sessions import announce_projects_changed

            announce_projects_changed(user_id)  # other open tabs list the new project
        return result

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

    @router.post("/slim/hangar/repo/send")
    async def post_send_to_repo(
        request: Request, body: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        require_user(request, auth_provider)
        return send_to_repo(str((body or {}).get("summary") or "")[:120])

    @router.get("/slim/hangar/aviator/{session_id}")
    async def get_aviator_home(request: Request, session_id: str) -> dict[str, Any]:
        require_user(request, auth_provider)
        return aviator_home(session_id)

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

    @router.patch("/slim/hangar/drafts/person/{pid}")
    async def patch_draft(request: Request, pid: str, body: dict[str, Any]) -> dict[str, Any]:
        require_user(request, auth_provider)
        return edit_person_draft(pid, body)

    @router.post("/slim/hangar/drafts/person")
    async def post_new_draft(request: Request, body: dict[str, Any]) -> dict[str, Any]:
        require_user(request, auth_provider)
        name = str(body.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=422, detail="a new person needs a name")
        duplicate = body.get("duplicate_of")
        return new_person_draft(name[:80], str(duplicate) if duplicate else None)

    @router.put("/slim/hangar/drafts/person/{pid}/avatar")
    async def put_avatar(request: Request, pid: str) -> dict[str, Any]:
        require_user(request, auth_provider)
        data = await request.body()
        name = request.headers.get("x-filename", "avatar")[:120]
        return set_person_avatar(pid, name, data)

    @router.delete("/slim/hangar/drafts/person/{pid}/avatar")
    async def delete_avatar(request: Request, pid: str) -> dict[str, Any]:
        require_user(request, auth_provider)
        return set_person_avatar(pid, "", None)

    @router.get("/slim/hangar/avatars")
    async def get_avatars(request: Request) -> dict[str, str]:
        require_user(request, auth_provider)
        return avatars()

    @router.get("/slim/hangar/avatars/{pid}")
    async def get_avatar(request: Request, pid: str, draft: bool = False) -> FileResponse:
        require_user(request, auth_provider)
        path = avatar_file(pid, draft)
        return FileResponse(
            path,
            media_type=_AVATAR_TYPES[path.suffix],
            headers={"Cache-Control": "no-cache", "X-Content-Type-Options": "nosniff"},
        )

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

    @router.get("/slim/hangar/drafts/workflow/{fid}/views/{view}", response_class=HTMLResponse)
    async def get_draft_view(request: Request, fid: str, view: str) -> HTMLResponse:
        require_user(request, auth_provider)
        return HTMLResponse(render_draft_view(fid, view))

    @router.get("/slim/hangar/drafts/{kind}/{fid}/preview", response_class=HTMLResponse)
    async def get_folder_preview(request: Request, kind: str, fid: str) -> HTMLResponse:
        require_user(request, auth_provider)
        return HTMLResponse(render_draft_preview(kind, fid))

    @router.get("/slim/hangar/drafts/{kind}/{fid}")
    async def get_folder_draft(request: Request, kind: str, fid: str) -> dict[str, Any]:
        require_user(request, auth_provider)
        return folder_draft_detail(kind, fid)

    @router.post("/slim/hangar/drafts/{kind}/{fid}")
    async def post_folder_draft(
        request: Request, kind: str, fid: str, body: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        require_user(request, auth_provider)
        return start_folder_draft(kind, fid, remove=bool((body or {}).get("remove")))

    @router.patch("/slim/hangar/drafts/{kind}/{fid}")
    async def patch_folder_draft(
        request: Request, kind: str, fid: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        require_user(request, auth_provider)
        return edit_folder_draft(kind, fid, body)

    @router.post("/slim/hangar/drafts/{kind}")
    async def post_new_folder_draft(
        request: Request, kind: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        require_user(request, auth_provider)
        return new_folder_draft(kind, body)

    @router.delete("/slim/hangar/drafts/{kind}/{fid}")
    async def delete_folder_draft(request: Request, kind: str, fid: str) -> dict[str, Any]:
        require_user(request, auth_provider)
        return discard_folder(kind, fid)

    @router.post("/slim/hangar/drafts/{kind}/{fid}/publish")
    async def post_folder_publish(
        request: Request, kind: str, fid: str, body: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        require_user(request, auth_provider)
        return publish_folder(kind, fid, str((body or {}).get("summary") or "")[:200])

    @router.post("/slim/hangar/history/{kind}/{fid}/{version}/restore")
    async def post_folder_restore(
        request: Request, kind: str, fid: str, version: str
    ) -> dict[str, Any]:
        require_user(request, auth_provider)
        return restore_folder(kind, fid, version)

    return router
