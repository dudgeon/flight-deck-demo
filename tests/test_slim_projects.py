"""Projects with a goal, and the typed links between them (D-97, D-119)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "view-kit" / "scripts"))

import pa  # noqa: E402

from omnigent.server.routes.slim_projects import connections_for, create_slim_projects_router  # noqa: E402

MINE = "Held payments clarity"


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "reqs.json").write_text(json.dumps({"records": [
        {"id": "R-07", "type": "requirement", "title": "Alert when a hold is placed"},
        {"id": "R-08", "type": "requirement", "title": "Say why it is held"},
    ]}))
    (tmp_path / "data" / "problems.json").write_text(json.dumps({"records": [
        {"id": "P-2", "type": "problem", "title": "No idea when I get my money"},
    ]}))
    return tmp_path


def _pa(*argv: str) -> None:
    pa.main(list(argv))


def _story() -> None:
    _pa("project", MINE, "--goal", "Customers know when held money arrives", "--area", "Held payments",
        "--data", "data/reqs.json")
    _pa("project", "Held payments", "--goal", "Understand held payments", "--data", "data/problems.json")
    _pa("project", "Hold alerts", "--goal", "Push alerts", "--team", "Cards Platform", "--state", "slipped",
        "--state-note", "slipped 2 wks")
    _pa("link", "data/reqs.json", "R-07", "--to", "Hold alerts")
    _pa("link", "data/reqs.json", "R-08", "--to", "Reason codes", "--type", "relies-on")
    _pa("link", "data/problems.json", "P-2", "--to", MINE, "--type", "started")


def test_a_project_file_says_its_goal_area_and_state(workspace: Path) -> None:
    _pa("project", MINE, "--goal", "A goal", "--area", "Held payments")
    _pa("project", MINE, "--state", "slipped", "--state-note", "two weeks")
    card = json.loads((workspace / "projects" / "held-payments-clarity.json").read_text())
    assert (card["name"], card["goal"], card["area"], card["state_note"]) == (MINE, "A goal", "Held payments", "two weeks")
    # A new state drops the note that described the old one.
    _pa("project", MINE, "--state", "shipped")
    assert "state_note" not in json.loads((workspace / "projects" / "held-payments-clarity.json").read_text())
    assert pa.main(["project", "Never described"]) != 0


def test_a_link_is_one_line_on_the_record_it_hangs_from(workspace: Path) -> None:
    _pa("link", "data/reqs.json", "R-07", "--to", "Hold alerts")
    _pa("link", "data/reqs.json", "R-07", "--to", "Hold alerts")  # said twice, stored once
    record = json.loads((workspace / "data" / "reqs.json").read_text())["records"][0]
    assert record["links"] == [{"type": "handed-to", "project": "Hold alerts"}]
    _pa("link", "data/reqs.json", "R-07", "--to", "Hold alerts", "--remove")
    assert "links" not in json.loads((workspace / "data" / "reqs.json").read_text())["records"][0]
    assert pa.main(["link", "data/reqs.json", "R-99", "--to", "Hold alerts"]) != 0


def test_connections_are_grouped_by_what_the_link_means(workspace: Path) -> None:
    _story()
    mine = connections_for(workspace, MINE)
    assert mine["project"]["goal"] == "Customers know when held money arrives"
    assert mine["lives_in"] == "Held payments"
    assert [(c["item"]["id"], c["project"]["name"], c["project"]["state"]) for c in mine["handed_to"]] == [
        ("R-07", "Hold alerts", "slipped")
    ]
    # A link may name a project nobody has described yet.
    assert [(c["item"]["id"], c["project"]) for c in mine["relies_on"]] == [("R-08", {"name": "Reason codes"})]
    assert [(c["item"]["id"], c["project"]["name"], c["type"]) for c in mine["came_from"]] == [
        ("P-2", "Held payments", "started")
    ]


def test_a_link_reads_the_other_way_from_its_far_end(workspace: Path) -> None:
    _story()
    theirs = connections_for(workspace, "Hold alerts")
    assert [(c["item"]["id"], c["project"]["name"]) for c in theirs["came_from"]] == [("R-07", MINE)]
    assert theirs["handed_to"] == []
    relied = connections_for(workspace, "Reason codes")
    assert relied["project"] is None
    assert [(c["item"]["id"], c["project"]["name"]) for c in relied["relied_on_by"]] == [("R-08", MINE)]


def test_a_view_carries_the_linked_projects_for_its_chips(workspace: Path) -> None:
    _story()
    public = pa._public(json.loads((workspace / "data" / "reqs.json").read_text()))
    assert public["projects"] == {"Hold alerts": {"name": "Hold alerts", "goal": "Push alerts", "team": "Cards Platform",
                                                  "state": "slipped", "state_note": "slipped 2 wks"}}


def test_the_route_answers_for_a_project_by_name(workspace: Path) -> None:
    _story()
    projects = SimpleNamespace(list=lambda user_id=None: [
        SimpleNamespace(id="p1", name=MINE, config={"workspace": str(workspace)})
    ])
    app = FastAPI()
    app.include_router(create_slim_projects_router(project_store=projects), prefix="/v1")  # type: ignore[arg-type]
    client = TestClient(app)
    answer: dict[str, Any] = client.get("/v1/slim/projects/connections", params={"project": MINE}).json()
    assert answer["lives_in"] == "Held payments"
    assert len(answer["handed_to"]) == 1
    nothing = client.get("/v1/slim/projects/connections", params={"project": "Unknown"}).json()
    assert nothing["project"] is None and nothing["handed_to"] == []
