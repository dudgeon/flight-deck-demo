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


def test_edit_on_the_page_casts_and_gives_skills(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = _scratch_workspace(tmp_path, monkeypatch)
    shutil.copytree(REPO / "workspace" / "scenarios", workspace / "scenarios")
    skills = tmp_path / "skills"
    shutil.copytree(REPO / "skills", skills, ignore=shutil.ignore_patterns("node_modules"))
    monkeypatch.setenv("OMNIGENT_SLIM_SKILLS_DIR", str(skills))
    slim_hangar.start_person_draft("mara-okafor")
    # Taking Mara out of a scenario whose script she speaks in is blocked.
    draft = slim_hangar.edit_person_draft(
        "mara-okafor", {"cast": {"scenarios": ["decision-review", "delivery-status"]}}
    )
    assert any("speaks in the scenario" in p for p in draft["problems"])
    everything = sorted(slim_hangar.load_hangar()["people"][0]["used_in"].get("scenarios", []))
    assert everything
    draft = slim_hangar.edit_person_draft(
        "mara-okafor",
        {
            "fields": {"role": "Design director, Cards", "skills": ["intent"]},
            "cast": {
                "scenarios": draft["uses"]["scenarios"],
                "workflows": [*draft["uses"]["workflows"], "prd-to-requirements"],
            },
        },
    )
    assert draft["problems"] == [], draft["problems"]
    assert {"kind": "workflows", "id": "prd-to-requirements", "change": "add"} in draft[
        "cast_changes"
    ]
    slim_hangar.publish_person("mara-okafor", "director, and on requirements")
    import json

    wf = json.loads((skills / "prd-to-requirements" / "workflow.json").read_text())
    assert "mara-okafor" in wf["participants"]
    pa = slim_hangar._pa()
    person = pa._participants(workspace / "participants")["mara-okafor"]
    assert person["skills"] == ["intent"]
    assert "`intent`" in pa.opening_message(person, "hello")


def test_build_scenarios_and_workflows_as_folder_drafts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = _scratch_workspace(tmp_path, monkeypatch)
    shutil.copytree(REPO / "workspace" / "scenarios", workspace / "scenarios")
    # A scenario: change the title and the script, see the change, publish, restore.
    draft = slim_hangar.start_folder_draft("scenario", "document-review")
    assert "nothing has changed yet" in draft["problems"]
    script = next(f for f in draft["files"] if f["path"] == "script.md")["text"]
    draft = slim_hangar.edit_folder_draft(
        "scenario",
        "document-review",
        {
            "manifest": {"title": "PRD review, take 2", "opening": "Let's review it."},
            "files": {"script.md": script + "\n**Aviator:** That is everything.\n"},
        },
    )
    assert draft["problems"] == [], draft["problems"]
    assert {f["path"] for f in draft["files"] if f["change"] == "changed"} == {
        "scenario.json",
        "script.md",
    }
    assert "PRD review" in slim_hangar.render_draft_preview("scenario", "document-review")
    slim_hangar.publish_folder("scenario", "document-review", "take 2")
    live = slim_hangar.load_hangar()
    entry = next(s for s in live["scenarios"] if s["id"] == "document-review")
    assert entry["title"] == "PRD review, take 2" and entry["opening"] == "Let's review it."
    assert len(entry["history"]) == 1
    slim_hangar.restore_folder("scenario", "document-review", entry["history"][0]["version"])
    entry = next(s for s in slim_hangar.load_hangar()["scenarios"] if s["id"] == "document-review")
    assert entry["title"] == "Allowances PRD review"
    # A broken script is caught before publishing.
    slim_hangar.start_folder_draft("scenario", "document-review")
    draft = slim_hangar.edit_folder_draft(
        "scenario", "document-review", {"files": {"script.md": "**Nobody Here:** hi\n"}}
    )
    assert draft["problems"]
    with pytest.raises(Exception, match="checks fail"):
        slim_hangar.publish_folder("scenario", "document-review", "")
    slim_hangar.discard_folder("scenario", "document-review")
    # A shipped workflow: editing it publishes a workspace copy; removing that brings it back.
    draft = slim_hangar.start_folder_draft("workflow", "document-review")
    assert draft["builtin"] and draft["shipped"]
    draft = slim_hangar.edit_folder_draft(
        "workflow", "document-review", {"manifest": {"steps": ["Read", "Call in", "Decide"]}}
    )
    assert draft["problems"] == [], draft["problems"]
    slim_hangar.publish_folder("workflow", "document-review", "three steps")
    copy = workspace / ".claude" / "skills" / "document-review"
    assert (copy / "workflow.json").is_file()
    wf = next(w for w in slim_hangar.load_hangar()["workflows"] if w["id"] == "document-review")
    assert wf["steps"] == ["Read", "Call in", "Decide"] and not wf["builtin"]
    draft = slim_hangar.start_folder_draft("workflow", "document-review", remove=True)
    assert draft["problems"] == []  # the shipped one takes over again
    slim_hangar.publish_folder("workflow", "document-review", "back to shipped")
    assert not copy.exists()
    # A new scenario starts from a copy and can't escape its folder.
    draft = slim_hangar.new_folder_draft(
        "scenario", {"name": "Fraud rules review", "duplicate_of": "document-review"}
    )
    assert draft["id"] == "fraud-rules-review" and draft["problems"] == []
    with pytest.raises(Exception, match="not a file inside"):
        slim_hangar.edit_folder_draft(
            "scenario", "fraud-rules-review", {"files": {"../../evil.md": "x"}}
        )


PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def test_an_avatar_is_copied_in_and_published_with_the_person(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = _scratch_workspace(tmp_path, monkeypatch)
    slim_hangar.start_person_draft("risk-review")
    with pytest.raises(Exception, match="not a png picture"):
        slim_hangar.set_person_avatar("risk-review", "face.png", b"<svg/>")
    with pytest.raises(Exception, match="is a gif, jpg, png, webp picture"):
        slim_hangar.set_person_avatar("risk-review", "face.svg", b"<svg/>")
    draft = slim_hangar.set_person_avatar("risk-review", "My Face.PNG", PNG)
    assert draft["problems"] == [] and draft["person"]["avatar"] == "avatars/risk-review.png"
    assert slim_hangar.avatar_file("risk-review", draft=True).read_bytes() == PNG
    # Nothing is live until publish.
    assert not (workspace / "participants" / "avatars").exists()
    slim_hangar.publish_person("risk-review", "a face")
    live = workspace / "participants" / "avatars" / "risk-review.png"
    assert live.read_bytes() == PNG
    person = next(p for p in slim_hangar.load_hangar()["people"] if p["id"] == "risk-review")
    assert person["avatar"].startswith("/v1/slim/hangar/avatars/risk-review?v=")
    assert "risk-review" in slim_hangar.avatars()
    # Taking it away again removes the file; the old picture stays in History.
    slim_hangar.start_person_draft("risk-review")
    slim_hangar.set_person_avatar("risk-review", "", None)
    slim_hangar.publish_person("risk-review", "no face")
    assert not live.exists()
    kept = list(
        (workspace / ".hangar" / "history" / "people" / "risk-review").glob("*.avatar.png")
    )
    assert kept


def test_published_config_travels_with_the_repo() -> None:
    """People, avatars, scenarios, workspace workflows and starters are committed; drafts are not."""
    import subprocess

    def ignored(path: str) -> bool:
        return (
            subprocess.run(["git", "check-ignore", "-q", path], cwd=REPO, check=False).returncode
            == 0
        )

    for path in (
        "workspace/participants/someone.md",
        "workspace/participants/avatars/someone.png",
        "workspace/scenarios/demo/scenario.json",
        "workspace/scenarios/demo/fixtures/data.json",
        "workspace/scenarios/demo/context/brief.md",
        "workspace/scenarios/demo/cast/someone.md",
        "workspace/.claude/skills/my-workflow/workflow.json",
        "workspace/templates/sessions/starter.md",
        "skills/some-skill/SKILL.md",
    ):
        assert not ignored(path), f"{path} would not travel with the repo"
    assert ignored("workspace/.hangar/drafts/people/someone.md")


def test_send_to_repo_commits_published_config_to_a_new_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D-113: Send to repo pushes only the published config, and leaves the checkout alone."""
    import subprocess

    def git(*args: str, cwd: Path) -> str:
        return subprocess.run(
            ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
        ).stdout.strip()

    remote = tmp_path / "remote.git"
    git("init", "--bare", "-b", "main", str(remote), cwd=tmp_path)
    app = tmp_path / "app"
    git("clone", str(remote), str(app), cwd=tmp_path)
    git("config", "user.email", "t@example.com", cwd=app)
    git("config", "user.name", "T", cwd=app)
    workspace = app / "workspace"
    (workspace / "participants").mkdir(parents=True)
    (workspace / "participants" / "mara.md").write_text("Mara\n")
    (app / "README.md").write_text("app\n")
    git("add", "-A", cwd=app)
    git("commit", "-m", "start", cwd=app)
    git("push", "origin", "main", cwd=app)
    monkeypatch.setenv("OMNIGENT_SLIM_WORKSPACE", str(workspace))
    monkeypatch.setattr(slim_hangar.shutil, "which", lambda _: None)  # no gh here
    with pytest.raises(HTTPException, match="already in the repo"):
        slim_hangar.send_to_repo()
    # A Hangar publish, a new workflow copy, and an unrelated edit that must stay behind.
    (workspace / "participants" / "mara.md").write_text("Mara Okafor\n")
    (workspace / ".claude" / "skills" / "decision-review").mkdir(parents=True)
    (workspace / ".claude" / "skills" / "decision-review" / "workflow.json").write_text("{}\n")
    (app / "README.md").write_text("changed by hand\n")
    status = slim_hangar.repo_status()
    assert status["count"] == 2
    sent = slim_hangar.send_to_repo("Mara's full name")
    assert sent["branch"].startswith("hangar/") and sent["files"] == 2
    assert sent["pull_request"] is None and sent["open_pr"] is None  # not a GitHub remote
    pushed = git("ls-tree", "-r", "--name-only", sent["branch"], cwd=remote).splitlines()
    assert "workspace/.claude/skills/decision-review/workflow.json" in pushed
    assert (
        git("show", f"{sent['branch']}:workspace/participants/mara.md", cwd=remote)
        == "Mara Okafor"
    )
    assert git("show", f"{sent['branch']}:README.md", cwd=remote) == "app"
    assert "Mara's full name" in git("log", "-1", "--format=%s", sent["branch"], cwd=remote)
    # The checkout is untouched: same branch, same HEAD, edits still in the working tree.
    assert git("rev-parse", "--abbrev-ref", "HEAD", cwd=app) == "main"
    assert git("rev-parse", "HEAD", cwd=app) == git("rev-parse", "main", cwd=remote)
    assert slim_hangar.repo_status()["sent"]["branch"] == sent["branch"]
    with pytest.raises(HTTPException, match="already sent"):
        slim_hangar.send_to_repo()


def test_compare_url_for_github_remotes() -> None:
    url = slim_hangar._compare_url("git@github.com:dudgeon/omnigent-slim.git", "main", "hangar/x")
    assert url == "https://github.com/dudgeon/omnigent-slim/compare/main...hangar/x?expand=1"
    assert slim_hangar._compare_url("https://github.com/a/b", "main", "h") == (
        "https://github.com/a/b/compare/main...h?expand=1"
    )
    assert slim_hangar._compare_url("/srv/git/x.git", "main", "h") is None
