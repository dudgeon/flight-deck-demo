"""Workflow routing (D-120, D-122) and the director's memory (D-128)."""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "view-kit" / "scripts"))

import pa  # noqa: E402

from omnigent.server.routes.slim_director import create_slim_director_router, read_notes  # noqa: E402

SHIPPED = ["decision-review", "delivery-status", "document-review", "intent-shaping",
           "prd-to-requirements", "problem-discovery", "requirements-to-dependencies"]


# ------------------------------------------------------------------ routing

def test_every_shipped_workflow_is_routable_and_checks_clean() -> None:
    stages = [s["id"] for s in pa.lifecycle_stages(ROOT / "workspace")]
    assert stages == ["discover", "shape", "specify", "map", "decide", "deliver"]
    for wid in SHIPPED:
        manifest = json.loads((ROOT / "skills" / wid / "workflow.json").read_text())
        assert pa.routing_problems(manifest, wid, stages, required=True) == [], wid
        assert manifest["routing"]["stage"] in stages


def test_the_catalog_lists_workflows_in_lifecycle_order() -> None:
    catalog = pa.workflow_catalog(ROOT / "workspace")
    ids = [w["id"] for w in catalog]
    assert set(SHIPPED) <= set(ids)
    order = [w["routing"]["stage"] for w in catalog if w["routing"]]
    stages = [s["id"] for s in pa.lifecycle_stages(ROOT / "workspace")]
    assert order == sorted(order, key=stages.index)


def test_the_director_skill_names_no_workflow() -> None:
    # D-120: adding a workflow never means editing Aviator.
    text = (ROOT / "skills" / "director" / "SKILL.md").read_text() + (ROOT / "skills" / "director" / "charter.md").read_text()
    for wid in SHIPPED:
        assert wid not in text, wid
        title = json.loads((ROOT / "skills" / wid / "workflow.json").read_text())["title"]
        assert title not in text, title


def test_routing_problems_catch_what_would_make_a_workflow_unroutable() -> None:
    stages = ["discover", "shape"]
    assert "missing routing" in pa.routing_problems({}, "w.json", stages, required=True)[0]
    assert pa.routing_problems({}, "w.json", stages, required=False) == []
    bad = {"routing": {"when": [], "stage": "launch", "examples": {"maybe": ["x"]},
                       "persona": {"strictness": "strict"}}}
    problems = " | ".join(pa.routing_problems(bad, "w.json", stages, required=False))
    for words in ("when must list", "not a lifecycle stage", "examples needs prompts", "strictness must be one of"):
        assert words in problems


def test_check_fails_a_shipped_workflow_without_routing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # A copy in the workspace is a Hangar workflow: routing optional, but checked when present.
    folder = tmp_path / "skills" / "intent-shaping"
    shutil.copytree(ROOT / "skills" / "intent-shaping", folder)
    manifest = json.loads((folder / "workflow.json").read_text())
    manifest["routing"]["stage"] = "nowhere"
    (folder / "workflow.json").write_text(json.dumps(manifest))
    run = {"workflow": manifest, "workflow_dir": folder, "workflow_file": folder / "workflow.json", "scenario": None, "scenario_dir": None}
    assert any("not a lifecycle stage" in p for p in pa._workflow_problems(run))
    del manifest["routing"]
    assert not any("routing" in p for p in pa._workflow_problems(run))
    monkeypatch.setattr(pa, "_routing_required", lambda workflow, wdir: True)
    assert any("missing routing" in p for p in pa._workflow_problems(run))


def test_pa_workflows_prints_and_emits_json(capsys: pytest.CaptureFixture[str]) -> None:
    pa.main(["workflows", "--workspace", str(ROOT / "workspace")])
    out = capsys.readouterr().out
    assert "## Shape" in out and "Offer:" in out and "## Strictness levels" in out
    pa.main(["workflows", "--workspace", str(ROOT / "workspace"), "--json", "--stage", "shape"])
    data = json.loads(capsys.readouterr().out)
    assert [w["id"] for w in data["workflows"]] == ["intent-shaping"]
    assert set(data["strictness"]) == {"light", "guide", "by-the-book"}
    assert data["workflows"][0]["routing"]["examples"]["offer"]


