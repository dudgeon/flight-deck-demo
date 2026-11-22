#!/usr/bin/env python3
"""The routing eval suite (D-133): does Aviator start, offer, or stay out of the way?

Each task is one prompt a product manager might type, labelled with what the
routing ladder (D-128) says should happen:

- ``start``: the person named a workflow, so it starts (its skill loads, or a
  thread is briefed for it);
- ``offer``: the ask clearly fits a workflow, so Aviator offers it once and
  starts nothing;
- ``open`` and ``answer``: open thinking or a quick question, so nothing is
  started and nothing offered;
- ``lifecycle``: "I'm working on a new feature" starts the lifecycle skill
  (skipped until that skill exists).

Tasks come from two places: each workflow's own ``routing.examples`` (read
with ``pa workflows --json``, so a new workflow brings its own tests, D-120)
and ``evals/routing/tasks.json`` (near misses across workflows). Each task is
in the tuning set or the held-out set, fixed by its id (60/40).

A trial runs through the real app on this machine (D-133): a fresh copy of
the workspace, a new session in the Workspace project on the model under test
(Sonnet by default), the prompt, one turn. The evidence is what the app
recorded, not what the reply says: the usage log's lines for this trial
(``tool.used`` with the skill loaded, a thread created, ``offer.made``), the
files the turn wrote in its workspace copy (briefs, runs), and a question card
left waiting. Only when the code evidence is silent does a judge (Claude Code
on Haiku) read the reply, to tell an offer in words from open work or an
answer. Nothing here uses the Claude API (D-02).

Trials run one at a time, because the usage log's eval tag is one file for
the whole machine. A task passes when 2 of its 3 trials pass.

    python3 evals/routing_suite.py tasks
    python3 evals/routing_suite.py smoke
    python3 evals/routing_suite.py run [--split tune] [--trials 3] [--only id,id]
    python3 evals/routing_suite.py report evals/runs/<run>
    python3 evals/routing_suite.py pairs evals/runs/<a> evals/runs/<b>

Standard library only, like ``pa``.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import html
import importlib.util
import json
import os
import random
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "view-kit" / "scripts"
TASKS_FILE = Path(__file__).resolve().parent / "routing" / "tasks.json"
RUNS_DIR = Path(__file__).resolve().parent / "runs"
SUITE = "routing"
EXPECTS = ("start", "offer", "open", "answer", "lifecycle")
TUNE_SHARE = 0.6
DEFAULT_MODEL = "claude-sonnet-5-5"
DEFAULT_JUDGE_MODEL = "claude-haiku-5-5"
DEFAULT_URL = os.environ.get("OMNIGENT_SLIM_URL", "http://127.0.0.1:6767")
#: Files a trial's workspace copy leaves out: drafts, flown demos, a real director's notes.
_SKIP_COPY = {".hangar", "demos", "director"}


def _load(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(name, module)
    spec.loader.exec_module(module)
    return module


pa = _load("pa")
usagelog = sys.modules.get("usagelog") or _load("usagelog")


# ------------------------------------------------------------------ tasks

def split_of(task_id: str) -> str:
    """Tuning or held-out, fixed by the id so it never moves between runs."""
    bucket = int(hashlib.sha256(task_id.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return "tune" if bucket < TUNE_SHARE else "held-out"


def load_tasks(workspace: Path | None = None, extra: Path = TASKS_FILE) -> list[dict[str, Any]]:
    """Every task: each workflow's examples, then the hand-written ones."""
    tasks: list[dict[str, Any]] = []
    for wf in pa.workflow_catalog(workspace):
        examples = (wf.get("routing") or {}).get("examples") or {}
        for kind in ("start", "offer", "open"):
            for n, prompt in enumerate(examples.get(kind) or [], 1):
                tasks.append({
                    "id": f"{wf['id']}-{kind}-{n}",
                    "prompt": prompt,
                    "expect": kind,
                    "workflow": wf["id"] if kind != "open" else None,
                    "near": wf["id"] if kind == "open" else None,
                    "source": "workflow",
                })
    fixtures: dict[str, Any] = {}
    if extra.is_file():
        hand = json.loads(extra.read_text(encoding="utf-8"))
        fixtures = hand.get("fixtures") or {}
        for raw in hand.get("tasks", []):
            tasks.append({"workflow": None, "near": None, **raw, "source": extra.name})
    for task in tasks:
        if task["id"] in fixtures:
            task["fixtures"] = {**fixtures[task["id"]], **(task.get("fixtures") or {})}
    unknown = set(fixtures) - {t["id"] for t in tasks}
    if unknown:
        raise ValueError(f"fixtures for tasks that do not exist: {', '.join(sorted(unknown))}")
    seen: set[str] = set()
    for task in tasks:
        if task["id"] in seen:
            raise ValueError(f"two tasks are called {task['id']}")
        if task["expect"] not in EXPECTS:
            raise ValueError(f"{task['id']}: expect must be one of {', '.join(EXPECTS)}")
        if task["expect"] in ("start", "offer") and not task.get("workflow"):
            raise ValueError(f"{task['id']}: a {task['expect']} task names its workflow")
        seen.add(task["id"])
        task["split"] = split_of(task["id"])
    return tasks


