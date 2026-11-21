"""omnigent-slim: runs that pause and resume, and a project's "In flight" list (D-93, D-96)."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from omnigent.server.routes.slim_runs import create_slim_runs_router, load_runs, parse_run

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/view-kit/scripts"))  # pa imports docreview from beside it
_spec = importlib.util.spec_from_file_location("pa", ROOT / "skills/view-kit/scripts/pa.py")
assert _spec and _spec.loader
pa = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pa)

SCENARIO = str(ROOT / "skills/intent-shaping")
DATA = "data/allowances-intent.json"
SESSION = "0123456789abcdef0123456789abcdef"


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    assert pa.main(["init", DATA, "--title", "Allowances"]) == 0
    assert pa.main(["flow", DATA, "--scenario", SCENARIO, "--session", SESSION]) == 0
    return tmp_path


def _run(workspace: Path) -> dict[str, Any]:
    (file,) = (workspace / "progress").glob("*.json")
    return json.loads(file.read_text())


def test_a_new_run_is_working_and_names_its_session(workspace: Path) -> None:
    run = _run(workspace)
    assert run["state"] == "working"
    assert run["session"] == SESSION
    assert run["data"] == DATA
    assert run["started"]


def test_a_pause_needs_a_note_and_keeps_it(workspace: Path) -> None:
    assert pa.main(["flow", DATA, "--step", "2"]) == 0
    assert pa.main(["flow", DATA, "--pause"]) != 0
    assert _run(workspace)["state"] == "working"
    assert pa.main(["flow", DATA, "--pause", "--note", "Framed it; the metric is next."]) == 0
    run = _run(workspace)
    assert (run["state"], run["current"]) == ("paused", 2)
    assert run["left_off"] == "Framed it; the metric is next."
    assert run["paused_at"]


def test_a_paused_run_stays_paused_when_its_records_change(workspace: Path) -> None:
    pa.main(["flow", DATA, "--pause", "--note", "Left at the start."])
    pa.main(["add", DATA, "--json", '[{"type":"area","title":"Customer"}]'])
    assert _run(workspace)["state"] == "paused"


def test_resume_and_doing_work_both_pick_a_paused_run_up(workspace: Path) -> None:
    pa.main(["flow", DATA, "--pause", "--note", "Left at the start."])
    assert pa.main(["flow", DATA, "--resume"]) == 0
    run = _run(workspace)
    assert (run["state"], run["left_off"]) == ("working", "")
    pa.main(["flow", DATA, "--pause", "--note", "Again."])
    assert pa.main(["flow", DATA, "--step", "3"]) == 0
    assert _run(workspace)["state"] == "working"


def test_a_stopped_run_only_comes_back_with_resume(workspace: Path) -> None:
    assert pa.main(["flow", DATA, "--stop", "--note", "Not doing this."]) == 0
    assert _run(workspace)["state"] == "stopped"
    assert pa.main(["flow", DATA, "--step", "2"]) != 0
    assert pa.main(["flow", DATA, "--resume", "--step", "2"]) == 0
    assert (_run(workspace)["state"], _run(workspace)["current"]) == ("working", 2)


def test_needs_you_comes_from_the_agent_or_from_the_records(workspace: Path) -> None:
    pa.main(["flow", DATA, "--state", "needs-you", "--note", "Pick the target depth."])
    assert _run(workspace)["state"] == "needs-you"
    pa.main(["flow", DATA, "--state", "working"])
    assert _run(workspace)["state"] == "working"


def test_done_is_finished_and_cannot_be_paused(workspace: Path) -> None:
    assert pa.main(["flow", DATA, "--done"]) == 0
    assert _run(workspace)["state"] == "finished"
    assert pa.main(["flow", DATA, "--pause", "--note", "x"]) != 0


def test_runs_lists_what_is_in_flight(workspace: Path, capsys: pytest.CaptureFixture[str]) -> None:
    pa.main(["flow", DATA, "--pause", "--note", "Framed it; the metric is next."])
    capsys.readouterr()
    assert pa.main(["runs"]) == 0
    out = capsys.readouterr().out
    assert "paused" in out and "Allowances" in out and "the metric is next" in out
    pa.main(["flow", DATA, "--done"])
    capsys.readouterr()
    pa.main(["runs"])
    assert "no runs in flight" in capsys.readouterr().out


# ---------------------------------------------------------------- the project's list


def test_a_file_from_before_runs_had_a_state_still_reads() -> None:
    assert parse_run("a", {"steps": ["One", "Two"], "current": 2})["state"] == "working"  # type: ignore[index]
    assert parse_run("a", {"steps": ["One", "Two"], "current": 3})["state"] == "finished"  # type: ignore[index]
    assert parse_run("a", {"steps": []}) is None
    assert parse_run("a", ["not", "a", "run"]) is None


def test_runs_that_need_the_person_come_first(tmp_path: Path) -> None:
    folder = tmp_path / "progress"
    folder.mkdir()
    for name, state in (("a", "working"), ("b", "finished"), ("c", "needs-you"), ("d", "paused")):
        (folder / f"{name}.json").write_text(json.dumps({"steps": ["One"], "current": 1, "state": state}))
    (folder / "broken.json").write_text("{nope")
    assert [run["id"] for run in load_runs(tmp_path)] == ["c", "d", "a", "b"]


class _Projects:
    def __init__(self, workspace: Path) -> None:
        self._projects = [
            SimpleNamespace(id="p-work", name="Workspace", config={"workspace": str(workspace)}),
            SimpleNamespace(id="p-hangar", name="Hangar", config={"workspace": str(workspace)}),
        ]

    def list(self, *, user_id: str | None) -> list[Any]:
        return self._projects


class _Conversations:
    def get_conversation(self, conversation_id: str) -> Any:
        if conversation_id == SESSION:
            return SimpleNamespace(project_id="p-hangar", title="Build a person")
        return None


def _client(workspace: Path) -> TestClient:
    app = FastAPI()
    app.include_router(
        create_slim_runs_router(project_store=_Projects(workspace), conversation_store=_Conversations()),  # type: ignore[arg-type]
        prefix="/v1",
    )
    return TestClient(app)


def test_two_projects_sharing_a_folder_each_list_their_own_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(os.environ, "OMNIGENT_SLIM_PROJECT", "Workspace")
    folder = tmp_path / "progress"
    folder.mkdir()
    base = {"steps": ["One", "Two"], "current": 1, "workflow": "Intent shaping"}
    (folder / "in-hangar.json").write_text(json.dumps({**base, "state": "needs-you", "session": SESSION}))
    (folder / "no-session.json").write_text(json.dumps({**base, "state": "paused", "left_off": "Here."}))
    (folder / "gone.json").write_text(json.dumps({**base, "session": "f" * 32}))
    client = _client(tmp_path)

    hangar = client.get("/v1/slim/runs", params={"project": "Hangar"}).json()
    assert [run["id"] for run in hangar["runs"]] == ["in-hangar"]
    assert hangar["needs_you"] == 1
    assert hangar["runs"][0]["session_title"] == "Build a person"

    work = client.get("/v1/slim/runs", params={"project": "Workspace"}).json()
    assert [run["id"] for run in work["runs"]] == ["no-session", "gone"]
    assert work["needs_you"] == 0
    # A run whose session is gone can still be resumed, in a new session.
    assert all(run["session"] is None for run in work["runs"])
    assert work["runs"][0]["left_off"] == "Here."


def test_an_unknown_project_has_no_runs(tmp_path: Path) -> None:
    assert _client(tmp_path).get("/v1/slim/runs", params={"project": "Nope"}).json()["runs"] == []
