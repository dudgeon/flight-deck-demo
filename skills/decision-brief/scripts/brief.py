#!/usr/bin/env python3
"""Decision briefs: one JSON file in, one self-contained HTML page out.

The agent writes only the brief's content (a JSON file). The layout, styles,
answer handling and the visual components live in ../template/brief.html and
never change per brief, so every brief looks and works the same and costs only
its content in tokens.

  brief.py new <brief.json> --title "..." [--decisions 3] [--initiative <key>]
  brief.py check <brief.json>                 rules a brief must meet (never blind)
  brief.py render <brief.json> [--out <page.html>] [--fragment]
  brief.py answer <brief.json> <decision> <option|else> [--note "..."] [--at ISO]
  brief.py import <brief.json> (--text <file|-> | --db <folder>)
  brief.py record <brief.json> [--by <who>] [--no-register]
  brief.py note <brief.json> [--out <note.md>] [--url ...] [--archive ...]

A project's briefs live in its decisions folder, projects/<key>/decisions/:
<slug>.json (the brief and its answers), <slug>.html (the page) and
<slug>.md (the decision note), all side by side.

Standard library only. Nothing here reaches the network.
"""

from __future__ import annotations

import argparse
import base64
import datetime as _dt
import json
import mimetypes
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parent / "template" / "brief.html"
PA = HERE.parent.parent / "view-kit" / "scripts" / "pa.py"
ELSE = "else"
MAX_IMAGE = 1_500_000  # bytes per inlined image; bigger ones should be resized

# A literal color in a stage's html breaks the token rule (D-36) and dark mode.
STYLE_COLOR = re.compile(r"style\s*=\s*\"[^\"]*(?:#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\()", re.I)
REMOTE = re.compile(r"""(?:src|href)\s*=\s*["']?\s*(?:https?:)?//|url\(\s*["']?(?:https?:)?//""", re.I)


class BriefError(Exception):
    pass


def load(path: str | Path) -> dict:
    p = Path(path)
    if not p.exists():
        raise BriefError(f"{p}: no such brief")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise BriefError(f"{p}: not valid JSON ({e})") from e
    if not isinstance(data, dict):
        raise BriefError(f"{p}: a brief is one JSON object")
    return data


def save(path: str | Path, data: dict) -> None:
    Path(path).write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def decision(data: dict, did: str) -> dict:
    for d in data.get("decisions") or []:
        if d.get("id") == did or d.get("label") == did:
            return d
    raise BriefError(f"no decision {did!r} in this brief")


def label_of(d: dict, pick: str) -> str:
    if pick == ELSE:
        return "Something else"
    for o in d.get("options") or []:
        if o.get("id") == pick:
            return o.get("label", pick)
    raise BriefError(f"{d.get('id')}: no option {pick!r} (options: {', '.join(o.get('id', '?') for o in d.get('options') or [])}, or else)")


def recommended(d: dict) -> dict | None:
    return next((o for o in d.get("options") or [] if o.get("recommended")), None)


# ── check ────────────────────────────────────────────────────────────────────

