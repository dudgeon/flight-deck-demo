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
  pa draft   person [ID] [--name N] [--set k=v]   start or change a draft (the Hangar)
  pa publish person ID                            check it, keep the old version, make it live
  pa history person ID [--restore VERSION]        earlier versions; restore one
  pa uses    person ID                            what depends on them

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
            manifest = resolve_run(Path(args.scenario))["manifest"]
            steps = manifest.get("steps") or []
            if not steps:
                raise PaError(f"{args.scenario}: the workflow has no steps")
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
    if isinstance(meta.get("skills"), str):
        meta["skills"] = [s.strip() for s in meta["skills"].split(",") if s.strip()]
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
{skills}
## How this works

{conversation}- Stay in character as {name} for the whole session. Speak in the first person.
- Each reply is one turn in someone else's chat: a few short paragraphs at most, plain
  text, no headings, no code fences.
- Work in this folder. Read what you are pointed at. Never change files in `context/`.
- When you have several structured items (findings, options, risks), do not list them
  in your reply. Add them to the dataset Aviator names with the `pa` command it gives
  you, and set `by` to `{id}` on every record so they show as yours. Then say how many
  you added and what matters most.
- Never edit a document yourself. Any change you want to a document is a suggestion the
  product manager accepts or rejects: `pa review suggest <doc> --by {id} --replace "exact
  text" --with "new text"` (or `--insert TEXT --after "exact text"`, or `--delete "exact
  text"`), one line at a time, because a quoted passage cannot cross lines. To comment on
  a passage, use `pa review comment <doc> --by {id} --quote "exact text" --text "..."`.
- Do not open anything in the viewer and do not start sessions of your own.
- Ask the product manager at most one question per reply, as the last line.
- When you have nothing more to add, end your reply with a last line that starts with
  `DONE:` and sums up your contribution in one sentence.

## What you are asked

{ask}
"""


def opening_message(person: dict[str, Any], ask: str, conversation: str | None = None) -> str:
    standin = ""
    if person["stand_in"]:
        standin = (
            f"\nYou are standing in for a real person. Answer as {person['name']} would, from the notes below. "
            "Never claim to have spoken to them or to commit them to anything; say \"I would\" rather than \"we will\".\n"
        )
    seen = ""
    if conversation:
        seen = (
            f"- You can see the whole conversation. It is session `{conversation}`: read it now with\n"
            f"  `sys_session_get_history` (conversation_id `{conversation}`), before anything else, and read it\n"
            "  again each time you are asked something new, because it will have moved on.\n"
        )
    skills = ""
    if person.get("skills"):
        names = ", ".join(f"`{s}`" for s in person["skills"])
        skills = (f"\n## Skills you bring\n\nUse these skills when they fit what you are asked: {names}. "
                  "Read a skill's SKILL.md before you rely on it, and answer from what it says.\n")
    return OPENING.format(name=person["name"], role=person.get("role", ""), id=person["id"], brief=person["brief"],
                          standin=standin, conversation=seen, skills=skills,
                          ask=ask or "Introduce yourself in one sentence and wait.")


def cmd_who(args: argparse.Namespace) -> None:
    folder = _roster_dir(args.dir)
    roster = _participants(folder)
    if not roster:
        raise PaError(f"no participant files in {folder}/")
    if args.scenario:
        roster, missing = _eligible(resolve_run(Path(args.scenario))["manifest"], roster, "scenario.json")
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
        print(opening_message(person, args.ask or "", args.conversation))
        return
    print(json.dumps(person, indent=1, ensure_ascii=False))


DEFAULT_APP_URL = "http://127.0.0.1:6767"


def _script_entry(person: dict[str, Any], wanted: str) -> str:
    """The text under the `###` heading in a participant's `## Script` that matches `wanted`."""
    script = re.split(r"^## Script\s*$", person["brief"], maxsplit=1, flags=re.M)
    if len(script) < 2:
        raise PaError(f"{person['id']} has no '## Script' section")
    entries = re.split(r"^### +(.+?)\s*$", script[1], flags=re.M)[1:]
    found = [(h, t.strip()) for h, t in zip(entries[::2], entries[1::2]) if wanted.lower() in h.lower()]
    if len(found) != 1:
        heads = ", ".join(repr(h) for h in entries[::2]) or "none"
        raise PaError(f"no single script entry matches {wanted!r}; entries: {heads}")
    return found[0][1]


def cmd_tell(args: argparse.Namespace) -> None:
    """Put a participant's message, or their invitation to a session, in the user's Inbox."""
    import urllib.error
    import urllib.request

    roster = _participants(_roster_dir(args.dir))
    person = roster.get(args.id)
    if person is None:
        raise PaError(f"no participant {args.id!r}; ids: {', '.join(roster) or 'none'}")
    if bool(args.says) == bool(args.entry):
        raise PaError("give what they say with --says TEXT, or --entry HEADING from their script")
    text = args.says or _script_entry(person, args.entry)
    first = re.split(r"(?<=[.!?])\s", text.strip(), maxsplit=1)[0]
    title = args.title or (first if len(first) <= 120 else first[:117].rstrip() + "...")
    payload = {
        "participant": {
            "id": person["id"],
            "name": person["name"],
            "kind": person["kind"],
            "role": str(person.get("role", "")),
            "stand_in": bool(person["stand_in"]),
        },
        "intent": "invite" if args.invite else "message",
        "session_id": args.session,
        "title": title,
        "body_md": text,
    }
    base = (args.url or os.environ.get("OMNIGENT_SLIM_URL") or DEFAULT_APP_URL).rstrip("/")
    request = urllib.request.Request(
        f"{base}/v1/slim/inbox/participant-messages",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            item = json.loads(response.read().decode("utf-8"))["item"]
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:300]
        raise PaError(f"the app refused the message ({exc.code}): {detail}") from exc
    except urllib.error.URLError as exc:
        raise PaError(f"could not reach the app at {base}: {exc.reason}") from exc
    what = "invitation" if args.invite else "message"
    print(f"{person['name']}'s {what} is in the Inbox (item {item['id']}).")


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
    facts = _pairs(args.meta)
    if "records" in facts or "views" in facts:
        raise PaError("--meta cannot replace records or views")
    if not changes and not facts:
        raise PaError("nothing to set (give key=value pairs)")
    if changes and not ids and not args.where:
        raise PaError("say which records: ids like R-01,R-02 or --where type=requirement")
    path = Path(args.data)
    with _locked(path):
        data = _load(path)
        data.update(facts)  # dataset facts such as projected="2 Apr"
        records = _select(data, ids, args.where) if changes else []
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


def _fill_title(spec: dict[str, Any], data: dict[str, Any] | None = None) -> str:
    """A one-line name for a view shown in the chat."""
    data = data or {}
    if spec.get("record"):
        for record in data.get("records", []):
            if record.get("id") == spec["record"] and record.get("title"):
                return str(record["title"])[:120]
    title = re.sub(r"\{dataset\.(\w+)\}", lambda m: str(data.get(m.group(1), "")), str(spec.get("title") or ""))
    return re.sub(r"\{[^}]*\}", "", title).strip(" :·-")[:120]


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
    if args.host == "chat":
        # Asks in chat, work in canvas: the host draws this block inline.
        title = _fill_title(spec, _load(Path(args.data)) if args.data else None)
        print(
            "To show it in the chat, put this block in your reply as it is, "
            "and do not open the file:\n\n```view\nfile: "
            + str(out)
            + (f"\ntitle: {title}" if title else "")
            + "\n```"
        )


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


# ---------------------------------------------------------- workflows and scenarios
#
# A workflow (`skills/<id>/`, or `.claude/skills/<id>/` in the workspace for one
# built in the Hangar) is a kind of work: SKILL.md, `workflow.json`, schemas
# and views. A scenario (`<workspace>/scenarios/<id>/scenario.json`) is one
# scripted run of a workflow: the cast, invented data and `script.md` (D-42).
# Older workflow folders still hold everything in one `scenario.json`; those
# are read as a workflow with a built-in scenario.

WORKFLOW_FILE = "workflow.json"
LEGACY_WORKFLOW_FILE = "scenario.json"
SCENARIO_FILE = "scenario.json"
SCENARIOS_DIR = "scenarios"
SCENARIO_PARTS = ("participants", "fixtures", "script", "facts")


