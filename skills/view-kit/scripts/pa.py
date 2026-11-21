#!/usr/bin/env python3
"""pa: the Product Aviator data and view command.

One small program that skills call instead of writing JSON or HTML by hand.
Standard library only; nothing here touches the network.

  pa init    DATA --title T [--from FIXTURE]     create a dataset file
  pa get     DATA [IDS] [--where k=v] [--fields a,b] [--count-by FIELD]
  pa add     DATA --json '[{...}]' | --file F     add or replace records by id
  pa set     DATA IDS k=v ... [--where k=v]       change fields on records
  pa render  SPEC [--data DATA] --out HTML        draw a view as one HTML file
  pa refresh DATA                                 redraw every view of a dataset
  pa check   SCENARIO_DIR                         validate a scenario folder
  pa preview SCENARIO_DIR --out HTML              standalone demo, no agent needed

A dataset is one JSON file: {"dataset", "title", "updated", "records": [...]}.
Every record has "id" and "type"; "parent" nests it; "status", "stage",
"locked" and "stale" are the shared state fields. `render` remembers each view
in the dataset, so `set` and `add` redraw them: whoever changes the data never
has to think about the page. Later the same commands can talk to a service.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as _dt
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterator

KIT_DIR = Path(__file__).resolve().parent.parent / "kit"
LAYOUTS = {"tree-table", "board", "detail", "summary", "form"}
STATUSES = ["queued", "working", "needs-you", "ready", "reviewed", "returned", "failed", "draft"]
#: Fields whose change does not make derived records stale.
STATE_FIELDS = {"status", "stage", "locked", "stale", "updated", "note", "return_note", "question", "reviewed_by", "reviewed_at"}


STATE_SUFFIXES = ("_status", "_question", "_note", "_by", "_at")


def _is_state(key: str) -> bool:
    """State is about the work on a record, not what the record says."""
    return key in STATE_FIELDS or key.endswith(STATE_SUFFIXES)


class PaError(Exception):
    """A problem to report to the caller in one line."""


# ---------------------------------------------------------------- files


def _now() -> str:
    return _dt.datetime.now().astimezone().replace(microsecond=0).isoformat()


@contextlib.contextmanager
def _locked(path: Path) -> Iterator[None]:
    """Hold an exclusive lock for `path` so parallel agents cannot interleave writes."""
    key = hashlib.sha1(str(path.resolve()).encode()).hexdigest()[:16]
    lock_path = Path(tempfile.gettempdir()) / f"pa-{key}.lock"
    with open(lock_path, "w") as handle:
        try:
            import fcntl

            fcntl.flock(handle, fcntl.LOCK_EX)
        except ImportError:  # not POSIX: best effort
            pass
        yield


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise PaError(f"{path} does not exist") from None
    except json.JSONDecodeError as err:
        raise PaError(f"{path} is not valid JSON: {err}") from None


def _write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _load(path: Path) -> dict[str, Any]:
    data = _read_json(path)
    if not isinstance(data, dict) or not isinstance(data.get("records"), list):
        raise PaError(f"{path} is not a dataset (expected an object with a records list)")
    return data


def _save(path: Path, data: dict[str, Any]) -> None:
    data["updated"] = _now()
    _write_atomic(path, json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    if data.get("flow"):
        _write_flow(data)


# ---------------------------------------------------------------- workflow progress

FLOW_DIR = "progress"


def _flow_counts(data: dict[str, Any], count: dict[str, Any] | None) -> dict[str, Any] | None:
    """How many of the workflow's items are done, e.g. 12 of 20 requirements reviewed."""
    if not count:
        return None
    field = count.get("field", "status")
    done_values = [count["done"]] if isinstance(count.get("done"), str) else list(count.get("done") or ["reviewed"])
    items = [r for r in data.get("records", []) if _matches(r, count.get("records") or {})]
    by: dict[str, int] = {}
    for record in items:
        key = str(record.get(field) or "none")
        by[key] = by.get(key, 0) + 1
    return {
        "label": count.get("label", "reviewed"),
        "noun": count.get("noun", "items"),
        "done": sum(n for k, n in by.items() if k in done_values),
        "total": len(items),
        "waiting": by.get("needs-you", 0),
    }


def _write_flow(data: dict[str, Any]) -> None:
    """Write the small file the Session panel reads to draw the workflow card."""
    flow = data["flow"]
    out = {
        "workflow": flow.get("workflow", ""),
        "scenario": flow.get("scenario", ""),
        "subject": data.get("title", ""),
        "steps": flow.get("steps", []),
        "current": flow.get("current", 1),
        "note": flow.get("note", ""),
        "counts": _flow_counts(data, flow.get("count")),
        "participants": flow.get("participants"),
        "updated": _now(),
    }
    _write_atomic(Path(flow["file"]), json.dumps(out, indent=1, ensure_ascii=False) + "\n")