def problems(data: dict, base: Path) -> tuple[list[str], list[str]]:
    """Errors (the brief must not go out) and warnings (look again)."""
    err: list[str] = []
    warn: list[str] = []
    for key in ("id", "title"):
        if not data.get(key):
            err.append(f"the brief needs a {key}")
    if not data.get("why"):
        err.append("the brief needs `why`: what this is and why the person is seeing it")
    decs = data.get("decisions") or []
    if not decs:
        err.append("the brief has no decisions")
    if len(decs) > 8:
        warn.append(f"{len(decs)} decisions: more than 8 is hard to take in at once; split the brief or order it by dependency")
    seen: set[str] = set()
    for i, d in enumerate(decs, 1):
        name = d.get("label") or d.get("id") or f"decision {i}"
        did = d.get("id")
        if not did or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", str(did)):
            err.append(f"{name}: needs an id of lowercase letters, digits and hyphens")
        elif did in seen:
            err.append(f"{name}: id {did} used twice")
        seen.add(str(did))
        if not d.get("question"):
            err.append(f"{name}: needs a question")
        if not d.get("context"):
            err.append(f"{name}: needs context; never ask blind (D-33)")
        opts = d.get("options") or []
        if len(opts) < 2:
            err.append(f"{name}: needs at least two real options")
        if len(opts) > 5:
            warn.append(f"{name}: {len(opts)} options; three or four is usually enough")
        ids = [o.get("id") for o in opts]
        if len(set(ids)) != len(ids) or any(not x for x in ids):
            err.append(f"{name}: every option needs its own id")
        if ELSE in ids or any(re.fullmatch(r"(something|anything) else\b.*", str(o.get("label", "")), re.I) for o in opts):
            err.append(f"{name}: don't write a Something else option; the page adds it to every decision (D-105)")
        recs = [o for o in opts if o.get("recommended")]
        if len(recs) != 1:
            err.append(f"{name}: mark exactly one option recommended (has {len(recs)})")
        if not d.get("reason"):
            err.append(f"{name}: needs `reason`, why you recommend that option")
        for o in opts:
            if not o.get("label"):
                err.append(f"{name}: option {o.get('id')} needs a label")
            if not o.get("consequence"):
                err.append(f"{name}: option {o.get('label') or o.get('id')} needs a consequence: what happens and what it gives up")
        if not d.get("stage") and not any(o.get("visual") for o in opts):
            warn.append(f"{name}: no visual. Add a stage or option visuals unless the choice truly has nothing to look at")
        for dep in d.get("depends_on") or []:
            if dep not in {x.get("id") for x in decs}:
                err.append(f"{name}: depends_on names {dep}, which is not in this brief")
        visuals = [("stage", d.get("stage"))] + [(f"option {o.get('id')}", o.get("visual")) for o in opts]
        for where, v in visuals:
            if not v:
                continue
            if not isinstance(v, dict) or not (v.get("html") or v.get("image")):
                err.append(f"{name} {where}: a visual is {{\"html\": ...}} or {{\"image\": path}}")
                continue
            html = v.get("html") or ""
            if REMOTE.search(html):
                err.append(f"{name} {where}: loads something from the network; inline it (offline rule)")
            if STYLE_COLOR.search(html) or re.search(r"<style", html, re.I):
                err.append(f"{name} {where}: sets its own colors or styles; use the components and var(--pa-…) tokens")
            if re.search(r"<script", html, re.I):
                err.append(f"{name} {where}: no scripts in a visual")
            img = v.get("image")
            if img and not str(img).startswith("data:"):
                if re.match(r"(?:https?:)?//", str(img)):
                    err.append(f"{name} {where}: image is remote; save it beside the brief")
                else:
                    p = (base / img)
                    if not p.exists():
                        err.append(f"{name} {where}: image {img} not found next to the brief")
                    elif p.stat().st_size > MAX_IMAGE:
                        warn.append(f"{name} {where}: image {img} is {p.stat().st_size // 1024} KB; resize it")
        a = d.get("answer")
        if a and a.get("pick") not in set(ids) | {ELSE}:
            err.append(f"{name}: recorded answer picks {a.get('pick')!r}, which is not an option")
    for x in data.get("read") or []:
        if not x.get("label"):
            err.append("every entry in `read` needs a label")
    return err, warn


def cmd_check(args) -> int:
    data = load(args.brief)
    err, warn = problems(data, Path(args.brief).resolve().parent)
    for w in warn:
        print(f"warning: {w}")
    for e in err:
        print(f"error: {e}")
    if err:
        return 1
    n = len(data.get("decisions") or [])
    print(f"ok: {data.get('id')}, {n} decision{'s' if n != 1 else ''}" + (f", {len(warn)} warning(s)" if warn else ""))
    return 0


# ── render ───────────────────────────────────────────────────────────────────

def inline_image(base: Path, src: str) -> str:
    if src.startswith("data:"):
        return src
    p = base / src
    mime = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode("ascii")


def esc_attr(t: str) -> str:
    return (t or "").replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")


def render(data: dict, base: Path, fragment: bool = False, source: str = "") -> str:
    data = json.loads(json.dumps(data))  # a copy we can rewrite
    if source:
        data["source"] = source  # the page names its brief file when it sends answers
    for d in data.get("decisions") or []:
        for v in [d.get("stage")] + [o.get("visual") for o in d.get("options") or []]:
            if isinstance(v, dict) and v.get("image"):
                v["image"] = inline_image(base, v["image"])
    tpl = TEMPLATE.read_text(encoding="utf-8")
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/").replace("<!--", "<\\!--")
    desc = data.get("description") or f"{len(data.get('decisions') or [])} decisions for {data.get('for') or 'you'}: pick an option on each, add a note, and the answers are saved for Claude."
    out = (tpl.replace("__BRIEF_TITLE__", esc_attr(data.get("title", "Decision brief")))
              .replace("__BRIEF_DESC__", esc_attr(desc))
              .replace("__BRIEF_JSON__", blob))
    if fragment:
        # claude.ai wraps a page in its own skeleton: hand it the head's title,
        # metas and style followed by the body's content.
        head = re.search(r"<head>(.*?)</head>", out, re.S).group(1)
        head = re.sub(r'<meta charset[^>]*>\s*|<meta name="viewport"[^>]*>\s*', "", head)
        body = re.search(r"<body>(.*?)</body>", out, re.S).group(1)
        out = head.strip() + "\n" + body.strip() + "\n"
    return out