def workflow_manifest_path(folder: Path) -> Path | None:
    """The workflow manifest in a folder, or None when the folder is not a workflow."""
    if (folder / WORKFLOW_FILE).is_file():
        return folder / WORKFLOW_FILE
    legacy = folder / LEGACY_WORKFLOW_FILE
    if legacy.is_file() and (folder / "SKILL.md").is_file():
        try:
            if "workflow" not in _read_json(legacy):
                return legacy
        except PaError:
            return legacy
    return None


def is_scenario_folder(folder: Path) -> bool:
    path = folder / SCENARIO_FILE
    if not path.is_file() or workflow_manifest_path(folder):
        return False
    try:
        return bool(_read_json(path).get("workflow"))
    except PaError:
        return False


def default_workspace() -> Path:
    """The workspace pa works in: the current folder when it holds a roster, else the shipped one."""
    return _roster_dir().parent


def workflow_roots(workspace: Path | None = None) -> list[Path]:
    """Where workflows live, first match wins: ones built in the Hangar, then the shipped ones."""
    workspace = workspace or default_workspace()
    roots = [workspace / ".claude" / "skills", KIT_DIR.parent.parent]
    env = os.environ.get("OMNIGENT_SLIM_SKILLS_DIR", "").strip()
    if env:
        roots.insert(1, Path(env).expanduser())
    seen: list[Path] = []
    for root in roots:
        if root.is_dir() and root.resolve() not in [s.resolve() for s in seen]:
            seen.append(root)
    return seen


def find_workflow(wid: str, workspace: Path | None = None) -> Path | None:
    for root in workflow_roots(workspace):
        folder = root / wid
        if workflow_manifest_path(folder):
            return folder
    return None


def list_workflows(workspace: Path | None = None) -> dict[str, Path]:
    """Every workflow by id; one built in the workspace hides a shipped one of the same id."""
    found: dict[str, Path] = {}
    for root in workflow_roots(workspace):
        for folder in sorted(p for p in root.iterdir() if p.is_dir()):
            if folder.name not in found and workflow_manifest_path(folder):
                found[folder.name] = folder
    return found


def list_scenarios(workspace: Path | None = None) -> dict[str, Path]:
    workspace = workspace or default_workspace()
    root = workspace / SCENARIOS_DIR
    if not root.is_dir():
        return {}
    return {p.name: p for p in sorted(root.iterdir()) if is_scenario_folder(p)}


def scenarios_of(wid: str, workspace: Path | None = None) -> list[Path]:
    """The scenarios that run a workflow, the one sharing its id first."""
    out = []
    for sid, folder in list_scenarios(workspace).items():
        if _read_json(folder / SCENARIO_FILE).get("workflow") == wid:
            out.append(folder)
    return sorted(out, key=lambda f: (f.name != wid, f.name))


def _workspace_of_scenario(folder: Path) -> Path:
    folder = folder.resolve()
    if HANGAR_DIR in folder.parts:  # a draft: .hangar/drafts/scenarios/<id>
        return Path(*folder.parts[: folder.parts.index(HANGAR_DIR)])
    return folder.parent.parent


def resolve_run(folder: Path, workspace: Path | None = None) -> dict[str, Any]:
    """Read a workflow or scenario folder as one run.

    Returns the workflow folder and manifest, the scenario folder and manifest
    (None when the workflow has no scenario), and `manifest`: the workflow
    manifest with the scenario's cast, fixtures and script laid over it.
    Paths in `views` and `schemas` are relative to `workflow_dir`; paths in
    `fixtures` and `script` to `scenario_dir`.
    """
    folder = Path(folder)
    problems: list[str] = []
    if is_scenario_folder(folder):
        scenario = _read_json(folder / SCENARIO_FILE)
        ws = workspace or _workspace_of_scenario(folder)
        wid = str(scenario.get("workflow"))
        wdir = find_workflow(wid, ws)
        if not wdir:
            raise PaError(f"{folder.name}/scenario.json: runs the workflow {wid!r}, which does not exist")
        sdir: Path | None = folder
    else:
        wdir = folder
        if not workflow_manifest_path(wdir):
            raise PaError(f"{folder} is neither a workflow folder (workflow.json) nor a scenario folder (scenario.json)")
        scenario = None
        sdir = None
    wpath = workflow_manifest_path(wdir)
    assert wpath is not None
    workflow = _read_json(wpath)
    wid = str(workflow.get("workflow") or workflow.get("scenario") or wdir.name)
    if scenario is None:
        if any(workflow.get(k) for k in ("fixtures", "script")):
            scenario, sdir = workflow, wdir  # an older folder that holds its own scenario
        else:
            ws = workspace or default_workspace()
            found = scenarios_of(wid, ws)
            if found:
                sdir = found[0]
                scenario = _read_json(sdir / SCENARIO_FILE)
    manifest = {k: v for k, v in workflow.items() if k not in ("fixtures", "script", "facts")}
    manifest["scenario"] = wid
    manifest["workflow"] = wid
    if scenario is not None and scenario is not workflow:
        for key in SCENARIO_PARTS:
            if key in scenario:
                manifest[key] = scenario[key]
        allowed = workflow.get("participants")
        if allowed:
            for pid in scenario.get("participants") or []:
                if pid not in allowed:
                    problems.append(f"{sdir.name}/scenario.json: {pid!r} is in the cast but the workflow {wid} does not call on them")
    elif scenario is workflow:
        for key in ("fixtures", "script"):
            if key in workflow:
                manifest[key] = workflow[key]
    return {
        "workflow_id": wid,
        "workflow_dir": wdir,
        "workflow_file": wpath,
        "workflow": workflow,
        "scenario_id": (scenario or {}).get("scenario") if scenario is not workflow else wid,
        "scenario_dir": sdir,
        "scenario": scenario if scenario is not workflow else None,
        "manifest": manifest,
        "problems": problems,
    }


def _scenario(folder: Path) -> tuple[dict[str, Any], list[str]]:
    """Kept for callers of the one-folder layout: the merged manifest and its problems."""
    run = resolve_run(folder)
    return run["manifest"], _workflow_problems(run) + run["problems"]


def _workflow_problems(run: dict[str, Any]) -> list[str]:
    workflow, wdir, name = run["workflow"], run["workflow_dir"], run["workflow_file"].name
    problems = []
    for key in ("title", "summary", "views"):
        if not workflow.get(key):
            problems.append(f"{name}: missing {key}")
    if not (workflow.get("workflow") or workflow.get("scenario")):
        problems.append(f"{name}: missing workflow (its id)")
    if not (wdir / "SKILL.md").is_file():
        problems.append("SKILL.md is missing")
    steps = workflow.get("steps") or []
    if steps and not 2 <= len(steps) <= 8:
        problems.append(f"{name}: a workflow has 2 to 8 steps, not {len(steps)}")
    scenario = run["scenario"]
    if scenario is not None:
        for key in ("scenario", "title", "summary", "workflow"):
            if not scenario.get(key):
                problems.append(f"{run['scenario_dir'].name}/scenario.json: missing {key}")
    return problems


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
    if low.startswith("fact "):  # dataset facts such as projected="2 Apr"
        return "step", {"fact": _fields(tail("fact "))}
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