def cmd_flow(args: argparse.Namespace) -> None:
    path = Path(args.data)
    with _locked(path):
        data = _load(path)
        flow = data.get("flow") or {}
        if args.scenario:
            manifest = _read_json(Path(args.scenario) / "scenario.json")
            steps = manifest.get("steps") or []
            if not steps:
                raise PaError(f"{args.scenario}/scenario.json has no steps")
            flow.update({
                "workflow": manifest.get("title", ""), "scenario": manifest.get("scenario", ""),
                "steps": steps, "count": manifest.get("progress"), "participants": manifest.get("participants"),
                "file": f"{FLOW_DIR}/{path.stem}--{manifest.get('scenario', 'flow')}.json",
            })
            flow.setdefault("current", 1)
        if not flow.get("steps"):
            raise PaError("no workflow on this dataset yet; pass --scenario <scenario folder> once")
        total = len(flow["steps"])
        if args.done:
            flow["current"] = total + 1
        elif args.step is not None:
            step = args.step
            if step.isdigit():
                number = int(step)
            else:
                found = [i for i, label in enumerate(flow["steps"], 1) if step.lower() in label.lower()]
                if len(found) != 1:
                    raise PaError(f"no single step matches {step!r}; steps: {', '.join(flow['steps'])}")
                number = found[0]
            if not 1 <= number <= total:
                raise PaError(f"step must be 1 to {total}")
            flow["current"] = number
        if args.note is not None:
            flow["note"] = args.note
        elif args.step is not None or args.done:
            flow["note"] = ""
        data["flow"] = flow
        _save(path, data)
    where = "done" if flow["current"] > total else f"step {flow['current']} of {total}: {flow['steps'][flow['current'] - 1]}"
    print(f"{flow['workflow']}: {where}")


# ---------------------------------------------------------------- values


