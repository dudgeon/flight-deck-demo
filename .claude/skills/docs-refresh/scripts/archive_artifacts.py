#!/usr/bin/env python3
"""Keep offline HTML copies of the decision artifacts in docs/decision-artifacts/.

Standard library only. The fetching (from claude.ai or the project files) is
done by the agent running the docs-refresh skill; this script only turns a
fetched folder into an archived copy, and rebuilds the index.

  add    copy a fetched artifact into the archive, made offline-safe
  index  rebuild README.md and index.html from artifacts.json
  check  confirm every entry is present, offline and complete

Run from the repository root:

  python3 .claude/skills/docs-refresh/scripts/archive_artifacts.py add \
      --id YQcb4HDRGMnn6YW82uFNZd --src /tmp/arts/YQcb4HDRGMnn6YW82uFNZd \
      --answers /tmp/db/YQcb4HDRGMnn6YW82uFNZd/answers
  python3 .claude/skills/docs-refresh/scripts/archive_artifacts.py index
  python3 .claude/skills/docs-refresh/scripts/archive_artifacts.py check

`add` reads the entry's metadata (title, date, slug, ...) from artifacts.json,
so add or update the entry there first.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
ARCHIVE = ROOT / "docs" / "decision-artifacts"
MANIFEST = ARCHIVE / "artifacts.json"

# Anything a page would fetch from the network. Links a reader clicks (<a href>)
# are fine; things the page loads by itself are not.
LOADS_REMOTE = re.compile(
    r"""<(?:link|script|img|iframe|source)\b[^>]*?(?:href|src)\s*=\s*["']?(?:https?:)?//""",
    re.I,
)
REMOTE_CSS = re.compile(r"""@import\s+url\(\s*["']?(?:https?:)?//|url\(\s*["']?https?://""", re.I)
FONT_LINK = re.compile(
    r"""<link\b[^>]*?href\s*=\s*["'](?:https?:)?//fonts\.(?:googleapis|gstatic)\.com[^>]*>\s*""",
    re.I,
)
MARK = "<!-- decision-archive:start -->"
MARK_END = "<!-- decision-archive:end -->"


def load_manifest() -> list[dict]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))["artifacts"]


def entry_for(artifact_id: str) -> dict:
    for e in load_manifest():
        if e["id"] == artifact_id:
            return e
    sys.exit(f"{artifact_id} is not in {MANIFEST.relative_to(ROOT)}; add its entry first.")


def read_answers(folder: Path | None) -> dict:
    """Read the artifact's `answers` collection (one JSON file per document)."""
    if not folder or not folder.exists():
        return {}
    out = {}
    for f in sorted(folder.glob("*.json")):
        out[f.stem] = json.loads(f.read_text(encoding="utf-8"))
    return out


def banner_and_stub(e: dict, answers: dict) -> str:
    """A note at the top of the page, and a stand-in for the artifact's
    database so the page shows the recorded answers and saves nothing.
    System colors only, so it reads in light and dark without literal colors."""
    note = (
        f"Archived copy of <b>{html.escape(e['title'])}</b>, a decision artifact from "
        f"{html.escape(e['date'])}. "
        + (
            f"It shows the answers recorded on {html.escape(e.get('answers_as_of', e['date']))}; "
            "changes made here are not saved. "
            if answers
            else "Nothing on this page is saved. "
        )
        + 'The index of all of them is in <a href="../index.html">docs/decision-artifacts</a>.'
    )
    data = json.dumps(answers, ensure_ascii=False).replace("</", "<\\/")
    return f"""{MARK}
<div style="font:13px/1.45 system-ui,sans-serif;background:Canvas;color:CanvasText;border-bottom:1px solid GrayText;padding:8px 16px">{note}</div>
<script>
(function(){{
  var A={data};
  function snap(){{var docs=Object.keys(A).map(function(k){{return {{id:k,data:function(){{return A[k]}},exists:true}}}});return {{docs:docs,empty:!docs.length,size:docs.length,forEach:function(f){{docs.forEach(f)}}}}}}
  function doc(id){{return {{id:id,get:async function(){{return {{id:id,exists:id in A,data:function(){{return A[id]}}}}}},set:async function(){{}},update:async function(){{}},delete:async function(){{}}}}}}
  var db={{collection:function(){{return {{get:async function(){{return snap()}},doc:doc,onSnapshot:function(f){{setTimeout(function(){{f(snap())}},0);return function(){{}}}},add:async function(){{}}}}}},doc:function(p){{return doc(String(p).split("/").pop())}}}};
  window.claude={{use:async function(name){{return name==="db"?db:null}}}};
}})();
</script>
{MARK_END}
"""


