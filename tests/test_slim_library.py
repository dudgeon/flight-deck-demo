"""omnigent-slim: the Library is generated from workflow.json and scenario.json (D-82 to D-88)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from omnigent.server.routes import slim_hangar, slim_library

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _repo_folders(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OMNIGENT_SLIM_WORKSPACE", str(REPO / "workspace"))
    monkeypatch.setenv("OMNIGENT_SLIM_LIBRARY_DIR", str(REPO / "workspace" / "templates"))
    monkeypatch.setenv("OMNIGENT_SLIM_SKILLS_DIR", str(REPO / "skills"))


def _library() -> dict:
    return slim_library.load_library(slim_library.library_dir())


def test_featured_skills_in_lifecycle_order_with_one_spotlight() -> None:
    lib = _library()
    ids = [s["id"] for s in lib["skills"]]
    assert ids == [
        "problem-discovery",
        "intent-shaping",
        "document-review",
        "prd-to-dependencies",
        "decision-review",
        "delivery-status",
    ]
    # Utility workflows have no library flag and never show.
    assert "requirements-to-dependencies" not in ids
    # Parts of an arc run when named but have no card of their own (D-148).
    assert "prd-to-requirements" not in ids
    # Its demo shows on the arc's card instead.
    arc = next(s for s in lib["skills"] if s["id"] == "prd-to-dependencies")
    assert "prd-to-requirements" in [d["id"] for d in arc["demos"]]
    assert "requirements-to-dependencies" in [d["id"] for d in arc["demos"]]
    assert [s["id"] for s in lib["skills"] if s["spotlight"]] == ["intent-shaping"]
    assert "templates" not in lib and "sessions" not in lib


def test_a_skill_card_reads_its_workflow() -> None:
    skills = {s["id"]: s for s in _library()["skills"]}
    shaping = skills["intent-shaping"]
    assert shaping["title"] == "Intent shaping"
    assert shaping["steps"][0] == "Capture the idea"
    assert [f["name"] for f in shaping["fields"]] == ["idea"]
    # The workflow's cast is named so the agent can call them in.
    assert "Participants for this session: risk-review" in shaping["prompt"]
    assert {"id": "intent-shaping", "title": "Release dates, from a hunch"} in shaping["demos"]
    # A Hangar starter that names the workflow is an extra way in.
    review = skills["document-review"]
    assert [s["id"] for s in review["starters"]] == ["risk-read-first"]


def test_prompt_is_made_from_inputs_without_a_library_prompt() -> None:
    manifest = {"title": "Map it", "inputs": [{"name": "platform map", "hint": "a file"}]}
    prompt = slim_library.skill_prompt("map-it", manifest, ["risk-review"])
    assert prompt.startswith("Map it on {{platform-map: a file}}, using the map-it skill.")
    assert prompt.endswith("Participants for this session: risk-review.")


def test_demo_cards_read_the_scenario_and_its_script() -> None:
    demos = {d["id"]: d for d in _library()["demos"]}
    assert len(demos) == 7
    review = demos["document-review"]
    assert review["title"] == "Second opinions on a PRD"
    assert review["workflow_title"] == "Review a document with others"
    assert [c["initials"] for c in review["cast"]] == ["RR", "MO"]
    assert review["turns"] == len(review["meter"]) == 6
    assert review["live_turns"] == 1 and review["kind"] == "Mixed"
    assert review["length_minutes"] == 6
    assert demos["decision-review"]["kind"] == "Scripted"
    for demo in demos.values():
        assert len(demo["summary"].split()) <= 25, demo["id"]


def test_live_turns_switch_plays_every_turn_canned(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ws = tmp_path / "workspace"
    shutil.copytree(REPO / "workspace", ws, ignore=shutil.ignore_patterns("demos", ".hangar"))
    monkeypatch.setenv("OMNIGENT_SLIM_WORKSPACE", str(ws))
    pa = slim_hangar._pa()
    result = slim_hangar.fly_scenario("document-review", None, live_turns=False)
    folder = Path(result["demo"]["folder"])
    assert pa.demo_state(folder)["live_turns"] is False
    played = "\n".join(pa.demo_next(folder) for _ in range(6))
    assert "LIVE:" not in played
    # Keep going with the switch on again: the live turn is handed to the agent.
    slim_hangar.fly_scenario("document-review", "reset", live_turns=True)
    played = "\n".join(pa.demo_next(folder) for _ in range(6))
    assert "LIVE:" in played
    entry = next(d for d in slim_library.load_library(None)["demos"] if d["id"] == "document-review")
    assert entry["demo"]["live_turns"] is True
    assert json.loads((folder / ".demo" / "demo.json").read_text())["live_turns"] is True