def check_run(folder: Path, participants: str | None = None, workspace: Path | None = None) -> tuple[dict[str, Any], list[str], int]:
    """Every problem with a workflow or scenario folder; (run, problems, number of actions)."""
    run = resolve_run(folder, workspace)
    manifest, wdir, sdir = run["manifest"], run["workflow_dir"], run["scenario_dir"]
    problems = _workflow_problems(run) + run["problems"]
    actions: set[str] = set()
    for name, rel in (manifest.get("views") or {}).items():
        path = wdir / rel
        if not path.is_file():
            problems.append(f"view {name}: {rel} does not exist")
            continue
        spec = _read_json(path)
        problems += _check_spec(spec, rel)
        actions.update(a.get("id", "") for a in spec.get("actions", []) if a.get("prompt"))
    schemas: dict[str, Any] = {}
    if manifest.get("schemas"):
        if (wdir / manifest["schemas"]).is_file():
            schemas = _read_json(wdir / manifest["schemas"])
        else:
            problems.append(f"schemas: {manifest['schemas']} does not exist")
    for name, rel in (manifest.get("fixtures") or {}).items():
        if sdir is None or not (sdir / rel).is_file():
            problems.append(f"fixture {name}: {rel} does not exist")
    fixture = (manifest.get("fixtures") or {}).get("dataset")
    if fixture and sdir is not None and (sdir / fixture).is_file():
        data = _load(sdir / fixture)
        if schemas:
            problems += _check_records(data["records"], schemas, fixture)
    skill_text = (wdir / "SKILL.md").read_text(encoding="utf-8") if (wdir / "SKILL.md").is_file() else ""
    for action in sorted(actions):
        if action and action not in skill_text:
            problems.append(f"SKILL.md never mentions the action {action!r} that a view can send")
    whole = _participants(_roster_dir(participants))
    _, missing_live = _eligible(run["workflow"], whole, run["workflow_file"].name)
    eligible, missing = _eligible(manifest, whole, "scenario.json")
    problems += sorted(set(missing_live + missing)) + _check_participants(eligible)
    script_rel = manifest.get("script")
    if script_rel and sdir is not None:
        if not (sdir / script_rel).is_file():
            problems.append(f"script: {script_rel} does not exist")
        else:
            try:
                script = _read_script(sdir / script_rel, eligible)
            except PaError as err:
                problems.append(str(err))
            else:
                views = manifest.get("views") or {}
                if not script.get("steps"):
                    problems.append(f"{script_rel}: has no steps to play")
                for number, step in enumerate(script.get("steps", []), 1):
                    for key in ("canvas", "widget"):
                        if step.get(key) and step[key] not in views:
                            problems.append(f"{script_rel}: step {number} shows the view {step[key]!r}, which the workflow does not list")
    for base in {wdir, sdir} - {None}:
        for path in base.rglob("*"):
            if path.suffix in {".json", ".html"} and path.is_file() and re.search(r"https?://", path.read_text(encoding="utf-8")):
                problems.append(f"{path.relative_to(base)}: contains a web address; scenarios must work offline")
    return run, problems, len(actions)


def cmd_check(args: argparse.Namespace) -> None:
    folder = Path(args.scenario)
    run, problems, actions = check_run(folder, getattr(args, "participants", None))
    if problems:
        print(f"{len(problems)} problem{'s' if len(problems) != 1 else ''} in {folder}:")
        for problem in problems:
            print(f"  - {problem}")
        raise SystemExit(1)
    played = f", plays {run['scenario_dir'].name}" if run["scenario_dir"] is not None and run["manifest"].get("script") else ""
    print(f"{folder.name}: ok ({len(run['manifest'].get('views') or {})} views, {actions} actions{played})")


def preview_html(folder: Path, participants: str | None = None, workspace: Path | None = None) -> str:
    """The standalone player for a scenario (or a workflow's first scenario)."""
    run = resolve_run(Path(folder), workspace)
    manifest, wdir, sdir = run["manifest"], run["workflow_dir"], run["scenario_dir"]
    problems = _workflow_problems(run)
    if problems:
        raise PaError("; ".join(problems))
    if sdir is None:
        raise PaError(f"the workflow {run['workflow_id']} has no scenario to play yet")
    whole = _participants(_roster_dir(participants))
    eligible, missing = _eligible(manifest, whole, "scenario.json")
    if missing:
        raise PaError("; ".join(missing))
    script_rel = manifest.get("script") or "script.md"
    script = _read_script(sdir / script_rel, eligible)
    specs = {name: _read_json(wdir / rel) for name, rel in (manifest.get("views") or {}).items()}
    fixture = (manifest.get("fixtures") or {}).get("dataset")
    data = _public(_load(sdir / fixture)) if fixture else {"records": []}
    roster = {k: _card(v) for k, v in eligible.items()}
    if roster:
        data["participants"] = roster
    docs = {}
    for name, rel in (manifest.get("fixtures") or {}).items():
        if str(rel).endswith(".md"):
            docs[name] = (sdir / rel).read_text(encoding="utf-8")
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
    title = (run["scenario"] or {}).get("title") or manifest.get("title", Path(folder).name)
    return template.replace("/*__PAYLOAD__*/", _embed(payload)).replace("__TITLE__", _escape(str(title)))


def cmd_preview(args: argparse.Namespace) -> None:
    _write_atomic(Path(args.out), preview_html(Path(args.scenario), args.participants))
    print(f"wrote {args.out}")


# ------------------------------------------------------------------ builder
#
# The Hangar's builder (docs/product/hangar.md, D-43 to D-46). Nothing a person
# flies is ever edited in place: a change is a draft copy under
# `<workspace>/.hangar/drafts/`, checked on every change, and Publish keeps the
# previous version under `<workspace>/.hangar/history/` before swapping the file
# in. Only people (the roster) can be built so far.

HANGAR_DIR = ".hangar"
PERSON_FIELDS = ("name", "kind", "role", "initials", "stand_in", "backing", "call_for", "skills")
REQUIRED_FIELDS = ("name", "kind", "role", "backing", "call_for")
_ID = re.compile(r"[a-z][a-z0-9-]{1,40}")


