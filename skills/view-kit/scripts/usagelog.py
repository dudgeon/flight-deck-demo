"""The usage log: one local record of how Flight Deck is used (D-122 to D-127).

Every part of the platform writes here: the server (sessions, turns, tokens,
the Hangar), the web app (pages, clicks), the `pa` command (every command a
skill runs, plus `pa log` events skills write on purpose) and the tool
observer (each tool and skill an agent uses). Standard library only, so `pa`
and the server share this one file; nothing here touches the network.

Where it goes. One JSON object per line, one file per day:

    <app folder>/logs/usage/2026-11-21.jsonl          real use
    <app folder>/logs/usage/eval/<suite>/2026-11-21.jsonl   eval trials

`logs/` is gitignored and never shipped or touched by setup's updates, so it
survives every update. OMNIGENT_SLIM_USAGE_DIR moves it; OMNIGENT_SLIM_USAGE=0
turns it off.

What a line holds (schema "omnigent-slim.usage", version 1). Field names follow
upstream Omnigent's telemetry record (`omnigent/telemetry/client.py`), so a
future exporter can hand lines to the same kind of gateway (`to_upstream`):

    {"schema": "omnigent-slim.usage", "schema_version": 1,
     "event_id": "9f1c...", "event_name": "pa.flow",
     "timestamp": "2026-11-21T22:31:04.512Z", "timestamp_ns": 1795...,
     "source": "pa", "installation_id": "4be0...", "session_id": "conv_...",
     "omnigent_version": "...", "operating_system": "Darwin",
     "context": {"workflow": "intent-shaping", "mode": "flying"},
     "params": {"step": "shape", "state": "working", "duration_ms": 41}}

Privacy (D-124): ids and words, never sentences. A parameter may be a number,
a yes/no, or a short string with no spaces (an id, a status word, a file
name). Anything longer or with spaces is replaced by "<text N>", keeping only
its length, so prompts, record text and document content cannot land here by
accident. Paths are made relative to the app folder or the home folder. With
OMNIGENT_SLIM_USAGE_LEVEL=fingerprint, names are also replaced by a short
salted hash, except the fixed vocabulary in SAFE_KEYS.
"""

from __future__ import annotations

import datetime as _dt
import gzip
import hashlib
import json
import os
import platform
import re
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Iterable, Iterator

SCHEMA = "omnigent-slim.usage"
SCHEMA_VERSION = 1
DIR_ENV = "OMNIGENT_SLIM_USAGE_DIR"
ENABLED_ENV = "OMNIGENT_SLIM_USAGE"
LEVEL_ENV = "OMNIGENT_SLIM_USAGE_LEVEL"
EVAL_ENV = "OMNIGENT_SLIM_EVAL"
SESSION_ENV = "OMNIGENT_SLIM_SESSION_ID"
LEVELS = ("ids", "fingerprint")
SOURCES = ("server", "web", "pa", "skill", "tool", "eval")
MODES = ("flying", "hangar", "demo", "eval")

#: A day's file rolls over to ``<day>.2.jsonl`` past this size.
MAX_FILE_BYTES = 20 * 1024 * 1024
#: A line longer than this keeps its envelope and loses its params.
MAX_LINE_BYTES = 8 * 1024
MAX_STRING = 64
MAX_LIST = 20
MAX_PARAMS = 40

EVENT_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z0-9_]+)+$")
KEY_RE = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
WORD_RE = re.compile(r"^[\w.:/@+#=~-]+$")
CONTEXT_KEYS = ("project", "workflow", "run", "scenario", "mode", "eval")
#: Kept as written even at the fingerprint level: a fixed vocabulary, not names
#: a person chose.
SAFE_KEYS = frozenset(
    {
        "command", "subcommand", "tool", "skill", "page", "component", "component_kind",
        "kind", "status", "state", "step", "mode", "source", "workflow", "scenario",
        "layout", "host", "phase", "interaction", "upstream_event", "harness", "model",
        "surface", "scope", "policy_type", "action", "result", "level", "exit",
    }
)

_APP_ROOT = Path(__file__).resolve().parents[3]
_PROCESS_ID = uuid.uuid4().hex


# ---------------------------------------------------------------- settings


def app_root() -> Path:
    """The app folder: the git checkout, or ``~/flight-deck`` on the work Mac."""
    return _APP_ROOT