def runnable(task: dict[str, Any], skills: set[str]) -> bool:
    need = task.get("requires_skill")
    return not need or need in skills


def known_skills(workspace: Path | None = None) -> set[str]:
    roots = [ROOT / "skills", (workspace or ROOT / "workspace") / ".claude" / "skills"]
    return {p.name for r in roots if r.is_dir() for p in r.iterdir() if (p / "SKILL.md").is_file()}


# ------------------------------------------------------------------ the app

class AppError(RuntimeError):
    pass


class AppDriver:
    """Runs one prompt as one turn of a new session in the real app."""

    def __init__(self, url: str = DEFAULT_URL, project: str = "Workspace", model: str = DEFAULT_MODEL,
                 timeout: float = 300.0, poll: float = 3.0) -> None:
        self.url, self.project_name, self.model = url.rstrip("/"), project, model
        self.timeout, self.poll = timeout, poll
        self._project: dict[str, Any] | None = None

    def _call(self, method: str, path: str, body: Any = None) -> Any:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.url + path, data=data, method=method,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as err:
            raise AppError(f"{method} {path}: {err.code} {err.read()[:300]!r}") from err
        except OSError as err:
            raise AppError(f"{method} {path}: {err}") from err
        return json.loads(raw) if raw else {}

    def project(self) -> dict[str, Any]:
        if self._project is None:
            rows = self._call("GET", "/v1/projects?limit=200").get("data", [])
            found = next((p for p in rows if p.get("name") == self.project_name), None)
            if not found:
                raise AppError(f"no project called {self.project_name!r}; start the app with ./start.sh first")
            config = found.get("config") or {}
            for key in ("agent_id", "host_id", "workspace"):
                if not config.get(key):
                    raise AppError(f"project {self.project_name!r} has no {key} in its settings")
            self._project = found
        return self._project

    def source_workspace(self) -> Path:
        return Path(self.project()["config"]["workspace"])

    def start(self, prompt: str, workspace: Path, title: str) -> str:
        project = self.project()
        config = project["config"]
        session = self._call("POST", "/v1/sessions", {
            "agent_id": config["agent_id"],
            "initial_items": [],
            "project_id": project["id"],
            "host_id": config["host_id"],
            "workspace": str(workspace),
            "title": title,
            # The launch rules keep the permission mode; only the model changes.
            "terminal_launch_args": ["--model", self.model],
        })
        sid = session["id"]
        self._call("POST", f"/v1/sessions/{sid}/events", {
            "type": "message",
            "data": {"role": "user", "content": [{"type": "input_text", "text": prompt}]},
        })
        return sid

    def snapshot(self, sid: str) -> dict[str, Any]:
        return self._call("GET", f"/v1/sessions/{sid}?include_items=false")

    def children(self, sid: str) -> list[str]:
        rows = self._call("GET", f"/v1/sessions/{sid}/child_sessions?descendants=true").get("data", [])
        return [r["id"] for r in rows if isinstance(r, dict) and r.get("id")]

    def interrupt(self, sid: str) -> None:
        try:
            self._call("POST", f"/v1/sessions/{sid}/events", {"type": "interrupt", "data": {}})
        except AppError:
            pass

    def archive(self, sid: str) -> None:
        try:
            self._call("PATCH", f"/v1/sessions/{sid}", {"archived": True})
        except AppError:
            pass

    def items(self, sid: str) -> list[dict[str, Any]]:
        return self._call("GET", f"/v1/sessions/{sid}/items?limit=500&order=asc").get("data", [])

    def run(self, prompt: str, workspace: Path, title: str) -> dict[str, Any]:
        """One turn. Threads the turn starts are stopped as soon as they appear:
        that a thread was made is the evidence, its work is not wanted."""
        started = time.monotonic()
        sid = self.start(prompt, workspace, title)
        seen_running, timed_out, question = False, False, None
        stopped: set[str] = set()
        snap: dict[str, Any] = {}
        while True:
            time.sleep(self.poll)
            snap = self.snapshot(sid)
            status = snap.get("status")
            seen_running = seen_running or status == "running"
            for child in self.children(sid):
                if child not in stopped:
                    self.interrupt(child)
                    stopped.add(child)
            if snap.get("pending_elicitations"):
                question = snap["pending_elicitations"]
                break
            waiting = bool(snap.get("pending_inputs"))
            if status != "running" and not waiting and (seen_running or time.monotonic() - started > 30):
                break
            if time.monotonic() - started > self.timeout:
                timed_out = True
                break
        if question is not None or timed_out:
            self.interrupt(sid)
        for child in stopped:
            self.archive(child)
        items = self.items(sid)
        self.archive(sid)
        return {
            "session": sid,
            "status": snap.get("status"),
            "error": snap.get("last_task_error"),
            "timed_out": timed_out,
            "question": question,
            "threads": sorted(stopped),
            "reply": reply_text(items),
            "seconds": round(time.monotonic() - started, 1),
        }