def slug(name: str) -> str:
    """The id a name becomes: lower-case words joined by hyphens."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40].rstrip("-")


def workspace_of(roster: Path) -> Path:
    return roster.resolve().parent


def _hangar(workspace: Path, *parts: str) -> Path:
    return workspace / HANGAR_DIR / Path(*parts)


def _draft_paths(workspace: Path, pid: str) -> tuple[Path, Path]:
    base = _hangar(workspace, "drafts", "people")
    return base / f"{pid}.md", base / f"{pid}.json"


def _checked_id(pid: str) -> str:
    if not _ID.fullmatch(pid):
        raise PaError(f"{pid!r} is not an id: lower-case words joined by hyphens")
    return pid


def person_text(meta: dict[str, Any], brief: str) -> str:
    """Write a participant file: the header lines in a fixed order, then the brief."""
    lines = ["---"]
    for key in PERSON_FIELDS:
        value = meta.get(key)
        if value is None or value == "" or value == []:
            continue
        if isinstance(value, bool):
            value = "true" if value else "false"
        elif isinstance(value, list):
            value = ", ".join(str(v) for v in value)
        text = str(value).replace("\n", " ").strip()
        lines.append(f"{key}: {text}")
    lines.append("---")
    return "\n".join(lines) + "\n" + brief.strip() + "\n"


def _meta_of(person: dict[str, Any]) -> dict[str, Any]:
    return {k: person[k] for k in PERSON_FIELDS if k in person and k != "id"}


def _read_meta(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def person_uses(workspace: Path, pid: str, skills: Path | None = None) -> dict[str, list[str]]:
    """What depends on a participant: workflows that call on them, scenarios and starters that cast them."""
    workflows = []
    folders = list_workflows(workspace)
    if skills is not None:
        for folder in sorted(skills.iterdir()):
            if folder.name not in folders and workflow_manifest_path(folder):
                folders[folder.name] = folder
    for wid, folder in sorted(folders.items()):
        path = workflow_manifest_path(folder)
        try:
            data = json.loads(path.read_text(encoding="utf-8")) if path else {}
        except (OSError, json.JSONDecodeError):
            continue
        if pid in (data.get("participants") or []):
            workflows.append(wid)
    scenarios = []
    for sid, folder in list_scenarios(workspace).items():
        try:
            data = _read_json(folder / SCENARIO_FILE)
        except PaError:
            continue
        if pid in (data.get("participants") or []):
            scenarios.append(sid)
    starters = []
    cast = re.compile(r"participants for this session:\s*([^\n]+)", re.I)
    for path in sorted((workspace / "templates" / "sessions").glob("*.md")):
        found = cast.search(path.read_text(encoding="utf-8"))
        if found and pid in [p.strip().rstrip(".") for p in found.group(1).split(",")]:
            starters.append(path.stem)
    return {"workflows": workflows, "scenarios": scenarios, "starters": starters}


def draft_info(workspace: Path, pid: str, skills: Path | None = None) -> dict[str, Any]:
    """One draft: what it is, what changes, what it affects, and whether it may be published."""
    text_path, meta_path = _draft_paths(workspace, pid)
    if not meta_path.is_file():
        raise PaError(f"there is no draft of {pid}")
    meta = _read_meta(meta_path)
    roster = workspace / PARTICIPANTS_DIR
    live_path = roster / f"{pid}.md"
    live = live_path.read_text(encoding="utf-8") if live_path.is_file() else None
    action = meta.get("action", "change")
    uses = person_uses(workspace, pid, skills)
    problems: list[str] = []
    person: dict[str, Any] | None = None
    text = None
    if action == "remove":
        if live is None:
            problems.append(f"{pid} is not live, so there is nothing to remove")
        for wid in uses["workflows"]:
            problems.append(f"the workflow {wid} names {pid}; take them out of it first")
        for sid in uses.get("scenarios", []):
            problems.append(f"the scenario {sid} casts {pid}; take them out of it first")
        for sid in uses["starters"]:
            problems.append(f"the starter {sid} casts {pid}; take them out of it first")
    else:
        text = text_path.read_text(encoding="utf-8") if text_path.is_file() else ""
        person = _participant(text_path)
        problems += [p.replace(f"{PARTICIPANTS_DIR}/{pid}.md", "this draft") for p in _check_participants({pid: person})]
        for key in REQUIRED_FIELDS:
            if not person.get(key) and key not in ("role",):
                problems.append(f"this draft: missing {key.replace('_', ' ')}")
        if action == "new" and live is not None:
            problems.append(f"someone called {pid} is already on the roster; pick another name")
    cast_changes = _cast_changes(workspace, pid, meta, uses) if action != "remove" else []
    if action != "remove":
        name = (person or {}).get("name") or pid
        for change in cast_changes:
            if change["kind"] == "scenarios" and change["change"] == "remove" and _speaks_in(workspace, change["id"], name):
                problems.append(f"{name} speaks in the scenario {change['id']}'s script; change the script before taking them out")
        for change in cast_changes:
            if change["kind"] == "workflows" and change["change"] == "remove":
                for sid, folder in list_scenarios(workspace).items():
                    data = _read_json(folder / SCENARIO_FILE)
                    if data.get("workflow") == change["id"] and pid in (data.get("participants") or []) \
                            and not any(c == {"kind": "scenarios", "id": sid, "change": "remove"} for c in cast_changes):
                        problems.append(f"the scenario {sid} of {change['id']} casts {name}; take them out of it too")
        workflows = list_workflows(workspace)
        added_wf = {c["id"] for c in cast_changes if c["kind"] == "workflows" and c["change"] == "add"}
        for change in cast_changes:
            if change["kind"] == "scenarios" and change["change"] == "add":
                wid = _read_json(list_scenarios(workspace)[change["id"]] / SCENARIO_FILE).get("workflow")
                folder = workflows.get(str(wid))
                allowed = _read_json(workflow_manifest_path(folder)).get("participants") if folder else None
                if allowed and pid not in allowed and wid not in added_wf:
                    problems.append(f"the scenario {change['id']} runs {wid}, which does not call on {name}; tick {wid} too")
        unchanged = live is not None and live.strip() == (text or "").strip() and not cast_changes
        if unchanged:
            problems.append("nothing has changed yet")
    return {
        "kind": "person",
        "id": pid,
        "action": action,
        "from": meta.get("from"),
        "started": meta.get("started"),
        "updated": meta.get("updated"),
        "step": meta.get("step"),
        "person": {k: v for k, v in (person or {}).items() if k != "brief"} if person else None,
        "brief": (person or {}).get("brief", ""),
        "text": text,
        "live": live,
        "problems": problems,
        "uses": uses,
        "cast": {k: sorted(set(uses.get(k, [])) - {c["id"] for c in cast_changes if c["kind"] == k and c["change"] == "remove"}
                          | {c["id"] for c in cast_changes if c["kind"] == k and c["change"] == "add"}) for k in CAST_KINDS},
        "cast_changes": cast_changes,
        "aviator": meta.get("aviator"),
        "path": f"{HANGAR_DIR}/drafts/people/{pid}.md",
        "target": f"{PARTICIPANTS_DIR}/{pid}.md",
    }


def list_drafts(workspace: Path, skills: Path | None = None) -> list[dict[str, Any]]:
    base = _hangar(workspace, "drafts", "people")
    return [draft_info(workspace, p.stem, skills) for p in sorted(base.glob("*.json"))] if base.is_dir() else []


def _write_draft(workspace: Path, pid: str, meta: dict[str, Any], text: str | None, info: dict[str, Any]) -> None:
    text_path, meta_path = _draft_paths(workspace, pid)
    text_path.parent.mkdir(parents=True, exist_ok=True)
    if text is not None:
        _write_atomic(text_path, text)
    info = {**info, "updated": _now()}
    info.setdefault("started", info["updated"])
    _write_atomic(meta_path, json.dumps(info, indent=1, ensure_ascii=False) + "\n")


def start_draft(workspace: Path, *, pid: str | None = None, name: str | None = None,
                duplicate_of: str | None = None, remove: bool = False) -> str:
    """Start a draft: of a live person (`pid`), a new one (`name`), a copy (`duplicate_of` + `name`) or a removal."""
    roster = workspace / PARTICIPANTS_DIR
    if pid and not name:
        pid = _checked_id(pid)
        if _draft_paths(workspace, pid)[1].is_file():
            return pid
        live = roster / f"{pid}.md"
        if not live.is_file():
            raise PaError(f"{pid} is not on the roster; use --name to start someone new")
        action = "remove" if remove else "change"
        _write_draft(workspace, pid, {}, None if remove else live.read_text(encoding="utf-8"), {"action": action, "from": pid})
        return pid
    if not name:
        raise PaError("give the id of someone on the roster, or --name for someone new")
    new_id = _checked_id(slug(name))
    if (roster / f"{new_id}.md").is_file() or _draft_paths(workspace, new_id)[1].is_file():
        raise PaError(f"the id {new_id} is taken; pick a different name")
    if duplicate_of:
        source = roster / f"{_checked_id(duplicate_of)}.md"
        if not source.is_file():
            raise PaError(f"{duplicate_of} is not on the roster")
        person = _participant(source)
        meta = {**_meta_of(person), "name": name, "initials": ""}
        brief = person["brief"].replace(str(person["name"]), name)
    else:
        meta = {"name": name, "kind": "agent", "backing": "session"}
        brief = ""
    meta["initials"] = "".join(w[0] for w in name.split()[:2]).upper()
    _write_draft(workspace, new_id, meta, person_text(meta, brief), {"action": "new", "from": duplicate_of})
    return new_id


CAST_KINDS = ("workflows", "scenarios", "starters")


def edit_draft(workspace: Path, pid: str, fields: dict[str, Any], brief: str | None = None, step: str | None = None,
               cast: dict[str, list[str]] | None = None, aviator: str | None = None) -> None:
    """Change fields of a draft. A person is always a stand-in; the id never changes.

    `cast` is where they should be called once published: the full list of
    workflows, scenarios and starters for each kind given. `aviator` remembers
    the builder session working on this draft.
    """
    text_path, meta_path = _draft_paths(workspace, _checked_id(pid))
    info = _read_meta(meta_path)
    if not info:
        raise PaError(f"there is no draft of {pid}; start one with `pa draft person {pid}`")
    if info.get("action") == "remove":
        raise PaError(f"the draft of {pid} removes them; discard it to make changes instead")
    unknown = sorted(set(fields) - set(PERSON_FIELDS))
    if unknown:
        raise PaError(f"a person has no {', '.join(unknown)}; fields are {', '.join(PERSON_FIELDS)}")
    if fields.get("kind") not in (None, *PARTICIPANT_KINDS):
        raise PaError(f"kind must be one of {', '.join(PARTICIPANT_KINDS)}")
    if fields.get("backing") not in (None, *PARTICIPANT_BACKINGS):
        raise PaError(f"backing must be one of {', '.join(PARTICIPANT_BACKINGS)}")
    if cast is not None:
        known = {"workflows": set(list_workflows(workspace)), "scenarios": set(list_scenarios(workspace)),
                 "starters": {p.stem for p in (workspace / "templates" / "sessions").glob("*.md")}}
        wanted = dict(info.get("cast") or {})
        for kind, ids in cast.items():
            if kind not in CAST_KINDS:
                raise PaError(f"cast is by {', '.join(CAST_KINDS)}, not {kind}")
            bad = sorted(set(ids) - known[kind])
            if bad:
                raise PaError(f"there is no {kind[:-1]} {', '.join(bad)}")
            wanted[kind] = sorted(set(ids))
        info["cast"] = wanted
    if aviator is not None:
        info["aviator"] = aviator
    person = _participant(text_path)
    meta = {**_meta_of(person), **fields}
    if meta.get("kind") == "person":
        meta["stand_in"] = True
    if "name" in fields and "initials" not in fields:
        meta["initials"] = "".join(w[0] for w in str(meta["name"]).split()[:2]).upper()
    if isinstance(meta.get("skills"), str):
        meta["skills"] = [s.strip() for s in meta["skills"].split(",") if s.strip()]
    _write_draft(workspace, pid, meta, person_text(meta, person["brief"] if brief is None else brief),
                 {**info, **({"step": step} if step else {})})


def _cast_changes(workspace: Path, pid: str, info: dict[str, Any], uses: dict[str, list[str]]) -> list[dict[str, str]]:
    changes = []
    for kind, ids in (info.get("cast") or {}).items():
        now = set(uses.get(kind, []))
        changes += [{"kind": kind, "id": i, "change": "add"} for i in sorted(set(ids) - now)]
        changes += [{"kind": kind, "id": i, "change": "remove"} for i in sorted(now - set(ids))]
    return changes


def _speaks_in(workspace: Path, sid: str, name: str) -> bool:
    folder = list_scenarios(workspace).get(sid)
    if not folder:
        return False
    rel = _read_json(folder / SCENARIO_FILE).get("script") or "script.md"
    path = folder / rel
    return path.is_file() and re.search(rf"^\*\*{re.escape(name)}:\*\*", path.read_text(encoding="utf-8"), re.M) is not None


def _apply_cast(workspace: Path, pid: str, changes: list[dict[str, str]]) -> None:
    """Add or take someone out of workflows, scenarios and starters, as the draft asks."""
    workflows, scenarios = list_workflows(workspace), list_scenarios(workspace)
    for change in changes:
        kind, cid, add = change["kind"], change["id"], change["change"] == "add"
        if kind in ("workflows", "scenarios"):
            path = workflow_manifest_path(workflows[cid]) if kind == "workflows" else scenarios[cid] / SCENARIO_FILE
            data = _read_json(path)
            ids = [i for i in data.get("participants") or [] if i != pid]
            if add:
                ids.append(pid)
            data["participants"] = ids
            _write_atomic(path, json.dumps(data, indent=1, ensure_ascii=False) + "\n")
        else:
            path = workspace / "templates" / "sessions" / f"{cid}.md"
            text = path.read_text(encoding="utf-8")
            line = re.compile(r"(participants for this session:\s*)([^\n]*)", re.I)
            found = line.search(text)
            ids = [i.strip().rstrip(".") for i in found.group(2).split(",") if i.strip()] if found else []
            ids = [i for i in ids if i != pid] + ([pid] if add else [])
            new = ", ".join(ids) + "." if ids else ""
            if found:
                text = text[:found.start(2)] + new + text[found.end(2):]
                if not ids:
                    text = line.sub("", text, count=1).rstrip() + "\n"
            elif ids:
                text = text.rstrip() + f"\n\nParticipants for this session: {new}\n"
            _write_atomic(path, text)


def discard_draft(workspace: Path, pid: str) -> None:
    for path in _draft_paths(workspace, _checked_id(pid)):
        path.unlink(missing_ok=True)


def _snapshot(workspace: Path, pid: str, text: str, summary: str, action: str) -> str:
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    folder = _hangar(workspace, "history", "people", pid)
    folder.mkdir(parents=True, exist_ok=True)
    n = 1
    version = stamp
    while (folder / f"{version}.md").exists():
        n += 1
        version = f"{stamp}-{n}"
    _write_atomic(folder / f"{version}.md", text)
    _write_atomic(folder / f"{version}.json", json.dumps({"at": _now(), "summary": summary, "replaced_by": action}, indent=1) + "\n")
    return version


def publish_draft(workspace: Path, pid: str, summary: str = "", skills: Path | None = None) -> dict[str, Any]:
    """Check, keep the live version, swap the draft in, and drop the draft."""
    info = draft_info(workspace, _checked_id(pid), skills)
    if info["problems"]:
        raise PaError("cannot publish while checks fail: " + "; ".join(info["problems"]))
    live_path = workspace / PARTICIPANTS_DIR / f"{pid}.md"
    kept = None
    if info["live"] is not None:
        kept = _snapshot(workspace, pid, info["live"], summary or info["action"], info["action"])
    if info["action"] == "remove":
        live_path.unlink()
    else:
        live_path.parent.mkdir(parents=True, exist_ok=True)
        _write_atomic(live_path, info["text"])
        _apply_cast(workspace, pid, info["cast_changes"])
    discard_draft(workspace, pid)
    return {"id": pid, "action": info["action"], "kept": kept}


def person_history(workspace: Path, pid: str) -> list[dict[str, Any]]:
    folder = _hangar(workspace, "history", "people", _checked_id(pid))
    out = []
    for path in sorted(folder.glob("*.md"), reverse=True) if folder.is_dir() else []:
        meta = _read_meta(path.with_suffix(".json"))
        out.append({"version": path.stem, "at": meta.get("at", ""), "summary": meta.get("summary", ""),
                    "text": path.read_text(encoding="utf-8")})
    return out


def restore_version(workspace: Path, pid: str, version: str, skills: Path | None = None) -> dict[str, Any]:
    """Make an earlier version live again. It goes through the same gate, and is itself a new version."""
    if not re.fullmatch(r"\d{8}-\d{6}(-\d+)?", version):
        raise PaError(f"{version!r} is not a version")
    old = _hangar(workspace, "history", "people", _checked_id(pid), f"{version}.md")
    if not old.is_file():
        raise PaError(f"{pid} has no version {version}")
    if _draft_paths(workspace, pid)[1].is_file():
        raise PaError(f"{pid} has a draft in progress; publish or discard it first")
    live = workspace / PARTICIPANTS_DIR / f"{pid}.md"
    _write_draft(workspace, pid, {}, old.read_text(encoding="utf-8"),
                 {"action": "change" if live.is_file() else "new", "from": f"{pid}@{version}"})
    try:
        return publish_draft(workspace, pid, f"restored the version of {version}", skills)
    except PaError:
        discard_draft(workspace, pid)
        raise



# --------------------------------------------------- workflows and scenarios
#
# Slice 3 of the Hangar: workflows and scenarios are built the same way as
# people, but a draft is a whole folder: `.hangar/drafts/<kinds>/<id>/` plus
# `<id>.json` for what the draft is. Publish keeps the folder it replaces under
# `.hangar/history/<kinds>/<id>/<version>/`. A scenario goes live in
# `<workspace>/scenarios/<id>/`; a workflow in `<workspace>/.claude/skills/<id>/`.
# A shipped workflow is never changed: changing it publishes a workspace copy
# that takes over its id, and removing that copy brings the shipped one back
# (D-71).

FOLDER_KINDS = {"scenario": "scenarios", "workflow": "workflows"}
BUILD_KINDS = ["person", "scenario", "workflow"]
SCENARIO_KEYS = ("title", "summary", "workflow", "participants", "fixtures", "script", "opening")
WORKFLOW_KEYS = ("title", "summary", "steps", "participants", "inputs", "launchers", "work_products")
_TEXT_SUFFIXES = {".md", ".json", ".txt", ".csv", ".html", ".yaml", ".yml"}
_MAX_FILE = 1_000_000
_MAX_SHOWN = 300_000


def _kind(kind: str) -> str:
    if kind not in FOLDER_KINDS:
        raise PaError(f"a draft is of a person, scenario or workflow, not {kind!r}")
    return kind


def _fd_paths(workspace: Path, kind: str, fid: str) -> tuple[Path, Path]:
    base = _hangar(workspace, "drafts", FOLDER_KINDS[_kind(kind)])
    return base / fid, base / f"{fid}.json"


def _manifest_name(kind: str, folder: Path | None = None) -> str:
    if kind == "scenario":
        return SCENARIO_FILE
    found = workflow_manifest_path(folder) if folder else None
    return found.name if found else WORKFLOW_FILE


def live_folder(workspace: Path, kind: str, fid: str) -> Path | None:
    if _kind(kind) == "scenario":
        return list_scenarios(workspace).get(fid)
    return find_workflow(fid, workspace)


def publish_target(workspace: Path, kind: str, fid: str) -> Path:
    if _kind(kind) == "scenario":
        return workspace / SCENARIOS_DIR / fid
    return workspace / ".claude" / "skills" / fid


def is_builtin(workspace: Path, folder: Path) -> bool:
    """A shipped workflow, outside the workspace: it can be copied, never changed in place."""
    return not folder.resolve().is_relative_to(workspace.resolve())


def shipped_workflow(workspace: Path, fid: str) -> Path | None:
    """The shipped workflow of this id, whether or not a workspace copy hides it."""
    for root in workflow_roots(workspace):
        if not is_builtin(workspace, root):
            continue
        if workflow_manifest_path(root / fid):
            return root / fid
    return None


def _copy_folder(source: Path, dest: Path) -> None:
    import shutil

    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(source, dest, ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))


def _rename_skill(folder: Path, old: str, new: str) -> None:
    skill = folder / "SKILL.md"
    if skill.is_file():
        text = skill.read_text(encoding="utf-8")
        _write_atomic(skill, re.sub(rf"^name:\s*{re.escape(old)}\s*$", f"name: {new}", text, count=1, flags=re.M))


def start_folder_draft(workspace: Path, kind: str, *, fid: str | None = None, name: str | None = None,
                       duplicate_of: str | None = None, remove: bool = False, workflow: str | None = None) -> str:
    """Start a draft of a scenario or workflow: a change, a removal, a copy, or (scenarios) a new one."""
    folder, meta_path = _fd_paths(workspace, kind, fid or "x")
    if fid and not name:
        fid = _checked_id(fid)
        folder, meta_path = _fd_paths(workspace, kind, fid)
        if meta_path.is_file():
            return fid
        live = live_folder(workspace, kind, fid)
        if not live:
            raise PaError(f"there is no {kind} {fid}")
        builtin = is_builtin(workspace, live)
        if remove:
            if builtin:
                raise PaError(f"{fid} ships with the app and cannot be removed; only a workspace copy can")
            _write_folder_meta(workspace, kind, fid, {"action": "remove", "from": fid})
            return fid
        _copy_folder(live, folder)
        _write_folder_meta(workspace, kind, fid, {"action": "change", "from": fid, "builtin": builtin})
        return fid
    if not name:
        raise PaError(f"give the id of a {kind}, or a name for a new one")
    new_id = _checked_id(slug(name))
    folder, meta_path = _fd_paths(workspace, kind, new_id)
    if live_folder(workspace, kind, new_id) or meta_path.is_file():
        raise PaError(f"the id {new_id} is taken; pick a different name")
    if duplicate_of:
        source = live_folder(workspace, kind, _checked_id(duplicate_of))
        if not source:
            raise PaError(f"there is no {kind} {duplicate_of}")
        _copy_folder(source, folder)
        path = folder / _manifest_name(kind, folder)
        data = _read_json(path)
        data[kind] = new_id
        data["title"] = name
        _write_atomic(path, json.dumps(data, indent=1, ensure_ascii=False) + "\n")
        if kind == "workflow":
            _rename_skill(folder, duplicate_of, new_id)
    elif kind == "scenario":
        workflows = list_workflows(workspace)
        wid = workflow or next(iter(workflows), None)
        if not wid or wid not in workflows:
            raise PaError(f"a new scenario runs a workflow; there is no workflow {wid!r}")
        folder.mkdir(parents=True, exist_ok=True)
        data = {"scenario": new_id, "title": name, "summary": "", "workflow": wid, "participants": [],
                "fixtures": {}, "script": "script.md"}
        _write_atomic(folder / SCENARIO_FILE, json.dumps(data, indent=1, ensure_ascii=False) + "\n")
        _write_atomic(folder / "script.md", f"# {name}\n\n**You:** \n\n**Aviator:** \n")
    else:
        raise PaError("a new workflow starts as a copy of one that exists; give the one to copy")
    _write_folder_meta(workspace, kind, new_id, {"action": "new", "from": duplicate_of})
    return new_id


def _write_folder_meta(workspace: Path, kind: str, fid: str, info: dict[str, Any]) -> None:
    _, meta_path = _fd_paths(workspace, kind, fid)
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    info = {**info, "updated": _now()}
    info.setdefault("started", info["updated"])
    _write_atomic(meta_path, json.dumps(info, indent=1, ensure_ascii=False) + "\n")


def _safe_rel(rel: str) -> str:
    path = Path(rel)
    if not rel or path.is_absolute() or ".." in path.parts or rel.startswith("."):
        raise PaError(f"{rel!r} is not a file inside the folder")
    if path.suffix.lower() not in _TEXT_SUFFIXES:
        raise PaError(f"{rel}: only text files ({', '.join(sorted(_TEXT_SUFFIXES))}) can be edited here")
    return path.as_posix()


def edit_folder_draft(workspace: Path, kind: str, fid: str, manifest: dict[str, Any] | None = None,
                      files: dict[str, str | None] | None = None, step: str | None = None,
                      aviator: str | None = None) -> None:
    """Change a scenario or workflow draft: manifest fields (None removes one) and whole text files."""
    folder, meta_path = _fd_paths(workspace, kind, _checked_id(fid))
    info = _read_meta(meta_path)
    if not info:
        raise PaError(f"there is no draft of {fid}; start one first")
    if info.get("action") == "remove":
        raise PaError(f"the draft of {fid} removes it; discard it to make changes instead")
    if manifest:
        keys = SCENARIO_KEYS if kind == "scenario" else WORKFLOW_KEYS
        unknown = sorted(set(manifest) - set(keys))
        if unknown:
            raise PaError(f"a {kind} has no {', '.join(unknown)} here; fields are {', '.join(keys)}")
        for key in ("title", "summary", "workflow", "script", "opening"):
            if manifest.get(key) is not None and not isinstance(manifest[key], str):
                raise PaError(f"{key} must be text")
        for key in ("participants", "steps"):
            value = manifest.get(key)
            if value is not None and not (isinstance(value, list) and all(isinstance(v, str) for v in value)):
                raise PaError(f"{key} must be a list of text")
        if manifest.get("workflow") and manifest["workflow"] not in list_workflows(workspace):
            raise PaError(f"there is no workflow {manifest['workflow']}")
        path = folder / _manifest_name(kind, folder)
        data = _read_json(path)
        for key, value in manifest.items():
            if value is None:
                data.pop(key, None)
            else:
                data[key] = value
        _write_atomic(path, json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    for rel, text in (files or {}).items():
        rel = _safe_rel(rel)
        if rel == _manifest_name(kind, folder) and text is None:
            raise PaError(f"{rel} is what makes the folder a {kind}; it cannot be deleted")
        path = folder / rel
        if text is None:
            path.unlink(missing_ok=True)
            continue
        if len(text.encode("utf-8")) > _MAX_FILE:
            raise PaError(f"{rel} is too big to edit here (over 1 MB)")
        if path.suffix == ".json":
            try:
                json.loads(text)
            except json.JSONDecodeError as err:
                raise PaError(f"{rel} is not valid JSON: {err.msg} on line {err.lineno}") from err
        path.parent.mkdir(parents=True, exist_ok=True)
        _write_atomic(path, text)
    if step:
        info["step"] = step
    if aviator is not None:
        info["aviator"] = aviator
    _write_folder_meta(workspace, kind, fid, info)


def _files_of(folder: Path | None) -> dict[str, Path]:
    if not folder or not folder.is_dir():
        return {}
    return {p.relative_to(folder).as_posix(): p for p in sorted(folder.rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts and p.name != ".DS_Store"}


def _text(path: Path | None) -> str | None:
    if path is None or path.suffix.lower() not in _TEXT_SUFFIXES or path.stat().st_size > _MAX_SHOWN:
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def folder_uses(workspace: Path, kind: str, fid: str) -> dict[str, list[str]]:
    """What depends on a scenario or workflow: a workflow's scenarios and the starters that name it."""
    if kind == "scenario":
        return {"scenarios": [], "starters": []}
    scenarios = [f.name for f in scenarios_of(fid, workspace)]
    starters = [p.stem for p in sorted((workspace / "templates" / "sessions").glob("*.md"))
                if re.search(rf"\b{re.escape(fid)}\b", p.read_text(encoding="utf-8"))]
    return {"scenarios": scenarios, "starters": starters}