def cmd_render(args) -> int:
    data = load(args.brief)
    base = Path(args.brief).resolve().parent
    err, warn = problems(data, base)
    for w in warn:
        print(f"warning: {w}", file=sys.stderr)
    if err and not args.force:
        for e in err:
            print(f"error: {e}", file=sys.stderr)
        print("not rendered; fix the errors above (or --force for a draft)", file=sys.stderr)
        return 1
    out = Path(args.out) if args.out else Path(args.brief).with_suffix(".html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(data, base, args.fragment, str(args.brief)), encoding="utf-8")
    print(f"rendered {out} ({out.stat().st_size // 1024} KB)")
    return 0


# ── answers ──────────────────────────────────────────────────────────────────

def set_answer(data: dict, did: str, pick: str, note: str = "", at: str | None = None, via: str = "agent") -> dict:
    d = decision(data, did)
    if (d.get("answer") or {}).get("locked"):
        raise BriefError(f"{d.get('id')} is already recorded; supersede it with a new brief instead of changing it")
    pick = pick.strip()
    if pick.lower() in ("else", "something else", "something-else"):
        pick = ELSE
    lab = label_of(d, pick)
    if pick == ELSE and not note.strip():
        raise BriefError(f"{d.get('id')}: Something else needs the person's words in --note")
    d["answer"] = {"pick": pick, "label": lab, "note": note.strip(), "at": at or now(), "via": via}
    return d


def cmd_answer(args) -> int:
    data = load(args.brief)
    d = set_answer(data, args.decision, args.pick, args.note or "", args.at, args.via)
    save(args.brief, data)
    print(f"{d['id']}: {d['answer']['label']}" + (f" · {d['answer']['note']}" if d["answer"]["note"] else ""))
    return 0


ANSWER_LINE = re.compile(r"^\s*-\s*([a-z0-9][a-z0-9-]*)\s*\|\s*([^|]*?)\s*(?:\|(.*))?$")


def parse_answers_text(text: str) -> list[tuple[str, str, str]]:
    """Lines the page's Send or Copy produced: `- <id> | <pick> [| <label>] [| note: ...]`.

    The note is everything after the first `| note:`, so it may hold `|` itself.
    """
    out = []
    for line in text.splitlines():
        m = ANSWER_LINE.match(line)
        if not m:
            continue
        rest = m.group(3) or ""
        n = re.search(r"(?:^|\|)\s*note:\s*(.*)$", rest)
        note = n.group(1).strip() if n else ""
        if len(note) >= 2 and note[0] == note[-1] == '"':
            note = note[1:-1].replace('\\"', '"')
        out.append((m.group(1), m.group(2), note))
    return out


def cmd_import(args) -> int:
    data = load(args.brief)
    got: list[tuple[str, str, str, str | None, str]] = []
    if args.text:
        text = sys.stdin.read() if args.text == "-" else Path(args.text).read_text(encoding="utf-8")
        got = [(i, p, n, None, "page") for i, p, n in parse_answers_text(text)]
    elif args.db:
        # An `answers` collection saved with the ArtifactData tool: one JSON file per document.
        for f in sorted(Path(args.db).glob("*.json")):
            v = json.loads(f.read_text(encoding="utf-8"))
            v = v.get("data", v) if isinstance(v, dict) else {}
            if v.get("pick") or v.get("choice"):
                got.append((f.stem, v.get("pick") or v.get("choice"), v.get("note") or v.get("text") or "", v.get("at"), v.get("via") or "page"))
    else:
        raise BriefError("give --text <file|-> or --db <folder>")
    if not got:
        raise BriefError("no answers found")
    for did, pick, note, at, via in got:
        d = decision(data, did)
        if (d.get("answer") or {}).get("locked"):
            print(f"{did}: already recorded, left as it is")
            continue
        set_answer(data, did, pick, note, at, via)
        print(f"{did}: {d['answer']['label']}" + (f" · {note}" if note else ""))
    save(args.brief, data)
    return 0


def cmd_record(args) -> int:
    """Lock the answers the person gave and write each to the initiative's register."""
    data = load(args.brief)
    decs = data.get("decisions") or []
    open_ = [d.get("label") or d["id"] for d in decs if not (d.get("answer") or {}).get("pick")]
    todo = [d for d in decs if (d.get("answer") or {}).get("pick") and not d["answer"].get("locked")]
    if not todo:
        print("nothing new to record" + (f"; still open: {', '.join(open_)}" if open_ else ""))
        return 0
    ini = data.get("initiative")
    for d in todo:
        a = d["answer"]
        if ini and not args.no_register:
            cmd = [sys.executable, str(PA), "register", ini, "decision", f"{d['question']} {a['label']}",
                   "--source", str(args.brief), "--by", args.by]
            if a.get("note"):
                cmd += ["--note", a["note"]]
            if d.get("supersedes"):
                cmd += ["--supersedes", d["supersedes"]]
            run = subprocess.run(cmd, capture_output=True, text=True)
            if run.returncode != 0:
                raise BriefError(f"{d['id']}: pa register failed: {(run.stderr or run.stdout).strip()}")
            m = re.match(r"(\S+) decision ", run.stdout.strip())
            d["record"] = d.get("record") or (f"{m.group(1)} in {ini}'s decisions register" if m else f"{ini}'s decisions register")
        a["locked"] = True
        print(f"recorded {d.get('label') or d['id']}: {a['label']}" + (f" ({d['record']})" if d.get("record") else ""))
    data["recorded_at"] = now()
    save(args.brief, data)
    if open_:
        print(f"still open: {', '.join(open_)}")
    return 0


# ── note ─────────────────────────────────────────────────────────────────────

def note_md(data: dict, url: str = "", archive: str = "", brief_path: str = "") -> str:
    lines = [f"# {data.get('title', 'Decision brief')}: decisions", ""]
    when = data.get("recorded_at") or now()
    meta = [f"Decided {when[:10]}"]
    if data.get("for"):
        meta.append(f"by {data['for']}")
    if data.get("from"):
        meta.append(f"brief from {data['from']}")
    lines += [", ".join(meta) + ".", ""]
    links = []
    if url:
        links.append(f"- The brief: {url}")
    if archive:
        links.append(f"- Archived copy: [{archive}]({archive})")
    if brief_path:
        links.append(f"- Brief data (answers included): `{brief_path}`")
    for x in data.get("read") or []:
        links.append(f"- Research: " + (f"[{x['label']}]({x['href']})" if x.get("href") else x["label"]) + (f": {x['note']}" if x.get("note") else ""))
    if links:
        lines += ["## Links", ""] + links + [""]
    if data.get("recommendation"):
        rec = data["recommendation"]
        lines += ["## What was recommended", "", " ".join(rec) if isinstance(rec, list) else rec, ""]
    lines += ["## Decisions", ""]
    entries = []
    for d in data.get("decisions") or []:
        a = d.get("answer") or {}
        r = recommended(d) or {}
        lines.append(f"### {d.get('label') + ' · ' if d.get('label') else ''}{d['question']}")
        lines.append("")
        if a.get("pick"):
            took = "the recommendation" if a["pick"] == r.get("id") else f"not the recommendation ({r.get('label', '?')})"
            lines.append(f"**Decided:** {a['label']}, {took}." + (f" Note: {a['note']}" if a.get("note") else ""))
        else:
            lines.append("**Not decided yet.**")
        lines.append("")
        lines.append(f"**Why the recommendation:** {d.get('reason', '')}")
        lines.append("")
        lines.append("Options considered:")
        for o in d.get("options") or []:
            mark = " (picked)" if o.get("id") == a.get("pick") else ""
            lines.append(f"- {o['label']}{mark}: {o.get('consequence', '')}")
        if a.get("pick") == ELSE:
            lines.append(f"- Something else (picked): {a.get('note', '')}")
        if d.get("record"):
            lines += ["", f"Recorded as {d['record']}."]
        lines.append("")
        if a.get("pick"):
            who = f"**{d.get('d') or 'D-NN'} · {when[:10]} · {data.get('for') or 'Who'}.**"
            if a["pick"] == ELSE:
                entries.append(f"{who} {d['question']} {a.get('note', '')} *In their own words.*")
            else:
                why = a.get("note") or d.get("reason", "")
                entries.append(f"{who} {d['question']} {a['label']}. *{why}*")
    if entries:
        lines += ["## Log entries", "",
                  "Ready for a decisions log in the `**D-NN · date · Who.** The decision. *Why.*` form."
                  " Claim numbers the careful way before using them.", ""] + "\n\n".join(entries).split("\n") + [""]
    return "\n".join(lines)


def cmd_note(args) -> int:
    data = load(args.brief)
    out = Path(args.out) if args.out else Path(args.brief).with_suffix(".md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(note_md(data, args.url or data.get("url", ""), args.archive or "", args.brief), encoding="utf-8")
    print(f"wrote {out}")
    return 0


# ── new ──────────────────────────────────────────────────────────────────────

def cmd_new(args) -> int:
    p = Path(args.brief)
    if p.exists():
        raise BriefError(f"{p} exists; edit it instead")
    slug = re.sub(r"[^a-z0-9]+", "-", args.title.lower()).strip("-")[:48] or "brief"
    data = {
        "id": slug, "title": args.title, "for": args.for_ or "", "from": args.from_ or "",
        "date": _dt.date.today().strftime("%-d %B %Y") if sys.platform != "win32" else _dt.date.today().isoformat(),
        "why": "What this is about and why the person is seeing it, in two or three sentences.",
        "recommendation": "All the recommendations together, in one paragraph.",
        "read": [{"label": "What you read", "href": "", "note": ""}],
        "findings": [{"title": "One finding in a sentence.", "body": "What it means for the choices."}],
        "decisions": [],
        "after": ["What happens once the person decides."],
    }
    if args.initiative:
        data["initiative"] = args.initiative
    for i in range(1, args.decisions + 1):
        data["decisions"].append({
            "id": f"d{i}", "label": "", "question": "The question, as a sentence ending in a question mark?",
            "context": ["What the person needs to know to decide, in plain words."],
            "know": [], "stage": {"html": "", "caption": ""}, "depends_on": [],
            "options": [
                {"id": "a", "label": "Option A", "consequence": "What happens, and what it gives up.", "cost": "", "recommended": True},
                {"id": "b", "label": "Option B", "consequence": "What happens, and what it gives up.", "cost": ""},
            ],
            "reason": "Why you recommend A.",
        })
    p.parent.mkdir(parents=True, exist_ok=True)
    save(p, data)
    print(f"wrote {p}: fill in the content, then `brief.py check {p}`")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="brief.py", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("new", help="start a brief's JSON")
    p.add_argument("brief"); p.add_argument("--title", required=True)
    p.add_argument("--decisions", type=int, default=1); p.add_argument("--initiative")
    p.add_argument("--for", dest="for_"); p.add_argument("--from", dest="from_")
    p.set_defaults(run=cmd_new)
    p = sub.add_parser("check", help="check a brief against the rules")
    p.add_argument("brief"); p.set_defaults(run=cmd_check)
    p = sub.add_parser("render", help="draw the page")
    p.add_argument("brief"); p.add_argument("--out", help="default: the brief's path with .html")
    p.add_argument("--fragment", action="store_true", help="for publishing as a claude.ai Artifact")
    p.add_argument("--force", action="store_true", help="render a draft that fails check")
    p.set_defaults(run=cmd_render)
    p = sub.add_parser("answer", help="write down one answer the person gave")
    p.add_argument("brief"); p.add_argument("decision"); p.add_argument("pick")
    p.add_argument("--note"); p.add_argument("--at"); p.add_argument("--via", default="agent")
    p.set_defaults(run=cmd_answer)
    p = sub.add_parser("import", help="take answers from the page's text or a saved answers collection")
    p.add_argument("brief"); p.add_argument("--text"); p.add_argument("--db")
    p.set_defaults(run=cmd_import)
    p = sub.add_parser("record", help="lock the answers and write them to the initiative's register")
    p.add_argument("brief"); p.add_argument("--by", default="decision-brief")
    p.add_argument("--no-register", action="store_true")
    p.set_defaults(run=cmd_record)
    p = sub.add_parser("note", help="write the decision note (markdown)")
    p.add_argument("brief"); p.add_argument("--out", help="default: the brief's path with .md")
    p.add_argument("--url"); p.add_argument("--archive")
    p.set_defaults(run=cmd_note)
    args = ap.parse_args(argv)
    try:
        return args.run(args) or 0
    except BriefError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