def reply_text(items: list[dict[str, Any]]) -> str:
    """The assistant's words in a turn, in order."""
    parts: list[str] = []
    for item in items:
        if item.get("type") != "message" or item.get("role") != "assistant":
            continue
        for part in item.get("content") or []:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                parts.append(part["text"])
    return "\n\n".join(parts).strip()


# ------------------------------------------------------------------ evidence

def copy_workspace(source: Path, dest: Path) -> Path:
    """A fresh workspace for one trial: configuration, no state (D-133)."""
    if dest.exists():
        shutil.rmtree(dest)

    def ignore(folder: str, names: list[str]) -> set[str]:
        return {n for n in names if n in _SKIP_COPY and Path(folder) == source} | {"__pycache__", ".DS_Store"}

    shutil.copytree(source, dest, ignore=ignore)
    for state in ("data", "progress", "briefs", "projects", "artifacts"):
        folder = dest / state
        if folder.is_dir():
            for path in folder.iterdir():
                if path.name != ".gitkeep":
                    shutil.rmtree(path) if path.is_dir() else path.unlink()
    return dest


def add_fixtures(ws: Path, fixtures: dict[str, str] | None) -> list[str]:
    """Copy a task's fixtures into its trial workspace; both paths are relative to it.

    A source is read from the trial's own copy, so it must be configuration
    that copy_workspace keeps (a scenario's fixtures, say). A destination may
    not leave the workspace.
    """
    placed = []
    root = ws.resolve()
    for dest_rel, src_rel in (fixtures or {}).items():
        src, dest = (ws / src_rel).resolve(), (ws / dest_rel).resolve()
        if root not in src.parents or root not in dest.parents:
            raise ValueError(f"fixture {dest_rel}: paths stay inside the workspace")
        if not src.is_file():
            raise ValueError(f"fixture {dest_rel}: {src_rel} is not in the workspace")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        placed.append(dest_rel)
    return placed


def trial_lines(task_id: str, trial: str, usage_root: Path | None = None) -> list[dict[str, Any]]:
    """The usage log's lines for one trial."""
    want = {"suite": SUITE, "task": task_id, "trial": trial}
    files = usagelog.log_files(usage_root, suite=SUITE)
    return [r for r in usagelog.read(files) if (r.get("context") or {}).get("eval") == want]


_BRIEF = re.compile(r"^# Brief: (\S+) on ", re.M)


def workspace_evidence(ws: Path) -> dict[str, list[str]]:
    """Which workflows a turn briefed or started a run of, from its files."""
    briefed, runs = set(), set()
    for path in (ws / "briefs").glob("*.md") if (ws / "briefs").is_dir() else []:
        briefed.update(_BRIEF.findall(path.read_text(encoding="utf-8", errors="replace")))
    for path in (ws / "progress").glob("*.json") if (ws / "progress").is_dir() else []:
        try:
            wf = json.loads(path.read_text(encoding="utf-8")).get("workflow")
        except (OSError, ValueError):
            continue
        if isinstance(wf, str) and wf:
            runs.add(wf)
    return {"briefed": sorted(briefed), "runs": sorted(runs)}


_CARD_KEYS = {"question", "header", "label", "description", "title", "message", "text", "prompt"}
_START_LABEL = re.compile(r"^\s*(start|run|yes|begin|go ahead)\b", re.I)


def _names(text: str, wid: str, title: str) -> bool:
    return any(re.search(rf"(?<![\w-]){re.escape(n.lower())}(?![\w-])", text) for n in (wid, title))


def question_card(question: Any, workflows: dict[str, str] | None = None) -> dict[str, Any]:
    """The words a person sees on a question card, and whether it offers to start something.

    A card is an offer only when one of its answers starts something ("Start
    it", "Run it", "Yes") or names a workflow. A card that only asks which
    paragraph or which calls is a clarifying question, graded by the judge
    like any reply.
    """
    texts: list[str] = []
    labels: list[str] = []

    def walk(node: Any, key: str = "") -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, k)
        elif isinstance(node, list):
            for v in node:
                walk(v, key)
        elif isinstance(node, str) and key in _CARD_KEYS:
            (labels if key == "label" else texts).append(node)

    walk(question)
    answers = " ".join(labels).lower()
    offers = any(_START_LABEL.match(label) for label in labels) or any(
        _names(answers, wid, title) for wid, title in (workflows or {}).items())
    seen = " ".join(texts + labels).lower()
    named = [wid for wid, title in (workflows or {}).items() if _names(seen, wid, title)]
    # "?" marks an offer that names no workflow.
    return {"text": " ".join(texts + labels)[:4000], "labels": labels, "offers": offers,
            "asked": (named or ["?"]) if offers else []}