def folder_draft_info(workspace: Path, kind: str, fid: str) -> dict[str, Any]:
    folder, meta_path = _fd_paths(workspace, kind, _checked_id(fid))
    if not meta_path.is_file():
        raise PaError(f"there is no draft of the {kind} {fid}")
    meta = _read_meta(meta_path)
    action = meta.get("action", "change")
    live = live_folder(workspace, kind, fid)
    builtin = bool(live and is_builtin(workspace, live))
    uses = folder_uses(workspace, kind, fid)
    problems: list[str] = []
    manifest: dict[str, Any] = {}
    files: list[dict[str, Any]] = []
    if action == "remove":
        if not live or builtin:
            problems.append(f"{fid} has no workspace copy to remove")
        if kind == "workflow" and not shipped_workflow(workspace, fid):
            for sid in uses["scenarios"]:
                problems.append(f"the scenario {sid} runs {fid}; remove it or move it to another workflow first")
    else:
        mpath = folder / _manifest_name(kind, folder)
        try:
            manifest = _read_json(mpath)
        except PaError as err:
            problems.append(str(err))
        if manifest and manifest.get(kind) != fid:
            problems.append(f"{mpath.name}: {kind} must be {fid!r}, the folder's id")
        roster = str(workspace / PARTICIPANTS_DIR)
        try:
            _, found, _ = check_run(folder, roster, workspace)
            problems += [p for p in found if p not in problems]
        except PaError as err:
            problems.append(str(err))
        if kind == "scenario" and not problems:
            try:
                preview_html(folder, roster, workspace)
            except (PaError, OSError, ValueError, KeyError) as err:
                problems.append(f"the scenario does not play through: {err}")
        if action == "new" and live is not None:
            problems.append(f"a {kind} called {fid} already exists; pick another name")
        now, before = _files_of(folder), _files_of(live if action != "new" else None)
        for rel in sorted(set(now) | set(before)):
            after_text, before_text = _text(now.get(rel)), _text(before.get(rel))
            if rel not in before:
                change = "added"
            elif rel not in now:
                change = "removed"
            elif now[rel].read_bytes() == before[rel].read_bytes():
                change = "same"
            else:
                change = "changed"
            files.append({"path": rel, "change": change, "size": now[rel].stat().st_size if rel in now else 0,
                          "text": after_text, "live": before_text if change != "same" else None,
                          "editable": rel in now and after_text is not None})
        if action == "change" and all(f["change"] == "same" for f in files):
            problems.append("nothing has changed yet")
    return {
        "kind": kind,
        "id": fid,
        "action": action,
        "from": meta.get("from"),
        "builtin": builtin,
        "shipped": bool(kind == "workflow" and shipped_workflow(workspace, fid)),
        "started": meta.get("started"),
        "updated": meta.get("updated"),
        "step": meta.get("step"),
        "aviator": meta.get("aviator"),
        "manifest": manifest,
        "manifest_file": _manifest_name(kind, folder if folder.is_dir() else None),
        "files": files,
        "problems": problems,
        "uses": uses,
        "path": f"{HANGAR_DIR}/drafts/{FOLDER_KINDS[kind]}/{fid}/",
        "target": publish_target(workspace, kind, fid).relative_to(workspace).as_posix() + "/",
    }


