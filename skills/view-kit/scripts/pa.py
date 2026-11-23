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
  pa project NAME --goal G                        an initiative: goal, area, state, a stable id
  pa stamp   FILE --initiative I --template T     say what a file is and which initiative it serves
  pa artifacts [--initiative I]                   what each initiative has produced, from the stamps
  pa template list|show|check|new                 templates: markdown, records or page
  pa register I evidence|question|decision|check  the initiative's shared registers
  pa log     EVENT k=v ...                        write one event to the usage log
  pa usage   summary|tail|check|pack|eval|where   read the usage log

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
import time
from pathlib import Path
from typing import Any, Iterator

KIT_DIR = Path(__file__).resolve().parent.parent / "kit"
LAYOUTS = {"tree-table", "board", "detail", "summary", "form", "worksheet"}
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
        _write_flow(data, path)


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


RUN_STATES = ("working", "needs-you", "waiting", "paused", "finished", "stopped")


def _run_state(flow: dict[str, Any], counts: dict[str, Any] | None) -> str:
    """Where a run stands. Paused and stopped are the person's word and win;
    finished comes from the steps; needs-you from the records or the agent."""
    held = flow.get("state") or "working"
    if held in ("paused", "stopped"):
        return held
    if flow.get("current", 1) > len(flow.get("steps") or []):
        return "finished"
    if held == "needs-you" or (counts and counts.get("waiting")):
        return "needs-you"
    return "waiting" if held == "waiting" else "working"


def _write_flow(data: dict[str, Any], dataset: Path | None = None) -> None:
    """Write the small file the Session panel and the project page read to draw a run."""
    flow = data["flow"]
    counts = _flow_counts(data, flow.get("count"))
    out = {
        "workflow": flow.get("workflow", ""),
        "scenario": flow.get("scenario", ""),
        "subject": data.get("title", ""),
        "steps": flow.get("steps", []),
        "current": flow.get("current", 1),
        "note": flow.get("note", ""),
        "counts": counts,
        "participants": flow.get("participants"),
        # The run: its state, the note left at a pause, the session it runs in.
        "state": _run_state(flow, counts),
        "left_off": flow.get("left_off", ""),
        "session": flow.get("session", ""),
        "data": flow.get("data") or (dataset.as_posix() if dataset else ""),
        "started": flow.get("started", ""),
        "paused_at": flow.get("paused_at", ""),
        # Threads (D-89): who started the run, what it was told, what it has reported.
        "director": flow.get("director", ""),
        "brief": flow.get("brief", ""),
        "reports": flow.get("reports") or [],
        "updated": _now(),
    }
    _write_atomic(Path(flow["file"]), json.dumps(out, indent=1, ensure_ascii=False) + "\n")


def cmd_flow(args: argparse.Namespace) -> None:
    path = Path(args.data)
    moves = [name for name in ("pause", "resume", "stop", "done") if getattr(args, name, False)]
    if len(moves) > 1:
        raise PaError(f"pass one of --{', --'.join(moves)}, not several")
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
        flow.setdefault("started", _now())
        flow["data"] = path.as_posix()
        if getattr(args, "director", None):
            flow["director"] = args.director
        if getattr(args, "brief", None):
            flow["brief"] = args.brief
        if getattr(args, "session", None):
            flow["session"] = args.session
        total = len(flow["steps"])
        held = flow.get("state") or "working"
        advancing = args.done or args.step is not None
        if held == "stopped" and advancing and not args.resume:
            raise PaError("this run was stopped; pass --resume to pick it up again")
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
        if args.pause or args.stop:
            if flow["current"] > total:
                raise PaError("this run is finished; there is nothing to pause or stop")
            if args.pause and not (args.note or "").strip():
                raise PaError("a pause needs --note: one or two sentences on where the work was left")
            flow["state"] = "paused" if args.pause else "stopped"
            flow["paused_at"] = _now()
            if args.note is not None:
                flow["left_off"] = args.note.strip()
        else:
            # Doing work on a paused run picks it up; so does --resume.
            if args.resume or advancing or getattr(args, "state", None):
                if held in ("paused", "stopped"):
                    flow["paused_at"] = ""
                    flow["left_off"] = ""
                flow["state"] = getattr(args, "state", None) or "working"
            if args.note is not None:
                flow["note"] = args.note
            elif advancing:
                flow["note"] = ""
        data["flow"] = flow
        _save(path, data)
    state = _run_state(flow, _flow_counts(data, flow.get("count")))
    where = "done" if flow["current"] > total else f"step {flow['current']} of {total}: {flow['steps'][flow['current'] - 1]}"
    tail = "" if state in ("working", "finished") else f" ({state})"
    print(f"{flow['workflow']}: {where}{tail}")


def load_runs(folder: Path, include_done: bool = False) -> list[dict[str, Any]]:
    """The runs in a progress folder, the ones needing the person first."""
    runs: list[dict[str, Any]] = []
    for file in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        try:
            run = json.loads(file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(run, dict) or not isinstance(run.get("steps"), list):
            continue
        total = len(run["steps"])
        current = run.get("current", 1)
        # Files written before runs had a state: finished or working, from the steps.
        run["state"] = run.get("state") or ("finished" if current > total else "working")
        run["file"] = file.as_posix()
        if include_done or run["state"] not in ("finished", "stopped"):
            runs.append(run)
    order = {state: i for i, state in enumerate(("needs-you", "paused", "waiting", "working", "stopped", "finished"))}
    runs.sort(key=lambda r: (order.get(r["state"], 9), r.get("updated", "")))
    return runs


def _print_runs(runs: list[dict[str, Any]]) -> None:
    if not runs:
        print("no runs in flight")
        return
    for run in runs:
        total = len(run["steps"])
        current = run.get("current", 1)
        step = "finished" if current > total else f"step {current} of {total}: {run['steps'][current - 1]}"
        print(f"{run['state']:<10} {run.get('workflow', '')}: {run.get('subject', '')} ({step})")
        note = run.get("left_off") or run.get("note")
        if note:
            print(f"           {note}")
        reports = run.get("reports") or []
        if reports:
            last = reports[-1]
            print(f"           last report ({last.get('kind', 'milestone')}): {last.get('text', '')}")
        if run.get("session"):
            print(f"           thread: {run['session']}")
        if run.get("data"):
            print(f"           data: {run['data']}")


def cmd_runs(args: argparse.Namespace) -> None:
    """List the runs in this workspace: what is in flight and where each was left."""
    runs = load_runs(Path(args.dir or FLOW_DIR), args.all)
    if args.json:
        print(json.dumps(runs, indent=1, ensure_ascii=False))
        return
    _print_runs(runs)


# ------------------------------------------------------------------ director memory
#
# A director runs for days, across compactions and new sessions (D-134). What
# it must not lose is in three places: a short charter that ships with the
# director skill, and two files of its own in the workspace, written at
# checkpoints: state.md (what is in flight and what it is waiting on, rewritten
# whole) and memory.md (lasting facts, one dated line each). `pa recap` prints
# all three with the runs, so one command re-orients a director after a
# compaction. The person reads and edits both files as "Director's notes".

DIRECTOR_DIR = "director"
DIRECTOR_STATE = "state.md"
DIRECTOR_MEMORY = "memory.md"
CHARTER_FILE = KIT_DIR.parent.parent / "director" / "charter.md"
# Only headings: what to write when is in the director skill and its charter,
# so the person reading these notes sees the project, not instructions.
STATE_TEMPLATE = """# Where the project stands

## Working on now

## Waiting on the person

## Decided here

## Next
"""
MEMORY_TEMPLATE = """# What to remember
"""


def director_paths(workspace: Path | None = None) -> tuple[Path, Path]:
    folder = (workspace or Path.cwd()) / DIRECTOR_DIR
    return folder / DIRECTOR_STATE, folder / DIRECTOR_MEMORY


def ensure_director_files(workspace: Path | None = None) -> tuple[Path, Path]:
    state, memory = director_paths(workspace)
    state.parent.mkdir(parents=True, exist_ok=True)
    for path, template in ((state, STATE_TEMPLATE), (memory, MEMORY_TEMPLATE)):
        if not path.is_file():
            path.write_text(template, encoding="utf-8")
    return state, memory


def cmd_recap(args: argparse.Namespace) -> None:
    """Everything a director needs after a compaction or in a new session, in one read."""
    workspace = Path(args.workspace) if args.workspace else Path.cwd()
    state, memory = ensure_director_files(workspace)
    if CHARTER_FILE.is_file():
        print(CHARTER_FILE.read_text(encoding="utf-8").strip())
        print(f"\nThe full director skill: {CHARTER_FILE.parent / 'SKILL.md'}. Read it again if its steps are not in view.")
    print(f"\n---\n\n{DIRECTOR_DIR}/{DIRECTOR_STATE}:\n")
    print(state.read_text(encoding="utf-8").strip())
    print(f"\n---\n\n{DIRECTOR_DIR}/{DIRECTOR_MEMORY}:\n")
    print(memory.read_text(encoding="utf-8").strip())
    print("\n---\n\nRuns (pa runs):\n")
    _print_runs(load_runs(workspace / FLOW_DIR))


def cmd_remember(args: argparse.Namespace) -> None:
    """Add one lasting fact to the director's memory, dated."""
    text = " ".join(args.fact).strip()
    if not text:
        raise PaError("say what to remember")
    _, memory = ensure_director_files(Path(args.workspace) if args.workspace else None)
    body = memory.read_text(encoding="utf-8")
    line = f"- {_dt.date.today().isoformat()}: {text}"
    if line in body.splitlines():
        print(f"already remembered: {text}")
        return
    first = not any(l.startswith("- ") for l in body.splitlines())
    memory.write_text(body.rstrip("\n") + ("\n\n" if first else "\n") + line + "\n", encoding="utf-8")
    print(f"remembered in {DIRECTOR_DIR}/{DIRECTOR_MEMORY}: {text}")


REPORT_KINDS = ("milestone", "progress", "blocker", "done")
MAX_REPORTS = 20
BRIEF_DIR = "briefs"

BRIEF = """# Brief: {workflow} on "{subject}"

You are running one workflow in a thread of its own. The person's main
conversation is with Aviator, the project's director, in session
`{director}`. Aviator started this thread so the detail of the work stays
here and out of its own context. Do the work here, with the person, who can
see and answer everything you say in this thread.

## The work

- Workflow: **{workflow}**. Use the `{skill}` skill and follow it.
- Subject: {subject}
- Dataset: `{data}`{exists}
- Target: {target}
{ask}
## Read first

{context}

## Who you may call

{participants}

## What to tell the director

Aviator needs the state of this work, not its transcript. Tell it only:
a step crossed, real progress worth knowing, a blocker, that you need the
person, and when you finish. Use your judgment about when; never send
everything. Each time:

1. `$PA report {data} --kind <milestone|progress|blocker|done> "<one line, pointing at the file>"`
   (this is what the run card and the project page show).
2. For a blocker, when you need the person, and when you finish, also wake
   Aviator: `sys_session_message` with `session_id` `{director}` and the same
   line, starting "Thread report:". (Not `sys_session_send`: that only reaches
   sessions you started, and Aviator started you.)

## Starting, pausing, finishing

- Start the run with `$PA flow {data} --scenario <the skill's folder> --session <your session id> --director {director} --brief {brief}`
  (your session id is `conversation_id` from `sys_session_get_info`).
- Keep `$PA flow` true as you go (`--step`, `--state needs-you`).
- If the person or Aviator says to pause, `$PA flow {data} --pause --note "<where we left off>"`,
  report it as progress, and stop. Resume and stop work the same way ("Runs" in the `view-kit` skill).
- When the last step is done: `$PA flow {data} --done`, then report with `--kind done`.
"""


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:48].strip("-") or "work"