def evidence(result: dict[str, Any], lines: list[dict[str, Any]], files: dict[str, list[str]],
             workflows: dict[str, str]) -> dict[str, Any]:
    """What the turn did, from what the app recorded."""
    skills: list[str] = []
    offers: list[str] = []
    tools: list[str] = []
    for line in lines:
        params = line.get("params") or {}
        name = line.get("event_name")
        if name == "tool.used":
            tools.append(str(params.get("tool", "")))
            if params.get("skill"):
                skills.append(str(params["skill"]))
        elif name == "offer.made" and params.get("workflow"):
            offers.append(str(params["workflow"]))
    card = question_card(result.get("question"), workflows)
    asked = card["asked"]
    threads = bool(result.get("threads")) or any("sys_session_create" in t for t in tools)
    return {
        "skills": sorted(set(skills)),
        "offers": sorted(set(offers)),
        "asked": sorted(set(asked)),
        "question": bool(result.get("question")),
        "card_offers": card["offers"],
        "card_text": card["text"],
        "threads": threads,
        "briefed": files["briefed"],
        "runs": files["runs"],
        "tools": sorted(set(tools)),
    }


# ------------------------------------------------------------------ grading

JUDGE_PROMPT = """You grade one turn of a product manager's assistant. Reply with JSON only.

The assistant can run these workflows:
{catalog}

The person wrote:
<prompt>
{prompt}
</prompt>

The assistant replied (it may have been cut off):
<reply>
{reply}
</reply>

Classify the reply:
- "offer": it proposes running one of the workflows above (by name or by describing it) and asks whether to start.
- "answer": it answers a direct question or does a small task, with no workflow proposed.
- "open": it thinks the problem through with the person (questions, options, ideas), with no workflow proposed. Asking which document, paragraph or thing they mean is "open", not an offer.
- "start": it says it has started one of the workflows.
Name the workflow id for offer or start, else null. If you cannot tell, use "unknown".

{{"label": "offer|answer|open|start|unknown", "workflow": "<id or null>", "why": "<one short sentence>"}}"""


def claude_judge(model: str = DEFAULT_JUDGE_MODEL, command: str | None = None) -> Callable[..., dict[str, Any]]:
    """A judge that is Claude Code in print mode on a light model (D-133)."""
    base = (command or os.environ.get("OMNIGENT_SLIM_JUDGE_CMD") or f"claude -p --model {model}").split()

    def judge(prompt: str, reply: str, catalog: dict[str, str]) -> dict[str, Any]:
        text = JUDGE_PROMPT.format(
            catalog="\n".join(f"- {wid}: {title}" for wid, title in catalog.items()),
            prompt=prompt, reply=reply[:6000] or "(no reply)")
        try:
            out = subprocess.run(base, input=text, capture_output=True, text=True, timeout=180).stdout
        except (OSError, subprocess.TimeoutExpired) as err:
            return {"label": "unknown", "workflow": None, "why": f"judge failed: {err}"}
        match = re.search(r"\{.*\}", out, re.S)
        try:
            verdict = json.loads(match.group(0)) if match else {}
        except ValueError:
            verdict = {}
        label = verdict.get("label") if verdict.get("label") in ("offer", "answer", "open", "start", "unknown") else "unknown"
        wf = verdict.get("workflow") if verdict.get("workflow") in catalog else None
        return {"label": label, "workflow": wf, "why": str(verdict.get("why", ""))[:300]}

    return judge


def observe(ev: dict[str, Any], catalog: dict[str, str], lifecycle_skill: str | None = None) -> tuple[str, list[str], str]:
    """What happened, from code evidence alone: (label, workflows, how we know).

    Only workflows count as started: loading view-kit, director or any other
    helper skill is not starting a workflow."""
    touched = set(ev["skills"]) | set(ev["briefed"]) | set(ev["runs"])
    if lifecycle_skill and lifecycle_skill in touched:
        return "lifecycle", [lifecycle_skill], "the lifecycle skill loaded"
    workflows = sorted(touched & set(catalog))
    if workflows or ev["threads"]:
        return "start", workflows, "skill loaded, brief, run or thread"
    if ev["offers"] or ev["asked"]:
        return "offer", sorted((set(ev["offers"]) | set(ev["asked"])) - {"?"}), "offer logged or asked on a card"
    if ev["question"]:
        return "none", [], "a question card that starts nothing"
    return "none", [], "no workflow started or offered"