def usage_dir() -> Path:
    configured = os.environ.get(DIR_ENV, "").strip()
    return Path(configured).expanduser() if configured else _APP_ROOT / "logs" / "usage"


def enabled() -> bool:
    if os.environ.get(ENABLED_ENV, "").strip().lower() in ("0", "off", "false", "no"):
        return False
    # Test runs stay out of the real log unless a test points it somewhere.
    if os.environ.get("PYTEST_CURRENT_TEST") and not os.environ.get(DIR_ENV):
        return False
    return True


def level() -> str:
    value = os.environ.get(LEVEL_ENV, "").strip().lower()
    return value if value in LEVELS else "ids"


def installation_id(root: Path | None = None) -> str:
    """A random id for this copy of the app, made once. It names nobody."""
    root = root or usage_dir()
    path = root / "install-id"
    try:
        value = path.read_text().strip()
        if re.fullmatch(r"[0-9a-f]{32}", value):
            return value
    except OSError:
        pass
    value = uuid.uuid4().hex
    try:
        root.mkdir(parents=True, exist_ok=True)
        path.write_text(value + "\n")
    except OSError:
        pass
    return value


def eval_tag(root: Path | None = None) -> dict[str, str] | None:
    """The eval trial in progress, if any: ``{"suite", "task", "trial"}``.

    The eval runner sets OMNIGENT_SLIM_EVAL=suite/task/trial for processes it
    starts, or writes ``eval-tag.json`` in the usage folder (``pa usage eval
    start``) so sessions the server starts are tagged too.
    """
    raw = os.environ.get(EVAL_ENV, "").strip()
    if not raw:
        try:
            data = json.loads(((root or usage_dir()) / "eval-tag.json").read_text())
            raw = "/".join(str(data.get(k, "")) for k in ("suite", "task", "trial"))
        except (OSError, ValueError, AttributeError):
            return None
    parts = [p for p in raw.split("/")]
    if not parts or not parts[0]:
        return None
    parts += [""] * (3 - len(parts))
    tag = {"suite": parts[0], "task": parts[1], "trial": parts[2]}
    return {k: v for k, v in tag.items() if v and WORD_RE.match(v) and len(v) <= MAX_STRING}


def set_eval_tag(suite: str, task: str = "", trial: str = "", root: Path | None = None) -> Path:
    root = root or usage_dir()
    root.mkdir(parents=True, exist_ok=True)
    path = root / "eval-tag.json"
    path.write_text(json.dumps({"suite": suite, "task": task, "trial": trial}) + "\n")
    return path


def clear_eval_tag(root: Path | None = None) -> None:
    try:
        ((root or usage_dir()) / "eval-tag.json").unlink()
    except OSError:
        pass


# ---------------------------------------------------------------- cleaning


def _fingerprint(value: str) -> str:
    salt = installation_id()
    return "#" + hashlib.sha256(f"{salt}:{value}".encode()).hexdigest()[:10]


def _short_path(value: str) -> str:
    try:
        path = Path(value).expanduser()
        if not path.is_absolute():
            return value
        try:
            return path.resolve().relative_to(_APP_ROOT).as_posix()
        except ValueError:
            pass
        try:
            return "~/" + path.relative_to(Path.home()).as_posix()
        except ValueError:
            return "/" + path.name if path.name else "/"
    except (OSError, ValueError, RuntimeError):
        return value


def clean_value(value: Any, *, key: str = "", lvl: str | None = None) -> Any:
    """Return *value* safe to log, or None to drop it.

    Numbers and yes/no pass. A string passes when it is short and has no
    spaces; otherwise it becomes "<text N>" (its length only).
    """
    lvl = lvl or level()
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        if isinstance(value, float) and (value != value or value in (float("inf"), float("-inf"))):
            return None
        return value
    if isinstance(value, Path):
        value = str(value)
    if isinstance(value, str):
        text = value.strip()
        if text.startswith(("/", "~")) and "\n" not in text:
            text = _short_path(text)
        if not text:
            return None
        if len(text) > MAX_STRING or not WORD_RE.match(text):
            return f"<text {len(value)}>"
        if lvl == "fingerprint" and key not in SAFE_KEYS:
            return _fingerprint(text)
        return text
    if isinstance(value, (list, tuple, set, frozenset)):
        items = [clean_value(v, key=key, lvl=lvl) for v in list(value)[:MAX_LIST]]
        items = [v for v in items if v is not None and not isinstance(v, (list, dict))]
        return items
    # Mappings and other objects are not logged: flatten them at the call site.
    return None