def make_offline(text: str) -> str:
    text = FONT_LINK.sub("", text)
    text = re.sub(r"""<link\b[^>]*rel\s*=\s*["']?preconnect[^>]*>\s*""", "", text, flags=re.I)
    return text


def relink(text: str) -> str:
    """Point links to other archived artifacts at their copies here, so the
    record reads without a claude.ai account. Unarchived ones stay as they are."""
    local = {e["id"]: e["slug"] for e in load_manifest() if e.get("archived", True)}

    def swap(m: re.Match) -> str:
        slug = local.get(m.group(2))
        return f"{m.group(1)}../{slug}/index.html" if slug else m.group(0)

    return re.sub(r"""(href\s*=\s*["'])https://claude\.ai/artifact/([A-Za-z0-9]+)""", swap, text)


def inject(text: str, block: str) -> str:
    text = re.sub(re.escape(MARK) + r".*?" + re.escape(MARK_END) + r"\n?", "", text, flags=re.S)
    m = re.search(r"<body[^>]*>", text, re.I)
    if m:
        return text[: m.end()] + "\n" + block + text[m.end():]
    return block + text


def cmd_add(args) -> None:
    e = entry_for(args.id)
    src = Path(args.src)
    if not (src / "index.html").exists():
        sys.exit(f"{src}/index.html not found")
    dest = ARCHIVE / e["slug"]
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("*.map", ".DS_Store"))
    answers = read_answers(Path(args.answers) if args.answers else None)
    if answers:
        (dest / "answers.json").write_text(
            json.dumps(answers, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    for page in dest.rglob("*.html"):
        t = relink(make_offline(page.read_text(encoding="utf-8")))
        if page == dest / "index.html":
            t = inject(t, banner_and_stub(e, answers))
        page.write_text(t, encoding="utf-8")
    print(f"archived {e['title']} -> {dest.relative_to(ROOT)} ({len(answers)} answers)")


def problems() -> list[str]:
    out = []
    entries = load_manifest()
    slugs = set()
    for e in entries:
        slug = e["slug"]
        if slug in slugs:
            out.append(f"{slug}: slug used twice")
        slugs.add(slug)
        if e.get("archived") is False:
            continue
        d = ARCHIVE / slug
        page = d / "index.html"
        if not page.exists():
            out.append(f"{slug}: index.html missing")
            continue
        for p in d.rglob("*"):
            if p.suffix.lower() not in (".html", ".css", ".js"):
                continue
            t = p.read_text(encoding="utf-8", errors="replace")
            if LOADS_REMOTE.search(t) or REMOTE_CSS.search(t):
                out.append(f"{p.relative_to(ROOT)}: loads something from the network")
        t = page.read_text(encoding="utf-8", errors="replace")
        if MARK not in t:
            out.append(f"{slug}: archive note missing (run add again)")
        for ref in re.findall(r"""(?:src|href)\s*=\s*["']([^"'#?$]+)["']""", t):
            if re.match(r"^(?:[a-z]+:|//|\.\./index\.html$)", ref, re.I) or "${" in ref:
                continue
            if not (d / ref).exists():
                out.append(f"{slug}: {ref} is referenced but missing")
    return out


def cmd_check(_args) -> None:
    found = problems()
    for p in found:
        print("✗", p)
    if found:
        sys.exit(1)
    print(f"✓ {len(load_manifest())} entries, all offline and complete")


def cmd_index(_args) -> None:
    entries = sorted(load_manifest(), key=lambda e: (e["date"], e.get("order", 0)))
    rows = []
    for e in entries:
        where = f"[{e['slug']}]({e['slug']}/index.html)" if e.get("archived", True) else "not archived (see note)"
        rows.append(
            "| {date} | {title} | {kind} | {about} | {led} | {status} | {where} |".format(
                date=e["date"], title=e["title"], kind=e["kind"], about=e["about"],
                led=e.get("decisions", ""), status=e["status"], where=where,
            )
        )
    notes = [f"- **{e['title']}**: {e['note']}" for e in entries if e.get("note")]
    readme = f"""# Decision artifacts

Offline copies of the pages used to put decisions to Geoff: walkthroughs,
design rounds and proposals. They are kept here as the historic record behind
[../product/decisions.md](../product/decisions.md) and as worked examples of
how a decision is asked (D-32, D-33, D-105), so anyone can see them without a
claude.ai account.

**To view one,** download or clone the repository and open the folder's
`index.html` in a browser, or open [index.html](index.html) for the list.
Nothing loads from the network. Where Geoff answered on the page, the copy
shows his recorded answers (they are also in that folder's `answers.json`);
changing them in the copy saves nothing.

The decision log is the authority on what was decided. The "Led to" column is
a pointer, not a complete list. This folder is kept by the `docs-refresh`
skill (`.claude/skills/docs-refresh/`); add new artifacts with it rather than
by hand. Generated from `artifacts.json`; do not edit this table directly.

| Date | Title | Kind | What it asked | Led to | Status | Copy |
|---|---|---|---|---|---|---|
{chr(10).join(rows)}
"""
    if notes:
        readme += "\n## Notes\n\n" + "\n".join(notes) + "\n"
    (ARCHIVE / "README.md").write_text(readme, encoding="utf-8")

    items = []
    for e in entries:
        link = (
            f'<a href="{html.escape(e["slug"])}/index.html">{html.escape(e["title"])}</a>'
            if e.get("archived", True)
            else html.escape(e["title"]) + " <i>(not archived)</i>"
        )
        items.append(
            f"<tr><td>{html.escape(e['date'])}</td><td>{link}</td><td>{html.escape(e['about'])}</td>"
            f"<td>{html.escape(e.get('decisions', ''))}</td><td>{html.escape(e['status'])}</td></tr>"
        )
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Decision artifacts</title>
<style>
:root{{color-scheme:light dark}}
body{{margin:0;padding:24px 16px 48px;background:Canvas;color:CanvasText;font:15px/1.5 system-ui,-apple-system,sans-serif}}
main{{max-width:1100px;margin:0 auto}}
h1{{font-size:26px;margin:0 0 6px}}p{{max-width:72ch}}
.tw{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;font-size:14px}}
td,th{{border:1px solid GrayText;padding:6px 9px;text-align:left;vertical-align:top}}td:first-child{{white-space:nowrap}}
</style></head><body><main>
<h1>Decision artifacts</h1>
<p>Offline copies of the walkthroughs, design rounds and proposals used to put decisions to Geoff,
oldest first. Pages that recorded answers show them as they were saved. What was decided is in
<code>docs/product/decisions.md</code>; this is the record of how it was asked.</p>
<div class="tw"><table><tr><th>Date</th><th>Artifact</th><th>What it asked</th><th>Led to</th><th>Status</th></tr>
{chr(10).join(items)}
</table></div></main></body></html>
"""
    (ARCHIVE / "index.html").write_text(page, encoding="utf-8")
    print(f"index rebuilt: {len(entries)} entries")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add", help="archive one fetched artifact")
    a.add_argument("--id", required=True, help="artifact id (the end of its claude.ai URL)")
    a.add_argument("--src", required=True, help="folder holding the fetched index.html and its files")
    a.add_argument("--answers", help="folder of the `answers` collection, one JSON file per document")
    a.set_defaults(fn=cmd_add)
    sub.add_parser("index", help="rebuild README.md and index.html").set_defaults(fn=cmd_index)
    sub.add_parser("check", help="verify the archive").set_defaults(fn=cmd_check)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