def grade(task: dict[str, Any], ev: dict[str, Any], reply: str, catalog: dict[str, str],
          judge: Callable[..., dict[str, Any]] | None) -> dict[str, Any]:
    """Pass or fail for one trial, and why."""
    label, workflows, how = observe(ev, catalog, task.get("requires_skill") if task["expect"] == "lifecycle" else None)
    verdict = None
    if label == "none" and judge is not None:
        card = ev.get("card_text") or ""
        verdict = judge(task["prompt"], f"{reply}\n\n[Question card] {card}" if card else reply, catalog)
        if verdict["label"] == "offer":
            label, workflows, how = "offer", [verdict["workflow"]] if verdict["workflow"] else [], "judge: offer in words"
        elif verdict["label"] in ("open", "answer"):
            label, how = verdict["label"], f"judge: {verdict['label']}"
    expect, want = task["expect"], task.get("workflow")
    if expect == "start":
        ok = label == "start" and (want in workflows or (not workflows and ev["threads"]))
    elif expect == "offer":
        ok = label == "offer" and (want in workflows or not workflows)
    elif expect == "lifecycle":
        ok = label == "lifecycle"
    else:  # open and answer: nothing started, nothing offered
        ok = label not in ("start", "offer", "lifecycle")
    return {"pass": ok, "observed": label, "workflows": workflows, "how": how, "judge": verdict}


# ------------------------------------------------------------------ running