def list_folder_drafts(workspace: Path) -> list[dict[str, Any]]:
    out = []
    for kind, kinds in FOLDER_KINDS.items():
        base = _hangar(workspace, "drafts", kinds)
        for meta in sorted(base.glob("*.json")) if base.is_dir() else []:
            try:
                out.append(folder_draft_info(workspace, kind, meta.stem))
            except PaError:
                continue
    return out


def discard_folder_draft(workspace: Path, kind: str, fid: str) -> None:
    import shutil

    folder, meta_path = _fd_paths(workspace, kind, _checked_id(fid))
    if folder.is_dir():
        shutil.rmtree(folder)
    meta_path.unlink(missing_ok=True)


def publish_folder_draft(workspace: Path, kind: str, fid: str, summary: str = "") -> dict[str, Any]:
    """Check, keep the workspace folder it replaces, swap the draft in, and drop the draft."""
    import shutil

    info = folder_draft_info(workspace, kind, fid)
    if info["problems"]:
        raise PaError("cannot publish while checks fail: " + "; ".join(info["problems"]))
    target = publish_target(workspace, kind, fid)
    kept = None
    if target.is_dir():
        stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        base = _hangar(workspace, "history", FOLDER_KINDS[kind], fid)
        version, n = stamp, 1
        while (base / version).exists():
            n += 1
            version = f"{stamp}-{n}"
        _copy_folder(target, base / version)
        _write_atomic(base / f"{version}.json",
                      json.dumps({"at": _now(), "summary": summary or info["action"], "replaced_by": info["action"]}, indent=1) + "\n")
        kept = version
    if info["action"] == "remove":
        shutil.rmtree(target)
    else:
        staging = target.with_name(f".{fid}.publishing")
        _copy_folder(_fd_paths(workspace, kind, fid)[0], staging)
        if target.exists():
            shutil.rmtree(target)
        staging.rename(target)
    discard_folder_draft(workspace, kind, fid)
    return {"id": fid, "kind": kind, "action": info["action"], "kept": kept}