def cmd_brief(args: argparse.Namespace) -> None:
    """Write the brief a director hands a thread, and print the thread's first message."""
    run = resolve_run(Path(args.workflow))
    manifest = run["manifest"]
    wid = str(manifest.get("workflow") or manifest.get("scenario") or Path(args.workflow).name)
    title = manifest.get("title") or wid
    subject = args.subject.strip()
    if not subject:
        raise PaError("--subject is empty")
    pattern = (manifest.get("dataset") or {}).get("path") or "data/{slug}.json"
    data = Path(args.data or pattern.replace("{slug}", _slug(subject)))
    brief = Path(BRIEF_DIR) / f"{data.stem}--{wid}.md"
    progress = Path(FLOW_DIR) / f"{data.stem}--{manifest.get('scenario') or wid}.json"
    cast = manifest.get("participants")
    if cast:
        people = ("Only these, with the `participants` skill, when the work needs what they are for: "
                  + ", ".join(f"`{c}`" for c in cast) + ".")
    else:
        people = "Anyone on the roster (`$PA who`), with the `participants` skill, when the work needs them."
    text = BRIEF.format(
        workflow=title, skill=wid, subject=subject, director=args.director, data=data.as_posix(),
        exists=" (it exists; continue it, do not start over)" if data.exists() else " (not started yet)",
        target=(args.target or "the workflow's usual finish").strip(),
        ask=f"- From Aviator: {args.ask.strip()}\n" if args.ask else "",
        context="\n".join(f"- `{c}`" for c in args.context or []) or "- Nothing was handed over. Ask the person for what you need.",
        participants=people, brief=brief.as_posix(),
    )
    _write_atomic(brief, text)
    if args.json:
        print(json.dumps({"brief": brief.as_posix(), "data": data.as_posix(), "progress": progress.as_posix(),
                          "title": f"{title}: {subject}", "workflow": wid}, indent=1))
        return
    print(f"Read your brief at `{brief.as_posix()}` and begin. It is repeated here.\n\n{text}")
    print(f"brief: {brief.as_posix()}\nrun: {progress.as_posix()}\ntitle: {title}: {subject}", file=sys.stderr)


# ------------------------------------------------------- projects and links

PROJECTS_DIR = "projects"
# A link is stored once, on the item it hangs from, and reads the other way
# from the far end (D-119): "handed-to" there is "came from" here.
LINK_TYPES = ("handed-to", "started", "relies-on")
PROJECT_STATES = ("shaping", "in-delivery", "shipped", "slipped", "paused", "stopped")
_PROJECT_KEYS = ("name", "goal", "area", "team", "state", "state_note")


def _project_path(name: str, folder: str | None = None) -> Path:
    return Path(folder or PROJECTS_DIR) / f"{_slug(name)}.json"