def now_id() -> str:
    return _dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def run_suite(tasks: list[dict[str, Any]], driver: Any, out: Path, trials: int, model: str,
              judge: Callable[..., dict[str, Any]] | None, catalog: dict[str, str],
              usage_root: Path | None = None, log: Callable[[str], None] = print) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    source = driver.source_workspace()
    missing = [f"{t['id']}: {src}" for t in tasks for src in (t.get("fixtures") or {}).values()
               if not (source / src).is_file()]
    if missing:
        raise ValueError("fixtures not in the workspace: " + "; ".join(missing))
    run_tag = out.name.replace("-", "")
    meta = {"suite": SUITE, "run": out.name, "model": model, "trials": trials,
            "started": _dt.datetime.now().isoformat(timespec="seconds"), "tasks": len(tasks)}
    (out / "run.json").write_text(json.dumps(meta, indent=1) + "\n")
    records = []
    for t_index, task in enumerate(tasks, 1):
        for n in range(1, trials + 1):
            trial = f"{run_tag}.{n}"
            ws = copy_workspace(source, out / "ws" / f"{task['id']}.{n}")
            add_fixtures(ws, task.get("fixtures"))
            usagelog.set_eval_tag(SUITE, task["id"], trial, usage_root)
            try:
                result = driver.run(task["prompt"], ws, f"eval {SUITE} {task['id']} {n}")
            except AppError as err:
                result = {"session": None, "error": str(err), "reply": "", "question": None, "threads": [], "timed_out": False}
            finally:
                usagelog.clear_eval_tag(usage_root)
            ev = evidence(result, trial_lines(task["id"], trial, usage_root), workspace_evidence(ws), catalog)
            graded = grade(task, ev, result.get("reply", ""), catalog, judge) if not result.get("error") or result.get("reply") else {
                "pass": False, "observed": "error", "workflows": [], "how": str(result.get("error")), "judge": None}
            record = {"task": task, "trial": n, "result": result, "evidence": ev, **graded}
            records.append(record)
            with (out / "trials.jsonl").open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            log(f"[{t_index}/{len(tasks)}] {task['id']} #{n}: {'pass' if graded['pass'] else 'FAIL'} "
                f"(expected {task['expect']}, saw {graded['observed']}{' ' + ','.join(graded['workflows']) if graded['workflows'] else ''})")
            shutil.rmtree(ws, ignore_errors=True)
    summary = summarize(records)
    (out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    (out / "report.md").write_text(report_md(meta, summary, records))
    return summary


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Per task (2 of 3 trials), then by split and by expected label."""
    by_task: dict[str, dict[str, Any]] = {}
    for r in records:
        t = by_task.setdefault(r["task"]["id"], {"task": r["task"], "passes": 0, "trials": 0, "observed": []})
        t["trials"] += 1
        t["passes"] += 1 if r["pass"] else 0
        t["observed"].append(r["observed"])
    for t in by_task.values():
        t["pass"] = t["passes"] * 3 >= t["trials"] * 2  # 2 of 3
    def rate(rows: list[dict[str, Any]]) -> dict[str, Any]:
        passed = sum(1 for t in rows if t["pass"])
        return {"passed": passed, "tasks": len(rows), "rate": round(passed / len(rows), 3) if rows else None}
    tasks = list(by_task.values())
    confusion: dict[str, dict[str, int]] = {}
    for r in records:
        row = confusion.setdefault(r["task"]["expect"], {})
        row[r["observed"]] = row.get(r["observed"], 0) + 1
    return {
        "overall": rate(tasks),
        "by_split": {s: rate([t for t in tasks if t["task"]["split"] == s]) for s in ("tune", "held-out")},
        "by_expect": {e: rate([t for t in tasks if t["task"]["expect"] == e]) for e in EXPECTS
                      if any(t["task"]["expect"] == e for t in tasks)},
        "confusion": confusion,
        "failing": sorted(t["task"]["id"] for t in tasks if not t["pass"]),
        "tasks": {tid: {k: v for k, v in t.items() if k != "task"} for tid, t in by_task.items()},
    }


def _pct(r: dict[str, Any]) -> str:
    return "n/a" if r["rate"] is None else f"{r['passed']} of {r['tasks']} ({round(r['rate'] * 100)}%)"


def report_md(meta: dict[str, Any], summary: dict[str, Any], records: list[dict[str, Any]]) -> str:
    lines = [f"# Routing suite, run {meta['run']}", "",
             f"Model under test: {meta['model']}. {meta['trials']} trials per task; a task passes on 2 of 3.", "",
             "| | Tasks passed |", "|---|---|",
             f"| Overall | {_pct(summary['overall'])} |"]
    for split, r in summary["by_split"].items():
        lines.append(f"| {split.capitalize()} set | {_pct(r)} |")
    for expect, r in summary["by_expect"].items():
        lines.append(f"| Expected {expect} | {_pct(r)} |")
    seen = sorted({o for row in summary["confusion"].values() for o in row})
    lines += ["", "Trials by what was expected (rows) and what happened (columns):", "",
              "| Expected | " + " | ".join(seen) + " |", "|---|" + "---|" * len(seen)]
    for expect, row in summary["confusion"].items():
        lines.append(f"| {expect} | " + " | ".join(str(row.get(o, 0)) for o in seen) + " |")
    failing = [r for r in records if not r["pass"]]
    if failing:
        lines += ["", "## Failing trials", ""]
        for r in failing:
            reply = (r["result"].get("reply") or "").replace("\n", " ")
            lines.append(f"- **{r['task']['id']}** #{r['trial']} ({r['task']['split']}): expected "
                         f"{r['task']['expect']}{' ' + r['task']['workflow'] if r['task'].get('workflow') else ''}, "
                         f"saw {r['observed']} {','.join(r['workflows'])} ({r['how']}). "
                         f"Prompt: \"{r['task']['prompt']}\" Reply: \"{reply[:240]}{'…' if len(reply) > 240 else ''}\"")
    return "\n".join(lines) + "\n"


def load_records(run: Path) -> list[dict[str, Any]]:
    path = run / "trials.jsonl"
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()] if path.is_file() else []


# ------------------------------------------------------------------ blind pairs

PAIRS_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Routing pairs</title>
<style>
:root {{ color-scheme: light dark; }}
body {{ font: 15px/1.5 system-ui, sans-serif; margin: 0 auto; max-width: 980px; padding: 24px 16px; background: Canvas; color: CanvasText; }}
h1 {{ font-size: 22px; }} .pair {{ border: 1px solid GrayText; border-radius: 8px; padding: 16px; margin: 20px 0; }}
.prompt {{ font-weight: 600; }} .sides {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
@media (max-width: 700px) {{ .sides {{ grid-template-columns: 1fr; }} }}
.side {{ border: 1px solid GrayText; border-radius: 6px; padding: 10px; white-space: pre-wrap; }}
.what {{ font-size: 13px; opacity: .75; margin-bottom: 6px; }} label {{ margin-right: 16px; }}
textarea {{ width: 100%; min-height: 120px; }}
</style></head><body>
<h1>Routing: which reply is better?</h1>
<p>Each pair is one prompt answered two ways. Which version is which is hidden. Pick the better reply, or "Same". When done, press "Copy answers" and paste them back into the thread.</p>
{pairs}
<p><button id="copy" type="button">Copy answers</button></p>
<textarea id="out" readonly aria-label="Your answers"></textarea>
<script>
const ids = {ids};
document.getElementById("copy").addEventListener("click", () => {{
  const answers = {{}};
  for (const id of ids) {{
    const picked = document.querySelector(`input[name="${{id}}"]:checked`);
    answers[id] = picked ? picked.value : null;
  }}
  const text = JSON.stringify({{round: {round}, answers}});
  document.getElementById("out").value = text;
  navigator.clipboard?.writeText(text).catch(() => {{}});
}});
</script></body></html>
"""


def _side(record: dict[str, Any]) -> str:
    ev = record["evidence"]
    did = []
    if ev["skills"] or ev["briefed"] or ev["threads"]:
        did.append("started " + ", ".join(sorted(set(ev["skills"]) | set(ev["briefed"]))) if (ev["skills"] or ev["briefed"]) else "started a thread")
    if ev["question"]:
        did.append("asked a question card")
    what = "; ".join(did) or "started nothing"
    return f'<div class="what">{html.escape(what)}</div>{html.escape(record["result"].get("reply") or "(no reply)")}'


def make_pairs(a: Path, b: Path, n: int = 10, seed: int | None = None) -> tuple[str, dict[str, Any]]:
    """Ten prompts where the two runs differ most, sides shuffled; the key is kept apart."""
    ra = {r["task"]["id"]: r for r in load_records(a) if r["trial"] == 1}
    rb = {r["task"]["id"]: r for r in load_records(b) if r["trial"] == 1}
    common = sorted(set(ra) & set(rb))
    differ = [t for t in common if (ra[t]["pass"], ra[t]["observed"]) != (rb[t]["pass"], rb[t]["observed"])]
    same = [t for t in common if t not in differ]
    rng = random.Random(seed if seed is not None else int(time.time()))
    rng.shuffle(differ)
    rng.shuffle(same)
    chosen = (differ + same)[:n]
    # The round's name is a hash, so the page does not say which runs it compares.
    round_id = hashlib.sha256(f"{a.name}|{b.name}".encode()).hexdigest()[:8]
    key: dict[str, Any] = {"round": round_id, "a": a.name, "b": b.name, "pairs": {}}
    blocks = []
    for i, tid in enumerate(chosen, 1):
        pid = f"p{i}"
        left_is_a = rng.random() < 0.5
        left, right = (ra[tid], rb[tid]) if left_is_a else (rb[tid], ra[tid])
        key["pairs"][pid] = {"task": tid, "left": a.name if left_is_a else b.name, "right": b.name if left_is_a else a.name}
        blocks.append(
            f'<section class="pair"><p class="prompt">{i}. {html.escape(ra[tid]["task"]["prompt"])}</p>'
            f'<div class="sides"><div class="side">{_side(left)}</div><div class="side">{_side(right)}</div></div>'
            f'<p><label><input type="radio" name="{pid}" value="left"> Left is better</label>'
            f'<label><input type="radio" name="{pid}" value="right"> Right is better</label>'
            f'<label><input type="radio" name="{pid}" value="same"> Same</label></p></section>')
    page = PAIRS_PAGE.format(pairs="\n".join(blocks), ids=json.dumps(list(key["pairs"])), round=json.dumps(round_id))
    return page, key


# ------------------------------------------------------------------ commands

def _catalog(workspace: Path | None) -> dict[str, str]:
    return {w["id"]: w["title"] for w in pa.workflow_catalog(workspace)}


def _select(tasks: list[dict[str, Any]], args: argparse.Namespace, skills: set[str]) -> list[dict[str, Any]]:
    chosen = [t for t in tasks if runnable(t, skills)]
    if getattr(args, "split", None):
        chosen = [t for t in chosen if t["split"] == args.split]
    if getattr(args, "only", None):
        want = set(args.only.split(","))
        chosen = [t for t in chosen if t["id"] in want]
    if getattr(args, "limit", None):
        chosen = chosen[: args.limit]
    return chosen


def cmd_tasks(args: argparse.Namespace) -> None:
    ws = Path(args.workspace) if args.workspace else None
    tasks = load_tasks(ws)
    skills = known_skills(ws)
    for t in _select(tasks, args, skills) if not args.all else tasks:
        flag = "" if runnable(t, skills) else f"  (skipped: needs the {t['requires_skill']} skill)"
        print(f"{t['split']:<8} {t['expect']:<9} {t['id']:<34} {t.get('workflow') or ''}{flag}")
    counts: dict[str, int] = {}
    for t in tasks:
        counts[t["expect"]] = counts.get(t["expect"], 0) + 1
    print(f"\n{len(tasks)} tasks: " + ", ".join(f"{v} {k}" for k, v in counts.items()))


def cmd_smoke(args: argparse.Namespace) -> None:
    """One cheap turn on the light model, to check the app can be driven."""
    driver = AppDriver(args.url, args.project, model=args.model, timeout=120)
    out = RUNS_DIR / f"smoke-{now_id()}"
    ws = copy_workspace(driver.source_workspace(), out / "ws")
    result = driver.run("Reply with the single word ok.", ws, "eval smoke")
    shutil.rmtree(out, ignore_errors=True)
    print(json.dumps({k: result[k] for k in ("session", "status", "reply", "seconds", "error")}, indent=1))
    if "ok" not in (result.get("reply") or "").lower():
        raise SystemExit("smoke failed: no 'ok' in the reply")


def cmd_run(args: argparse.Namespace) -> None:
    driver = AppDriver(args.url, args.project, model=args.model, timeout=args.timeout)
    source = driver.source_workspace()
    tasks = _select(load_tasks(source), args, known_skills(source))
    if not tasks:
        raise SystemExit("no tasks to run")
    out = Path(args.out) if args.out else RUNS_DIR / f"{now_id()}-{args.label or args.split or 'all'}"
    print(f"{len(tasks)} tasks x {args.trials} trials on {args.model}, judge {'off' if args.no_judge else args.judge_model}; writing {out}")
    judge = None if args.no_judge else claude_judge(args.judge_model)
    summary = run_suite(tasks, driver, out, args.trials, args.model, judge, _catalog(source))
    print(f"\n{_pct(summary['overall'])} tasks passed; report: {out / 'report.md'}")


def regrade(record: dict[str, Any], catalog: dict[str, str], judge: Callable[..., dict[str, Any]] | None) -> dict[str, Any]:
    """Grade a saved trial again with today's grader: the card is re-read, the rest of the evidence kept."""
    result, ev = record["result"], dict(record["evidence"])
    card = question_card(result.get("question"), catalog)
    ev.update(card_offers=card["offers"], card_text=card["text"], asked=sorted(card["asked"]))
    if result.get("error") and not result.get("reply"):
        return {**record, "evidence": ev}
    return {**record, "evidence": ev, **grade(record["task"], ev, result.get("reply", ""), catalog, judge)}


def cmd_report(args: argparse.Namespace) -> None:
    run = Path(args.run_dir)
    records = load_records(run)
    if not records:
        raise SystemExit(f"no trials in {run}")
    if args.regrade:
        judge = None if args.no_judge else claude_judge(args.judge_model)
        records = [regrade(r, _catalog(None), judge) for r in records]
        with (run / "trials.jsonl").open("w", encoding="utf-8") as fh:
            fh.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in records)
    meta = json.loads((run / "run.json").read_text()) if (run / "run.json").is_file() else {"run": run.name, "model": "?", "trials": "?"}
    summary = summarize(records)
    (run / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    text = report_md(meta, summary, records)
    (run / "report.md").write_text(text)
    print(text)


def cmd_pairs(args: argparse.Namespace) -> None:
    page, key = make_pairs(Path(args.a), Path(args.b), args.n)
    out = Path(args.out or (RUNS_DIR / f"pairs-{Path(args.a).name}-vs-{Path(args.b).name}"))
    out.mkdir(parents=True, exist_ok=True)
    (out / "pairs.html").write_text(page, encoding="utf-8")
    (out / "key.json").write_text(json.dumps(key, indent=1) + "\n")
    print(f"{len(key['pairs'])} pairs: {out / 'pairs.html'} (the key, {out / 'key.json'}, stays with you)")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="routing_suite", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("tasks", help="list the tasks, their split and what each expects")
    p.add_argument("--workspace")
    p.add_argument("--split", choices=("tune", "held-out"))
    p.add_argument("--all", action="store_true", help="include tasks whose skill does not exist yet")
    p.set_defaults(func=cmd_tasks)
    for name, fn in (("smoke", cmd_smoke), ("run", cmd_run)):
        p = sub.add_parser(name, help="check the app can be driven" if name == "smoke" else "run the suite through the app")
        p.add_argument("--url", default=DEFAULT_URL)
        p.add_argument("--project", default="Workspace")
        p.add_argument("--model", default=DEFAULT_JUDGE_MODEL if name == "smoke" else DEFAULT_MODEL)
        p.set_defaults(func=fn)
        if name == "run":
            p.add_argument("--trials", type=int, default=3)
            p.add_argument("--split", choices=("tune", "held-out"))
            p.add_argument("--only", help="task ids, comma separated")
            p.add_argument("--limit", type=int)
            p.add_argument("--timeout", type=float, default=300.0, help="seconds per turn")
            p.add_argument("--judge-model", default=DEFAULT_JUDGE_MODEL)
            p.add_argument("--no-judge", action="store_true", help="code graders only")
            p.add_argument("--label", help="a word for the run folder, e.g. baseline")
            p.add_argument("--out")
    p = sub.add_parser("report", help="re-grade a run's summary and print its report")
    p.add_argument("run_dir")
    p.add_argument("--regrade", action="store_true", help="grade every saved trial again with this grader")
    p.add_argument("--judge-model", default=DEFAULT_JUDGE_MODEL)
    p.add_argument("--no-judge", action="store_true", help="code graders only")
    p.set_defaults(func=cmd_report)
    p = sub.add_parser("pairs", help="a blind page of ten pairs from two runs, for Geoff")
    p.add_argument("a")
    p.add_argument("b")
    p.add_argument("--n", type=int, default=10)
    p.add_argument("--out")
    p.set_defaults(func=cmd_pairs)
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
