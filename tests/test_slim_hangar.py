"""omnigent-slim: the read-only Hangar catalog reads the real repo files."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi import HTTPException

from omnigent.server.routes import slim_hangar

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _repo_folders(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OMNIGENT_SLIM_WORKSPACE", str(REPO / "workspace"))
    monkeypatch.setenv("OMNIGENT_SLIM_LIBRARY_DIR", str(REPO / "workspace" / "templates"))
    monkeypatch.setenv("OMNIGENT_SLIM_SKILLS_DIR", str(REPO / "skills"))


def test_every_shelf_is_filled_and_healthy() -> None:
    hangar = slim_hangar.load_hangar()
    for shelf in (
        "people",
        "workflows",
        "views",
        "templates",
        "scenarios",
        "skills",
        "starters",
        "frameworks",
    ):
        assert hangar[shelf], shelf
    # The shipped things all pass their checks; a failure here is a real bug.
    for item in hangar["people"] + hangar["workflows"]:
        assert item["problems"] == [], (item["id"], item["problems"])


def test_used_in_links_go_both_ways() -> None:
    hangar = slim_hangar.load_hangar()
    people = {p["id"]: p for p in hangar["people"]}
    workflows = {w["id"]: w for w in hangar["workflows"]}
    review = workflows["document-review"]
    assert "mara-okafor" in review["participants"]
    assert "document-review" in people["mara-okafor"]["used_in"]["workflows"]
    assert "review-with-others" in review["starters"]
    assert "review-with-others" in people["risk-review"]["used_in"]["starters"]
    # Script steps tell where a view appears.
    hosts = {v["name"]: v["host"] for v in review["views"]}
    assert hosts["findings"] == "canvas" and hosts["who"] == "chat"
    framework = next(f for f in hangar["frameworks"] if f["id"] == "intent")
    assert framework["used_by"] == ["intent-shaping"]


def test_views_render_offline_from_sample_data() -> None:
    html = slim_hangar.render_view("document-review", "findings")
    assert 'id="pa-data"' in html and "F-08" in html
    assert "http://" not in html.replace("http://www.w3.org", "") and "https://" not in html
    assert "<title>" in slim_hangar.render_preview("decision-review")
    assert "<html" in slim_hangar.read_template("decision-matrix").lower()


@pytest.mark.parametrize(
    "call",
    [
        lambda: slim_hangar.render_view("../etc", "x"),
        lambda: slim_hangar.render_view("document-review", "nope"),
        lambda: slim_hangar.read_template("../../secrets"),
        lambda: slim_hangar.render_preview("not-a-workflow"),
    ],
)
def test_bad_names_are_404(call) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(HTTPException) as err:
        call()
    assert err.value.status_code == 404


def test_a_broken_person_shows_its_problem(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = tmp_path / "workspace"
    shutil.copytree(REPO / "workspace" / "participants", workspace / "participants")
    (workspace / "participants" / "no-role.md").write_text(
        "---\nname: No Role\nkind: person\nstand_in: false\n---\nA brief.\n", encoding="utf-8"
    )
    monkeypatch.setenv("OMNIGENT_SLIM_WORKSPACE", str(workspace))
    person = next(p for p in slim_hangar.load_hangar()["people"] if p["id"] == "no-role")
    assert any("stand_in" in problem for problem in person["problems"])
    assert any("role" in problem for problem in person["problems"])


def _scratch_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    workspace = tmp_path / "workspace"
    shutil.copytree(REPO / "workspace" / "participants", workspace / "participants")
    shutil.copytree(REPO / "workspace" / "templates", workspace / "templates")
    monkeypatch.setenv("OMNIGENT_SLIM_WORKSPACE", str(workspace))
    monkeypatch.setenv("OMNIGENT_SLIM_LIBRARY_DIR", str(workspace / "templates"))
    return workspace


def test_edit_publish_and_restore_a_person(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = _scratch_workspace(tmp_path, monkeypatch)
    pa = slim_hangar._pa()
    draft = slim_hangar.start_person_draft("mara-okafor")
    assert draft["action"] == "change"
    assert "nothing has changed yet" in draft["problems"]
    with pytest.raises(HTTPException) as err:
        slim_hangar.publish_person("mara-okafor", "")
    assert err.value.status_code == 409
    pa.edit_draft(workspace, "mara-okafor", {"role": "Design director, Cards"})
    # Live is untouched until publish.
    assert "Design lead" in (workspace / "participants" / "mara-okafor.md").read_text()
    hangar = slim_hangar.load_hangar()
    assert [d["id"] for d in hangar["drafts"]] == ["mara-okafor"]
    assert hangar["drafts"][0]["problems"] == []
    result = slim_hangar.publish_person("mara-okafor", "promoted")
    assert result["kept"]
    assert "Design director" in (workspace / "participants" / "mara-okafor.md").read_text()
    person = next(p for p in slim_hangar.load_hangar()["people"] if p["id"] == "mara-okafor")
    assert person["history"][0]["summary"] == "promoted"
    slim_hangar.restore_person("mara-okafor", result["kept"])
    assert "Design lead" in (workspace / "participants" / "mara-okafor.md").read_text()
    assert slim_hangar.load_hangar()["drafts"] == []


def test_removal_is_blocked_while_in_use(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workspace = _scratch_workspace(tmp_path, monkeypatch)
    draft = slim_hangar.start_person_draft("risk-review", remove=True)
    assert any("document-review" in p for p in draft["problems"])
    with pytest.raises(HTTPException):
        slim_hangar.publish_person("risk-review", "")
    assert (workspace / "participants" / "risk-review.md").is_file()
    slim_hangar.discard_person_draft("risk-review")
    assert slim_hangar.load_hangar()["drafts"] == []


def test_new_person_needs_every_required_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = _scratch_workspace(tmp_path, monkeypatch)
    pa = slim_hangar._pa()
    pid = pa.start_draft(workspace, name="Fraud Ops")
    assert pid == "fraud-ops"
    problems = slim_hangar.draft_detail(pid)["problems"]
    assert any("call for" in p for p in problems) and any("brief" in p for p in problems)
    pa.edit_draft(
        workspace,
        pid,
        {"role": "Fraud operations", "call_for": "chargebacks", "kind": "person"},
        "You are Fraud Ops.",
    )
    detail = slim_hangar.draft_detail(pid)
    assert detail["problems"] == [] and detail["person"]["stand_in"] is True
    slim_hangar.publish_person(pid, "new")
    assert (workspace / "participants" / "fraud-ops.md").is_file()
    with pytest.raises(pa.PaError):
        pa.start_draft(workspace, name="Fraud Ops")
