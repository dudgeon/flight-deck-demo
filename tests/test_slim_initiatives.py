"""Initiatives, artifact stamps, templates and registers (D-138 to D-142)."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "view-kit" / "scripts"))

import pa  # noqa: E402

NAME = "Held payment dates"


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    for folder in ("data", "artifacts", "context"):
        (tmp_path / folder).mkdir()
    (tmp_path / "data" / "reqs.json").write_text(json.dumps({"records": [
        {"id": "R-01", "type": "requirement", "title": "Show the release date"}]}))
    (tmp_path / "context" / "prd.md").write_text("# The PRD\n\nWords.\n")
    pa.main(["project", NAME, "--goal", "Customers know when held money arrives", "--area", "Held payments"])
    return tmp_path


def _card(ws: Path) -> dict:
    return json.loads((ws / "projects" / "held-payment-dates.json").read_text())


def test_an_initiative_gets_a_stable_id_and_key_that_survive_edits(workspace: Path) -> None:
    card = _card(workspace)
    assert re.fullmatch(r"ini_[0-9a-f]{32}", card["id"])
    assert card["key"] == "held-payment-dates"
    pa.main(["project", NAME, "--state", "in-delivery"])
    again = _card(workspace)
    assert (again["id"], again["key"], again["state"]) == (card["id"], card["key"], "in-delivery")


def test_an_old_card_without_an_id_gets_one_when_used(workspace: Path) -> None:
    path = workspace / "projects" / "old.json"
    path.write_text(json.dumps({"name": "Old one", "goal": "g"}))
    _, card = pa._initiative_or_fail("old one")
    assert card["id"].startswith("ini_") and json.loads(path.read_text())["id"] == card["id"]


def test_an_initiative_is_found_by_id_key_or_name(workspace: Path) -> None:
    card = _card(workspace)
    for ref in (card["id"], "held-payment-dates", "held PAYMENT dates"):
        assert pa.find_initiative(ref)[1]["id"] == card["id"]
    assert pa.find_initiative("nothing like it") is None


def test_a_dataset_given_to_a_project_carries_its_stamp(workspace: Path) -> None:
    pa.main(["project", NAME, "--data", "data/reqs.json"])
    data = json.loads((workspace / "data" / "reqs.json").read_text())
    assert data["project"] == NAME
    assert data["artifact"]["initiative"] == _card(workspace)["id"]
    assert data["artifact"]["id"].startswith("art_")


def test_stamps_round_trip_in_markdown_json_and_html(workspace: Path) -> None:
    md = workspace / "artifacts" / "brief.md"
    md.write_text("---\ndepth: 3\n---\n# Brief\n")
    page = workspace / "artifacts" / "page.html"
    page.write_text("<!doctype html><html><head><title>p</title></head><body>x</body></html>")
    ids = {}
    for path in (md, workspace / "data" / "reqs.json", page):
        stamp = pa.stamp_file(path, initiative=NAME, stages=["shape", "specify"], by="intent-shaping")
        ids[path.name] = stamp["id"]
        again = pa.read_stamp(path)
        assert again["id"] == stamp["id"] and again["stage"] == ["shape", "specify"]
    assert "depth: 3" in md.read_text() and md.read_text().endswith("# Brief\n")
    assert "<body>x</body>" in page.read_text()
    # Restamping keeps the id.
    assert pa.stamp_file(md, status="final")["id"] == ids["brief.md"]


def test_a_drawn_view_counts_as_a_rendition_of_its_dataset(workspace: Path) -> None:
    pa.main(["project", NAME, "--data", "data/reqs.json"])
    spec = ROOT / "skills" / "prd-to-requirements" / "views" / "catalog.json"
    pa.main(["render", str(spec), "--data", "data/reqs.json", "--out", "artifacts/reqs.html"])
    reg = pa.artifact_registry()
    reqs = next(a for a in reg["artifacts"] if a["path"] == "data/reqs.json")
    assert reqs["renditions"] == ["artifacts/reqs.html"]
    assert not any(a["path"] == "artifacts/reqs.html" for a in reg["artifacts"])


def test_the_persons_context_files_are_listed_not_written_into(workspace: Path) -> None:
    before = (workspace / "context" / "prd.md").read_text()
    pa.main(["stamp", "context/prd.md", "--initiative", NAME, "--stage", "specify"])
    assert (workspace / "context" / "prd.md").read_text() == before
    refs = _card(workspace)["refs"]
    assert refs[0]["path"] == "context/prd.md" and refs[0]["stage"] == ["specify"]
    listed = [a for a in pa.artifact_registry()["artifacts"] if a.get("listed")]
    assert listed[0]["initiative"] == _card(workspace)["id"]


def test_a_copied_file_with_the_same_id_is_reported(workspace: Path) -> None:
    md = workspace / "artifacts" / "a.md"
    md.write_text("# A\n")
    pa.stamp_file(md, initiative=NAME)
    (workspace / "artifacts" / "b.md").write_text(md.read_text())
    assert "a copy kept its stamp" in pa.artifact_registry()["problems"][0]


def test_loose_artifacts_are_allowed_and_adopted_later(workspace: Path) -> None:
    md = workspace / "artifacts" / "loose.md"
    md.write_text("# Loose\n")
    stamp = pa.stamp_file(md, stages=["discover"])
    assert "initiative" not in stamp
    pa.stamp_file(md, initiative=NAME)
    assert pa.read_stamp(md)["initiative"] == _card(workspace)["id"]


def test_an_unknown_stage_is_refused(workspace: Path) -> None:
    md = workspace / "artifacts" / "x.md"
    md.write_text("# X\n")
    with pytest.raises(pa.PaError, match="not a lifecycle stage"):
        pa.stamp_file(md, stages=["sometime"])


def test_the_shipped_templates_pass_their_checks() -> None:
    templates = pa.list_templates(ROOT / "workspace")
    assert {"initiative-intent", "initiative-registers", "prd-one-pager"} <= set(templates)
    assert templates["prd-one-pager"]["kind"] == "page"
    for t in templates.values():
        assert pa.template_problems(t) == [], t["template"]


def test_a_template_with_a_missing_heading_or_a_web_link_fails(tmp_path: Path) -> None:
    folder = tmp_path / "bad"
    folder.mkdir()
    (folder / "template.md").write_text('# T\n\n## Goal\n\n<img src="https://example.com/x.png">\n')
    t = {"template": "bad", "folder": str(folder), "kind": "markdown", "title": "t", "summary": "s", "out": "x.md",
         "file": "template.md", "stage": ["any"],
         "sections": [{"id": "goal", "heading": "Goal"}, {"id": "scope", "heading": "Scope"}]}
    problems = pa.template_problems(t)
    assert any("no heading 'Scope'" in p for p in problems)
    assert any("from the web" in p for p in problems)


def test_new_from_a_markdown_template_lands_in_the_initiative_folder(workspace: Path) -> None:
    path, stamp = pa.new_from_template("initiative-intent", initiative=NAME)
    assert path == Path("projects/held-payment-dates/intent.md")
    text = path.read_text()
    assert text.count("\n---\n") == 1 and "# Held payment dates" in text and "## Scope" in text
    assert stamp["template"] == "initiative-intent@1" and stamp["status"] == "draft"
    with pytest.raises(pa.PaError, match="already exists"):
        pa.new_from_template("initiative-intent", initiative=NAME)


def test_a_template_that_lives_in_an_initiative_needs_one(workspace: Path) -> None:
    with pytest.raises(pa.PaError, match="give --initiative"):
        pa.new_from_template("initiative-intent")


def test_registers_keep_evidence_attached_and_decisions_immutable(workspace: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert pa.main(["register", NAME, "evidence", "41% go inactive"]) != 0
    assert "needs --source" in capsys.readouterr().err
    pa.main(["register", NAME, "evidence", "41% go inactive", "--source", "context/prd.md"])
    pa.main(["register", NAME, "question", "Can every hold carry a date?", "--blocking", "--owner", "risk-review"])
    pa.main(["register", NAME, "decision", "Date only after the hold"])
    path = workspace / "projects" / "held-payment-dates" / "registers.json"
    assert pa.main(["set", str(path), "D-01", "title=Something else"]) != 0
    assert "is a decision" in capsys.readouterr().err
    pa.main(["register", NAME, "decision", "Date and reason", "--supersedes", "D-01"])
    records = {r["id"]: r for r in json.loads(path.read_text())["records"]}
    assert records["E-01"]["source"] == "context/prd.md"
    assert records["Q-01"]["blocking"] is True and records["Q-01"]["status"] == "open"
    assert records["D-01"]["status"] == "superseded" and records["D-01"]["superseded_by"] == "D-02"
    assert records["D-02"]["supersedes"] == "D-01"
    assert pa.read_stamp(path)["template"] == "initiative-registers@1"
    # Answering a question is an ordinary edit.
    assert pa.main(["set", str(path), "Q-01", "status=answered"]) == 0


def test_artifacts_lists_by_initiative_and_stage(workspace: Path, capsys: pytest.CaptureFixture[str]) -> None:
    pa.main(["project", NAME, "--data", "data/reqs.json"])
    md = workspace / "artifacts" / "brief.md"
    md.write_text("# B\n")
    pa.stamp_file(md, initiative=NAME, stages=["shape"])
    capsys.readouterr()
    pa.main(["artifacts", "--initiative", "held-payment-dates", "--stage", "shape", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert [a["path"] for a in out["artifacts"]] == ["artifacts/brief.md"]
