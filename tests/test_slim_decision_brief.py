"""Decision briefs: one JSON file, one fixed template (D-159)."""

from __future__ import annotations

import copy
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "decision-brief"
EXAMPLE = SKILL / "examples" / "decision-briefs.json"
sys.path.insert(0, str(ROOT / "skills" / "view-kit" / "scripts"))

import pa  # noqa: E402


def _load_brief():
    spec = importlib.util.spec_from_file_location("brief", SKILL / "scripts" / "brief.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["brief"] = module
    spec.loader.exec_module(module)
    return module


brief = _load_brief()


@pytest.fixture
def sample(tmp_path: Path) -> Path:
    path = tmp_path / "briefs" / "sample.json"
    path.parent.mkdir()
    path.write_text(EXAMPLE.read_text())
    return path


def _errors(data: dict) -> list[str]:
    return brief.problems(data, SKILL / "examples")[0]


def test_the_shipped_example_passes_check() -> None:
    err, _ = brief.problems(json.loads(EXAMPLE.read_text()), EXAMPLE.parent)
    assert err == []


def test_check_refuses_a_blind_or_unrecommended_decision() -> None:
    data = json.loads(EXAMPLE.read_text())
    d = data["decisions"][0]
    blind = copy.deepcopy(data)
    blind["decisions"][0]["context"] = []
    assert any("never ask blind" in e for e in _errors(blind))
    two = copy.deepcopy(data)
    for o in two["decisions"][0]["options"]:
        o["recommended"] = True
    assert any("exactly one option recommended" in e for e in _errors(two))
    one = copy.deepcopy(data)
    one["decisions"][0]["options"] = d["options"][:1]
    assert any("two real options" in e for e in _errors(one))


def test_check_refuses_a_written_something_else_option() -> None:
    data = json.loads(EXAMPLE.read_text())
    data["decisions"][0]["options"].append({"id": "x", "label": "Something else", "consequence": "..."})
    assert any("Something else" in e for e in _errors(data))


@pytest.mark.parametrize("html", [
    '<div style="color:#ff0000">x</div>',
    "<style>.x{}</style>",
    '<img src="https://example.com/a.png">',
    "<script>alert(1)</script>",
])
def test_check_refuses_visuals_that_break_tokens_or_offline(html: str) -> None:
    data = json.loads(EXAMPLE.read_text())
    data["decisions"][0]["stage"] = {"html": html}
    assert _errors(data)


def test_render_inlines_everything_and_carries_the_tokens(sample: Path, tmp_path: Path) -> None:
    out = tmp_path / "page.html"
    assert brief.main(["render", str(sample), "--out", str(out)]) == 0
    html = out.read_text()
    assert html.startswith("<!doctype html>")
    assert "<title>How decision briefs should work</title>" in html
    assert "--pa-navy:" in html and 'prefers-color-scheme: dark' in html
    assert not re.search(r"""(?:src|href)=["'](?:https?:)?//""", html), "nothing may load from the network"
    data = json.loads(re.search(r'<script type="application/json" id="brief-data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))
    assert data["id"] == "decision-briefs" and len(data["decisions"]) == 4


def test_render_fragment_is_for_claude_ai(sample: Path, tmp_path: Path) -> None:
    out = tmp_path / "page.html"
    assert brief.main(["render", str(sample), "--out", str(out), "--fragment"]) == 0
    html = out.read_text()
    assert html.startswith("<title>") and "<body" not in html and "<html" not in html


def test_render_inlines_a_local_image(sample: Path, tmp_path: Path) -> None:
    (sample.parent / "shot.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")
    data = json.loads(sample.read_text())
    data["decisions"][0]["stage"] = {"image": "shot.png", "caption": "Now"}
    sample.write_text(json.dumps(data))
    out = tmp_path / "page.html"
    assert brief.main(["render", str(sample), "--out", str(out)]) == 0
    assert "data:image/png;base64," in out.read_text()


def test_template_tokens_are_current() -> None:
    import subprocess
    run = subprocess.run([sys.executable, str(ROOT / "design" / "build_tokens.py"), "--check"], capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr


def test_answers_round_trip_from_the_pages_text(sample: Path, tmp_path: Path) -> None:
    text = (
        "Decision brief answers: How decision briefs should work (decision-briefs)\n"
        "- layout | stepper | One decision at a time\n"
        "- trigger | else | Something else | note: Only for visual choices | and dates\n"
    )
    t = tmp_path / "sent.txt"
    t.write_text(text)
    assert brief.main(["import", str(sample), "--text", str(t)]) == 0
    data = json.loads(sample.read_text())
    d = {x["id"]: x for x in data["decisions"]}
    assert d["layout"]["answer"]["pick"] == "stepper"
    assert d["trigger"]["answer"] == {**d["trigger"]["answer"], "pick": "else", "label": "Something else", "note": "Only for visual choices | and dates"}
    assert "answer" not in d["answers"]


def test_answers_import_from_what_flight_decks_send_button_sends(sample: Path, tmp_path: Path) -> None:
    # The app writes this message itself (web/src/lib/artifactBridge.ts, briefAnswersText).
    text = (
        "Decision brief answers for briefs/sample.json, sent from the brief by the person "
        "(notes are their own words, quoted):\n"
        "- layout | page\n"
        '- trigger | else | note: "Use judgment, \\"mostly\\" visual | ones"\n'
    )
    t = tmp_path / "sent.txt"
    t.write_text(text)
    assert brief.main(["import", str(sample), "--text", str(t)]) == 0
    d = {x["id"]: x for x in json.loads(sample.read_text())["decisions"]}
    assert d["layout"]["answer"]["pick"] == "page" and d["layout"]["answer"]["note"] == ""
    assert d["trigger"]["answer"]["note"] == 'Use judgment, "mostly" visual | ones'


def test_render_names_the_brief_file_for_the_send_button(sample: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(sample.parent.parent)
    assert brief.main(["render", "briefs/sample.json"]) == 0
    html = (sample.parent / "sample.html").read_text()
    assert '"source": "briefs/sample.json"' in html


def test_answers_import_from_a_saved_answers_collection(sample: Path, tmp_path: Path) -> None:
    folder = tmp_path / "answers"
    folder.mkdir()
    (folder / "record.json").write_text(json.dumps({"pick": "note-only", "note": "", "at": "2026-11-22T04:00:00Z"}))
    (folder / "answers.json").write_text(json.dumps({"data": {"choice": "direct", "text": "later"}}))
    assert brief.main(["import", str(sample), "--db", str(folder)]) == 0
    d = {x["id"]: x for x in json.loads(sample.read_text())["decisions"]}
    assert d["record"]["answer"]["pick"] == "note-only"
    assert d["answers"]["answer"]["pick"] == "direct" and d["answers"]["answer"]["note"] == "later"


def test_something_else_needs_the_persons_words(sample: Path) -> None:
    assert brief.main(["answer", str(sample), "layout", "else"]) == 1
    assert brief.main(["answer", str(sample), "layout", "nope"]) == 1
    assert brief.main(["answer", str(sample), "layout", "else", "--note", "A deck"]) == 0


def test_record_locks_answers_and_writes_the_register(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    pa.main(["project", "Checkout", "--goal", "Pay in one step", "--area", "Payments"])
    path = tmp_path / "briefs" / "b.json"
    path.parent.mkdir()
    data = json.loads(EXAMPLE.read_text())
    data["initiative"] = "checkout"
    path.write_text(json.dumps(data))
    assert brief.main(["answer", str(path), "layout", "page"]) == 0
    assert brief.main(["record", str(path)]) == 0
    d = {x["id"]: x for x in json.loads(path.read_text())["decisions"]}
    assert d["layout"]["answer"]["locked"] is True
    assert "D-01" in d["layout"]["record"]
    regs = json.loads((tmp_path / "projects" / "checkout" / "registers.json").read_text())
    dec = [r for r in regs["records"] if r["type"] == "decision"]
    assert len(dec) == 1 and "One page, briefing beside your call" in dec[0]["title"]
    # A recorded answer is never changed; a later choice is a new brief.
    assert brief.main(["answer", str(path), "layout", "stepper"]) == 1


def test_note_links_research_page_and_archive(sample: Path, tmp_path: Path) -> None:
    brief.main(["answer", str(sample), "answers", "direct", "--note", "Fewer presses"])
    out = tmp_path / "note.md"
    assert brief.main(["note", str(sample), "--out", str(out), "--url", "https://claude.ai/artifact/x",
                       "--archive", "docs/decision-artifacts/2026-11-22-decision-briefs/index.html"]) == 0
    note = out.read_text()
    assert "https://claude.ai/artifact/x" in note and "decision-artifacts/2026-11-22-decision-briefs" in note
    assert "Lifecycle walkthrough" in note
    assert "**Decided:** Straight to the agent, one press, not the recommendation" in note
    assert "Not decided yet." in note
    assert "**D-NN · " in note and "*Fewer presses*" in note


def test_new_starts_a_brief_that_check_sends_back_to_be_filled(tmp_path: Path) -> None:
    path = tmp_path / "b.json"
    assert brief.main(["new", str(path), "--title", "Checkout scope", "--decisions", "2"]) == 0
    data = json.loads(path.read_text())
    assert data["id"] == "checkout-scope" and len(data["decisions"]) == 2
    assert brief.main(["new", str(path), "--title", "Again"]) == 1


def test_routing_points_every_complex_decision_at_the_skill() -> None:
    for path in ("workspace/CLAUDE.md", "skills/director/SKILL.md", "skills/decision-review/SKILL.md",
                 "docs/skill-writers/README.md", "AGENTS.md"):
        assert "decision-brief" in (ROOT / path).read_text(), path
