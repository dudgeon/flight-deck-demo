"""omnigent-slim Library (``/v1/slim/library``): where work and demos start (D-82 to D-88).

The Library is built from what is published in the Hangar, never typed into it:

- **Skills.** A workflow whose ``workflow.json`` has ``"library": {"show": true}``
  is a featured product skill. ``order`` places it in rough product-lifecycle
  order; the first one (or the one with ``"spotlight": true``) is the spotlight.
  Its title, summary, steps and inputs come from the same file. ``library.prompt``
  is what Start puts in the composer (``{{name: hint}}`` becomes a field);
  without one, a prompt is made from the inputs. Utility skills (person and
  scenario builders and the like) have no flag and never show.
- **Extra starters.** ``<library>/sessions/*.md`` files still work: a starter
  that names a featured workflow shows as an extra way in on that skill's card.
- **Demos.** Every published scenario, unless its ``scenario.json`` says
  ``"library": {"show": false}``. Title, summary, cast and the workflow it runs
  come from ``scenario.json``; how many turns are live comes from its script.

Each demo names the card it belongs to (``arc_title``): a part of an arc shows
under the arc's name, not its own. Each cast member has a ``hue`` (1 to 8), its
place in the roster, so a person keeps one colour everywhere in the Library.

Artifact templates are no longer listed here (D-88): they are managed in the
Hangar and the agent finds them when asked. ``parse_artifact_template`` stays
for the Hangar.

Everything is read on every request, so edits show up on the next page load.
"""

from __future__ import annotations

import html
import json
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


def _starters(root: Path | None) -> list[dict[str, Any]]:
    """Extra starters: ``sessions/*.md`` files, each a prompt with fields."""
    found: list[dict[str, Any]] = []
    if root is None:
        return found
    for path in sorted((root / "sessions").glob("*.md")):
        text = _read_text(path)
        if text is not None:
            found.append(parse_canned_session(path.stem, text))
    return found


def _fields(prompt: str) -> list[dict[str, str]]:
    fields: list[dict[str, str]] = []
    seen: set[str] = set()
    for field in _FIELD.finditer(prompt):
        name = field.group(1)
        if name not in seen:
            seen.add(name)
            fields.append({"name": name, "hint": (field.group(2) or "").strip()})
    return fields


def skill_prompt(wid: str, manifest: dict[str, Any], participants: list[str]) -> str:
    """What Start puts in the composer: ``library.prompt``, or one made from the inputs."""
    lib = manifest.get("library") or {}
    prompt = str(lib.get("prompt") or "").strip()
    if not prompt:
        title = str(manifest.get("title") or wid)
        parts = []
        for item in manifest.get("inputs") or []:
            name = re.sub(r"[^\w-]+", "-", str(item.get("name") or "input")).strip("-") or "input"
            hint = str(item.get("hint") or "").replace("}", ")")
            parts.append(f"{{{{{name}: {hint}}}}}" if hint else f"{{{{{name}}}}}")
        on = " on " + ", ".join(parts) if parts else ""
        prompt = f"{title}{on}, using the {wid} skill."
    if participants and "Participants for this session" not in prompt:
        prompt += "\n\nParticipants for this session: " + ", ".join(participants) + "."
    return prompt


def _live_meter(steps: list[dict[str, Any]], turns: int) -> list[bool]:
    """One flag per turn: does any step in it hand over to a real agent? A turn starts at each "You" line or wait."""
    meter: list[bool] = []
    for step in steps:
        if "pm" in step or step.get("await") or not meter:
            meter.append(False)
        if step.get("live"):
            meter[-1] = True
    if len(meter) > turns and not meter[0]:
        meter = meter[1:]  # steps before the first turn belong to it
    return (meter + [False] * turns)[:turns]


def _order(lib: dict[str, Any], fallback: str) -> tuple[float, str]:
    try:
        return (float(lib.get("order")), fallback)
    except (TypeError, ValueError):
        return (float("inf"), fallback)


