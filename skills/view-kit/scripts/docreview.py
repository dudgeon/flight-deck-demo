"""`pa review`: comments, replies and suggested changes in a markdown document.

Everything stays in plain files next to the document, so any session (the
user's main session or a participant's background session) can take part with
ordinary file tools or this command, and the editor in the app shows it all
attributed to whoever wrote it.

* Suggested changes live in the document itself as CriticMarkup, followed by a
  CriticMarkup comment that names who made them::

      {++added text++}{>>@risk-review 2026-11-21T12:40<<}
      {--removed text--}{>>@mara-okafor<<}
      {~~old text~>new text~~}{>>@aviator<<}

* Comment threads live in a sidecar file, ``<document>.review.json``::

      {"version": 1, "threads": [{"id": "t1", "anchor": {"quote": "weekly limits"},
        "by": "you", "at": "...", "resolved": false,
        "messages": [{"id": "m1", "by": "you", "at": "...", "text": "@mara-okafor thoughts?",
                      "mentions": ["mara-okafor"]}]}]}

``by`` is a participant id from ``participants/``, ``you`` for the user, or
``aviator`` for the user's main agent.
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

SIDECAR_SUFFIX = ".review.json"
USER_ID = "you"
MAIN_AGENT_ID = "aviator"
#: Names people type for the main agent.
MAIN_AGENT_ALIASES = ("aviator", "claude")

# One suggestion: the change, then an optional {>>...<<} saying who made it.
_CHANGE = re.compile(
    r"\{\+\+(?P<ins>.*?)\+\+\}"
    r"|\{--(?P<del>.*?)--\}"
    r"|\{~~(?P<old>.*?)~>(?P<new>.*?)~~\}",
    re.S,
)
_META = re.compile(r"\{>>(?P<meta>.*?)<<\}", re.S)
_MENTION = re.compile(r"(?<![\w@])@([A-Za-z][\w-]*(?: [A-Z][\w-]*)?)")


class ReviewError(Exception):
    """A problem to report to the caller in one line."""


# ---------------------------------------------------------------- files


def _now() -> str:
    return _dt.datetime.now().astimezone().replace(microsecond=0).isoformat()


@contextlib.contextmanager
def _locked(path: Path) -> Iterator[None]:
    """Same lock file as `pa`, so `pa` and the editor's writers never interleave."""
    key = hashlib.sha1(str(path.resolve()).encode()).hexdigest()[:16]
    with open(Path(tempfile.gettempdir()) / f"pa-{key}.lock", "w") as handle:
        try:
            import fcntl

            fcntl.flock(handle, fcntl.LOCK_EX)
        except ImportError:
            pass
        yield


def _write_atomic(path: Path, text: str) -> None:
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def sidecar_path(doc: Path) -> Path:
    return doc.with_name(doc.name + SIDECAR_SUFFIX)


def _doc(path: str) -> Path:
    doc = Path(path)
    if doc.name.endswith(SIDECAR_SUFFIX):
        doc = doc.with_name(doc.name[: -len(SIDECAR_SUFFIX)])
    if not doc.is_file():
        raise ReviewError(f"{doc} does not exist")
    return doc