def folder_history(workspace: Path, kind: str, fid: str) -> list[dict[str, Any]]:
    base = _hangar(workspace, "history", FOLDER_KINDS[_kind(kind)], _checked_id(fid))
    out = []
    for folder in sorted((p for p in base.iterdir() if p.is_dir()), reverse=True) if base.is_dir() else []:
        meta = _read_meta(base / f"{folder.name}.json")
        out.append({"version": folder.name, "at": meta.get("at", ""), "summary": meta.get("summary", ""),
                    "files": sorted(_files_of(folder))})
    return out


def restore_folder_version(workspace: Path, kind: str, fid: str, version: str) -> dict[str, Any]:
    """Make an earlier version live again, through the same gate."""
    if not re.fullmatch(r"\d{8}-\d{6}(-\d+)?", version):
        raise PaError(f"{version!r} is not a version")
    old = _hangar(workspace, "history", FOLDER_KINDS[_kind(kind)], _checked_id(fid), version)
    if not old.is_dir():
        raise PaError(f"{fid} has no version {version}")
    folder, meta_path = _fd_paths(workspace, kind, fid)
    if meta_path.is_file():
        raise PaError(f"{fid} has a draft in progress; publish or discard it first")
    _copy_folder(old, folder)
    live = live_folder(workspace, kind, fid)
    _write_folder_meta(workspace, kind, fid, {"action": "change" if live else "new", "from": f"{fid}@{version}"})
    try:
        return publish_folder_draft(workspace, kind, fid, f"restored the version of {version}")
    except PaError:
        discard_folder_draft(workspace, kind, fid)
        raise


def cmd_folder_draft(args: argparse.Namespace, workspace: Path) -> None:
    kind = args.kind
    if args.list:
        print(json.dumps(list_folder_drafts(workspace), indent=1, ensure_ascii=False))
        return
    if args.discard:
        discard_folder_draft(workspace, kind, args.id or "")
        print(f"discarded the draft of {args.id}")
        return
    fid = start_folder_draft(workspace, kind, fid=args.id, name=args.name, duplicate_of=args.duplicate,
                             remove=args.remove, workflow=args.workflow)
    manifest: dict[str, Any] = {}
    for key, value in _pairs(args.set).items():
        if key in ("participants", "steps"):
            value = [v.strip() for v in str(value or "").split(",") if v.strip()]
        manifest[key] = value
    files: dict[str, str | None] = {}
    for item in args.file:
        rel, _, local = item.partition("=")
        files[rel.strip()] = Path(local).read_text(encoding="utf-8") if local.strip() else None
    if manifest or files or args.step:
        edit_folder_draft(workspace, kind, fid, manifest or None, files or None, args.step)
    info = folder_draft_info(workspace, kind, fid)
    if args.json:
        print(json.dumps(info, indent=1, ensure_ascii=False))
        return
    print(f"draft {info['path']} ({info['action']}) -> {info['target']}")
    for f in info["files"]:
        if f["change"] != "same":
            print(f"  {f['change']}: {f['path']}")
    print("checks: ok, ready to publish" if not info["problems"] else "checks: " + "; ".join(info["problems"]))


def cmd_draft(args: argparse.Namespace) -> None:
    workspace = workspace_of(_roster_dir(args.dir))
    if args.kind != "person":
        cmd_folder_draft(args, workspace)
        return
    if args.list:
        print(json.dumps([{k: v for k, v in d.items() if k not in ("text", "live")} for d in list_drafts(workspace)], indent=1))
        return
    if args.discard:
        discard_draft(workspace, args.id or "")
        print(f"discarded the draft of {args.id}")
        return
    pid = start_draft(workspace, pid=args.id, name=args.name, duplicate_of=args.duplicate, remove=args.remove)
    fields = _pairs(args.set)
    for key in ("stand_in",):
        if isinstance(fields.get(key), str):
            fields[key] = fields[key].lower() in ("true", "yes", "1")
    brief = Path(args.brief_file).read_text(encoding="utf-8") if args.brief_file else args.brief
    cast = None
    for item in args.cast:
        kind, _, ids = item.partition("=")
        cast = cast or {}
        cast[kind.strip()] = [i.strip() for i in ids.split(",") if i.strip()]
    if fields or brief is not None or args.step or cast is not None:
        edit_draft(workspace, pid, fields, brief, args.step, cast)
    info = draft_info(workspace, pid)
    if args.json:
        print(json.dumps({k: v for k, v in info.items() if k not in ("live",)}, indent=1, ensure_ascii=False))
        return
    print(f"draft {info['path']} ({info['action']})")
    print("checks: ok, ready to publish" if not info["problems"] else "checks: " + "; ".join(info["problems"]))