# ------------------------------------------------------------------ memory

def test_recap_makes_the_files_and_prints_charter_state_memory_and_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    pa.main(["remember", "Geoff wants status in one line"])
    pa.main(["remember", "Geoff wants status in one line"])  # once is enough
    capsys.readouterr()
    pa.main(["recap"])
    out = capsys.readouterr().out
    assert "Director's charter" in out
    assert "Where the project stands" in out
    assert out.count("Geoff wants status in one line") == 1
    assert "no runs in flight" in out
    memory = (tmp_path / "director" / "memory.md").read_text()
    assert memory.count("- ") == 1 and "\n\n- " in memory


def test_the_charter_stays_short() -> None:
    # It is re-read after every compaction; the skill too must stay well under 5,000 tokens.
    assert len((ROOT / "skills" / "director" / "charter.md").read_text().split()) < 400
    assert len((ROOT / "skills" / "director" / "SKILL.md").read_text().split()) < 2500


def test_workspace_instructions_point_a_director_at_recap() -> None:
    assert "pa recap" in (ROOT / "workspace" / "CLAUDE.md").read_text()


def test_director_files_are_not_committed() -> None:
    assert "workspace/director/" in (ROOT / ".gitignore").read_text().splitlines()


# ------------------------------------------------------------------ notes route

def _client(workspace: Path) -> TestClient:
    projects = SimpleNamespace(list=lambda user_id=None: [
        SimpleNamespace(id="p1", name="Workspace", config={"workspace": str(workspace)})
    ])
    app = FastAPI()
    app.include_router(create_slim_director_router(project_store=projects), prefix="/v1")  # type: ignore[arg-type]
    return TestClient(app)


def test_notes_are_hidden_until_a_director_writes_them(tmp_path: Path) -> None:
    body = _client(tmp_path).get("/v1/slim/director/notes?project=Workspace").json()
    assert body["exists"] is False and body["state"]["updated"] is None
    assert read_notes(None)["exists"] is False


def test_the_person_edits_a_note_and_a_stale_edit_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    pa.main(["remember", "First fact"])
    client = _client(tmp_path)
    notes = client.get("/v1/slim/director/notes?project=Workspace").json()
    assert notes["exists"] and "First fact" in notes["memory"]["text"]
    base = notes["memory"]["updated"]
    saved = client.put("/v1/slim/director/notes", json={"project": "Workspace", "note": "memory", "text": "- Mine", "base": base})
    assert saved.status_code == 200
    assert (tmp_path / "director" / "memory.md").read_text() == "- Mine\n"
    # The director wrote meanwhile: the old base is refused, with the newest text.
    path = tmp_path / "director" / "memory.md"
    path.write_text("- Director's\n")
    os.utime(path, (base + 10, base + 10))
    stale = client.put("/v1/slim/director/notes", json={"project": "Workspace", "note": "memory", "text": "- Lost?", "base": base})
    assert stale.status_code == 409
    assert stale.json()["detail"]["memory"]["text"] == "- Director's\n"
    assert path.read_text() == "- Director's\n"
    # A file that does not exist yet needs no base.
    (tmp_path / "director" / "state.md").unlink()
    made = client.put("/v1/slim/director/notes", json={"project": "Workspace", "note": "state", "text": "## Next\n- Ship", "base": None})
    assert made.status_code == 200 and made.json()["state"]["text"] == "## Next\n- Ship\n"


def test_an_unknown_note_is_rejected(tmp_path: Path) -> None:
    bad = _client(tmp_path).put("/v1/slim/director/notes", json={"note": "secrets", "text": "x"})
    assert bad.status_code == 422