def load_library(root: Path | None) -> dict[str, Any]:
    """Featured skills and demos, built from published workflows and scenarios."""
    # Imported here: slim_hangar imports this module for its parsers.
    from omnigent.server.routes import slim_hangar

    pa = slim_hangar._pa()
    ws = slim_hangar.workspace_dir()
    roster = slim_hangar._roster(pa)
    starters = _starters(root)
    stages = _stage_titles(ws)
    hues = {pid: i % 8 + 1 for i, pid in enumerate(sorted(roster))}

    skills: list[dict[str, Any]] = []
    titles: dict[str, str] = {}
    for wid, folder in pa.list_workflows(ws).items():
        path = pa.workflow_manifest_path(folder)
        manifest = slim_hangar._json(path) if path else None
        if not isinstance(manifest, dict):
            continue
        titles[wid] = str(manifest.get("title") or wid)
        lib = manifest.get("library") or {}
        if not isinstance(lib, dict) or not lib.get("show"):
            continue
        if manifest.get("tier") in _HIDDEN_TIERS:
            continue  # moves are offered on artifacts, not in the Library (D-153)
        routing = manifest.get("routing") if isinstance(manifest.get("routing"), dict) else {}
        stage = routing.get("stage")
        stage = stage[0] if isinstance(stage, list) and stage else stage
        participants = [p for p in manifest.get("participants") or [] if isinstance(p, str)]
        prompt = skill_prompt(wid, manifest, participants)
        parts = [
            str(part["workflow"])
            for part in manifest.get("parts") or []
            if isinstance(part, dict) and part.get("workflow")
        ]
        crew = list(participants)
        for part in parts:
            for pid in _manifest_of(pa, part, ws).get("participants") or []:
                if isinstance(pid, str) and pid not in crew:
                    crew.append(pid)
        skills.append(
            {
                "id": wid,
                "title": titles[wid],
                "summary": str(lib.get("summary") or manifest.get("summary") or ""),
                "steps": [s for s in manifest.get("steps") or [] if isinstance(s, str)],
                "prompt": prompt,
                "fields": _fields(prompt),
                "spotlight": bool(lib.get("spotlight")),
                "stage": stages.get(str(stage)) if stage else None,
                "view": _main_view(pa, wid, manifest, parts, ws),
                "cast": [_cast_member(pa, roster, hues, pid) for pid in crew],
                "sort": _order(lib, titles[wid]),
                "starters": [],
                "demos": [],
            }
        )
    skills.sort(key=lambda s: s.pop("sort"))
    if skills and not any(s["spotlight"] for s in skills):
        skills[0]["spotlight"] = True
    elif skills:
        first = next(s for s in skills if s["spotlight"])
        for other in skills:
            other["spotlight"] = other is first
    by_skill = {s["id"]: s for s in skills}
    for starter in starters:
        for wid in by_skill:
            if re.search(rf"(?<![\w-]){re.escape(wid)}(?![\w-])", starter["prompt"]):
                by_skill[wid]["starters"].append(starter)
                break

    demos: list[dict[str, Any]] = []
    for sid, folder in pa.list_scenarios(ws).items():
        raw = slim_hangar._json(folder / "scenario.json") or {}
        lib = raw.get("library") or {}
        if isinstance(lib, dict) and lib.get("show") is False:
            continue
        try:
            run = pa.resolve_run(folder, ws)
            manifest = run["manifest"]
            script = pa._read_script(folder / str(manifest.get("script") or "script.md"), roster)
            steps = script["steps"]
            turns = pa._turn_count(steps)
            meter = _live_meter(steps, turns)
            live = sum(meter)
            wid = run["workflow_id"]
        except Exception:  # noqa: BLE001 -- a broken scenario can't be flown, so it isn't listed
            _logger.warning("skipping scenario %s", sid, exc_info=True)
            continue
        cast = [_cast_member(pa, roster, hues, pid) for pid in manifest.get("participants") or []]
        minutes = raw.get("length_minutes")
        demo = {
            "id": sid,
            "title": str(raw.get("title") or sid),
            "summary": str(raw.get("summary") or ""),
            "workflow": wid,
            "workflow_title": titles.get(wid, wid),
            "cast": cast,
            "turns": turns,
            "live_turns": live,
            "meter": meter,
            "kind": "Scripted" if live == 0 else "Mixed",
            "length_minutes": minutes if isinstance(minutes, (int, float)) else None,
            "demo": slim_hangar.demo_of(pa, sid),
            "sort": _order(lib if isinstance(lib, dict) else {}, str(raw.get("title") or sid)),
        }
        # A part of an arc (D-148) has no card; its demos show on the arc's card.
        card = wid if wid in by_skill else _arc_of(pa, wid, ws)
        demo["arc"] = card if card in by_skill else wid
        demo["arc_title"] = by_skill[card]["title"] if card in by_skill else demo["workflow_title"]
        if card in by_skill:
            demo["sort_skill"] = card
            by_skill[card]["demos"].append({"id": sid, "title": demo["title"]})
        demos.append(demo)
    # Demos follow the skills they show, in the same lifecycle order; the rest after.
    rank = {s["id"]: i for i, s in enumerate(skills)}
    demos.sort(key=lambda d: (rank.get(d.pop("sort_skill", d["workflow"]), len(rank)), d.pop("sort")))

    return {
        "library_dir": str(root) if root is not None else None,
        "project": os.environ.get(PROJECT_ENV, "").strip() or None,
        "skills": skills,
        "demos": demos,
    }