def clean_params(params: dict[str, Any] | None, lvl: str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in (params or {}).items():
        if len(out) >= MAX_PARAMS:
            break
        key = str(key).replace("-", "_").lower()
        if not KEY_RE.match(key):
            continue
        cleaned = clean_value(value, key=key, lvl=lvl)
        if cleaned is not None and cleaned != []:
            out[key] = cleaned
    return out


def clean_context(context: dict[str, Any] | None, lvl: str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in CONTEXT_KEYS:
        value = (context or {}).get(key)
        if key == "eval":
            if isinstance(value, dict):
                tag = clean_params({k: value.get(k) for k in ("suite", "task", "trial")}, "ids")
                if tag:
                    out["eval"] = tag
            continue
        cleaned = clean_value(value, key=key, lvl=lvl)
        if isinstance(cleaned, str):
            out[key] = cleaned
    return out


# ---------------------------------------------------------------- writing


def _version() -> str | None:
    """The upstream commit this copy is synced to (``UPSTREAM``), the same in
    every process, whether or not the omnigent package is importable."""
    try:
        for line in (_APP_ROOT / "UPSTREAM").read_text().split():
            if re.fullmatch(r"[0-9a-f]{7,40}", line):
                return line[:12]
    except OSError:
        pass
    return None


_VERSION_CACHE: list[str | None] = []


def make_record(
    event_name: str,
    *,
    source: str,
    params: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
    session_id: str | None = None,
    now_ns: int | None = None,
) -> dict[str, Any]:
    """Build one line. Raises ValueError for a bad event name or source."""
    if not EVENT_RE.match(event_name):
        raise ValueError(f"event names look like area.action, lower case: {event_name!r}")
    if source not in SOURCES:
        raise ValueError(f"source must be one of {', '.join(SOURCES)}")
    lvl = level()
    now_ns = now_ns or time.time_ns()
    stamp = _dt.datetime.fromtimestamp(now_ns / 1e9, tz=_dt.timezone.utc)
    ctx = dict(context or {})
    tag = eval_tag()
    if tag and "eval" not in ctx:
        ctx["eval"] = tag
        ctx.setdefault("mode", "eval")
    if not _VERSION_CACHE:
        _VERSION_CACHE.append(_version())
    session = session_id or os.environ.get(SESSION_ENV, "").strip() or None
    record: dict[str, Any] = {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "event_id": uuid.uuid4().hex,
        "event_name": event_name,
        "timestamp": stamp.strftime("%Y-%m-%dT%H:%M:%S.") + f"{stamp.microsecond // 1000:03d}Z",
        "timestamp_ns": now_ns,
        "source": source,
        "installation_id": installation_id(),
        "process_id": _PROCESS_ID,
        "session_id": clean_value(session, key="session", lvl="ids") if session else None,
        "omnigent_version": _VERSION_CACHE[0],
        "operating_system": platform.system(),
        "level": lvl,
        "context": clean_context(ctx, lvl),
        "params": clean_params(params, lvl),
    }
    if record["session_id"] is None or str(record["session_id"]).startswith("<"):
        record["session_id"] = None
    return record


def file_for(record: dict[str, Any], root: Path | None = None) -> Path:
    root = root or usage_dir()
    day = str(record.get("timestamp", ""))[:10] or _dt.date.today().isoformat()
    tag = (record.get("context") or {}).get("eval")
    folder = root / "eval" / tag["suite"] if isinstance(tag, dict) and tag.get("suite") else root
    path = folder / f"{day}.jsonl"
    n = 1
    while True:
        try:
            if path.stat().st_size < MAX_FILE_BYTES:
                return path
        except OSError:
            return path
        n += 1
        path = folder / f"{day}.{n}.jsonl"


def write(record: dict[str, Any], root: Path | None = None) -> Path:
    line = json.dumps(record, separators=(",", ":"), ensure_ascii=False, sort_keys=False)
    if len(line.encode()) > MAX_LINE_BYTES:
        record = {**record, "params": {"dropped": "too_long"}}
        line = json.dumps(record, separators=(",", ":"), ensure_ascii=False)
    path = file_for(record, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    # One write of one line with O_APPEND: lines from several processes do not
    # interleave.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(fd, (line + "\n").encode())
    finally:
        os.close(fd)
    return path


def log(
    event_name: str,
    *,
    source: str,
    params: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
    session_id: str | None = None,
) -> dict[str, Any] | None:
    """Write one event. Never raises: logging must never break the work."""
    if not enabled():
        return None
    try:
        record = make_record(
            event_name, source=source, params=params, context=context, session_id=session_id
        )
        write(record)
        return record
    except Exception:
        return None


# ---------------------------------------------------------------- reading


def log_files(root: Path | None = None, include_eval: bool = False, suite: str | None = None) -> list[Path]:
    root = root or usage_dir()
    if not root.is_dir():
        return []
    files: list[Path] = []
    if suite is None:
        files += sorted(root.glob("*.jsonl"))
    if include_eval or suite:
        pattern = f"eval/{suite}/*.jsonl" if suite else "eval/*/*.jsonl"
        files += sorted(root.glob(pattern))
    return files


def parse_since(text: str | None) -> int | None:
    """"7d", "12h", "2026-11-20" or None, as a timestamp_ns lower bound."""
    if not text:
        return None
    text = text.strip()
    m = re.fullmatch(r"(\d+)([dhm])", text)
    if m:
        seconds = int(m.group(1)) * {"d": 86400, "h": 3600, "m": 60}[m.group(2)]
        return time.time_ns() - seconds * 1_000_000_000
    try:
        day = _dt.datetime.fromisoformat(text)
    except ValueError as err:
        raise ValueError(f"--since takes 7d, 12h, 30m or a date like 2026-11-20: {text!r}") from err
    if day.tzinfo is None:
        day = day.replace(tzinfo=_dt.timezone.utc)
    return int(day.timestamp() * 1e9)


def read(files: Iterable[Path], since_ns: int | None = None) -> Iterator[dict[str, Any]]:
    for path in files:
        opener = gzip.open if path.suffix == ".gz" else open
        try:
            with opener(path, "rt", encoding="utf-8") as handle:  # type: ignore[operator]
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except ValueError:
                        continue
                    if not isinstance(record, dict) or record.get("schema") != SCHEMA:
                        continue
                    if since_ns and int(record.get("timestamp_ns") or 0) < since_ns:
                        continue
                    yield record
        except OSError:
            continue


def check_record(record: Any) -> list[str]:
    """Problems with one line, as short sentences. Empty when it is fine."""
    if not isinstance(record, dict):
        return ["not a JSON object"]
    problems = []
    if record.get("schema") != SCHEMA:
        problems.append("schema is not omnigent-slim.usage")
    if record.get("schema_version") != SCHEMA_VERSION:
        problems.append(f"schema_version is not {SCHEMA_VERSION}")
    name = record.get("event_name")
    if not isinstance(name, str) or not EVENT_RE.match(name):
        problems.append("event_name is not area.action")
    if record.get("source") not in SOURCES:
        problems.append("unknown source")
    if not isinstance(record.get("timestamp_ns"), int):
        problems.append("timestamp_ns missing")
    params = record.get("params")
    if not isinstance(params, dict):
        problems.append("params is not an object")
    else:
        for key, value in params.items():
            if clean_value(value, key=key, lvl="ids") != value and not (
                isinstance(value, str) and value.startswith("<text ")
            ):
                problems.append(f"params.{key} holds text that should have been redacted")
    return problems


# ---------------------------------------------------------------- analysis


def _bump(table: dict[str, int], key: Any, n: int = 1) -> None:
    if key is None or key == "":
        return
    table[str(key)] = table.get(str(key), 0) + n


def _top(table: dict[str, int], n: int = 15) -> list[list[Any]]:
    return [[k, v] for k, v in sorted(table.items(), key=lambda kv: (-kv[1], kv[0]))[:n]]


def summarize(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Counts that answer "how is the platform being used"."""
    events: dict[str, int] = {}
    sources: dict[str, int] = {}
    days: dict[str, int] = {}
    pages: dict[str, int] = {}
    clicks: dict[str, int] = {}
    pa_commands: dict[str, int] = {}
    pa_failures: dict[str, int] = {}
    tools: dict[str, int] = {}
    skills: dict[str, int] = {}
    workflows: dict[str, int] = {}
    hangar: dict[str, int] = {}
    modes: dict[str, int] = {}
    sessions: set[str] = set()
    turns = {"completed": 0, "failed": 0, "other": 0}
    usage: dict[str, dict[str, float]] = {}
    first = last = None
    total = 0
    for rec in records:
        total += 1
        name = str(rec.get("event_name", ""))
        params = rec.get("params") or {}
        ctx = rec.get("context") or {}
        stamp = str(rec.get("timestamp", ""))
        first = stamp if first is None or stamp < first else first
        last = stamp if last is None or stamp > last else last
        _bump(events, name)
        _bump(sources, rec.get("source"))
        _bump(days, stamp[:10])
        _bump(modes, ctx.get("mode") or "flying")
        if rec.get("session_id"):
            sessions.add(str(rec["session_id"]))
        workflow = ctx.get("workflow") or params.get("workflow")
        if workflow and name in ("pa.flow", "pa.brief", "skill.started", "workflow.started"):
            _bump(workflows, workflow)
        if name == "web.page_view":
            _bump(pages, params.get("page"))
        elif name == "web.click":
            _bump(clicks, params.get("component"))
        elif name.startswith("pa.") and name != "pa.log":
            _bump(pa_commands, name[3:])
            if params.get("exit") not in (None, 0):
                _bump(pa_failures, name[3:])
        elif name == "tool.used":
            _bump(tools, params.get("tool"))
            if params.get("skill"):
                _bump(skills, params.get("skill"))
        elif name.startswith("hangar."):
            _bump(hangar, name[7:])
        elif name == "upstream.turn_end":
            status = params.get("status")
            turns[status if status in ("completed", "failed") else "other"] += 1
        elif name == "upstream.native_session_usage" and rec.get("session_id"):
            usage[str(rec["session_id"])] = {
                "input_tokens": float(params.get("input_tokens") or 0),
                "output_tokens": float(params.get("output_tokens") or 0),
                "cost_usd": float(params.get("cost_usd") or 0),
            }
    return {
        "events": total,
        "first": first,
        "last": last,
        "sessions": len(sessions),
        "turns": turns,
        "tokens": {
            "input": int(sum(u["input_tokens"] for u in usage.values())),
            "output": int(sum(u["output_tokens"] for u in usage.values())),
            "cost_usd": round(sum(u["cost_usd"] for u in usage.values()), 2),
        },
        "by_day": sorted(days.items()),
        "by_source": _top(sources),
        "by_mode": _top(modes),
        "top_events": _top(events),
        "pages": _top(pages),
        "clicks": _top(clicks),
        "workflows": _top(workflows),
        "skills": _top(skills),
        "tools": _top(tools),
        "pa_commands": _top(pa_commands),
        "pa_failures": _top(pa_failures),
        "hangar": _top(hangar),
    }


def format_summary(summary: dict[str, Any]) -> str:
    if not summary["events"]:
        return "No usage logged yet."
    lines = [
        f"{summary['events']} events, {summary['first'][:16]} to {summary['last'][:16]} (UTC)",
        f"{summary['sessions']} sessions; turns: {summary['turns']['completed']} completed, "
        f"{summary['turns']['failed']} failed; tokens in {summary['tokens']['input']:,}, "
        f"out {summary['tokens']['output']:,}, about ${summary['tokens']['cost_usd']}",
    ]
    sections = [
        ("By day", "by_day"), ("Where from", "by_source"), ("Mode", "by_mode"),
        ("Pages", "pages"), ("Clicks", "clicks"), ("Workflows started", "workflows"),
        ("Skills loaded", "skills"), ("Tools used", "tools"), ("pa commands", "pa_commands"),
        ("pa commands that failed", "pa_failures"), ("Hangar", "hangar"),
    ]
    for title, key in sections:
        rows = summary.get(key) or []
        if not rows:
            continue
        lines.append("")
        lines.append(title)
        width = max(len(str(r[0])) for r in rows)
        for name, count in rows:
            lines.append(f"  {str(name).ljust(width)}  {count}")
    return "\n".join(lines)


# ---------------------------------------------------------------- leaving the machine


def to_upstream(record: dict[str, Any]) -> dict[str, Any]:
    """One line in upstream Omnigent's gateway record shape (``client.py``).

    Everything without a top-level slot in that shape (context, source, event
    id, the slim event name) goes into the JSON-encoded ``params``, as upstream
    does with its own event fields.
    """
    params = dict(record.get("params") or {})
    params["slim_event"] = record.get("event_name")
    params["slim_source"] = record.get("source")
    params["slim_event_id"] = record.get("event_id")
    params["slim_session_id"] = record.get("session_id")
    if record.get("context"):
        params["slim_context"] = record["context"]
    return {
        "data": {
            "event_name": record.get("event_name"),
            "session_id": record.get("process_id") or "",
            "omnigent_version": record.get("omnigent_version") or "",
            "schema_version": record.get("schema_version"),
            "python_version": sys.version.split()[0],
            "operating_system": record.get("operating_system") or "",
            "timestamp_ns": record.get("timestamp_ns"),
            "status": "success",
            "duration_ms": int(params.get("duration_ms") or 0),
            "installation_id": record.get("installation_id"),
            "anon_user_id": None,
            "host_installation_id": None,
            "environment": "omnigent-slim",
            "params": json.dumps(params, default=str),
        },
        "partition-key": record.get("event_id") or uuid.uuid4().hex,
    }


class Exporter:
    """Where packed lines go once there is somewhere to send them (D-127).

    Today the only exporter writes a file (``FileExporter``). A remote one
    implements ``send`` the same way, takes batches in the ``to_upstream``
    shape, and must be switched on by a person: the offline guard blocks
    every connection from the app's own processes until then.
    """

    name = "abstract"

    def send(self, batch: list[dict[str, Any]]) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class FileExporter(Exporter):
    name = "file"

    def __init__(self, path: Path, shape: str = "slim") -> None:
        self.path = path
        self.shape = shape
        self.count = 0

    def send(self, batch: list[dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        opener = gzip.open if self.path.suffix == ".gz" else open
        mode = "at"
        with opener(self.path, mode, encoding="utf-8") as handle:  # type: ignore[operator]
            for rec in batch:
                line = to_upstream(rec) if self.shape == "upstream" else rec
                handle.write(json.dumps(line, separators=(",", ":"), ensure_ascii=False) + "\n")
                self.count += 1


def fingerprint_record(record: dict[str, Any]) -> dict[str, Any]:
    """The same line with every name hashed, except the fixed vocabulary.

    For a pack that leaves a machine whose file and record names are
    themselves sensitive (the work Mac): counts and links between events stay,
    the names do not. Already-redacted text stays as it is.
    """
    def _one(key: str, value: Any) -> Any:
        if isinstance(value, str) and not value.startswith("<text ") and key not in SAFE_KEYS:
            return _fingerprint(value)
        if isinstance(value, list):
            return [_one(key, v) for v in value]
        return value

    out = dict(record)
    out["params"] = {k: _one(k, v) for k, v in (record.get("params") or {}).items()}
    ctx = dict(record.get("context") or {})
    for key in ("project", "run"):
        if isinstance(ctx.get(key), str):
            ctx[key] = _fingerprint(ctx[key])
    out["context"] = ctx
    out["level"] = "fingerprint"
    return out


def pack(
    out: Path,
    files: Iterable[Path],
    since_ns: int | None = None,
    shape: str = "slim",
    batch_size: int = 500,
    fingerprint: bool = False,
) -> dict[str, Any]:
    """Copy lines into one file to carry off this machine, re-checking each.

    A line that fails ``check_record`` is left out and counted, so a pack never
    carries something the writer should have redacted. ``fingerprint`` hashes
    names on the way out (``fingerprint_record``).
    """
    if out.exists():
        out.unlink()
    exporter = FileExporter(out, shape)
    batch: list[dict[str, Any]] = []
    skipped = 0
    for rec in read(files, since_ns):
        if check_record(rec):
            skipped += 1
            continue
        batch.append(fingerprint_record(rec) if fingerprint else rec)
        if len(batch) >= batch_size:
            exporter.send(batch)
            batch = []
    if batch:
        exporter.send(batch)
    return {
        "path": str(out),
        "lines": exporter.count,
        "left_out": skipped,
        "shape": shape,
        "fingerprint": fingerprint,
    }