def cmd_publish(args: argparse.Namespace) -> None:
    if args.kind != "person":
        result = publish_folder_draft(workspace_of(_roster_dir(args.dir)), args.kind, args.id, args.summary or "")
        kept = f"; the previous version is kept as {result['kept']}" if result["kept"] else ""
        print(f"published the {args.kind} {result['id']} ({result['action']}){kept}")
        return
    result = publish_draft(workspace_of(_roster_dir(args.dir)), args.id, args.summary or "")
    kept = f"; the previous version is kept as {result['kept']}" if result["kept"] else ""
    print(f"published {result['id']} ({result['action']}){kept}")


def cmd_history(args: argparse.Namespace) -> None:
    workspace = workspace_of(_roster_dir(args.dir))
    if args.kind != "person":
        if args.restore:
            result = restore_folder_version(workspace, args.kind, args.id, args.restore)
            print(f"restored {args.id} to {args.restore}; the version it replaced is kept as {result['kept']}")
            return
        for v in folder_history(workspace, args.kind, args.id) or [{"version": f"{args.id} has no earlier versions", "summary": ""}]:
            print(f"{v['version']}  {v['summary']}".rstrip())
        return
    if args.restore:
        result = restore_version(workspace, args.id, args.restore)
        print(f"restored {args.id} to {args.restore}; the version it replaced is kept as {result['kept']}")
        return
    versions = person_history(workspace, args.id)
    if not versions:
        print(f"{args.id} has no earlier versions")
    for v in versions:
        print(f"{v['version']}  {v['summary']}")


def cmd_uses(args: argparse.Namespace) -> None:
    workspace = workspace_of(_roster_dir(args.dir))
    if args.kind == "person":
        uses = person_uses(workspace, _checked_id(args.id))
    else:
        uses = folder_uses(workspace, args.kind, _checked_id(args.id))
    if args.json:
        print(json.dumps(uses))
        return
    if not any(uses.values()):
        print(f"nothing names {args.id}")
    for kind, items in uses.items():
        for item in items:
            print(f"{kind[:-1]}: {item}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pa", description="Product Aviator data and view command")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("flow", help="record which step of a workflow the work is at, for the Session panel")
    p.add_argument("data")
    p.add_argument("--scenario", help="the workflow (or scenario) folder, the first time, to take its steps")
    p.add_argument("--step", help="a step number, or part of its name")
    p.add_argument("--done", action="store_true", help="the workflow is finished")
    p.add_argument("--note", help="one line on what is happening in this step")
    p.set_defaults(run=cmd_flow)

    p = sub.add_parser("who", help="list the participants the agent can call, or show one")
    p.add_argument("id", nargs="?", help="an id, or part of a name or role")
    p.add_argument("--dir", help="the roster folder; default participants/ in the workspace")
    p.add_argument("--scenario", help="list only the participants this workflow or scenario folder names")
    p.add_argument("--json", action="store_true")
    p.add_argument("--header", action="store_true", help="print the opening lines of a participant block")
    p.add_argument("--session", help="with --header: the id of the session speaking for them")
    p.add_argument("--check", action="store_true", help="check every participant file")
    p.add_argument("--opening", action="store_true", help="print the first message for the background session that plays them")
    p.add_argument("--ask", help="with --opening: what they are asked to do")
    p.add_argument("--conversation", help="with --opening: the id of the user's session, so they can read the whole conversation")
    p.set_defaults(run=cmd_who)

    p = sub.add_parser("tell", help="put a participant's message, or their invitation to a session, in the user's Inbox")
    p.add_argument("id", help="the participant's id")
    p.add_argument("--session", required=True, help="the session the card opens: the one it is about, or theirs for --invite")
    p.add_argument("--says", help="what they say, word for word")
    p.add_argument("--entry", help="instead of --says: a heading (or part of one) from their '## Script'")
    p.add_argument("--title", help="one line for the collapsed card; default the first sentence")
    p.add_argument("--invite", action="store_true", help="they are asking the user to join --session, a session of their own")
    p.add_argument("--dir", help="the roster folder; default participants/ in the workspace")
    p.add_argument("--url", help=f"the app's address; default $OMNIGENT_SLIM_URL or {DEFAULT_APP_URL}")
    p.set_defaults(run=cmd_tell)

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
    p.add_argument("--meta", action="append", default=[], help="dataset fact to change, key=value")
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

    p = sub.add_parser("check", help="validate a workflow or scenario folder")
    p.add_argument("scenario")
    p.add_argument("--participants", help="the roster folder; default participants/ in the workspace")
    p.set_defaults(run=cmd_check)

    p = sub.add_parser("preview", help="build a standalone demo of a scenario (or a workflow's first one)")
    p.add_argument("scenario")
    p.add_argument("--out", required=True)
    p.add_argument("--participants", help="the roster folder; default participants/ in the workspace")
    p.set_defaults(run=cmd_preview)

    # The Hangar's builder: drafts, publish, history, used-by.
    p = sub.add_parser("draft", help="start or change a draft of a participant, scenario or workflow (nothing is live until publish)")
    p.add_argument("kind", choices=BUILD_KINDS, help="what is being built")
    p.add_argument("id", nargs="?", help="the id of someone on the roster, or of a scenario or workflow")
    p.add_argument("--name", help="a new one's name (its id is made from it)")
    p.add_argument("--duplicate", help="with --name: start from a copy of this id")
    p.add_argument("--remove", action="store_true", help="draft taking them off the roster")
    p.add_argument("--set", action="append", default=[],
                   help="field=value. person: " + ", ".join(PERSON_FIELDS) + "; scenario: " + ", ".join(SCENARIO_KEYS)
                   + "; workflow: " + ", ".join(WORKFLOW_KEYS) + " (participants and steps are comma lists)")
    p.add_argument("--file", action="append", default=[],
                   help="scenario or workflow: path/in/folder=local-file replaces a text file; path= deletes it")
    p.add_argument("--workflow", help="a new scenario: the workflow it runs")
    p.add_argument("--brief", help="replace the brief or script")
    p.add_argument("--brief-file", help="replace the brief or script with this file")
    p.add_argument("--step", help="which step of the guided build the draft is at, for the Hangar")
    p.add_argument("--cast", action="append", default=[],
                   help="where they are called once published: workflows=a,b or scenarios=a or starters=a (the full list)")
    p.add_argument("--discard", action="store_true")
    p.add_argument("--list", action="store_true", help="list every draft as JSON")
    p.add_argument("--json", action="store_true")
    p.add_argument("--dir", help="the roster folder; default participants/ in the workspace")
    p.set_defaults(run=cmd_draft)

    p = sub.add_parser("publish", help="check a draft, keep the live version, and make the draft live")
    p.add_argument("kind", choices=BUILD_KINDS)
    p.add_argument("id")
    p.add_argument("--summary", help="one line on what changed")
    p.add_argument("--dir")
    p.set_defaults(run=cmd_publish)

    p = sub.add_parser("history", help="earlier versions of a participant, or restore one")
    p.add_argument("kind", choices=BUILD_KINDS)
    p.add_argument("id")
    p.add_argument("--restore", metavar="VERSION")
    p.add_argument("--dir")
    p.set_defaults(run=cmd_history)

    p = sub.add_parser("uses", help="what depends on a participant")
    p.add_argument("kind", choices=BUILD_KINDS)
    p.add_argument("id")
    p.add_argument("--json", action="store_true")
    p.add_argument("--dir")
    p.set_defaults(run=cmd_uses)

    # Comments and suggested changes in markdown documents (docreview.py).
    from docreview import ReviewError, register as register_review

    register_review(sub)

    args = parser.parse_args(argv)
    try:
        args.run(args)
    except (PaError, ReviewError) as err:
        print(f"pa: {err}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