_HIDDEN_TIERS = ("move", "kit", "companion")


def _stage_titles(ws: Path) -> dict[str, str]:
    """Stage id to its title, from the lifecycle framework (Discover, Shape, ...)."""
    try:
        data = json.loads((ws / "frameworks" / "lifecycle.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {
        str(s["id"]): str(s.get("title") or s["id"])
        for s in data.get("stages") or []
        if isinstance(s, dict) and s.get("id")
    }


def _cast_member(pa: Any, roster: dict[str, Any], hues: dict[str, int], pid: str) -> dict[str, Any]:
    """A person as a Library card shows them: name, initials, picture and colour."""
    from omnigent.server.routes import slim_hangar

    person = roster.get(pid) or {}
    return {
        "id": pid,
        "name": str(person.get("name") or pid),
        "initials": str(person.get("initials") or pid[:2].upper()),
        "avatar": slim_hangar._avatar_url(pa, pid),
        "hue": hues.get(pid, 1),
    }


def _manifest_of(pa: Any, wid: str, ws: Path) -> dict[str, Any]:
    folder = pa.find_workflow(wid, ws)
    path = pa.workflow_manifest_path(folder) if folder else None
    try:
        manifest = json.loads(Path(path).read_text(encoding="utf-8")) if path else None
    except (OSError, ValueError):
        manifest = None
    return manifest if isinstance(manifest, dict) else {}


def _main_view(
    pa: Any, wid: str, manifest: dict[str, Any], parts: list[str], ws: Path
) -> dict[str, str] | None:
    """What the work makes, drawn the way the Hangar draws it (D-170).

    The first work product that is a view. A part of the arc that has the same
    view is preferred, because its scenario gives the drawing real sample data.
    """
    for product in manifest.get("work_products") or []:
        if not isinstance(product, dict) or not product.get("view"):
            continue
        name = str(product["view"])
        owner = next(
            (p for p in parts if name in (_manifest_of(pa, p, ws).get("views") or {})),
            wid if name in (manifest.get("views") or {}) else None,
        )
        if owner:
            return {"workflow": owner, "name": name, "title": str(product.get("name") or name)}
    return None


def _arc_of(pa: Any, wid: str, ws: Path) -> str | None:
    """The arc a workflow is a part of (its ``part_of``), if any."""
    part_of = _manifest_of(pa, wid, ws).get("part_of")
    return str(part_of) if part_of else None


def create_slim_library_router(*, auth_provider: AuthProvider | None = None) -> APIRouter:
    """Build the router for ``GET /v1/slim/library``."""
    router = APIRouter()

    @router.get("/slim/library")
    async def get_library(request: Request) -> dict[str, Any]:
        require_user(request, auth_provider)
        return load_library(library_dir())

    return router