def _value(raw: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _pairs(items: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for item in items:
        if "=" not in item:
            raise PaError(f"expected key=value, got {item!r}")
        key, raw = item.split("=", 1)
        out[key.strip()] = _value(raw)
    return out


def _matches(record: dict[str, Any], where: dict[str, Any]) -> bool:
    for key, want in where.items():
        wants = want if isinstance(want, list) else [want]
        have = record.get(key)
        if want in ("", None):  # "field=" means: not set
            if have not in ("", None):
                return False
        elif have not in wants:
            return False
    return True


def _select(data: dict[str, Any], ids: str | None, where: list[str]) -> list[dict[str, Any]]:
    records = data["records"]
    if ids:
        wanted = [part.strip() for part in ids.split(",") if part.strip()]
        by_id = {r.get("id"): r for r in records}
        missing = [i for i in wanted if i not in by_id]
        if missing:
            raise PaError(f"no record with id {', '.join(missing)}")
        records = [by_id[i] for i in wanted]
    if where:
        cond = _pairs(where)
        records = [r for r in records if _matches(r, cond)]
    return records


def _next_id(data: dict[str, Any], rtype: str) -> str:
    prefix = (rtype[:1] or "x").upper()
    used = [r.get("id", "") for r in data["records"]]
    nums = [int(m.group(1)) for i in used if (m := re.fullmatch(rf"{prefix}-(\d+)", str(i)))]
    return f"{prefix}-{(max(nums) + 1 if nums else 1):02d}"


# ---------------------------------------------------------------- rendering


def _embed(obj: Any) -> str:
    """JSON that is safe inside a <script> element."""
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/").replace("<!--", "<\\!--")


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _public(data: dict[str, Any]) -> dict[str, Any]:
    public = {k: v for k, v in data.items() if k not in ("views", "flow")}
    if "participants" not in public:
        # Views name who made a record with `"as": "who"`; give them the roster.
        roster = _participants(_roster_dir())
        if roster:
            public["participants"] = {k: _card(v) for k, v in roster.items()}
    return public


# ------------------------------------------------------------- participants

PARTICIPANTS_DIR = "participants"
PARTICIPANT_KINDS = ("agent", "person")
PARTICIPANT_BACKINGS = ("session", "script")
_CARD_KEYS = ("name", "kind", "role", "initials", "stand_in")


def _roster_dir(explicit: str | None = None) -> Path:
    """The one roster: `participants/` in the workspace, or the copy that ships beside the skills."""
    if explicit:
        return Path(explicit)
    here = Path.cwd() / PARTICIPANTS_DIR
    if here.is_dir():
        return here
    return KIT_DIR.parent.parent.parent / "workspace" / PARTICIPANTS_DIR


def _eligible(manifest: dict[str, Any], roster: dict[str, dict[str, Any]], where: str) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """The part of the roster a scenario names in `participants`, and what it names that is missing."""
    wanted = manifest.get("participants") or []
    if not isinstance(wanted, list):
        return {}, [f"{where}: participants must be a list of ids from the roster"]
    missing = [f"{where}: participant {pid!r} is not in the roster" for pid in wanted if pid not in roster]
    return {pid: roster[pid] for pid in wanted if pid in roster}, missing


def _participant(path: Path) -> dict[str, Any]:
    """Read one participant file: `key: value` lines between `---` lines, then the brief."""
    text = path.read_text(encoding="utf-8")
    meta: dict[str, Any] = {}
    body = text
    if text.startswith("---"):
        head, _, body = text[3:].partition("\n---")
        for line in head.splitlines():
            key, sep, raw = line.partition(":")
            if sep and key.strip():
                meta[key.strip()] = _value(raw.strip().strip('"'))
    meta["id"] = path.stem
    meta.setdefault("name", path.stem.replace("-", " ").title())
    meta.setdefault("kind", "agent")
    meta.setdefault("backing", "session")
    if not meta.get("initials"):
        meta["initials"] = "".join(w[0] for w in str(meta["name"]).split()[:2]).upper()
    meta["stand_in"] = bool(meta.get("stand_in", meta["kind"] == "person"))
    meta["brief"] = body.strip()
    return meta


def _participants(folder: Path) -> dict[str, dict[str, Any]]:
    if not folder.is_dir():
        return {}
    return {p.stem: _participant(p) for p in sorted(folder.glob("*.md")) if not p.name.startswith(("_", "README"))}


def _card(person: dict[str, Any]) -> dict[str, Any]:
    return {k: person[k] for k in _CARD_KEYS if k in person}


def _check_participants(roster: dict[str, dict[str, Any]]) -> list[str]:
    problems = []
    for pid, person in roster.items():
        where = f"{PARTICIPANTS_DIR}/{pid}.md"
        if not re.fullmatch(r"[a-z][a-z0-9-]{1,40}", pid):
            problems.append(f"{where}: the file name must be lower-case words joined by hyphens")
        if person["kind"] not in PARTICIPANT_KINDS:
            problems.append(f"{where}: kind must be one of {', '.join(PARTICIPANT_KINDS)}")
        if person["backing"] not in PARTICIPANT_BACKINGS:
            problems.append(f"{where}: backing must be one of {', '.join(PARTICIPANT_BACKINGS)}")
        if person["kind"] == "person" and not person["stand_in"]:
            problems.append(f"{where}: a person played by an agent must keep stand_in: true")
        if not person.get("role"):
            problems.append(f"{where}: missing role")
        if person["backing"] == "script" and not re.search(r"^## Script\s*$", person["brief"], re.M):
            problems.append(f"{where}: backing is script, so the file needs a '## Script' section with '### <question>' entries")
        if not person["brief"]:
            problems.append(f"{where}: the brief below the header is empty")
    return problems


def turn_header(person: dict[str, Any], session: str | None = None) -> str:
    """The opening lines of a ```participant block for this participant."""
    lines = [f"name: {person['name']}", f"kind: {person['kind']}", f"role: {person.get('role', '')}"]
    if person["stand_in"]:
        lines.append("stand_in: true")
    if session:
        lines.append(f"session: {session}")
    return "\n".join(lines) + "\n---"


OPENING = """You are joining a conversation as {name} ({role}). This is a background session: the
product manager is talking with their agent, Aviator, in another session, and Aviator
has called you in. Aviator passes your replies on word for word, shown under your name.
{standin}
## Who you are

{brief}

## How this works

- Stay in character as {name} for the whole session. Speak in the first person.
- Each reply is one turn in someone else's chat: a few short paragraphs at most, plain
  text, no headings, no code fences.
- Work in this folder. Read what you are pointed at. Never change files in `context/`.
- When you have several structured items (findings, options, risks), do not list them
  in your reply. Add them to the dataset Aviator names with the `pa` command it gives
  you, and set `by` to `{id}` on every record so they show as yours. Then say how many
  you added and what matters most.
- Do not open anything in the viewer and do not start sessions of your own.
- Ask the product manager at most one question per reply, as the last line.
- When you have nothing more to add, end your reply with a last line that starts with
  `DONE:` and sums up your contribution in one sentence.

## What you are asked

{ask}
"""


def opening_message(person: dict[str, Any], ask: str) -> str:
    standin = ""
    if person["stand_in"]:
        standin = (
            f"\nYou are standing in for a real person. Answer as {person['name']} would, from the notes below. "
            "Never claim to have spoken to them or to commit them to anything; say \"I would\" rather than \"we will\".\n"
        )
    return OPENING.format(name=person["name"], role=person.get("role", ""), id=person["id"], brief=person["brief"],
                          standin=standin, ask=ask or "Introduce yourself in one sentence and wait.")


def cmd_who(args: argparse.Namespace) -> None:
    folder = _roster_dir(args.dir)
    roster = _participants(folder)
    if not roster:
        raise PaError(f"no participant files in {folder}/")
    if args.scenario:
        roster, missing = _eligible(_read_json(Path(args.scenario) / "scenario.json"), roster, "scenario.json")
        if missing:
            raise PaError("; ".join(missing))
        if not roster:
            raise PaError("this scenario names no participants")
    if args.check:
        problems = _check_participants(roster)
        if problems:
            raise PaError("; ".join(problems))
        print(f"{len(roster)} participants: ok")
        return
    if not args.id:
        if args.json:
            print(json.dumps([{k: v for k, v in p.items() if k != "brief"} for p in roster.values()], indent=1))
            return
        for pid, person in roster.items():
            tag = " (stand-in)" if person["stand_in"] else ""
            print(f"{pid}: {person['name']}{tag}, {person['kind']}, {person.get('role', '')}. Backed by a {person['backing']}.")
            if person.get("call_for"):
                print(f"    call for: {person['call_for']}")
        return
    person = roster.get(args.id)
    if person is None:
        wanted = args.id.lower()
        found = [p for p in roster.values() if wanted in str(p["name"]).lower() or wanted in str(p.get("role", "")).lower()]
        if len(found) != 1:
            raise PaError(f"no single participant matches {args.id!r}; ids: {', '.join(roster)}")
        person = found[0]
    if args.header:
        print(turn_header(person, args.session))
        return
    if args.opening:
        print(opening_message(person, args.ask or ""))
        return
    print(json.dumps(person, indent=1, ensure_ascii=False))


def page(spec: dict[str, Any], data: dict[str, Any], host: str = "canvas") -> str:
    """Return one self-contained HTML page for `spec` over `data`."""
    css = (KIT_DIR / "pa-kit.css").read_text(encoding="utf-8")
    js = (KIT_DIR / "pa-kit.js").read_text(encoding="utf-8")
    title = re.sub(r"\{dataset\.(\w+)\}", lambda m: str(data.get(m.group(1), "")), str(spec.get("title", "View")))
    description = spec.get("description") or f"{spec.get('layout', 'view')} view made with the view kit"
    return (
        f'<!doctype html>\n<html lang="en" data-host="{_escape(host)}">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{_escape(title)}</title>\n"
        f'<meta name="description" content="{_escape(str(description))}">\n'
        '<meta name="generator" content="pa view-kit">\n'
        f"<style>\n{css}</style>\n</head>\n<body>\n"
        '<div id="pa-app"></div>\n'
        f'<script type="application/json" id="pa-spec">{_embed(spec)}</script>\n'
        f'<script type="application/json" id="pa-data">{_embed(_public(data))}</script>\n'
        f"<script>\n{js}</script>\n</body>\n</html>\n"
    )


def _check_spec(spec: Any, where: str) -> list[str]:
    problems: list[str] = []
    if not isinstance(spec, dict):
        return [f"{where}: a view spec must be a JSON object"]
    layout = spec.get("layout")
    if layout not in LAYOUTS:
        problems.append(f"{where}: layout must be one of {', '.join(sorted(LAYOUTS))} (got {layout!r})")
    if not spec.get("view"):
        problems.append(f"{where}: needs a short 'view' name")
    if not spec.get("title"):
        problems.append(f"{where}: needs a 'title'")
    seen: set[str] = set()
    for action in spec.get("actions", []):
        aid = action.get("id")
        if not aid:
            problems.append(f"{where}: every action needs an 'id'")
        elif aid in seen:
            problems.append(f"{where}: action id {aid!r} is used twice")
        seen.add(aid)
        if not (action.get("prompt") or action.get("set") or action.get("ask")):
            problems.append(f"{where}: action {aid!r} does nothing (give it 'prompt' or 'set')")
    if layout == "form" and not spec.get("fields"):
        problems.append(f"{where}: a form needs 'fields'")
    if layout == "board" and not isinstance(spec.get("lanes", {}), dict):
        problems.append(f"{where}: 'lanes' must be an object like {{\"field\": \"status\"}}")
    text = json.dumps(spec)
    if re.search(r"https?://", text):
        problems.append(f"{where}: contains a web address; views must work offline")
    return problems


def _render_views(path: Path, data: dict[str, Any]) -> list[str]:
    written = []
    for view in data.get("views", []):
        out = Path(view["out"])
        if not out.is_absolute():
            out = path.parent / out if view.get("relative_to") == "data" else Path.cwd() / out
        spec = dict(view["spec"])
        _write_atomic(out, page(spec, data, view.get("host", "canvas")))
        written.append(str(view["out"]))
    return written


# ---------------------------------------------------------------- commands


def cmd_init(args: argparse.Namespace) -> None:
    path = Path(args.data)
    if path.exists() and not args.force:
        raise PaError(f"{path} already exists (use --force to replace it)")
    if args.source:
        data = _load(Path(args.source))
        data.pop("views", None)
    else:
        data = {"records": []}
    data["dataset"] = args.name or path.stem
    if args.title:
        data["title"] = args.title
    data.update(_pairs(args.meta))
    with _locked(path):
        _save(path, data)
    print(f"created {path} with {len(data['records'])} records")


def cmd_get(args: argparse.Namespace) -> None:
    data = _load(Path(args.data))
    records = _select(data, args.ids, args.where)
    if args.count_by:
        counts: dict[str, int] = {}
        for record in records:
            key = str(record.get(args.count_by))
            counts[key] = counts.get(key, 0) + 1
        print(json.dumps(counts))
        return
    fields = [f.strip() for f in args.fields.split(",")] if args.fields else None
    for record in records:
        shown = {k: record[k] for k in fields if k in record} if fields else record
        if fields and "id" not in shown:
            shown = {"id": record.get("id"), **shown}
        print(json.dumps(shown, ensure_ascii=False))
    if not records:
        print("no matching records", file=sys.stderr)


def _mark_stale(data: dict[str, Any], changed_ids: set[str]) -> list[str]:
    """Flag records built from a changed record so someone looks at them again."""
    flagged = []
    for record in data["records"]:
        sources = record.get("derived_from") or []
        if isinstance(sources, str):
            sources = [sources]
        if changed_ids.intersection(sources) and record.get("id") not in changed_ids and not record.get("stale"):
            record["stale"] = True
            flagged.append(record["id"])
    return flagged


def cmd_add(args: argparse.Namespace) -> None:
    if args.json:
        incoming = _value(args.json)
    elif args.file:
        incoming = _read_json(Path(args.file))
    else:
        incoming = json.loads(sys.stdin.read())
    if isinstance(incoming, dict) and "records" in incoming:
        incoming = incoming["records"]
    if isinstance(incoming, dict):
        incoming = [incoming]
    if not isinstance(incoming, list) or not all(isinstance(r, dict) for r in incoming):
        raise PaError("expected one record object or a list of them")
    path = Path(args.data)
    with _locked(path):
        data = _load(path)
        by_id = {r.get("id"): i for i, r in enumerate(data["records"])}
        added = replaced = 0
        ids: list[str] = []
        for record in incoming:
            if not record.get("type"):
                raise PaError(f"record {record.get('id', '(no id)')} has no type")
            if not record.get("id"):
                record["id"] = _next_id(data, record["type"])
            record.setdefault("updated", _now())
            ids.append(record["id"])
            if record["id"] in by_id:
                merged = {**data["records"][by_id[record["id"]]], **record}
                if "stale" not in record:  # rewritten from its sources, so current again
                    merged.pop("stale", None)
                data["records"][by_id[record["id"]]] = merged
                replaced += 1
            else:
                by_id[record["id"]] = len(data["records"])
                data["records"].append(record)
                added += 1
        _save(path, data)
        views = _render_views(path, data)
    print(f"added {added}, updated {replaced} ({', '.join(ids[:40])})" + (f"; redrew {', '.join(views)}" if views else ""))


def cmd_set(args: argparse.Namespace) -> None:
    ids = args.ids
    pairs = list(args.pairs)
    if ids and "=" in ids:  # no ids given, first positional is a pair
        pairs.insert(0, ids)
        ids = None
    changes = _pairs(pairs)
    if args.json:
        extra = _value(args.json)
        if not isinstance(extra, dict):
            raise PaError("--json must be an object of fields")
        changes.update(extra)
    if not changes:
        raise PaError("nothing to set (give key=value pairs)")
    if not ids and not args.where:
        raise PaError("say which records: ids like R-01,R-02 or --where type=requirement")
    path = Path(args.data)
    with _locked(path):
        data = _load(path)
        records = _select(data, ids, args.where)
        content_changed: set[str] = set()
        for record in records:
            for key, value in changes.items():
                if record.get(key) != value and not _is_state(key):
                    content_changed.add(record["id"])
                if value is None:
                    record.pop(key, None)
                else:
                    record[key] = value
            record["updated"] = _now()
        flagged = [] if args.no_stale else _mark_stale(data, content_changed)
        _save(path, data)
        views = _render_views(path, data)
    message = f"updated {len(records)} record{'s' if len(records) != 1 else ''}"
    if flagged:
        message += f"; marked stale: {', '.join(flagged)}"
    if views:
        message += f"; redrew {', '.join(views)}"
    print(message)


def cmd_render(args: argparse.Namespace) -> None:
    spec_path = Path(args.spec)
    spec = _read_json(spec_path)
    problems = _check_spec(spec, spec_path.name)
    if problems:
        raise PaError("; ".join(problems))
    if args.record:
        spec["record"] = args.record
    if args.title:
        spec["title"] = args.title
    out = Path(args.out)
    if args.data:
        path = Path(args.data)
        spec.setdefault("dataset", args.data)
        with _locked(path):
            data = _load(path)
            if not args.no_register:
                views = [v for v in data.get("views", []) if v.get("out") != args.out]
                views.append({"out": args.out, "host": args.host, "spec": spec})
                data["views"] = views
                _write_atomic(path, json.dumps(data, indent=1, ensure_ascii=False) + "\n")
            _write_atomic(out, page(spec, data, args.host))
    else:
        _write_atomic(out, page(spec, {"records": []}, args.host))
    print(f"wrote {out}")


def cmd_refresh(args: argparse.Namespace) -> None:
    path = Path(args.data)
    with _locked(path):
        data = _load(path)
        views = _render_views(path, data)
    print(f"redrew {', '.join(views)}" if views else "this dataset has no views yet")


def _check_records(records: list[dict[str, Any]], schemas: dict[str, Any], where: str) -> list[str]:
    problems: list[str] = []
    ids: set[str] = set()
    for record in records:
        rid = record.get("id")
        label = f"{where} {rid or '(no id)'}"
        if not rid:
            problems.append(f"{label}: missing id")
        elif rid in ids:
            problems.append(f"{label}: id used twice")
        ids.add(rid)
        schema = schemas.get(record.get("type", ""))
        if schema is None:
            problems.append(f"{label}: type {record.get('type')!r} is not in the schemas")
            continue
        for field in schema.get("required", []):
            if record.get(field) in (None, ""):
                problems.append(f"{label}: missing {field}")
        for field, rule in schema.get("fields", {}).items():
            if field not in record or record[field] is None:
                continue
            value = record[field]
            if "enum" in rule and value not in rule["enum"]:
                problems.append(f"{label}: {field}={value!r} is not one of {rule['enum']}")
            kinds = {"string": str, "number": (int, float), "boolean": bool, "array": list, "object": dict}
            if rule.get("type") in kinds and not isinstance(value, kinds[rule["type"]]):
                problems.append(f"{label}: {field} should be a {rule['type']}")
    for record in records:
        if record.get("parent") and record["parent"] not in ids:
            problems.append(f"{where} {record.get('id')}: parent {record['parent']} does not exist")
    return problems


def _scenario(folder: Path) -> tuple[dict[str, Any], list[str]]:
    manifest_path = folder / "scenario.json"
    manifest = _read_json(manifest_path)
    problems: list[str] = []
    for key in ("scenario", "title", "summary", "views"):
        if not manifest.get(key):
            problems.append(f"scenario.json: missing {key}")
    if not (folder / "SKILL.md").is_file():
        problems.append("SKILL.md is missing")
    return manifest, problems


# ------------------------------------------------------------------ scripts
#
# A preview script is a markdown file that reads like a screenplay. See
# references/script.md. `_read_script` turns it into the steps the player runs.

_SPEECH = re.compile(r"^\*\*(.+?):\*\*\s*(.*)$")
_PAIR = re.compile(r'(\w+)\s*=\s*("(?:[^"\\]|\\.)*"|[^,]+)')
_QUOTED = r'"((?:[^"\\]|\\.)*)"'


def _ids(text: str) -> list[str]:
    return [part.strip() for part in text.split(",") if part.strip()]


def _fields(text: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, raw in _PAIR.findall(text):
        raw = raw.strip()
        out[key] = None if raw in ("null", "none", "") else _value(raw)
    return out


def _who(name: str, roster: dict[str, dict[str, Any]], where: str) -> str:
    wanted = name.strip().lower()
    if wanted in ("aviator", "agent"):
        return "aviator"
    for pid, person in roster.items():
        if wanted in (pid, str(person["name"]).lower()):
            return pid
    known = ", ".join(["You", "Aviator"] + [str(p["name"]) for p in roster.values()])
    raise PaError(f"{where}: nobody called {name.strip()!r} is in this scenario. Known: {known}")


def _directive(text: str, roster: dict[str, dict[str, Any]], where: str, state: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Return ("step" | "modifier" | "start", fields) for one [bracketed] line."""
    low = text.lower()

    def tail(prefix: str) -> str:
        return text[len(prefix):].strip()

    if low == "wait":
        return "modifier", {"await": "any"}
    if low == "wait for submit":
        return "modifier", {"await": "submit"}
    if low.startswith("hint:"):
        return "modifier", {"hint": tail("hint:")}
    if low.startswith("task:"):
        value = tail("task:")
        return "modifier", {"task": None if value.lower() in ("none", "") else value}
    if low.startswith("start:"):
        rest = tail("start:")
        if rest.lower().startswith("hide "):
            return "start", {"hide": _ids(rest[5:])}
        m = re.fullmatch(r"set (.+?) where (.+)", rest, re.I)
        if m:
            return "start", {"set": {"fields": _fields(m.group(1)), "where": _fields(m.group(2))}}
        raise PaError(f"{where}: use [start: hide <types>] or [start: set k=v where k=v]")
    m = re.fullmatch(rf"open (\S+)(?: as {_QUOTED})?", text, re.I)
    if m:
        state["doc"] = m.group(1)
        return "step", {"doc": m.group(1), **({"title": m.group(2)} if m.group(2) else {})}
    m = re.fullmatch(rf"show (\S+)( empty)?(?: as {_QUOTED})?(?: by (.+))?", text, re.I)
    if m:
        step: dict[str, Any] = {"canvas": m.group(1)}
        if m.group(2):
            step["data"] = "empty"
        if m.group(3):
            step["title"] = m.group(3)
        if m.group(4):
            step["from"] = _who(m.group(4), roster, where)
        return "step", step
    m = re.fullmatch(r"widget (\S+)(?: for (\S+))?(?: from (.+))?", text, re.I)
    if m:
        step = {"widget": m.group(1)}
        if m.group(2):
            step["record"] = m.group(2)
        if m.group(3):
            step["from"] = _who(m.group(3), roster, where)
        return "step", step
    if low.startswith("reveal "):
        return "step", {"reveal": _ids(tail("reveal "))}
    if low.startswith("restore "):
        return "step", {"restore": _ids(tail("restore "))}
    if low == "apply edits":
        return "step", {"apply": "edits"}
    m = re.fullmatch(rf"tab {_QUOTED}", text, re.I)
    if m:
        return "step", {"tab": m.group(1)}
    m = re.fullmatch(r"status (.+?):\s*(\S+)", text, re.I)
    if m:
        return "step", {"status": {"ids": _ids(m.group(1)), "to": m.group(2)}}
    m = re.fullmatch(r"set (\S+?):\s*(.+)", text, re.I)
    if m:
        return "step", {"patch": [{"id": m.group(1), **_fields(m.group(2))}]}
    m = re.fullmatch(rf"comment by (.+?) on {_QUOTED}:\s*(.+)", text, re.I)
    if m:
        if not state.get("doc"):
            raise PaError(f"{where}: open a document before commenting on it")
        return "step", {"comment": {"doc": state["doc"], "on": m.group(2), "by": _who(m.group(1), roster, where), "text": m.group(3)}}
    m = re.fullmatch(rf"resolve comment on {_QUOTED}", text, re.I)
    if m:
        return "step", {"comment": {"doc": state.get("doc"), "resolve": m.group(1)}}
    m = re.fullmatch(r"call (.+?)(?::\s*(.+))?", text, re.I)
    if m:
        who = _who(m.group(1), roster, where)
        if who == "aviator":
            raise PaError(f"{where}: Aviator is the host and cannot be called")
        return "step", {"call": who, "by": "aviator", **({"ask": m.group(2)} if m.group(2) else {})}
    m = re.fullmatch(r"(.+?) leaves(?::\s*(.+))?", text, re.I)
    if m:
        _who(m.group(1), roster, where)
        return "step", {"end_call": m.group(2) or True}
    raise PaError(f"{where}: I do not know the direction [{text}]. See view-kit/references/script.md")


def parse_script(text: str, roster: dict[str, dict[str, Any]], name: str = "script.md") -> dict[str, Any]:
    script: dict[str, Any] = {"steps": []}
    steps: list[dict[str, Any]] = script["steps"]
    intro: list[str] = []
    state: dict[str, Any] = {}
    speech: dict[str, Any] | None = None  # the step whose text may continue on the next line
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        where = f"{name} line {number}"
        if not line:
            speech = None
            continue
        if line.startswith("<!--") or line.startswith(">"):
            continue
        if line.startswith("# ") and "title" not in script:
            script["title"] = line[2:].strip()
            continue
        if line.startswith("#"):
            speech = None
            continue
        if line.startswith("[") and line.endswith("]"):
            speech = None
            kind, fields = _directive(line[1:-1].strip(), roster, where, state)
            if kind == "start":
                script.setdefault("start", {}).update(fields)
            elif kind == "modifier":
                if not steps:
                    raise PaError(f"{where}: [{line[1:-1]}] must follow a step")
                steps[-1].update(fields)
            else:
                steps.append(fields)
            continue
        m = _SPEECH.match(line)
        if m:
            speaker, said = m.group(1).strip(), m.group(2)
            if speaker.lower() in ("you", "pm"):
                speech = {"pm": said}
            else:
                who = _who(speaker, roster, where)
                speech = {"agent": said} if who == "aviator" else {"from": who, "says": said}
            steps.append(speech)
            continue
        if speech is not None:
            key = "pm" if "pm" in speech else "agent" if "agent" in speech else "says"
            speech[key] += "\n" + line
        elif not steps:
            intro.append(line)
        # Any other loose text after the first step is a note to whoever edits the script.
    if intro:
        script["intro"] = " ".join(intro)
    if not steps:
        raise PaError(f"{name}: no steps")
    return script


def _read_script(path: Path, roster: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if path.suffix == ".json":
        return _read_json(path)
    return parse_script(path.read_text(encoding="utf-8"), roster, path.name)


def cmd_check(args: argparse.Namespace) -> None:
    folder = Path(args.scenario)
    manifest, problems = _scenario(folder)
    actions: set[str] = set()
    for name, rel in (manifest.get("views") or {}).items():
        path = folder / rel
        if not path.is_file():
            problems.append(f"view {name}: {rel} does not exist")
            continue
        spec = _read_json(path)
        problems += _check_spec(spec, rel)
        actions.update(a.get("id", "") for a in spec.get("actions", []) if a.get("prompt"))
    schemas: dict[str, Any] = {}
    if manifest.get("schemas"):
        schemas = _read_json(folder / manifest["schemas"])
    fixture = (manifest.get("fixtures") or {}).get("dataset")
    if fixture:
        data = _load(folder / fixture)
        if schemas:
            problems += _check_records(data["records"], schemas, fixture)
    skill_text = (folder / "SKILL.md").read_text(encoding="utf-8") if (folder / "SKILL.md").is_file() else ""
    for action in sorted(actions):
        if action and action not in skill_text:
            problems.append(f"SKILL.md never mentions the action {action!r} that a view can send")
    whole = _participants(_roster_dir(getattr(args, "participants", None)))
    eligible, missing = _eligible(manifest, whole, "scenario.json")
    problems += missing + _check_participants(eligible)
    script_rel = manifest.get("script")
    if script_rel and (folder / script_rel).is_file():
        try:
            script = _read_script(folder / script_rel, eligible)
        except PaError as err:
            problems.append(str(err))
        else:
            views = manifest.get("views") or {}
            for number, step in enumerate(script.get("steps", []), 1):
                for key in ("canvas", "widget"):
                    if step.get(key) and step[key] not in views:
                        problems.append(f"{script_rel}: step {number} shows the view {step[key]!r}, which scenario.json does not list")
    for path in folder.rglob("*"):
        if path.suffix in {".json", ".html"} and path.is_file() and re.search(r"https?://", path.read_text(encoding="utf-8")):
            problems.append(f"{path.relative_to(folder)}: contains a web address; scenarios must work offline")
    if problems:
        print(f"{len(problems)} problem{'s' if len(problems) != 1 else ''} in {folder}:")
        for problem in problems:
            print(f"  - {problem}")
        raise SystemExit(1)
    print(f"{folder.name}: ok ({len(manifest.get('views') or {})} views, {len(actions)} actions)")


def cmd_preview(args: argparse.Namespace) -> None:
    folder = Path(args.scenario)
    manifest, problems = _scenario(folder)
    if problems:
        raise PaError("; ".join(problems))
    whole = _participants(_roster_dir(args.participants))
    eligible, missing = _eligible(manifest, whole, "scenario.json")
    if missing:
        raise PaError("; ".join(missing))
    script_rel = manifest.get("script") or "script.md"
    script = _read_script(folder / script_rel, eligible)
    specs = {name: _read_json(folder / rel) for name, rel in (manifest.get("views") or {}).items()}
    fixture = (manifest.get("fixtures") or {}).get("dataset")
    data = _public(_load(folder / fixture)) if fixture else {"records": []}
    roster = {k: _card(v) for k, v in eligible.items()}
    if roster:
        data["participants"] = roster
    docs = {}
    for name, rel in (manifest.get("fixtures") or {}).items():
        if str(rel).endswith(".md"):
            docs[name] = (folder / rel).read_text(encoding="utf-8")
    template = (KIT_DIR / "harness.html").read_text(encoding="utf-8")
    payload = {
        "manifest": manifest,
        "script": script,
        "specs": specs,
        "data": data,
        "docs": docs,
        "participants": roster,
        "css": (KIT_DIR / "pa-kit.css").read_text(encoding="utf-8"),
        "js": (KIT_DIR / "pa-kit.js").read_text(encoding="utf-8"),
    }
    html = template.replace("/*__PAYLOAD__*/", _embed(payload)).replace("__TITLE__", _escape(str(manifest.get("title", folder.name))))
    _write_atomic(Path(args.out), html)
    print(f"wrote {args.out}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pa", description="Product Aviator data and view command")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("flow", help="record which step of a workflow the work is at, for the Session panel")
    p.add_argument("data")
    p.add_argument("--scenario", help="the scenario folder, the first time, to take its steps")
    p.add_argument("--step", help="a step number, or part of its name")
    p.add_argument("--done", action="store_true", help="the workflow is finished")
    p.add_argument("--note", help="one line on what is happening in this step")
    p.set_defaults(run=cmd_flow)

    p = sub.add_parser("who", help="list the participants the agent can call, or show one")
    p.add_argument("id", nargs="?", help="an id, or part of a name or role")
    p.add_argument("--dir", help="the roster folder; default participants/ in the workspace")
    p.add_argument("--scenario", help="list only the participants this scenario folder names as eligible")
    p.add_argument("--json", action="store_true")
    p.add_argument("--header", action="store_true", help="print the opening lines of a participant block")
    p.add_argument("--session", help="with --header: the id of the session speaking for them")
    p.add_argument("--check", action="store_true", help="check every participant file")
    p.add_argument("--opening", action="store_true", help="print the first message for the background session that plays them")
    p.add_argument("--ask", help="with --opening: what they are asked to do")
    p.set_defaults(run=cmd_who)

    p = sub.add_parser("init", help="create a dataset file")
    p.add_argument("data")
    p.add_argument("--title")
    p.add_argument("--name")
    p.add_argument("--from", dest="source", help="copy records from a fixture")
    p.add_argument("--meta", action="append", default=[], help="top-level key=value, e.g. source=context/prd.md")
    p.add_argument("--force", action="store_true")
    p.set_defaults(run=cmd_init)

    p = sub.add_parser("get", help="print records, one JSON object per line")
    p.add_argument("data")
    p.add_argument("ids", nargs="?")
    p.add_argument("--where", action="append", default=[])
    p.add_argument("--fields")
    p.add_argument("--count-by")
    p.set_defaults(run=cmd_get)

    p = sub.add_parser("add", help="add or replace records by id")
    p.add_argument("data")
    p.add_argument("--json")
    p.add_argument("--file")
    p.set_defaults(run=cmd_add)

    p = sub.add_parser("set", help="change fields on records")
    p.add_argument("data")
    p.add_argument("ids", nargs="?")
    p.add_argument("pairs", nargs="*")
    p.add_argument("--where", action="append", default=[])
    p.add_argument("--json")
    p.add_argument("--no-stale", action="store_true", help="do not flag derived records")
    p.set_defaults(run=cmd_set)

    p = sub.add_parser("render", help="draw a view as one HTML file")
    p.add_argument("spec")
    p.add_argument("--data")
    p.add_argument("--out", required=True)
    p.add_argument("--host", default="canvas", choices=["canvas", "chat"])
    p.add_argument("--record", help="for a detail view: the record to show")
    p.add_argument("--title")
    p.add_argument("--no-register", action="store_true", help="do not redraw this view when the data changes")
    p.set_defaults(run=cmd_render)

    p = sub.add_parser("refresh", help="redraw every view of a dataset")
    p.add_argument("data")
    p.set_defaults(run=cmd_refresh)

    p = sub.add_parser("check", help="validate a scenario folder")
    p.add_argument("scenario")
    p.add_argument("--participants", help="the roster folder; default participants/ in the workspace")
    p.set_defaults(run=cmd_check)

    p = sub.add_parser("preview", help="build a standalone demo of a scenario")
    p.add_argument("scenario")
    p.add_argument("--out", required=True)
    p.add_argument("--participants", help="the roster folder; default participants/ in the workspace")
    p.set_defaults(run=cmd_preview)

    args = parser.parse_args(argv)
    try:
        args.run(args)
    except PaError as err:
        print(f"pa: {err}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