def _project_cards(folder: Path | None = None) -> dict[str, dict[str, Any]]:
    """Every project that has a file, by name: its goal, area, team and state."""
    folder = folder or Path(PROJECTS_DIR)
    cards: dict[str, dict[str, Any]] = {}
    for file in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        try:
            raw = json.loads(file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(raw, dict) and isinstance(raw.get("name"), str) and raw["name"].strip():
            cards[raw["name"].strip()] = {k: raw[k] for k in _PROJECT_KEYS if isinstance(raw.get(k), str) and raw[k]}
    return cards


def cmd_project(args: argparse.Namespace) -> None:
    """Say what a project is: its goal, the area it lives in, who runs it, how it stands (D-97)."""
    if not args.name:
        cards = _project_cards(Path(args.dir) if args.dir else None)
        if args.json:
            print(json.dumps(list(cards.values()), indent=1, ensure_ascii=False))
        elif not cards:
            print("no projects have a file yet")
        for card in cards.values() if not args.json else []:
            where = f" (in {card['area']})" if card.get("area") else ""
            state = f" [{card['state']}]" if card.get("state") else ""
            print(f"{card['name']}{where}{state}: {card.get('goal', 'no goal written')}")
        return
    path = _project_path(args.name, args.dir)
    changes = {key: getattr(args, key) for key in ("goal", "area", "team", "state", "state_note") if getattr(args, key) is not None}
    with _locked(path):
        try:
            current = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            current = {}
        if not isinstance(current, dict):
            current = {}
        if not changes and not args.data and not current:
            raise PaError(f"no project file for {args.name!r} yet; give it a --goal")
        if changes or not current or not current.get("id"):
            card = {**current, "name": current.get("name") or args.name.strip(), **changes, "updated": _now()}
            # A stable id and key from the first write (D-138): the name can change, these do not.
            card.setdefault("id", new_id("initiative"))
            card.setdefault("key", path.stem)
            if "state" in changes and "state_note" not in changes:
                card.pop("state_note", None)  # the note described the old state
            path.parent.mkdir(parents=True, exist_ok=True)
            _write_atomic(path, json.dumps(card, indent=1, ensure_ascii=False) + "\n")
            current = card
    for dataset in args.data or []:
        dpath = Path(dataset)
        with _locked(dpath):
            data = _load(dpath)
            data["project"] = current["name"]
            stamp = {"id": new_id("artifact"), "made": _now(), **(data.get("artifact") or {}), "initiative": current["id"]}
            data["artifact"] = _normal(stamp)
            _save(dpath, data)
            _render_views(dpath, data)
    if args.json:
        print(json.dumps(current, indent=1, ensure_ascii=False))
    else:
        print(f"{current['name']}: {current.get('goal', 'no goal written')}" + (f" · in {current['area']}" if current.get("area") else "")
              + (f" · {current['state']}" if current.get("state") else "") + f" ({path.as_posix()})")


def cmd_link(args: argparse.Namespace) -> None:
    """Hang a typed link to another project from one record (D-119)."""
    path = Path(args.data)
    target = args.to.strip()
    if not target:
        raise PaError("--to needs the other project's name")
    with _locked(path):
        data = _load(path)
        record = next((r for r in data["records"] if r.get("id") == args.id), None)
        if record is None:
            raise PaError(f"no record {args.id} in {path}")
        links = [l for l in record.get("links") or [] if isinstance(l, dict)]
        kept = [l for l in links if not (l.get("project") == target and l.get("type") == args.type)]
        if args.remove:
            if len(kept) == len(links):
                raise PaError(f"{args.id} has no {args.type} link to {target!r}")
        else:
            kept.append({"type": args.type, "project": target})
        if kept:
            record["links"] = kept
        else:
            record.pop("links", None)
        record["updated"] = _now()
        _save(path, data)
        views = _render_views(path, data)
    known = target in _project_cards()
    print(("removed" if args.remove else "linked") + f" {args.id} {args.type} {target!r}"
          + ("" if known or args.remove else f"; no project file for it yet (pa project {target!r} --goal ...)")
          + (f"; redrew {', '.join(views)}" if views else ""))


# ------------------------------------------- initiatives, artifacts and templates
#
# An initiative is a project with a goal (D-97): its card is
# `projects/<key>.json`. It gets a stable id the first time it is written
# (D-138), and owns a folder `projects/<key>/` for its shared intent document
# and its registers. Every artifact says which initiative it belongs to in a
# small stamp inside the file itself (frontmatter, a JSON block, or a script
# tag), so the registry is assembled by reading the files and nothing has to be
# kept in sync (D-140). Files that cannot carry a stamp are listed on the card
# under `refs`. A template is a folder with a `template.json` of one of three
# kinds: markdown, records or page (D-139). Spec:
# docs/product/initiatives-and-templates.md.

ID_PREFIXES = {"initiative": "ini", "artifact": "art"}
_ID_RE = re.compile(r"^(ini|art)_[0-9a-f]{32}$")
STAMP_KEYS = ("id", "initiative", "template", "stage", "status", "title", "from", "by", "made")
ARTIFACT_STATUSES = ("draft", "in-review", "final", "superseded")
ARTIFACT_ROOTS = ("data", "artifacts", "context", "projects", "briefs")
_STAMPABLE = (".md", ".json", ".html", ".htm")
TEMPLATE_FILE = "template.json"
TEMPLATE_KINDS = ("markdown", "records", "page")
REGISTER_TYPES = ("evidence", "question", "decision", "check")
REGISTERS_TEMPLATE = "initiative-registers"
INTENT_TEMPLATE = "initiative-intent"


def new_id(kind: str) -> str:
    """A stable id: a type prefix and a bare 32-character UUID, like upstream's project ids."""
    import uuid

    return f"{ID_PREFIXES[kind]}_{uuid.uuid4().hex}"


def _cards_with_paths(folder: Path | None = None) -> list[tuple[Path, dict[str, Any]]]:
    folder = folder or Path(PROJECTS_DIR)
    out = []
    for file in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        try:
            raw = json.loads(file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(raw, dict) and isinstance(raw.get("name"), str) and raw["name"].strip():
            out.append((file, raw))
    return out


def find_initiative(ref: str, folder: Path | None = None) -> tuple[Path, dict[str, Any]] | None:
    """An initiative by its id, its key or its name (any case)."""
    want = (ref or "").strip()
    if not want:
        return None
    for path, card in _cards_with_paths(folder):
        if want in (card.get("id"), card.get("key"), path.stem) or card["name"].strip().casefold() == want.casefold():
            return path, card
    return None


def _initiative_or_fail(ref: str) -> tuple[Path, dict[str, Any]]:
    found = find_initiative(ref)
    if not found:
        raise PaError(f"no initiative {ref!r}; list them with `pa project`, or make one with `pa project {ref!r} --goal ...`")
    path, card = found
    if not card.get("id"):  # a card written before ids: give it one now
        with _locked(path):
            card = {**card, "id": new_id("initiative"), "key": card.get("key") or path.stem}
            _write_atomic(path, json.dumps(card, indent=1, ensure_ascii=False) + "\n")
    return path, card


def initiative_folder(card_path: Path, card: dict[str, Any]) -> Path:
    return card_path.parent / str(card.get("key") or card_path.stem)


# --- stamps


def _split_frontmatter(text: str) -> tuple[list[str] | None, str]:
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---", 3)
    if end < 0:
        return None, text
    head = text[4:end]
    rest = text[end + 4:]
    if rest.startswith("\n"):
        rest = rest[1:]
    return head.splitlines(), rest


def _stamp_value(raw: str) -> Any:
    raw = raw.strip()
    if raw.startswith("["):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
    return raw.strip('"')


_HTML_STAMP = re.compile(r'<script type="application/json" id="pa-artifact">(.*?)</script>\n?', re.S)
_HTML_DATA = re.compile(r'<script type="application/json" id="pa-data">(.*?)</script>', re.S)


def _normal(stamp: dict[str, Any]) -> dict[str, Any]:
    out = {k: stamp[k] for k in STAMP_KEYS if stamp.get(k) not in (None, "", [])}
    for key in ("stage", "from"):
        if isinstance(out.get(key), str):
            out[key] = [s.strip() for s in out[key].split(",") if s.strip()]
    return out


def read_stamp(path: Path) -> dict[str, Any] | None:
    """What a file says about itself, or None. A drawn view reports the dataset it was drawn from."""
    suffix = path.suffix.lower()
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    if suffix == ".md":
        head, _ = _split_frontmatter(text)
        if head is None:
            return None
        meta = {}
        for line in head:
            key, sep, raw = line.partition(":")
            if sep and key.strip():
                meta[key.strip()] = _stamp_value(raw)
        if not meta.get("artifact"):
            return None
        meta["id"] = meta.pop("artifact")
        return _normal(meta)
    if suffix == ".json":
        try:
            raw = json.loads(text)
        except json.JSONDecodeError:
            return None
        stamp = raw.get("artifact") if isinstance(raw, dict) else None
        return _normal(stamp) if isinstance(stamp, dict) and stamp.get("id") else None
    if suffix in (".html", ".htm"):
        match = _HTML_STAMP.search(text)
        if match:
            try:
                stamp = json.loads(match.group(1))
            except json.JSONDecodeError:
                return None
            return _normal(stamp) if isinstance(stamp, dict) and stamp.get("id") else None
        match = _HTML_DATA.search(text)
        if match:  # a view drawn by pa render: a rendition of its dataset
            try:
                data = json.loads(match.group(1))
            except json.JSONDecodeError:
                return None
            stamp = data.get("artifact") if isinstance(data, dict) else None
            if isinstance(stamp, dict) and stamp.get("id"):
                return {"rendition_of": stamp["id"], "initiative": stamp.get("initiative", "")}
    return None


def write_stamp(path: Path, stamp: dict[str, Any]) -> None:
    """Write a stamp into the file, keeping everything else in it."""
    stamp = _normal(stamp)
    suffix = path.suffix.lower()
    if suffix == ".md":
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        head, body = _split_frontmatter(text)
        lines = head or []
        values = {("artifact" if k == "id" else k): v for k, v in stamp.items()}
        kept: list[str] = []
        for line in lines:
            key = line.partition(":")[0].strip()
            if key in values or key in ("artifact",) + STAMP_KEYS[1:]:
                continue
            kept.append(line)
        order = ["artifact"] + [k for k in STAMP_KEYS[1:]]
        ours = [f"{k}: {json.dumps(values[k], ensure_ascii=False) if isinstance(values[k], list) else values[k]}"
                for k in order if k in values]
        _write_atomic(path, "---\n" + "\n".join(ours + kept) + "\n---\n" + body)
        return
    if suffix == ".json":
        with _locked(path):
            raw = _read_json(path) if path.exists() else {}
            if not isinstance(raw, dict):
                raise PaError(f"{path}: only a JSON object can carry a stamp")
            raw["artifact"] = stamp
            if isinstance(raw.get("records"), list):
                _save(path, raw)
                _render_views(path, raw)
            else:
                _write_atomic(path, json.dumps(raw, indent=1, ensure_ascii=False) + "\n")
        return
    if suffix in (".html", ".htm"):
        text = path.read_text(encoding="utf-8")
        tag = f'<script type="application/json" id="pa-artifact">{_embed(stamp)}</script>\n'
        if _HTML_STAMP.search(text):
            text = _HTML_STAMP.sub(lambda _m: tag, text, count=1)
        elif "</head>" in text:
            text = text.replace("</head>", tag + "</head>", 1)
        else:
            text = tag + text
        _write_atomic(path, text)
        return
    raise PaError(f"{path}: a {suffix or 'plain'} file cannot carry a stamp; list it on the initiative with --initiative")


def _check_stages(stages: list[str]) -> None:
    known = [s["id"] for s in lifecycle_stages()]
    bad = [s for s in stages if known and s not in known and s != "any"]
    if bad:
        raise PaError(f"not a lifecycle stage: {', '.join(bad)} (stages: {', '.join(known)})")


def stamp_file(path: Path, *, initiative: str | None = None, template: str | None = None,
               stages: list[str] | None = None, status: str | None = None, title: str | None = None,
               sources: list[str] | None = None, by: str | None = None) -> dict[str, Any]:
    """Give a file its stamp, or change it. Keeps the id it already has."""
    current = read_stamp(path) or {}
    current.pop("rendition_of", None)
    stamp = {**current}
    stamp.setdefault("id", new_id("artifact"))
    stamp.setdefault("made", _now())
    if initiative is not None:
        stamp["initiative"] = _initiative_or_fail(initiative)[1]["id"] if initiative else ""
    if template:
        found = find_template(template)
        if not found:
            raise PaError(f"no template {template!r} (see `pa template list`)")
        stamp["template"] = f"{found['template']}@{found.get('version', 1)}"
        if stages is None and isinstance(found.get("stage"), list) and found["stage"] != ["any"]:
            stages = found["stage"]
    if stages is not None:
        _check_stages(stages)
        stamp["stage"] = stages
    if status:
        if status not in ARTIFACT_STATUSES:
            raise PaError(f"status must be one of {', '.join(ARTIFACT_STATUSES)}")
        stamp["status"] = status
    if title:
        stamp["title"] = title
    if sources:
        bad = [s for s in sources if not _ID_RE.match(s)]
        if bad:
            raise PaError(f"--from takes artifact ids (art_...), not {', '.join(bad)}")
        stamp["from"] = sorted(set((stamp.get("from") or []) + sources))
    if by:
        stamp["by"] = by
    write_stamp(path, stamp)
    return _normal(stamp)


def _add_ref(card_path: Path, entry: dict[str, Any]) -> dict[str, Any]:
    """List a file that cannot carry a stamp on the initiative's card."""
    with _locked(card_path):
        card = json.loads(card_path.read_text(encoding="utf-8"))
        refs = [r for r in card.get("refs") or [] if isinstance(r, dict) and r.get("path") != entry["path"]]
        old = next((r for r in card.get("refs") or [] if isinstance(r, dict) and r.get("path") == entry["path"]), {})
        merged = {**old, **{k: v for k, v in entry.items() if v not in (None, "", [])}}
        merged.setdefault("id", new_id("artifact"))
        merged.setdefault("made", _now())
        card["refs"] = refs + [merged]
        card["updated"] = _now()
        _write_atomic(card_path, json.dumps(card, indent=1, ensure_ascii=False) + "\n")
    return merged


def cmd_stamp(args: argparse.Namespace) -> None:
    path = Path(args.file)
    if not path.exists() and not args.ref:
        raise PaError(f"{path} does not exist")
    stages = args.stage if args.stage else None
    # The person's own documents in context/ are listed, never written into (D-140).
    theirs = bool(path.parts) and path.parts[0] == CONTEXT_DIR
    if args.ref or theirs or path.suffix.lower() not in _STAMPABLE:
        if not args.initiative:
            raise PaError(f"{path} cannot carry a stamp; give --initiative to list it on the initiative's card")
        card_path, card = _initiative_or_fail(args.initiative)
        if stages:
            _check_stages(stages)
        entry = _add_ref(card_path, {"path": path.as_posix(), "title": args.title, "stage": stages,
                                     "status": args.status, "by": args.by})
        print(f"{entry['id']} listed on {card['name']} ({card_path.as_posix()})")
        return
    stamp = stamp_file(path, initiative=args.initiative, template=args.template, stages=stages,
                       status=args.status, title=args.title, sources=args.source, by=args.by)
    where = stamp.get("initiative") or "no initiative yet"
    print(f"{stamp['id']} {path.as_posix()} ({where}" + (f", {stamp['template']}" if stamp.get("template") else "")
          + (f", {', '.join(stamp['stage'])}" if stamp.get("stage") else "") + ")")


def artifact_registry(root: Path | None = None) -> dict[str, Any]:
    """Every stamped file and listed ref under the workspace, assembled on demand."""
    root = root or Path.cwd()
    artifacts: dict[str, dict[str, Any]] = {}
    renditions: dict[str, list[str]] = {}
    duplicates: list[str] = []
    for top in ARTIFACT_ROOTS:
        base = root / top
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in _STAMPABLE or ".hangar" in path.parts:
                continue
            if top == PROJECTS_DIR and path.parent == base and path.suffix == ".json":
                continue  # an initiative card, not an artifact
            stamp = read_stamp(path)
            if not stamp:
                continue
            rel = path.relative_to(root).as_posix()
            if "rendition_of" in stamp:
                renditions.setdefault(stamp["rendition_of"], []).append(rel)
                continue
            if stamp["id"] in artifacts:
                duplicates.append(f"{stamp['id']} is in both {artifacts[stamp['id']]['path']} and {rel} (a copy kept its stamp; restamp one with a new id)")
                continue
            artifacts[stamp["id"]] = {**stamp, "path": rel}
    initiatives = {}
    for card_path, card in _cards_with_paths(root / PROJECTS_DIR):
        if card.get("id"):
            initiatives[card["id"]] = {k: card[k] for k in ("id", "key", "name", "goal", "area", "state") if card.get(k)}
        for ref in card.get("refs") or []:
            if isinstance(ref, dict) and ref.get("id"):
                artifacts.setdefault(ref["id"], {**_normal(ref), "path": ref.get("path", ""), "initiative": card.get("id", ""), "listed": True})
    for aid, paths in renditions.items():
        if aid in artifacts:
            artifacts[aid]["renditions"] = paths
    return {"initiatives": initiatives, "artifacts": list(artifacts.values()), "problems": duplicates}


def cmd_artifacts(args: argparse.Namespace) -> None:
    reg = artifact_registry()
    items = reg["artifacts"]
    if args.initiative:
        _, card = _initiative_or_fail(args.initiative)
        items = [a for a in items if a.get("initiative") == card["id"]]
    elif args.loose:
        items = [a for a in items if not a.get("initiative")]
    if args.stage:
        items = [a for a in items if args.stage in (a.get("stage") or [])]
    if args.template:
        items = [a for a in items if str(a.get("template", "")).split("@")[0] == args.template]
    if args.json:
        print(json.dumps({**reg, "artifacts": items}, indent=1, ensure_ascii=False))
        return
    names = {i: v.get("name", i) for i, v in reg["initiatives"].items()}
    if not items:
        print("no artifacts match")
    group = None
    for a in sorted(items, key=lambda a: (names.get(a.get("initiative", ""), "~"), a["path"])):
        g = names.get(a.get("initiative", ""), "Not in an initiative yet" if not a.get("initiative") else a["initiative"])
        if g != group:
            group = g
            print(f"\n## {g}")
        bits = [a.get("template", ""), ", ".join(a.get("stage") or []), a.get("status", "")]
        print(f"{a['path']}  {a['id']}" + (f"  ({'; '.join(b for b in bits if b)})" if any(bits) else ""))
        for r in a.get("renditions") or []:
            print(f"  drawn as {r}")
    for problem in reg["problems"]:
        print(f"problem: {problem}", file=sys.stderr)


# --- templates


def template_roots(workspace: Path | None = None) -> list[Path]:
    """Where templates live: the workspace's own, then each workflow's `templates/`."""
    workspace = workspace or default_workspace()
    roots = []
    here = Path.cwd() / "templates"
    shipped = KIT_DIR.parent.parent.parent / "workspace" / "templates"  # a demo folder has none of its own
    for root in [here, workspace / "templates"]:
        if root.is_dir() and root.resolve() not in [r.resolve() for r in roots]:
            roots.append(root)
    for folder in list_workflows(workspace).values():
        if (folder / "templates").is_dir():
            roots.append(folder / "templates")
    if shipped.is_dir() and shipped.resolve() not in [r.resolve() for r in roots]:
        roots.append(shipped)
    return roots


def list_templates(workspace: Path | None = None) -> dict[str, dict[str, Any]]:
    """Every template by id, first found wins. Older artifact pages count as page templates."""
    found: dict[str, dict[str, Any]] = {}
    for root in template_roots(workspace):
        for folder in sorted(p for p in root.iterdir() if p.is_dir()):
            mpath = folder / TEMPLATE_FILE
            if not mpath.is_file():
                continue
            try:
                manifest = _read_json(mpath)
            except PaError:
                manifest = {}
            tid = manifest.get("template") if isinstance(manifest, dict) else None
            tid = tid or folder.name
            found.setdefault(tid, {**(manifest if isinstance(manifest, dict) else {}), "template": tid, "folder": str(folder)})
        legacy = root / "artifacts"
        for page_file in sorted(legacy.glob("*.html")) if legacy.is_dir() else []:
            text = page_file.read_text(encoding="utf-8")
            title = re.search(r"<title>(.*?)</title>", text, re.S)
            desc = re.search(r'<meta name="description" content="([^"]*)"', text)
            found.setdefault(page_file.stem, {
                "template": page_file.stem, "version": 1, "kind": "page", "legacy": True,
                "title": title.group(1).strip() if title else page_file.stem,
                "summary": desc.group(1) if desc else "", "stage": ["any"],
                "file": page_file.name, "out": f"artifacts/{{slug}}-{page_file.stem}.html", "folder": str(legacy),
            })
    for t in found.values():
        stage = t.get("stage")
        t["stage"] = [stage] if isinstance(stage, str) else (stage if isinstance(stage, list) else ["any"])
    return found


def find_template(ref: str, workspace: Path | None = None) -> dict[str, Any] | None:
    tid = ref.split("@", 1)[0].strip()
    return list_templates(workspace).get(tid)


def template_problems(t: dict[str, Any]) -> list[str]:
    """What is wrong with one template: the same rules `pa check` would apply."""
    name, folder, problems = t["template"], Path(t["folder"]), []
    kind = t.get("kind")
    if kind not in TEMPLATE_KINDS:
        return [f"{name}: kind must be one of {', '.join(TEMPLATE_KINDS)}"]
    for key in ("title", "summary", "out"):
        if not t.get(key):
            problems.append(f"{name}: missing {key}")
    if not isinstance(t.get("version", 1), int) or t.get("version", 1) < 1:
        problems.append(f"{name}: version must be a whole number from 1")
    stages = [s["id"] for s in lifecycle_stages()]
    bad = [s for s in t["stage"] if stages and s not in stages and s != "any"]
    if bad:
        problems.append(f"{name}: stage {', '.join(bad)} is not a lifecycle stage")
    if kind in ("markdown", "page"):
        file = folder / str(t.get("file") or "")
        if not t.get("file") or not file.is_file():
            problems.append(f"{name}: file {t.get('file')!r} is missing")
        else:
            text = file.read_text(encoding="utf-8")
            if re.search(r"""(src|href)\s*=\s*["']?https?://|url\(\s*["']?https?://|@import\s+["']?https?://""", text):
                problems.append(f"{name}: {file.name} loads something from the web; templates must work offline")
            if kind == "markdown":
                seen = set()
                for section in t.get("sections") or []:
                    if not isinstance(section, dict) or not section.get("id") or not section.get("heading"):
                        problems.append(f"{name}: every section needs an id and a heading")
                        continue
                    if section["id"] in seen:
                        problems.append(f"{name}: section id {section['id']!r} is used twice")
                    seen.add(section["id"])
                    if not re.search(rf"^#+ {re.escape(section['heading'])}\s*$", text, re.M):
                        problems.append(f"{name}: {file.name} has no heading '{section['heading']}'")
                    owner = section.get("owner", "any")
                    if stages and owner not in stages and owner != "any":
                        problems.append(f"{name}: section {section['id']} owner {owner!r} is not a lifecycle stage")
                if not t.get("sections"):
                    problems.append(f"{name}: a markdown template lists its sections")
    if kind == "records":
        spath = folder / str(t.get("schemas") or "")
        if not t.get("schemas") or not spath.is_file():
            problems.append(f"{name}: schemas {t.get('schemas')!r} is missing")
        else:
            try:
                schemas = _read_json(spath)
                if not isinstance(schemas, dict) or not schemas:
                    problems.append(f"{name}: schemas must name at least one record type")
            except PaError as err:
                problems.append(f"{name}: {err}")
        for vname, vrel in (t.get("views") or {}).items():
            vpath = folder / str(vrel)
            if not vpath.is_file():
                problems.append(f"{name}: view {vname} file {vrel} is missing")
                continue
            try:
                problems += _check_spec(_read_json(vpath), f"{name}/{vrel}")
            except PaError as err:
                problems.append(f"{name}: {err}")
    return problems


def _fill_out(pattern: str, card: dict[str, Any] | None, title: str) -> Path:
    if "{key}" in pattern and not card:
        raise PaError(f"this template lives in an initiative's folder ({pattern}); give --initiative")
    return Path(pattern.replace("{key}", str((card or {}).get("key", ""))).replace("{slug}", _slug(title)))


def new_from_template(tid: str, *, initiative: str | None = None, out: str | None = None,
                      title: str | None = None, by: str | None = None, force: bool = False) -> tuple[Path, dict[str, Any]]:
    t = find_template(tid)
    if not t:
        raise PaError(f"no template {tid!r} (see `pa template list`)")
    problems = template_problems(t)
    if problems:
        raise PaError("the template has problems:\n  " + "\n  ".join(problems))
    card_path, card = _initiative_or_fail(initiative) if initiative else (None, None)
    title = (title or (card or {}).get("name") or t["title"]).strip()
    path = Path(out) if out else _fill_out(t["out"], card, title)
    if path.exists() and not force:
        raise PaError(f"{path} already exists (use --force to replace it, or pa stamp to adopt it)")
    path.parent.mkdir(parents=True, exist_ok=True)
    folder = Path(t["folder"])
    if t["kind"] == "markdown":
        text = (folder / t["file"]).read_text(encoding="utf-8").replace("{title}", title)
        _, body = _split_frontmatter(text)
        _write_atomic(path, body)
    elif t["kind"] == "page":
        _write_atomic(path, (folder / t["file"]).read_text(encoding="utf-8"))
    else:
        data = {"dataset": path.stem, "title": title, "records": []}
        if card:
            data["project"] = card["name"]
        with _locked(path):
            _save(path, data)
    stamp = stamp_file(path, initiative=initiative or None, template=t["template"], title=title, by=by, status="draft")
    return path, stamp


def cmd_template(args: argparse.Namespace) -> None:
    templates = list_templates()
    if args.template_command == "list":
        items = [t for t in templates.values() if not args.stage or args.stage in t["stage"] or "any" in t["stage"]]
        if args.json:
            print(json.dumps(items, indent=1, ensure_ascii=False))
            return
        for t in items:
            print(f"{t['template']}@{t.get('version', 1)} ({t.get('kind')}; {', '.join(t['stage'])}): {t.get('title', '')}"
                  + (" [older page template]" if t.get("legacy") else ""))
        return
    if args.template_command == "show":
        t = find_template(args.id)
        if not t:
            raise PaError(f"no template {args.id!r}")
        print(json.dumps(t, indent=1, ensure_ascii=False))
        return
    if args.template_command == "check":
        chosen = [find_template(args.id)] if args.id else list(templates.values())
        if args.id and not chosen[0]:
            raise PaError(f"no template {args.id!r}")
        problems = [p for t in chosen for p in template_problems(t)]  # type: ignore[arg-type]
        for p in problems:
            print(p)
        if problems:
            raise PaError(f"{len(problems)} problem{'s' if len(problems) != 1 else ''}")
        print(f"{len(chosen)} template{'s' if len(chosen) != 1 else ''} ok")
        return
    path, stamp = new_from_template(args.id, initiative=args.initiative, out=args.out, title=args.title,
                                    by=args.by, force=args.force)
    print(f"made {path.as_posix()} from {stamp.get('template')} ({stamp['id']})")


# --- registers: the checkable layer every skill reads and adds to


def registers_path(card_path: Path, card: dict[str, Any]) -> Path:
    return initiative_folder(card_path, card) / "registers.json"


def _guard_decisions(data: dict[str, Any], records: list[dict[str, Any]], changes: dict[str, Any]) -> None:
    """Decisions in an initiative's registers are never edited, only superseded."""
    template = str((data.get("artifact") or {}).get("template", ""))
    if not template.startswith(REGISTERS_TEMPLATE + "@"):
        return
    allowed = {"status", "superseded_by", "updated"}
    for record in records:
        if record.get("type") == "decision" and set(changes) - allowed:
            raise PaError(f"{record.get('id')} is a decision: add a new one with `pa register ... decision --supersedes {record.get('id')}` instead of editing it")


def cmd_register(args: argparse.Namespace) -> None:
    card_path, card = _initiative_or_fail(args.initiative)
    path = registers_path(card_path, card)
    if not path.exists():
        new_from_template(REGISTERS_TEMPLATE, initiative=card["id"], out=str(path), title=f"{card['name']}: registers")
    text = " ".join(args.text.split())
    if not text:
        raise PaError("say what it is in a line")
    record: dict[str, Any] = {"type": args.type, "title": text, "updated": _now()}
    for key in ("source", "owner", "by", "note"):
        if getattr(args, key):
            record[key] = getattr(args, key)
    if args.type == "evidence" and not args.source:
        raise PaError("evidence needs --source: where it came from, so it stays attached")
    if args.type == "question":
        record["status"] = args.status or "open"
        record["blocking"] = bool(args.blocking)
    elif args.type == "decision":
        record["status"] = "decided"
    elif args.type == "evidence":
        record["status"] = "recorded"
    elif args.type == "check":
        record["status"] = args.status or "unknown"
    elif args.status:
        record["status"] = args.status
    if args.stage:
        _check_stages(args.stage)
        record["stage"] = args.stage
    with _locked(path):
        data = _load(path)
        record["id"] = _next_id(data, args.type)
        if args.supersedes:
            old = next((r for r in data["records"] if r.get("id") == args.supersedes), None)
            if not old or old.get("type") != args.type:
                raise PaError(f"no {args.type} {args.supersedes} to supersede")
            old["status"] = "superseded"
            old["superseded_by"] = record["id"]
            record["supersedes"] = args.supersedes
        data["records"].append(record)
        _save(path, data)
        views = _render_views(path, data)
    print(f"{record['id']} {args.type} on {card['name']}: {text}" + (f"; redrew {', '.join(views)}" if views else ""))


def cmd_report(args: argparse.Namespace) -> None:
    """One line from a run to its director: a milestone, progress, a blocker, or done (D-118)."""
    path = Path(args.data)
    text = " ".join(args.text.split())
    if not text:
        raise PaError("a report needs one line of text")
    if len(text) > 280:
        raise PaError("a report is one line, at most 280 characters; point at the file for the rest")
    with _locked(path):
        data = _load(path)
        flow = data.get("flow") or {}
        if not flow.get("steps"):
            raise PaError("no workflow on this dataset yet; start it with pa flow --scenario first")
        reports = list(flow.get("reports") or [])
        reports.append({"at": _now(), "kind": args.kind, "step": flow.get("current", 1), "text": text})
        flow["reports"] = reports[-MAX_REPORTS:]
        if args.kind == "blocker" and (flow.get("state") or "working") == "working":
            flow["state"] = "waiting"
        data["flow"] = flow
        _save(path, data)
    print(f"reported ({args.kind}): {text}")


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
    # A linked record shows a chip naming the other project and its state (D-119).
    linked = {l.get("project") for r in data.get("records") or [] if isinstance(r, dict)
              for l in r.get("links") or [] if isinstance(l, dict)}
    if linked:
        cards = _project_cards()
        public["projects"] = {name: cards[name] for name in sorted(n for n in linked if isinstance(n, str)) if name in cards}
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



# ------------------------------------------------------------------- demos
#
# "Scenario you build, demo you fly." Flying a scenario makes a demo folder
# (by default `<workspace>/demos/<scenario id>/`) that a real session runs in:
# the scenario's context/ documents, a starting dataset, the roster with each
# cast member's story notes, and `.demo/` with a snapshot of the scenario and
# a cursor. The agent there calls `pa demo next` after each user message and
# gets the next turn of the script: canned turns to play word for word, live
# turns to answer for real. See references/script.md.

DEMOS_DIR = "demos"
DEMO_STATE = ".demo"
CAST_DIR = "cast"
CONTEXT_DIR = "context"

DEMO_CLAUDE = """# Demo: {title}

This folder is a flown demo of the scenario **{title}**. {summary}
The people, documents and data here are invented for the story.

How to run it:

1. After every message from the user, run `{pa} demo next` before you answer.
   It prints the next turn of the script and does the data changes itself.
2. Do what the turn says, in order. A **canned** line is said word for word,
   with nothing added. A **live** turn is yours: answer it for real, the way
   you would outside a demo, using the workflow skill `{workflow}`; the written
   line is only a guide to what the turn is about.
3. Participants: a canned participant line is passed on in a participant block
   word for word (participants skill, step 4), with no session behind it. A
   live participant turn means calling them for real (participants skill,
   step 2); what they know in this story is in their file under
   "In this story".
4. If the user says something the script did not expect, answer them for real
   and do not run `demo next` again until they come back to the story.
5. When `demo next` says the script is over, carry on as a normal session.

Do not copy anything from `.demo/` into the conversation, and do not edit it.
`{pa} demo status` says where the story is.
"""


def demo_dir(workspace: Path, sid: str) -> Path:
    return workspace / DEMOS_DIR / sid


def demo_state(folder: Path) -> dict[str, Any] | None:
    path = folder / DEMO_STATE / "demo.json"
    return _read_json(path) if path.is_file() else None


def _save_demo_state(folder: Path, state: dict[str, Any]) -> None:
    _write_atomic(folder / DEMO_STATE / "demo.json", json.dumps(state, indent=1, ensure_ascii=False) + "\n")


def scenario_opening(sdir: Path, scenario: dict[str, Any] | None = None) -> str:
    """The line the user starts the demo with: `opening` in scenario.json, else the script's first You line."""
    scenario = scenario if scenario is not None else _read_json(sdir / SCENARIO_FILE)
    if scenario.get("opening"):
        return str(scenario["opening"])
    script = sdir / str(scenario.get("script") or "script.md")
    if script.is_file():
        for line in script.read_text(encoding="utf-8").splitlines():
            m = _SPEECH.match(line.strip())
            if m and m.group(1).strip().lower() in ("you", "pm"):
                return m.group(2).strip()
    return ""


def _turn_count(steps: list[dict[str, Any]]) -> int:
    return max(1, sum(1 for s in steps if "pm" in s or s.get("await")))


def _apply_start(data: dict[str, Any], start: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """(the full fixture after `start: set`, the starting dataset without hidden records)."""
    full = json.loads(json.dumps(data))
    full.pop("views", None)
    rule = start.get("set")
    if rule:
        for record in full["records"]:
            if all(record.get(k) == v for k, v in rule["where"].items()):
                record.update(rule["fields"])
    shown = json.loads(json.dumps(full))
    hide = set(start.get("hide") or [])
    shown["records"] = [r for r in shown["records"] if r.get("type") not in hide]
    return full, shown


def fly_demo(scenario_dir: Path, workspace: Path, *, reset: bool = False, dest: Path | None = None,
             live_turns: bool | None = None) -> dict[str, Any]:
    """Make (or keep) the demo folder for a scenario. Returns what the caller needs to open a session.

    With `reset`, an existing demo folder is emptied and set up again from the
    scenario as it is now. Without it, an existing demo is kept as it is.
    `live_turns` False plays every turn canned, even ones the script marks
    live (the Library's "Live turns" switch, D-85); None keeps what was set.
    """
    import shutil

    scenario_dir = Path(scenario_dir)
    scenario = _read_json(scenario_dir / SCENARIO_FILE)
    sid = str(scenario.get("scenario") or scenario_dir.name)
    folder = dest or demo_dir(workspace, sid)
    existing = demo_state(folder)
    if existing and not reset:
        if live_turns is not None and existing.get("live_turns", True) != live_turns:
            existing["live_turns"] = live_turns
            _save_demo_state(folder, existing)
        return {**_demo_summary(folder, existing), "created": False}
    if folder.exists():
        if any(folder.iterdir()) and not (folder / DEMO_STATE).is_dir():
            raise PaError(f"{folder} exists and is not a demo folder; move it away first")
        shutil.rmtree(folder)
    run = resolve_run(scenario_dir, workspace)
    folder.mkdir(parents=True)
    state_dir = folder / DEMO_STATE
    _copy_folder(scenario_dir, state_dir / "scenario")
    for sub in ("artifacts", "data", "progress", CONTEXT_DIR):
        (folder / sub).mkdir(exist_ok=True)
    # Invented documents the story starts from.
    if (scenario_dir / CONTEXT_DIR).is_dir():
        shutil.copytree(scenario_dir / CONTEXT_DIR, folder / CONTEXT_DIR, dirs_exist_ok=True)
    # The roster, with what each cast member knows in this story.
    roster_src = workspace / PARTICIPANTS_DIR
    if roster_src.is_dir():
        shutil.copytree(roster_src, folder / PARTICIPANTS_DIR, dirs_exist_ok=True)
    primed = []
    for note in sorted((scenario_dir / CAST_DIR).glob("*.md")) if (scenario_dir / CAST_DIR).is_dir() else []:
        target = folder / PARTICIPANTS_DIR / note.name
        if target.is_file():
            story = note.read_text(encoding="utf-8").strip()
            text = target.read_text(encoding="utf-8").rstrip()
            _write_atomic(target, f"{text}\n\n## In this story\n\n{story}\n")
            primed.append(note.stem)
    # A workflow built in the Hangar travels with the demo; shipped ones reach every session anyway.
    wdir = run["workflow_dir"]
    if not is_builtin(workspace, wdir):
        _copy_folder(wdir, folder / ".claude" / "skills" / wdir.name)
    # The starting dataset, and the whole fixture that canned turns reveal records from.
    manifest = run["manifest"]
    dataset = None
    fixture = (manifest.get("fixtures") or {}).get("dataset")
    script = _read_script(scenario_dir / str(manifest.get("script") or "script.md"), _participants(folder / PARTICIPANTS_DIR))
    if fixture:
        full, shown = _apply_start(_load(scenario_dir / fixture), script.get("start") or {})
        dataset = f"data/{Path(fixture).stem}.json"
        _save(state_dir / "full.json", full)
        _save(folder / dataset, shown)
    pa_cmd = f"python3 {Path(__file__).resolve()}"
    title = str(scenario.get("title") or sid)
    _write_atomic(folder / "CLAUDE.md", DEMO_CLAUDE.format(
        title=title, summary=str(scenario.get("summary") or ""), pa=pa_cmd, workflow=run["workflow_id"]))
    state = {
        "scenario": sid,
        "title": title,
        "workflow": run["workflow_id"],
        "dataset": dataset,
        "status_field": ((manifest.get("dataset") or {}).get("status_field")) or "status",
        "cursor": 0,
        "turn": 0,
        "turns": _turn_count(script["steps"]),
        "opening": scenario_opening(scenario_dir, scenario),
        "primed": primed,
        "live_turns": True if live_turns is None else bool(live_turns),
        "started": _now(),
    }
    _save_demo_state(folder, state)
    return {**_demo_summary(folder, state), "created": True}


def _demo_summary(folder: Path, state: dict[str, Any]) -> dict[str, Any]:
    return {
        "folder": str(folder),
        "scenario": state.get("scenario"),
        "title": state.get("title"),
        "opening": state.get("opening", ""),
        "turn": state.get("turn", 0),
        "turns": state.get("turns", 0),
        "started": state.get("started"),
        "finished": bool(state.get("finished")),
        "live_turns": bool(state.get("live_turns", True)),
    }


def _demo_doc(folder: Path, sdir: Path, fixtures: dict[str, Any], name: str) -> str:
    """The working copy in artifacts/ of a document the script opens. Nobody changes context/, so comments go on the copy."""
    rel = str(fixtures.get(name) or name)
    target = Path("artifacts") / Path(rel).name
    source = folder / rel if (folder / rel).is_file() else sdir / rel
    if source.is_file() and not (folder / target).exists():
        (folder / target).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return str(target)


def _demo_data(folder: Path, state: dict[str, Any], step: dict[str, Any]) -> str | None:
    """Apply a step's data changes to the demo's dataset; a line saying what changed, or None."""
    keys = ("reveal", "restore", "status", "patch", "fact")
    empty = step.get("canvas") and step.get("data") == "empty"
    if not state.get("dataset") or not (any(k in step for k in keys) or empty):
        return None
    path = folder / state["dataset"]
    full = _load(folder / DEMO_STATE / "full.json")
    by_full = {r.get("id"): r for r in full["records"]}
    done = []
    with _locked(path):
        data = _load(path)
        index = {r.get("id"): i for i, r in enumerate(data["records"])}

        def put(record: dict[str, Any]) -> None:
            if record.get("id") in index:
                data["records"][index[record["id"]]] = json.loads(json.dumps(record))
            else:
                index[record["id"]] = len(data["records"])
                data["records"].append(json.loads(json.dumps(record)))

        if empty:
            data["records"] = []
            index.clear()
            done.append("emptied the dataset")
        for rid in step.get("reveal") or []:
            if rid in by_full:
                put(by_full[rid])
        if step.get("reveal"):
            done.append("added " + ", ".join(step["reveal"]))
        for rid in step.get("restore") or []:
            if rid in by_full:
                put(by_full[rid])
                kids = [r for r in full["records"] if r.get("parent") == rid]
                while kids:
                    kid = kids.pop()
                    put(kid)
                    kids += [r for r in full["records"] if r.get("parent") == kid.get("id")]
        if step.get("restore"):
            done.append("restored " + ", ".join(step["restore"]))
        if step.get("status"):
            field = state.get("status_field") or "status"
            for rid in step["status"]["ids"]:
                if rid in index:
                    data["records"][index[rid]][field] = step["status"]["to"]
            done.append(f"set {field}={step['status']['to']} on " + ", ".join(step["status"]["ids"]))
        for patch in step.get("patch") or []:
            if patch["id"] in index:
                record = data["records"][index[patch["id"]]]
                for key, value in patch.items():
                    if value is None:
                        record.pop(key, None)
                    else:
                        record[key] = value
                done.append(f"changed {patch['id']}")
        if step.get("fact"):
            data.update(step["fact"])
            done.append("changed " + ", ".join(step["fact"]))
        _save(path, data)
        _render_views(path, data)
    return "; ".join(done)


def _demo_lines(folder: Path, state: dict[str, Any], steps: list[dict[str, Any]], run: dict[str, Any], roster: dict[str, dict[str, Any]], pa_cmd: str) -> list[str]:
    manifest, sdir, wdir = run["manifest"], folder / DEMO_STATE / "scenario", run["workflow_dir"]
    fixtures = manifest.get("fixtures") or {}
    views = manifest.get("views") or {}
    dataset = state.get("dataset")

    def name(pid: str) -> str:
        return "Aviator" if pid == "aviator" else str((roster.get(pid) or {}).get("name") or pid)

    def spec(view: str) -> str:
        rel = views.get(view)
        return str((wdir / rel).resolve()) if rel else view

    lines: list[str] = []
    live_on = state.get("live_turns", True)
    for step in steps:
        live = step.get("live") if live_on else None
        guide = "" if live in (None, True) else f" ({live})"
        if "agent" in step:
            if live:
                lines.append(f"LIVE: answer this part yourself, for real{guide}. The script's line, as a guide only: \"{step['agent']}\"")
            else:
                lines.append(f"Say, word for word: \"{step['agent']}\"")
        if "says" in step:
            who = name(step["from"])
            if live:
                lines.append(f"LIVE: ask {who} for real and pass on their answer{guide}. The script's line, as a guide only: \"{step['says']}\"")
            else:
                person = roster.get(step["from"]) or {}
                head = "\n".join(f"{k}: {person[k]}" for k in ("name", "kind", "role") if person.get(k))
                fence = "````" if "```" in step["says"] else "```"
                lines.append(f"Canned line from {who}. Put this block in your reply exactly as it is (no session behind it):\n{fence}participant\n{head}\n---\n{step['says']}\n{fence}")
        if step.get("call"):
            ask = f" They are asked: {step['ask']}" if step.get("ask") else ""
            lines.append(f"Call in {name(step['call'])}: say in one line that you are bringing them in.{ask} Their lines below are canned unless a step says it is live.")
        if step.get("doc"):
            path = _demo_doc(folder, sdir, fixtures, step["doc"])
            lines.append(f"Open {path} in the canvas with ui_open_file" + (f" (tab title \"{step['title']}\")." if step.get("title") else "."))
        if step.get("comment"):
            c = step["comment"]
            doc = _demo_doc(folder, sdir, fixtures, c["doc"]) if c.get("doc") else "the open document"
            if c.get("resolve"):
                lines.append(f"Resolve the comment on \"{c['resolve']}\": find its thread with {pa_cmd} review show {doc}, then {pa_cmd} review resolve {doc} <thread>.")
            else:
                lines.append(f"Comment as {name(c['by'])}: {pa_cmd} review comment {doc} --by {c['by']} --quote \"{c['on']}\" --text \"{c['text']}\"")
        if step.get("canvas"):
            out = f"artifacts/{step['canvas']}.html"
            title = f" --title \"{step['title']}\"" if step.get("title") else ""
            data = f" --data {dataset}" if dataset else ""
            lines.append(f"Show the {step['canvas']} view in the canvas: {pa_cmd} render {spec(step['canvas'])}{data} --out {out}{title}, then ui_open_file {out}" + (f" (opened by {name(step['from'])})." if step.get("from") else "."))
        if step.get("tab"):
            lines.append(f"Bring the \"{step['tab']}\" tab to the front (ui_open_file on its file again).")
        if step.get("widget"):
            out = f"artifacts/{step['widget']}-chat.html"
            rec = f" --record {step['record']}" if step.get("record") else ""
            data = f" --data {dataset}" if dataset else ""
            by = f" Show it as from {name(step['from'])}." if step.get("from") else ""
            lines.append(f"Put the {step['widget']} view in the chat: {pa_cmd} render {spec(step['widget'])}{data} --host chat{rec} --out {out}, and put the block it prints in your reply.{by}")
        changed = _demo_data(folder, state, step)
        if changed:
            lines.append(f"(Done for you: {changed}. The views redraw on their own.)")
        if step.get("apply"):
            lines.append("The user's edits in the canvas are already saved; say what changed if the script's next line refers to it.")
        if step.get("end_call") is not None:
            result = str(step["end_call"]).rstrip(".") if step["end_call"] is not True else ""
            lines.append("End the call" + (f" with the result: {result}" if result else "") + ".")
        if "task" in step:
            lines.append(f"Progress line: {step['task']}" if step["task"] else "Progress line: clear it.")
        if step.get("hint"):
            lines.append(f"Suggest to the user, in one short line: {step['hint']}")
        if step.get("await") == "submit":
            lines.append("Then stop and wait for the user to answer the view in the chat.")
        elif step.get("await"):
            lines.append("Then stop and wait for the user.")
    return lines


def demo_next(folder: Path) -> str:
    """Advance the demo by one turn and say what to do."""
    state = demo_state(folder)
    if state is None:
        raise PaError(f"{folder} is not a demo folder (no {DEMO_STATE}/demo.json). Fly the scenario from the Hangar first.")
    sdir = folder / DEMO_STATE / "scenario"
    run = resolve_run(sdir, folder)
    roster, _ = _eligible(run["manifest"], _participants(folder / PARTICIPANTS_DIR), "scenario.json")
    script = _read_script(sdir / str(run["manifest"].get("script") or "script.md"), roster)
    steps = script["steps"]
    i = int(state.get("cursor") or 0)
    if i >= len(steps):
        state["finished"] = True
        _save_demo_state(folder, state)
        return "The script is over. Carry on as a normal session from here."
    turn: list[dict[str, Any]] = []
    expected = None
    if i == 0:
        while i < len(steps) and "pm" not in steps[i]:
            turn.append(steps[i])
            i += 1
    if i < len(steps) and "pm" in steps[i]:
        expected = steps[i]["pm"]
        i += 1
    while i < len(steps) and "pm" not in steps[i]:
        turn.append(steps[i])
        i += 1
        if steps[i - 1].get("await"):
            break
    pa_cmd = f"python3 {Path(__file__).resolve()}"
    state["cursor"] = i
    state["turn"] = int(state.get("turn") or 0) + 1
    out = [f"Demo {state.get('title')}: turn {state['turn']} of {state.get('turns')}."]
    if expected:
        out.append(f"The script expected the user to say: \"{expected}\". If they said something clearly different, answer them for real instead and leave the rest of this turn for when they come back to the story.")
    lines = _demo_lines(folder, state, turn, run, roster, pa_cmd)
    out += [f"{n}. {line}" for n, line in enumerate(lines, 1)] or ["Nothing to do this turn but answer naturally."]
    if i >= len(steps):
        state["finished"] = True
        out.append("This was the last turn. After it, carry on as a normal session.")
    _save_demo_state(folder, state)
    return "\n".join(out)


def cmd_demo(args: argparse.Namespace) -> None:
    folder = Path(args.dir or ".")
    if args.action == "next":
        print(demo_next(folder))
        return
    if args.action == "fly":
        if not args.scenario:
            raise PaError("say which scenario folder to fly: pa demo fly --scenario scenarios/<id>")
        ws = Path(args.workspace) if args.workspace else _workspace_of_scenario(Path(args.scenario))
        info = fly_demo(Path(args.scenario), ws, reset=args.reset, dest=Path(args.dir) if args.dir else None,
                        live_turns=False if args.canned else None)
        print(json.dumps(info, indent=1, ensure_ascii=False))
        return
    state = demo_state(folder)
    if state is None:
        raise PaError(f"{folder} is not a demo folder")
    info = _demo_summary(folder, state)
    print(json.dumps(info, indent=1, ensure_ascii=False))

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
        _guard_decisions(data, records, changes)
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


def _workspace_for_checks(run: dict[str, Any]) -> Path:
    sdir = run.get("scenario_dir")
    return _workspace_of_scenario(sdir) if sdir is not None else default_workspace()


# ------------------------------------------------------------------ routing
#
# Each workflow says when it fits in a `routing` block of its manifest, so the
# director routes from data and never names a workflow (D-120). The stages a
# workflow can serve live in the workspace's frameworks/lifecycle.json; the
# strictness levels are defined once, here (D-130).

LIFECYCLE_FILE = Path("frameworks") / "lifecycle.json"
STRICTNESS = {
    "light": "Light touch: follows the person's lead, one nudge where the method would differ, skips steps they wave off.",
    "guide": "Guide: keeps the method's order and asks for what is missing, but bends on pace, wording and how many questions at once.",
    "by-the-book": "By the book: every step in order, nothing skipped without the person saying so, gaps block the next step.",
}
ROUTING_EXAMPLE_KINDS = ("start", "offer", "open")


def lifecycle_stages(workspace: Path | None = None) -> list[dict[str, Any]]:
    """The lifecycle stages in order, or [] when the workspace has no lifecycle file."""
    path = (workspace or default_workspace()) / LIFECYCLE_FILE
    if not path.is_file():
        return []
    stages = _read_json(path).get("stages")
    return [s for s in stages if isinstance(s, dict) and s.get("id")] if isinstance(stages, list) else []


def _strings(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(v, str) and v.strip() for v in value)


def routing_problems(workflow: dict[str, Any], name: str, stages: list[str], required: bool) -> list[str]:
    """What is wrong with a manifest's routing block. Required for a workflow people are shown."""
    routing = workflow.get("routing")
    if routing is None:
        return [f"{name}: missing routing (when it fits, its stage and examples), so Aviator cannot offer it"] if required else []
    if not isinstance(routing, dict):
        return [f"{name}: routing must be an object"]
    where, problems = f"{name}: routing", []
    if not _strings(routing.get("when")):
        problems.append(f"{where}.when must list at least one situation it fits")
    if "not_when" in routing and not _strings(routing["not_when"]):
        problems.append(f"{where}.not_when must be a list of sentences")
    for key in ("needs", "offer"):
        if key in routing and not (isinstance(routing[key], str) and routing[key].strip()):
            problems.append(f"{where}.{key} must be a sentence")
    stage = routing.get("stage")
    if not (isinstance(stage, str) and stage.strip()):
        problems.append(f"{where}.stage is missing")
    elif stages and stage not in stages and stage != "any":  # "any": a move, usable at every stage
        problems.append(f"{where}.stage {stage!r} is not a lifecycle stage ({', '.join(stages)})")
    examples = routing.get("examples")
    if not isinstance(examples, dict) or not any(_strings(examples.get(k)) for k in ROUTING_EXAMPLE_KINDS):
        problems.append(f"{where}.examples needs prompts under start, offer or open")
    else:
        for kind, prompts in examples.items():
            if kind not in ROUTING_EXAMPLE_KINDS:
                problems.append(f"{where}.examples.{kind}: use start, offer or open")
            elif not _strings(prompts):
                problems.append(f"{where}.examples.{kind} must be a list of prompts")
    persona = routing.get("persona")
    if persona is not None:
        if not isinstance(persona, dict):
            problems.append(f"{where}.persona must be an object")
        else:
            if persona.get("strictness", "guide") not in STRICTNESS:
                problems.append(f"{where}.persona.strictness must be one of {', '.join(STRICTNESS)}")
            if "invariants" in persona and not _strings(persona["invariants"]):
                problems.append(f"{where}.persona.invariants must be a list of rules")
    return problems


# What kind of skill a workflow is (D-153): one optional field, kept loose. A
# workflow without it is an arc; an unknown value is a note, never a failure.
TIERS = {
    "arc": "something a person sets out to do; shown in the Library",
    "move": "done to any artifact at any stage (Review, Decide)",
    "companion": "holds the initiative and offers the next arc",
    "kit": "tools other skills use; never shown",
}


def workflow_tier(workflow: dict[str, Any]) -> str:
    tier = workflow.get("tier")
    return tier if tier in TIERS else "arc"


def workflow_notes(workflow: dict[str, Any], name: str, known: set[str] | None = None) -> list[str]:
    """Soft checks on tier, parts and checkpoints (D-149, D-153). Notes, not problems."""
    notes = []
    tier = workflow.get("tier")
    if tier is not None and tier not in TIERS:
        notes.append(f"{name}: tier {tier!r} is not one of {', '.join(TIERS)}; treated as arc")
    checkpoints = workflow.get("checkpoints")
    if checkpoints is not None and not _strings(checkpoints):
        notes.append(f"{name}: checkpoints should be a list of sentences that always hold")
    parts = workflow.get("parts")
    if parts is not None:
        if not isinstance(parts, list) or not all(isinstance(x, dict) and x.get("title") for x in parts):
            notes.append(f"{name}: parts should be a list of {{id, title}} objects")
        elif known is not None:
            for part in parts:
                wid = part.get("workflow")
                if wid and wid not in known:
                    notes.append(f"{name}: part {part['title']!r} names workflow {wid!r}, which is not installed")
    part_of = workflow.get("part_of")
    if part_of and known is not None and part_of not in known:
        notes.append(f"{name}: part_of names {part_of!r}, which is not installed")
    return notes


def _routing_required(workflow: dict[str, Any], wdir: Path) -> bool:
    """Shown in the Library (D-83), or shipped with the app: both must be routable (D-120)."""
    library = workflow.get("library")
    if isinstance(library, dict) and library.get("show"):
        return True
    return wdir.resolve().parent == KIT_DIR.parent.parent.resolve()


def workflow_catalog(workspace: Path | None = None) -> list[dict[str, Any]]:
    """Every workflow with what the director routes on, in lifecycle order."""
    workspace = workspace or default_workspace()
    order = {s["id"]: n for n, s in enumerate(lifecycle_stages(workspace))}
    out = []
    for wid, folder in list_workflows(workspace).items():
        path = workflow_manifest_path(folder)
        try:
            manifest = _read_json(path) if path else {}
        except PaError:
            continue
        routing = manifest.get("routing") if isinstance(manifest.get("routing"), dict) else None
        out.append({
            "id": wid,
            "title": manifest.get("title") or wid,
            "summary": manifest.get("summary") or "",
            "folder": str(folder),
            "source": "shipped" if is_builtin(workspace, folder) else "hangar",
            "after": manifest.get("needs") or [],
            "next": manifest.get("next") or [],
            "tier": workflow_tier(manifest),
            "part_of": manifest.get("part_of") or None,
            "parts": manifest.get("parts") if isinstance(manifest.get("parts"), list) else [],
            "checkpoints": manifest.get("checkpoints") if _strings(manifest.get("checkpoints")) else [],
            "routing": routing,
        })
    out.sort(key=lambda w: (order.get((w["routing"] or {}).get("stage"), len(order)), w["id"]))
    return out


def cmd_workflows(args: argparse.Namespace) -> None:
    workspace = Path(args.workspace).resolve() if args.workspace else default_workspace()
    catalog = workflow_catalog(workspace)
    stages = lifecycle_stages(workspace)
    if args.stage:
        catalog = [w for w in catalog if (w["routing"] or {}).get("stage") == args.stage]
    if args.json:
        print(json.dumps({"stages": stages, "strictness": STRICTNESS, "workflows": catalog}, indent=1))
        return
    titles = {s["id"]: s.get("title") or s["id"] for s in stages}
    stage_now = None
    for w in catalog:
        r = w["routing"] or {}
        stage = r.get("stage")
        if stage != stage_now:
            stage_now = stage
            heading = "Any stage" if stage == "any" else titles.get(stage, stage)
            print(f"\n## {heading if stage else 'Not routed: start only when the person names it'}")
        kind = "" if w["tier"] == "arc" else f", {w['tier']}"
        print(f"\n{w['id']}: {w['title']} ({w['source']}{kind}, {w['folder']})")
        if w["part_of"]:
            print(f"  Part of: {w['part_of']} (can also be started on its own)")
        if w["parts"]:
            print("  Parts (move between them freely): " + " / ".join(
                p["title"] + (f" [{p['workflow']}]" if p.get("workflow") else "") for p in w["parts"]))
        if w["checkpoints"]:
            print("  Always holds: " + "; ".join(w["checkpoints"]))
        if not r:
            print(f"  {w['summary']}")
            continue
        print("  When: " + " / ".join(r.get("when") or []))
        if r.get("not_when"):
            print("  Not when: " + " / ".join(r["not_when"]))
        if r.get("needs"):
            print(f"  Needs: {r['needs']}")
        if w["after"]:
            print(f"  Comes after: {', '.join(w['after'])}")
        if r.get("offer"):
            print(f"  Offer: {r['offer']}")
        persona = r.get("persona") or {}
        if persona.get("invariants"):
            print(f"  Always ({persona.get('strictness', 'guide')} by default): " + "; ".join(persona["invariants"]))
    if not args.stage:
        print("\n## Strictness levels")
        for text in STRICTNESS.values():
            print(f"  {text}")


def _workflow_problems(run: dict[str, Any]) -> list[str]:
    workflow, wdir, name = run["workflow"], run["workflow_dir"], run["workflow_file"].name
    problems = []
    stages = [s["id"] for s in lifecycle_stages(_workspace_for_checks(run))]
    problems += routing_problems(workflow, name, stages, _routing_required(workflow, wdir))
    for key in ("title", "summary", "views"):
        if not workflow.get(key):
            problems.append(f"{name}: missing {key}")
    if not (workflow.get("workflow") or workflow.get("scenario")):
        problems.append(f"{name}: missing workflow (its id)")
    if not (wdir / "SKILL.md").is_file():
        problems.append("SKILL.md is missing")
    for product in workflow.get("work_products") or []:
        tid = product.get("template") if isinstance(product, dict) else None
        if tid and not find_template(str(tid), _workspace_for_checks(run)):
            problems.append(f"{name}: work product {product.get('name', '?')!r} names template {tid!r}, which does not exist")
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
    if low == "live" or low.startswith("live:"):
        # A flown demo hands this turn to a real agent; the written line is only a guide.
        return "modifier", {"live": tail("live:") if low.startswith("live:") else True}
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
                if "live" in fields and not ("agent" in steps[-1] or "says" in steps[-1]):
                    raise PaError(f"{where}: [live] must follow an Aviator or participant line")
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
    try:
        known = set(list_workflows(_workspace_for_checks(run)))
    except Exception:  # noqa: BLE001 - notes are best effort
        known = None
    for note in workflow_notes(run["workflow"], run["workflow_file"].name, known):
        print(f"  note: {note}")


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
PERSON_FIELDS = ("name", "kind", "role", "initials", "stand_in", "backing", "call_for", "skills", "avatar")
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
        if person.get("avatar") and not (draft_avatar(workspace, pid) or live_avatar(workspace, pid)):
            problems.append(f"this draft: the avatar {person['avatar']} is missing; pick the picture again")
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
        unchanged = live is not None and live.strip() == (text or "").strip() and not cast_changes \
            and draft_avatar(workspace, pid) is None
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
        "avatar_changed": draft_avatar(workspace, pid) is not None
        or bool(live_avatar(workspace, pid)) != bool((person or {}).get("avatar")),
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


# Avatars (D-74): a picture for a person or agent, kept beside the roster in
# `participants/avatars/<id>.<ext>` so it travels with the repo. A draft holds
# its picture as `.hangar/drafts/people/<id>.avatar.<ext>` until it is published.

AVATARS_DIR = "avatars"
AVATAR_TYPES = {"png": b"\x89PNG", "jpg": b"\xff\xd8\xff", "webp": b"RIFF", "gif": b"GIF8"}
AVATAR_MAX = 2_000_000


def _avatar_ext(filename: str, data: bytes) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    ext = "jpg" if ext == "jpeg" else ext
    if ext not in AVATAR_TYPES:
        raise PaError(f"an avatar is a {', '.join(sorted(AVATAR_TYPES))} picture, not {filename!r}")
    if len(data) > AVATAR_MAX:
        raise PaError("an avatar must be under 2 MB")
    if not data.startswith(AVATAR_TYPES[ext]) or (ext == "webp" and data[8:12] != b"WEBP"):
        raise PaError(f"{filename} is not a {ext} picture")
    return ext


def draft_avatar(workspace: Path, pid: str) -> Path | None:
    base = _hangar(workspace, "drafts", "people")
    found = sorted(base.glob(f"{pid}.avatar.*")) if base.is_dir() else []
    return found[0] if found else None


def live_avatar(workspace: Path, pid: str) -> Path | None:
    folder = workspace / PARTICIPANTS_DIR / AVATARS_DIR
    found = sorted(folder.glob(f"{pid}.*")) if folder.is_dir() else []
    return next((p for p in found if p.suffix[1:] in AVATAR_TYPES), None)


def avatar_of(workspace: Path, pid: str, draft: bool = False) -> Path | None:
    """The picture for someone: the draft's when asked and there is one, else the live one."""
    if draft:
        meta = _participant(_draft_paths(workspace, pid)[0]) if _draft_paths(workspace, pid)[0].is_file() else {}
        if not meta.get("avatar"):
            return None
        return draft_avatar(workspace, pid) or live_avatar(workspace, pid)
    return live_avatar(workspace, pid)


def set_draft_avatar(workspace: Path, pid: str, filename: str, data: bytes | None) -> None:
    """Give a draft a picture (copied into the draft), or take it away (data None)."""
    text_path, meta_path = _draft_paths(workspace, _checked_id(pid))
    info = _read_meta(meta_path)
    if not info or info.get("action") == "remove":
        raise PaError(f"there is no draft of {pid} to change")
    old = draft_avatar(workspace, pid)
    if old:
        old.unlink()
    person = _participant(text_path)
    meta = _meta_of(person)
    if data is None:
        meta.pop("avatar", None)
    else:
        ext = _avatar_ext(filename, data)
        path = text_path.with_name(f"{pid}.avatar.{ext}")
        path.write_bytes(data)
        meta["avatar"] = f"{AVATARS_DIR}/{pid}.{ext}"
    _write_draft(workspace, pid, meta, person_text(meta, person["brief"]), info)


def _publish_avatar(workspace: Path, pid: str, avatar: str | None) -> None:
    folder = workspace / PARTICIPANTS_DIR / AVATARS_DIR
    drafted = draft_avatar(workspace, pid)
    if avatar and not drafted:
        return  # the draft keeps the live picture
    for old in folder.glob(f"{pid}.*") if folder.is_dir() else []:
        old.unlink()
    if avatar and drafted:
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{pid}{drafted.suffix}").write_bytes(drafted.read_bytes())


def discard_draft(workspace: Path, pid: str) -> None:
    for path in _draft_paths(workspace, _checked_id(pid)):
        path.unlink(missing_ok=True)
    avatar = draft_avatar(workspace, pid)
    if avatar:
        avatar.unlink()


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
    old_avatar = live_avatar(workspace, pid)
    if kept and old_avatar:
        history = _hangar(workspace, "history", "people", pid)
        (history / f"{kept}.avatar{old_avatar.suffix}").write_bytes(old_avatar.read_bytes())
    if info["action"] == "remove":
        live_path.unlink()
        _publish_avatar(workspace, pid, None)
    else:
        live_path.parent.mkdir(parents=True, exist_ok=True)
        _write_atomic(live_path, info["text"])
        _publish_avatar(workspace, pid, (info["person"] or {}).get("avatar"))
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
    for picture in old.parent.glob(f"{version}.avatar.*"):
        (_draft_paths(workspace, pid)[0].with_name(f"{pid}.avatar{picture.suffix}")).write_bytes(picture.read_bytes())
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
WORKFLOW_KEYS = ("title", "summary", "steps", "participants", "inputs", "launchers", "work_products", "views")
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
        views = manifest.get("views")
        if views is not None:
            # A workflow's widgets and views (D-112): a name to a spec file in the folder.
            if not isinstance(views, dict) or not all(
                isinstance(k, str) and re.fullmatch(r"[a-z0-9][a-z0-9-]{0,40}", k)
                and isinstance(v, str) and v.endswith(".json")
                for k, v in views.items()
            ):
                raise PaError("views must map a short lower-case name to a .json spec file")
            for v in views.values():
                _safe_rel(v)
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


# ---------------------------------------------------------------- usage log (D-122 to D-127)

def _load_usagelog() -> Any:
    """``usagelog.py`` beside this file, also when pa is loaded as a module
    (the server's Hangar routes do) and this folder is not on sys.path."""
    import importlib.util

    try:
        import usagelog as module  # type: ignore[import-not-found]

        return module
    except ImportError:
        path = Path(__file__).resolve().parent / "usagelog.py"
        spec = importlib.util.spec_from_file_location("usagelog", path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules.setdefault("usagelog", module)
        spec.loader.exec_module(module)
        return module


usagelog = _load_usagelog()

#: Arguments never worth a column: how the command was called, not what it did.
_UNLOGGED_ARGS = {"run", "command", "json", "url", "dir", "out", "workspace", "fact"}


def _command_context(args: argparse.Namespace) -> dict[str, Any]:
    context: dict[str, Any] = {}
    scenario = getattr(args, "scenario", None)
    if isinstance(scenario, str) and scenario:
        name = Path(scenario).name
        folder = Path(scenario)
        if (folder / "workflow.json").is_file():
            context["workflow"] = name
        elif (folder / "scenario.json").is_file():
            context["scenario"] = name
            try:
                context["workflow"] = json.loads((folder / "scenario.json").read_text()).get("workflow")
            except (OSError, ValueError, AttributeError):
                pass
        else:
            context["workflow"] = name
    cwd = Path.cwd().as_posix()
    if "/workspace/demos/" in cwd + "/":
        context["mode"] = "demo"
        context.setdefault("scenario", cwd.split("/workspace/demos/", 1)[1].split("/")[0] or None)
    elif "/.hangar/" in cwd + "/":
        context["mode"] = "hangar"
    return context


def _log_command(args: argparse.Namespace, code: int, started: float) -> None:
    """Every pa command is one line in the usage log: what ran, not what it said."""
    try:
        command = getattr(args, "command", None)
        if not command or command in ("usage", "log"):
            return
        params: dict[str, Any] = {"exit": code, "duration_ms": int((time.monotonic() - started) * 1000)}
        for key, value in vars(args).items():
            if key in _UNLOGGED_ARGS or key.endswith("_command") and key != "review_command":
                continue
            if key == "review_command":
                params["subcommand"] = value
                continue
            if value is False or value is None:
                continue
            if isinstance(value, str) and key in ("data", "spec", "doc", "folder", "scenario"):
                value = Path(value).name
            params[key] = value
        usagelog.log(
            f"pa.{command.replace('-', '_')}",
            source="pa",
            params=params,
            context=_command_context(args),
            session_id=getattr(args, "session", None),
        )
    except Exception:
        pass


def cmd_log(args: argparse.Namespace) -> None:
    params: dict[str, Any] = {}
    for pair in args.pairs:
        if "=" not in pair:
            raise PaError(f"write fields as key=value: {pair!r}")
        key, value = pair.split("=", 1)
        params[key] = _parse_value(value)
    context = {k: getattr(args, k) for k in ("project", "workflow", "run", "scenario", "mode") if getattr(args, k)}
    try:
        record = usagelog.make_record(
            args.event, source="skill", params=params, context=context, session_id=args.session
        )
    except ValueError as err:
        raise PaError(str(err)) from err
    if not usagelog.enabled():
        return
    usagelog.write(record)
    if args.show:
        print(json.dumps(record, indent=2))


def _parse_value(text: str) -> Any:
    lowered = text.lower()
    if lowered in ("true", "yes"):
        return True
    if lowered in ("false", "no"):
        return False
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


def _usage_files(args: argparse.Namespace) -> list[Path]:
    return usagelog.log_files(include_eval=getattr(args, "eval", False), suite=getattr(args, "suite", None))


def _since(args: argparse.Namespace) -> int | None:
    try:
        return usagelog.parse_since(getattr(args, "since", None))
    except ValueError as err:
        raise PaError(str(err)) from err


def cmd_usage_summary(args: argparse.Namespace) -> None:
    summary = usagelog.summarize(usagelog.read(_usage_files(args), _since(args)))
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(usagelog.format_summary(summary))


def cmd_usage_tail(args: argparse.Namespace) -> None:
    records = list(usagelog.read(_usage_files(args), _since(args)))[-args.n :]
    for rec in records:
        if args.json:
            print(json.dumps(rec, separators=(",", ":")))
            continue
        params = " ".join(f"{k}={v}" for k, v in (rec.get("params") or {}).items())
        ctx = " ".join(f"{k}={v}" for k, v in (rec.get("context") or {}).items() if k != "eval")
        print(f"{rec.get('timestamp', '')[:19]}  {rec.get('source', ''):6}  {rec.get('event_name')}  {ctx}  {params}".rstrip())


def cmd_usage_check(args: argparse.Namespace) -> None:
    bad = 0
    lines = 0
    for path in usagelog.log_files(include_eval=True):
        with open(path, encoding="utf-8") as handle:
            for number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                lines += 1
                try:
                    problems = usagelog.check_record(json.loads(line))
                except ValueError:
                    problems = ["not JSON"]
                if problems:
                    bad += 1
                    if bad <= 20:
                        print(f"{path.name}:{number}: {'; '.join(problems)}")
    print(f"{lines} lines checked, {bad} with problems")
    if bad:
        raise PaError("the usage log has lines that do not match the schema")


def _default_pack_path(shape: str) -> Path:
    desktop = Path.home() / "Desktop"
    folder = desktop if desktop.is_dir() else usagelog.usage_dir() / "packs"
    stamp = _dt.datetime.now().strftime("%Y-%m-%d-%H%M")
    suffix = "-upstream" if shape == "upstream" else ""
    return folder / f"flight-deck-usage-{usagelog.installation_id()[:8]}-{stamp}{suffix}.jsonl.gz"


def cmd_usage_pack(args: argparse.Namespace) -> None:
    out = Path(args.out).expanduser() if args.out else _default_pack_path(args.shape)
    result = usagelog.pack(out, _usage_files(args), _since(args), shape=args.shape, fingerprint=args.fingerprint)
    print(f"packed {result['lines']} lines into {result['path']}")
    if result["left_out"]:
        print(f"left out {result['left_out']} lines that failed the privacy check")


def cmd_usage_eval(args: argparse.Namespace) -> None:
    if args.action == "start":
        if not args.suite:
            raise PaError("pa usage eval start SUITE [TASK] [TRIAL]")
        path = usagelog.set_eval_tag(args.suite, args.task or "", args.trial or "")
        print(f"tagging events as eval {args.suite}/{args.task or ''}/{args.trial or ''} ({path})")
    elif args.action == "stop":
        usagelog.clear_eval_tag()
        print("eval tag cleared")
    else:
        tag = usagelog.eval_tag()
        print(json.dumps(tag) if tag else "no eval in progress")


def cmd_usage_where(args: argparse.Namespace) -> None:
    root = usagelog.usage_dir()
    state = "on" if usagelog.enabled() else "off"
    print(f"{root}  (logging {state}, level {usagelog.level()})")
    for path in usagelog.log_files(include_eval=True)[-10:]:
        print(f"  {path.relative_to(root)}  {path.stat().st_size:,} bytes")


def register_usage(sub: Any) -> None:
    p = sub.add_parser("log", help="write one event to the usage log (for skills: a step, an offer, an outcome)")
    p.add_argument("event", help="area.action, lower case, e.g. skill.step or offer.made")
    p.add_argument("pairs", nargs="*", help="key=value fields: ids, status words and numbers only, never sentences")
    p.add_argument("--session")
    p.add_argument("--project")
    p.add_argument("--workflow")
    p.add_argument("--run")
    p.add_argument("--scenario")
    p.add_argument("--mode", choices=usagelog.MODES)
    p.add_argument("--show", action="store_true", help="print the line as written")
    p.set_defaults(run=cmd_log)

    usage = sub.add_parser("usage", help="read the usage log: summary, tail, check, pack, eval tags")
    usub = usage.add_subparsers(dest="usage_command", required=True)

    def common(q: Any) -> None:
        q.add_argument("--since", help="7d, 12h, 30m or a date like 2026-11-20")
        q.add_argument("--eval", action="store_true", help="include eval trials")
        q.add_argument("--suite", help="only this eval suite")

    q = usub.add_parser("summary", help="counts: sessions, pages, workflows, skills, tools, pa commands")
    common(q)
    q.add_argument("--json", action="store_true")
    q.set_defaults(run=cmd_usage_summary)

    q = usub.add_parser("tail", help="the latest lines")
    common(q)
    q.add_argument("-n", type=int, default=20)
    q.add_argument("--json", action="store_true")
    q.set_defaults(run=cmd_usage_tail)

    q = usub.add_parser("check", help="every line matches the schema and holds no sentences")
    q.set_defaults(run=cmd_usage_check)

    q = usub.add_parser("pack", help="copy the log into one file to carry off this machine")
    common(q)
    q.add_argument("--out", help="default: a dated file on the Desktop")
    q.add_argument("--shape", choices=("slim", "upstream"), default="slim",
                   help="upstream: Omnigent's telemetry gateway records")
    q.add_argument("--fingerprint", action="store_true",
                   help="hash every name (files, records, projects) on the way out; counts stay")
    q.set_defaults(run=cmd_usage_pack)

    q = usub.add_parser("eval", help="tag every event as part of an eval trial, until stopped")
    q.add_argument("action", choices=("start", "stop", "show"))
    q.add_argument("suite", nargs="?")
    q.add_argument("task", nargs="?")
    q.add_argument("trial", nargs="?")
    q.set_defaults(run=cmd_usage_eval)

    q = usub.add_parser("where", help="where the log is, and its latest files")
    q.set_defaults(run=cmd_usage_where)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pa", description="Product Aviator data and view command")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("flow", help="record which step of a workflow the work is at, for the Session panel")
    p.add_argument("data")
    p.add_argument("--scenario", help="the workflow (or scenario) folder, the first time, to take its steps")
    p.add_argument("--step", help="a step number, or part of its name")
    p.add_argument("--done", action="store_true", help="the workflow is finished")
    p.add_argument("--note", help="one line on what is happening in this step; with --pause, where the work was left")
    p.add_argument("--pause", action="store_true", help="the person set this run aside; needs --note")
    p.add_argument("--resume", action="store_true", help="pick a paused or stopped run up again")
    p.add_argument("--stop", action="store_true", help="the person abandoned this run; the work so far is kept")
    p.add_argument("--state", choices=["working", "needs-you", "waiting"],
                   help="needs-you: the run cannot move until the person answers; waiting: on someone else")
    p.add_argument("--session", help="the id of the session this run is in, so the project page can reopen it")
    p.add_argument("--director", help="the id of the director session that started this run in a thread")
    p.add_argument("--brief", help="the path of the brief the thread was handed")
    p.set_defaults(run=cmd_flow)

    p = sub.add_parser("brief", help="write the brief a director hands a workflow's thread, and print the thread's first message")
    p.add_argument("workflow", help="the workflow (or scenario) folder")
    p.add_argument("--subject", required=True, help="what the run is about, in the person's words")
    p.add_argument("--director", required=True, help="the director's session id, so the thread can report to it")
    p.add_argument("--data", help="the dataset path; default is the workflow's own pattern for the subject")
    p.add_argument("--context", action="append", help="a file the thread should read first; repeatable")
    p.add_argument("--target", help="what finished looks like for this run")
    p.add_argument("--ask", help="anything else the director wants the thread to know")
    p.add_argument("--json", action="store_true", help="print the paths instead of the message")
    p.set_defaults(run=cmd_brief)

    p = sub.add_parser("report", help="one line from a run to its director: a milestone, progress, a blocker or done")
    p.add_argument("data")
    p.add_argument("text")
    p.add_argument("--kind", choices=REPORT_KINDS, default="milestone")
    p.set_defaults(run=cmd_report)

    p = sub.add_parser("project", help="say what a project is: its goal, area, team and state; or list projects")
    p.add_argument("name", nargs="?")
    p.add_argument("--goal", help="the one in-market goal, in a line")
    p.add_argument("--area", help="the lasting problem space it lives in")
    p.add_argument("--team", help="who runs it, when it is another team's")
    p.add_argument("--state", choices=PROJECT_STATES)
    p.add_argument("--state-note", dest="state_note", help='a few words on the state, e.g. "slipped 2 wks"')
    p.add_argument("--data", action="append", help="a dataset that belongs to this project (repeat)")
    p.add_argument("--dir", help="the projects folder; default projects/ in the workspace")
    p.add_argument("--json", action="store_true")
    p.set_defaults(run=cmd_project)

    p = sub.add_parser("stamp", help="say which initiative, template and stage a file belongs to (writes a stamp into it)")
    p.add_argument("file")
    p.add_argument("--initiative", help="the initiative's id, key or name; empty to take it out of one")
    p.add_argument("--template", help="the template it follows, e.g. initiative-intent")
    p.add_argument("--stage", action="append", help="a lifecycle stage it serves (repeat for several)")
    p.add_argument("--status", choices=ARTIFACT_STATUSES)
    p.add_argument("--title")
    p.add_argument("--from", dest="source", action="append", help="the id of an artifact it was made from (repeat)")
    p.add_argument("--by", help="who made it: a workflow id, a participant id, aviator or you")
    p.add_argument("--ref", action="store_true", help="list it on the initiative's card instead of writing into it")
    p.set_defaults(run=cmd_stamp)

    p = sub.add_parser("artifacts", help="list what each initiative has produced, read from the files' stamps")
    p.add_argument("--initiative", help="only this initiative (id, key or name)")
    p.add_argument("--loose", action="store_true", help="only artifacts not in an initiative yet")
    p.add_argument("--stage")
    p.add_argument("--template")
    p.add_argument("--json", action="store_true")
    p.set_defaults(run=cmd_artifacts)

    p = sub.add_parser("template", help="list, show, check or start from a template (markdown, records or page)")
    tsub = p.add_subparsers(dest="template_command", required=True)
    tp = tsub.add_parser("list")
    tp.add_argument("--stage")
    tp.add_argument("--json", action="store_true")
    tp = tsub.add_parser("show")
    tp.add_argument("id")
    tp = tsub.add_parser("check")
    tp.add_argument("id", nargs="?")
    tp = tsub.add_parser("new")
    tp.add_argument("id")
    tp.add_argument("--initiative", help="the initiative it belongs to (id, key or name)")
    tp.add_argument("--out", help="where to write it; default is the template's own pattern")
    tp.add_argument("--title")
    tp.add_argument("--by")
    tp.add_argument("--force", action="store_true")
    p.set_defaults(run=cmd_template)

    p = sub.add_parser("register", help="add evidence, a question, a decision or a ready check to an initiative's registers")
    p.add_argument("initiative", help="the initiative's id, key or name")
    p.add_argument("type", choices=REGISTER_TYPES)
    p.add_argument("text", help="one line")
    p.add_argument("--source", help="evidence: where it came from (a path, a person, a link)")
    p.add_argument("--owner", help="questions and checks: who can settle it")
    p.add_argument("--blocking", action="store_true", help="questions: nothing moves until it is answered")
    p.add_argument("--status", choices=("open", "answered", "pass", "fail", "unknown"))
    p.add_argument("--supersedes", help="decisions: the earlier decision this one replaces")
    p.add_argument("--stage", action="append")
    p.add_argument("--note")
    p.add_argument("--by", help="who added it")
    p.set_defaults(run=cmd_register)

    p = sub.add_parser("link", help="hang a link to another project from one record")
    p.add_argument("data")
    p.add_argument("id")
    p.add_argument("--to", required=True, help="the other project's name")
    p.add_argument("--type", choices=LINK_TYPES, default="handed-to")
    p.add_argument("--remove", action="store_true")
    p.set_defaults(run=cmd_link)

    p = sub.add_parser("runs", help="list the workflow runs in this workspace and where each was left")
    p.add_argument("--dir", help="the progress folder; default progress/ in the workspace")
    p.add_argument("--all", action="store_true", help="include finished and stopped runs")
    p.add_argument("--json", action="store_true")
    p.set_defaults(run=cmd_runs)

    p = sub.add_parser("workflows", help="list every workflow with when it fits, by lifecycle stage (for routing)")
    p.add_argument("--stage", help="only the workflows that serve this stage")
    p.add_argument("--workspace", help="the workspace; default the current one")
    p.add_argument("--json", action="store_true", help="everything, including example prompts, as JSON")
    p.set_defaults(run=cmd_workflows)

    p = sub.add_parser("recap", help="for a director: its charter, state, memory and the runs, after a compaction or in a new session")
    p.add_argument("--workspace", help="the workspace; default the current folder")
    p.set_defaults(run=cmd_recap)

    p = sub.add_parser("remember", help="for a director: add one lasting fact to director/memory.md")
    p.add_argument("fact", nargs="+")
    p.add_argument("--workspace", help="the workspace; default the current folder")
    p.set_defaults(run=cmd_remember)

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

    p = sub.add_parser("demo", help="fly a scenario as a demo, or play its next turn")
    p.add_argument("action", choices=("next", "status", "fly"))
    p.add_argument("--dir", help="the demo folder (default: here)")
    p.add_argument("--scenario", help="fly: the scenario folder")
    p.add_argument("--workspace")
    p.add_argument("--reset", action="store_true", help="fly: start again from the beginning")
    p.add_argument("--canned", action="store_true", help="fly: play every turn canned, even live ones")
    p.set_defaults(run=cmd_demo)

    # Comments and suggested changes in markdown documents (docreview.py).
    from docreview import ReviewError, register as register_review

    register_review(sub)

    register_usage(sub)

    args = parser.parse_args(argv)
    started = time.monotonic()
    code = 0
    try:
        args.run(args)
    except (PaError, ReviewError) as err:
        print(f"pa: {err}", file=sys.stderr)
        code = 2
    except SystemExit as err:
        code = err.code if isinstance(err.code, int) else 1
        raise
    except BaseException:
        code = 1
        raise
    finally:
        _log_command(args, code, started)
    return code


if __name__ == "__main__":
    sys.exit(main())