def load_review(doc: Path) -> dict[str, Any]:
    path = sidecar_path(doc)
    if not path.exists():
        return {"version": 1, "threads": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise ReviewError(f"{path} is not valid JSON: {err}") from None
    if not isinstance(data, dict) or not isinstance(data.get("threads"), list):
        raise ReviewError(f"{path} is not a review file (expected an object with a threads list)")
    return data


def save_review(doc: Path, data: dict[str, Any]) -> None:
    data["version"] = 1
    data["updated"] = _now()
    _write_atomic(sidecar_path(doc), json.dumps(data, indent=1, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------- people


def _roster(doc: Path) -> dict[str, dict[str, Any]]:
    """The one participant roster (see `pa who`). `doc` is unused but kept for callers."""
    try:
        from pa import _participants, _roster_dir  # type: ignore[import-not-found]
    except ImportError:  # loaded on its own, outside the kit
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from pa import _participants, _roster_dir  # type: ignore[import-not-found]
    return _participants(_roster_dir())


def resolve_mentions(text: str, roster: dict[str, dict[str, Any]]) -> list[str]:
    """Ids of everyone @mentioned in `text`, by id, name or first name, in order."""
    by_name: dict[str, str] = {}
    for pid, person in roster.items():
        name = str(person.get("name", pid)).lower()
        by_name[pid] = pid
        by_name[name] = pid
        by_name.setdefault(name.split()[0], pid)
    for alias in MAIN_AGENT_ALIASES:
        by_name.setdefault(alias, MAIN_AGENT_ID)
    found: list[str] = []
    for match in _MENTION.finditer(text):
        raw = match.group(1).lower()
        # "@Mara Okafor" or, failing that, "@Mara" followed by an ordinary word.
        pid = by_name.get(raw) or by_name.get(raw.split()[0].rstrip("-"))
        if pid and pid not in found:
            found.append(pid)
    return found


def _check_author(by: str, roster: dict[str, dict[str, Any]]) -> None:
    if by in (USER_ID, MAIN_AGENT_ID) or by in roster or not roster:
        return
    raise ReviewError(f"--by {by!r} is not you, aviator or a participant id ({', '.join(roster)})")


# ---------------------------------------------------------------- suggestions


def suggestions(text: str) -> list[dict[str, Any]]:
    """Every suggested change in document order, numbered s1, s2, ..."""
    out = []
    for n, match in enumerate(_CHANGE.finditer(text), start=1):
        end = match.end()
        meta = _META.match(text, end)
        by, at, note = None, None, ""
        if meta:
            end = meta.end()
            words = meta.group("meta").strip().split(None, 2)
            if words and words[0].startswith("@"):
                by = words[0][1:]
                rest = words[1:]
                if rest and re.match(r"\d{4}-\d\d-\d\d", rest[0]):
                    at = rest.pop(0)
                note = " ".join(rest)
            else:
                note = meta.group("meta").strip()
        if match.group("ins") is not None:
            kind, old, new = "insert", "", match.group("ins")
        elif match.group("del") is not None:
            kind, old, new = "delete", match.group("del"), ""
        else:
            kind, old, new = "replace", match.group("old"), match.group("new")
        out.append({"id": f"s{n}", "kind": kind, "old": old, "new": new, "by": by, "at": at, "note": note,
                    "start": match.start(), "end": end})
    return out


def accepted_text(text: str) -> str:
    """The document as it reads with every suggestion accepted."""
    return _apply(text, suggestions(text), accept=True)


def _apply(text: str, chosen: list[dict[str, Any]], *, accept: bool) -> str:
    for s in sorted(chosen, key=lambda s: s["start"], reverse=True):
        keep = s["new"] if accept else s["old"]
        text = text[: s["start"]] + keep + text[s["end"] :]
    return text


def _tag(by: str, note: str = "") -> str:
    stamp = _dt.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M")
    return "{>>@" + by + " " + stamp + (" " + note if note else "") + "<<}"


def _find_once(text: str, quote: str, occurrence: int | None) -> int:
    """Index of `quote` in `text`, outside existing suggestions."""
    taken = [(s["start"], s["end"]) for s in suggestions(text)]
    hits = [m.start() for m in re.finditer(re.escape(quote), text)
            if not any(a < m.start() + len(quote) and m.start() < b for a, b in taken)]
    if not hits:
        raise ReviewError(f"the text {quote!r} is not in the document (or is already inside a suggestion)")
    if occurrence is None:
        if len(hits) > 1:
            raise ReviewError(f"{quote!r} appears {len(hits)} times; quote more words or pass --occurrence N")
        return hits[0]
    if not 1 <= occurrence <= len(hits):
        raise ReviewError(f"{quote!r} appears {len(hits)} times; --occurrence must be 1 to {len(hits)}")
    return hits[occurrence - 1]


# ---------------------------------------------------------------- threads


def _thread(data: dict[str, Any], tid: str) -> dict[str, Any]:
    for thread in data["threads"]:
        if thread.get("id") == tid:
            return thread
    raise ReviewError(f"no thread {tid!r}; threads: {', '.join(t['id'] for t in data['threads']) or 'none'}")


def _next(prefix: str, ids: list[str]) -> str:
    nums = [int(i[len(prefix):]) for i in ids if i.startswith(prefix) and i[len(prefix):].isdigit()]
    return f"{prefix}{max(nums, default=0) + 1}"


def _message(data: dict[str, Any], by: str, text: str, roster: dict[str, dict[str, Any]]) -> dict[str, Any]:
    ids = [m.get("id", "") for t in data["threads"] for m in t.get("messages", [])]
    msg = {"id": _next("m", ids), "by": by, "at": _now(), "text": text.strip()}
    mentions = [m for m in resolve_mentions(text, roster) if m != by]
    if mentions:
        msg["mentions"] = mentions
    return msg


def pending_mentions(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Mentions nobody has answered: no later message in the thread by the one mentioned."""
    out = []
    for thread in data["threads"]:
        if thread.get("resolved"):
            continue
        messages = thread.get("messages", [])
        for i, msg in enumerate(messages):
            for who in msg.get("mentions", []):
                if not any(later.get("by") == who for later in messages[i + 1 :]):
                    out.append({"thread": thread["id"], "message": msg["id"], "who": who, "from": msg.get("by"),
                                "quote": thread.get("anchor", {}).get("quote", ""), "text": msg.get("text", "")})
    return out


# ---------------------------------------------------------------- commands


def cmd_show(args: argparse.Namespace) -> None:
    doc = _doc(args.doc)
    text = doc.read_text(encoding="utf-8")
    data = load_review(doc)
    changes = suggestions(text)
    if args.json:
        print(json.dumps({"doc": str(doc), "suggestions": [{k: v for k, v in s.items() if k not in ("start", "end")}
                                                             for s in changes],
                          "threads": data["threads"], "pending": pending_mentions(data)}, indent=1, ensure_ascii=False))
        return
    open_threads = [t for t in data["threads"] if not t.get("resolved")]
    print(f"{doc}: {len(changes)} suggestion(s), {len(open_threads)} open thread(s)"
          f" of {len(data['threads'])}.")
    for s in changes:
        what = {"insert": f"add {s['new']!r}", "delete": f"remove {s['old']!r}",
                "replace": f"change {s['old']!r} to {s['new']!r}"}[s["kind"]]
        print(f"  {s['id']} {s['by'] or 'unknown'}: {what}" + (f" ({s['note']})" if s["note"] else ""))
    for thread in data["threads"] if args.all else open_threads:
        flag = " [resolved]" if thread.get("resolved") else ""
        print(f"  {thread['id']}{flag} on {thread.get('anchor', {}).get('quote', '')!r}")
        for msg in thread.get("messages", []):
            print(f"    {msg['id']} {msg['by']}: {msg['text']}")
    for p in pending_mentions(data):
        print(f"  waiting: {p['who']} was asked in {p['thread']} ({p['message']})")


def cmd_comment(args: argparse.Namespace) -> None:
    doc = _doc(args.doc)
    roster = _roster(doc)
    _check_author(args.by, roster)
    text = doc.read_text(encoding="utf-8")
    if args.quote not in text and args.quote not in accepted_text(text):
        raise ReviewError(f"the text {args.quote!r} is not in the document; quote it exactly")
    with _locked(sidecar_path(doc)):
        data = load_review(doc)
        tid = _next("t", [t.get("id", "") for t in data["threads"]])
        anchor: dict[str, Any] = {"quote": args.quote}
        if args.occurrence:
            anchor["occurrence"] = args.occurrence
        msg = _message(data, args.by, args.text, roster)
        data["threads"].append({"id": tid, "anchor": anchor, "by": args.by, "at": msg["at"], "resolved": False,
                                "messages": [msg]})
        save_review(doc, data)
    print(f"{tid}: comment added" + (f"; mentions {', '.join(msg['mentions'])}" if msg.get("mentions") else ""))


def cmd_reply(args: argparse.Namespace) -> None:
    doc = _doc(args.doc)
    roster = _roster(doc)
    _check_author(args.by, roster)
    with _locked(sidecar_path(doc)):
        data = load_review(doc)
        thread = _thread(data, args.thread)
        msg = _message(data, args.by, args.text, roster)
        thread.setdefault("messages", []).append(msg)
        if thread.get("resolved"):
            thread["resolved"] = False
        save_review(doc, data)
    print(f"{args.thread}: reply {msg['id']} added" + (f"; mentions {', '.join(msg['mentions'])}" if msg.get("mentions") else ""))


def cmd_resolve(args: argparse.Namespace) -> None:
    doc = _doc(args.doc)
    with _locked(sidecar_path(doc)):
        data = load_review(doc)
        thread = _thread(data, args.thread)
        thread["resolved"] = not args.reopen
        if args.reopen:
            thread.pop("resolved_by", None)
        else:
            thread["resolved_by"] = args.by
            thread["resolved_at"] = _now()
        save_review(doc, data)
    print(f"{args.thread}: {'reopened' if args.reopen else 'resolved'}")


_BLOCK_MARKER = re.compile(r"^\s*(?:[-*+]|\d+[.)]|#{1,6}|>)\s+")


def _inline_only(quote: str | None, new: str | None) -> tuple[str | None, str | None]:
    """Suggestions sit inside one line: strip a list, heading or quote marker both sides share."""
    if quote is None:
        return quote, new
    if "\n" in quote or (new is not None and "\n" in new):
        raise ReviewError("suggest one line at a time: the quoted text and the new text must not contain line breaks")
    marker = _BLOCK_MARKER.match(quote)
    if marker:
        prefix = marker.group(0)
        quote = quote[len(prefix):]
        if new is not None and new.startswith(prefix):
            new = new[len(prefix):]
    return quote, new


def cmd_suggest(args: argparse.Namespace) -> None:
    doc = _doc(args.doc)
    args.replace, args.with_ = _inline_only(args.replace, args.with_)
    args.delete, _ = _inline_only(args.delete, None)
    args.after, args.insert = _inline_only(args.after, args.insert) if args.after else (args.after, args.insert)
    args.before, _ = _inline_only(args.before, None)
    _check_author(args.by, _roster(doc))
    tag = _tag(args.by, args.note or "")
    with _locked(doc):
        text = doc.read_text(encoding="utf-8")
        if args.insert is not None:
            if not args.after and not args.before:
                raise ReviewError("say where with --after TEXT or --before TEXT")
            quote = args.after or args.before
            at = _find_once(text, quote, args.occurrence) + (len(quote) if args.after else 0)
            text = text[:at] + "{++" + args.insert + "++}" + tag + text[at:]
        elif args.delete is not None:
            at = _find_once(text, args.delete, args.occurrence)
            text = text[:at] + "{--" + args.delete + "--}" + tag + text[at + len(args.delete):]
        elif args.replace is not None:
            if args.with_ is None:
                raise ReviewError("--replace needs --with")
            at = _find_once(text, args.replace, args.occurrence)
            text = text[:at] + "{~~" + args.replace + "~>" + args.with_ + "~~}" + tag + text[at + len(args.replace):]
        else:
            raise ReviewError("give one of --insert, --delete or --replace")
        _write_atomic(doc, text)
    print("suggestion added")


def cmd_decide(args: argparse.Namespace) -> None:
    doc = _doc(args.doc)
    with _locked(doc):
        text = doc.read_text(encoding="utf-8")
        changes = suggestions(text)
        if args.ids == ["all"]:
            chosen = changes
        else:
            chosen = [s for s in changes if s["id"] in args.ids]
            missing = set(args.ids) - {s["id"] for s in chosen}
            if missing:
                raise ReviewError(f"no suggestion {', '.join(sorted(missing))}; run `pa review show` for the ids")
        if args.from_:
            chosen = [s for s in chosen if s["by"] == args.from_]
        _write_atomic(doc, _apply(text, chosen, accept=args.accept))
    print(f"{'accepted' if args.accept else 'rejected'} {len(chosen)} suggestion(s)")


def cmd_pending(args: argparse.Namespace) -> None:
    docs = [_doc(d) for d in args.docs] if args.docs else [
        Path(str(p)[: -len(SIDECAR_SUFFIX)]) for p in sorted(Path(args.dir).rglob("*" + SIDECAR_SUFFIX))]
    rows = []
    for doc in docs:
        if doc.is_file():
            rows += [{"doc": str(doc), **p} for p in pending_mentions(load_review(doc))]
    if args.who:
        rows = [r for r in rows if r["who"] == args.who]
    if args.json:
        print(json.dumps(rows, indent=1, ensure_ascii=False))
        return
    if not rows:
        print("no unanswered mentions")
    for r in rows:
        print(f"{r['doc']} {r['thread']} {r['message']}: {r['from']} asked {r['who']}: {r['text']}")


ASK = """{asker} asked you in a comment on the document `{doc}`.

They commented on this passage:

> {quote}

The thread so far:

{transcript}

Read the document first. Then answer in the thread, as yourself, with:

    {pa} review reply {doc} {thread} --by {who} --text "your reply"

Keep it to a few sentences. If you want to propose wording, do not edit the
document directly: suggest it, and it shows as your change for them to accept:

    {pa} review suggest {doc} --by {who} --replace "exact text" --with "new text"

(also --insert TEXT --after "exact text", or --delete "exact text"). Mention
someone with @their-id only if you need them to answer too. When you have
replied, end your turn with one line starting `DONE:`.
"""


def cmd_ask(args: argparse.Namespace) -> None:
    doc = _doc(args.doc)
    data = load_review(doc)
    thread = _thread(data, args.thread)
    roster = _roster(doc)
    names = {pid: p.get("name", pid) for pid, p in roster.items()}
    names.update({USER_ID: "The product manager", MAIN_AGENT_ID: "Aviator"})
    lines = [f"- {names.get(m['by'], m['by'])}: {m['text']}" for m in thread.get("messages", [])]
    asker = next((names.get(m["by"], m["by"]) for m in reversed(thread.get("messages", []))
                  if args.who in m.get("mentions", [])), "Someone")
    print(ASK.format(asker=asker, doc=doc, quote=thread.get("anchor", {}).get("quote", ""),
                     transcript="\n".join(lines), pa=args.pa, thread=thread["id"], who=args.who).rstrip())


def register(sub: Any) -> None:
    """Add `review` and its subcommands to `pa`'s argument parser."""
    review = sub.add_parser("review", help="comments, replies and suggested changes in a markdown document")
    rsub = review.add_subparsers(dest="review_command", required=True)

    p = rsub.add_parser("show", help="list the suggestions, threads and unanswered mentions")
    p.add_argument("doc")
    p.add_argument("--all", action="store_true", help="include resolved threads")
    p.add_argument("--json", action="store_true")
    p.set_defaults(run=cmd_show)

    p = rsub.add_parser("comment", help="start a thread on a passage")
    p.add_argument("doc")
    p.add_argument("--quote", required=True, help="the exact text the comment is about")
    p.add_argument("--occurrence", type=int, help="which match of --quote, when it appears more than once")
    p.add_argument("--text", required=True)
    p.add_argument("--by", required=True, help="your participant id, or aviator")
    p.set_defaults(run=cmd_comment)

    p = rsub.add_parser("reply", help="reply in a thread")
    p.add_argument("doc")
    p.add_argument("thread")
    p.add_argument("--text", required=True)
    p.add_argument("--by", required=True)
    p.set_defaults(run=cmd_reply)

    p = rsub.add_parser("resolve", help="resolve a thread, or reopen it")
    p.add_argument("doc")
    p.add_argument("thread")
    p.add_argument("--by", default=MAIN_AGENT_ID)
    p.add_argument("--reopen", action="store_true")
    p.set_defaults(run=cmd_resolve)

    p = rsub.add_parser("suggest", help="propose a change, shown as yours for the user to accept")
    p.add_argument("doc")
    p.add_argument("--by", required=True)
    p.add_argument("--insert")
    p.add_argument("--after")
    p.add_argument("--before")
    p.add_argument("--delete")
    p.add_argument("--replace")
    p.add_argument("--with", dest="with_")
    p.add_argument("--occurrence", type=int)
    p.add_argument("--note", help="a few words on why")
    p.set_defaults(run=cmd_suggest)

    for name, accept in (("accept", True), ("reject", False)):
        p = rsub.add_parser(name, help=f"{name} suggestions by id, or all")
        p.add_argument("doc")
        p.add_argument("ids", nargs="+", help="s1 s2 ..., or all")
        p.add_argument("--from", dest="from_", help="only those by this participant")
        p.set_defaults(run=cmd_decide, accept=accept)

    p = rsub.add_parser("pending", help="mentions nobody has answered yet")
    p.add_argument("docs", nargs="*")
    p.add_argument("--dir", default=".", help="without docs: search this folder")
    p.add_argument("--who", help="only mentions of this participant")
    p.add_argument("--json", action="store_true")
    p.set_defaults(run=cmd_pending)

    p = rsub.add_parser("ask", help="print the message that asks a participant to answer in a thread")
    p.add_argument("doc")
    p.add_argument("thread")
    p.add_argument("who", help="the participant id")
    p.add_argument("--pa", default="pa", help="how the participant should run this command")
    p.set_defaults(run=cmd_ask)
