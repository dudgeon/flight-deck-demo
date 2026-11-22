"""The routing eval suite (D-133): tasks, evidence, grading, the run loop and blind pairs.

These run without the app: a fake driver plays the part of a session and
writes what the real one would leave behind (usage-log lines under the eval
tag, briefs in the trial's workspace copy).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("routing_suite", ROOT / "evals" / "routing_suite.py")
assert _spec and _spec.loader
rs = importlib.util.module_from_spec(_spec)
sys.modules["routing_suite"] = rs
_spec.loader.exec_module(rs)

CATALOG = {"intent-shaping": "Intent shaping", "decision-review": "Decision review",
           "problem-discovery": "Problem discovery"}


@pytest.fixture
def usage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "usage"
    monkeypatch.setenv(rs.usagelog.DIR_ENV, str(root))
    return root


def _ev(**kw: Any) -> dict[str, Any]:
    base = {"skills": [], "offers": [], "asked": [], "question": False, "threads": False,
            "briefed": [], "runs": [], "tools": []}
    return {**base, **kw}


# ------------------------------------------------------------------ tasks

def test_every_workflow_brings_its_own_examples_and_ids_are_unique() -> None:
    tasks = rs.load_tasks(ROOT / "workspace")
    ids = [t["id"] for t in tasks]
    assert len(ids) == len(set(ids))
    for wf in rs.pa.workflow_catalog(ROOT / "workspace"):
        assert any(t["id"].startswith(wf["id"] + "-") for t in tasks), wf["id"]
    kinds = {t["expect"] for t in tasks}
    assert {"start", "offer", "open", "answer"} <= kinds
    # About a third are near misses or cross-workflow cases, as D-133 asks.
    hand = [t for t in tasks if t["source"] == "tasks.json"]
    assert len(hand) * 4 >= len(tasks)


def test_the_split_is_fixed_by_id_and_roughly_sixty_forty() -> None:
    tasks = rs.load_tasks(ROOT / "workspace")
    assert all(rs.split_of(t["id"]) == t["split"] for t in tasks)
    tune = sum(1 for t in tasks if t["split"] == "tune")
    assert 0.4 < tune / len(tasks) < 0.8
    assert rs.split_of("anything") == rs.split_of("anything")


def test_lifecycle_tasks_wait_for_their_skill() -> None:
    tasks = rs.load_tasks(ROOT / "workspace")
    lifecycle = [t for t in tasks if t["expect"] == "lifecycle"]
    assert lifecycle and not any(rs.runnable(t, {"intent-shaping"}) for t in lifecycle)
    assert all(rs.runnable(t, {"feature-lifecycle"}) for t in lifecycle)


def test_a_bad_task_file_is_refused(tmp_path: Path) -> None:
    bad = tmp_path / "tasks.json"
    bad.write_text(json.dumps({"tasks": [{"id": "x", "expect": "offer", "prompt": "p"}]}))
    with pytest.raises(ValueError, match="names its workflow"):
        rs.load_tasks(ROOT / "workspace", bad)


# ------------------------------------------------------------------ grading

@pytest.mark.parametrize(
    ("expect", "workflow", "ev", "judge_label", "ok", "observed"),
    [
        ("start", "intent-shaping", _ev(skills=["intent-shaping"]), None, True, "start"),
        ("start", "intent-shaping", _ev(briefed=["intent-shaping"], threads=True), None, True, "start"),
        ("start", "intent-shaping", _ev(skills=["decision-review"]), None, False, "start"),
        ("start", "intent-shaping", _ev(skills=["view-kit", "director"]), "answer", False, "answer"),
        ("offer", "intent-shaping", _ev(offers=["intent-shaping"]), None, True, "offer"),
        ("offer", "intent-shaping", _ev(question=True, asked=["intent-shaping"]), None, True, "offer"),
        ("open", None, _ev(question=True), "open", True, "open"),
        ("offer", "intent-shaping", _ev(skills=["intent-shaping"]), None, False, "start"),
        ("offer", "intent-shaping", _ev(), "offer", True, "offer"),
        ("offer", "intent-shaping", _ev(), "open", False, "open"),
        ("open", None, _ev(), "open", True, "open"),
        ("open", None, _ev(offers=["intent-shaping"]), None, False, "offer"),
        ("answer", None, _ev(), "answer", True, "answer"),
        ("answer", None, _ev(), "unknown", True, "none"),
        ("answer", None, _ev(threads=True), None, False, "start"),
    ],
)
def test_grading_follows_the_ladder(expect: str, workflow: str | None, ev: dict[str, Any],
                                    judge_label: str | None, ok: bool, observed: str) -> None:
    calls: list[str] = []

    def judge(prompt: str, reply: str, catalog: dict[str, str]) -> dict[str, Any]:
        calls.append(prompt)
        return {"label": judge_label or "unknown", "workflow": workflow if judge_label == "offer" else None, "why": ""}

    task = {"id": "t", "prompt": "p", "expect": expect, "workflow": workflow}
    graded = rs.grade(task, ev, "reply", CATALOG, judge)
    assert (graded["pass"], graded["observed"]) == (ok, observed)
    # The judge is asked only when the code evidence is silent.
    has_code = any(ev[k] for k in ("skills", "offers", "asked", "threads", "briefed", "runs")) and not (
        set(ev["skills"]) <= {"view-kit", "director"} and not any(ev[k] for k in ("offers", "asked", "threads", "briefed", "runs")))
    assert bool(calls) == (not has_code)


def test_evidence_reads_skills_threads_offers_and_question_cards() -> None:
    lines = [
        {"event_name": "tool.used", "params": {"tool": "Skill", "skill": "intent-shaping"}},
        {"event_name": "tool.used", "params": {"tool": "mcp__omnigent__sys_session_create"}},
        {"event_name": "offer.made", "params": {"workflow": "decision-review"}},
    ]
    result = {"question": [{"questions": [{"question": "Start Problem discovery in a thread?",
                                           "options": [{"label": "Start it"}, {"label": "Not now"}]}]}],
              "threads": []}
    ev = rs.evidence(result, lines, {"briefed": [], "runs": []}, CATALOG)
    assert ev["skills"] == ["intent-shaping"] and ev["threads"] is True
    assert ev["offers"] == ["decision-review"] and ev["asked"] == ["problem-discovery"]


def test_a_clarifying_card_is_not_an_offer() -> None:
    # Seen on the Mac mini: "Which calls do you mean?" was graded an offer.
    ask = {"questions": [{"question": "Which calls do you mean?", "header": "Calls",
                          "options": [{"label": "Calls to participants", "description": "Agents on the roster"},
                                      {"label": "Customer or user calls", "description": "Fits problem discovery later"}]}]}
    ev = rs.evidence({"question": [ask], "threads": []}, [], {"briefed": [], "runs": []}, CATALOG)
    assert ev["question"] is True and ev["asked"] == [] and not ev["card_offers"]
    assert "Which calls do you mean?" in ev["card_text"]
    seen: dict[str, str] = {}

    def judge(prompt: str, reply: str, catalog: dict[str, str]) -> dict[str, Any]:
        seen["reply"] = reply
        return {"label": "open", "workflow": None, "why": ""}

    task = {"id": "t", "prompt": "What else could we do about those calls?", "expect": "open", "workflow": None}
    graded = rs.grade(task, ev, "Which calls?", CATALOG, judge)
    assert graded["pass"] and graded["observed"] == "open"
    assert "[Question card] Which calls do you mean?" in seen["reply"]
    # A card whose answer starts something is an offer, even naming no workflow.
    start = {"questions": [{"question": "Shall I?", "options": [{"label": "Yes, start"}, {"label": "Not now"}]}]}
    ev2 = rs.evidence({"question": [start], "threads": []}, [], {"briefed": [], "runs": []}, CATALOG)
    assert ev2["asked"] == ["?"]
    assert rs.observe(ev2, CATALOG) == ("offer", [], "offer logged or asked on a card")
    # Naming a workflow in an answer counts; "intent-shaping-ish" text elsewhere does not.
    named = {"questions": [{"question": "Next?", "options": [{"label": "Decision review"}, {"label": "Not now"}]}]}
    ev3 = rs.evidence({"question": [named], "threads": []}, [], {"briefed": [], "runs": []}, CATALOG)
    assert ev3["asked"] == ["decision-review"]


def test_regrade_reads_old_trials_with_the_new_grader(tmp_path: Path) -> None:
    run = tmp_path / "run"
    run.mkdir()
    ask = {"questions": [{"question": "Which paragraph should I read?",
                          "options": [{"label": "I'll paste it"}, {"label": "A file in context/"}]}]}
    old = {"task": {"id": "document-review-open-1", "prompt": "Does this opening paragraph read well?",
                    "expect": "open", "workflow": None, "split": "tune"},
           "trial": 1, "result": {"question": [ask], "reply": "", "threads": []},
           "evidence": {**_ev(question=True, asked=["document-review"])}, "pass": False, "observed": "offer"}
    (run / "trials.jsonl").write_text(json.dumps(old) + "\n")
    rs.main(["report", str(run), "--regrade", "--no-judge"])
    again = rs.load_records(run)[0]
    assert again["pass"] and again["observed"] == "none" and again["evidence"]["asked"] == []


def test_workspace_evidence_reads_briefs_and_runs(tmp_path: Path) -> None:
    (tmp_path / "briefs").mkdir()
    (tmp_path / "briefs" / "a.md").write_text('# Brief: intent-shaping on "release dates"\n')
    (tmp_path / "progress").mkdir()
    (tmp_path / "progress" / "r.json").write_text(json.dumps({"workflow": "decision-review", "steps": []}))
    assert rs.workspace_evidence(tmp_path) == {"briefed": ["intent-shaping"], "runs": ["decision-review"]}


def test_a_trial_gets_configuration_but_no_state(tmp_path: Path) -> None:
    src = tmp_path / "ws"
    for rel in ("CLAUDE.md", "data/old.json", "data/.gitkeep", "progress/run.json", "frameworks/lifecycle.json",
                ".hangar/drafts/x.json", "director/state.md", ".claude/skills/w/SKILL.md"):
        (src / rel).parent.mkdir(parents=True, exist_ok=True)
        (src / rel).write_text("x")
    dest = rs.copy_workspace(src, tmp_path / "trial")
    assert (dest / "CLAUDE.md").is_file() and (dest / "frameworks/lifecycle.json").is_file()
    assert (dest / ".claude/skills/w/SKILL.md").is_file() and (dest / "data/.gitkeep").is_file()
    assert not (dest / "data/old.json").exists() and not (dest / "progress/run.json").exists()
    assert not (dest / ".hangar").exists() and not (dest / "director").exists()


def test_offer_tasks_get_fixtures_from_real_scenarios() -> None:
    tasks = {t["id"]: t for t in rs.load_tasks(ROOT / "workspace")}
    for tid in ("decision-review-offer-1", "requirements-to-dependencies-offer-1"):
        fixtures = tasks[tid]["fixtures"]
        assert fixtures and all((ROOT / "workspace" / src).is_file() for src in fixtures.values()), tid
    # Mapping dependencies starts from requirements that have none yet, or there is nothing to offer.
    deps = tasks["requirements-to-dependencies-offer-1"]["fixtures"]["data/allowances.json"]
    records = json.loads((ROOT / "workspace" / deps).read_text())["records"]
    assert records and not any(r["type"] == "dependency" for r in records)


def test_fixtures_for_an_unknown_task_are_refused(tmp_path: Path) -> None:
    bad = tmp_path / "tasks.json"
    bad.write_text(json.dumps({"tasks": [], "fixtures": {"nobody": {"data/x.json": "x.json"}}}))
    with pytest.raises(ValueError, match="do not exist"):
        rs.load_tasks(ROOT / "workspace", bad)


def test_fixtures_are_copied_and_stay_inside_the_trial(tmp_path: Path) -> None:
    ws = tmp_path / "trial"
    (ws / "scenarios/s/fixtures").mkdir(parents=True)
    (ws / "scenarios/s/fixtures/d.json").write_text("{}")
    assert rs.add_fixtures(ws, {"data/d.json": "scenarios/s/fixtures/d.json"}) == ["data/d.json"]
    assert (ws / "data/d.json").read_text() == "{}"
    with pytest.raises(ValueError, match="inside the workspace"):
        rs.add_fixtures(ws, {"../out.json": "scenarios/s/fixtures/d.json"})
    with pytest.raises(ValueError, match="not in the workspace"):
        rs.add_fixtures(ws, {"data/e.json": "scenarios/s/missing.json"})


# ------------------------------------------------------------------ the run loop

class FakeDriver:
    """Plays a session: loads the right skill for start prompts, offers on offer prompts."""

    def __init__(self, source: Path, flaky: set[str] | None = None) -> None:
        self.source, self.flaky, self.calls = source, flaky or set(), 0

    def source_workspace(self) -> Path:
        return self.source

    def run(self, prompt: str, workspace: Path, title: str) -> dict[str, Any]:
        self.calls += 1
        task_id, trial = title.split()[2], int(title.split()[3])
        if prompt.startswith("Run "):
            assert (workspace / "data" / "d.json").is_file()  # its fixture is in place first
            rs.usagelog.log("tool.used", source="tool", params={"tool": "Skill", "skill": "decision-review"})
            (workspace / "briefs").mkdir(exist_ok=True)
            (workspace / "briefs" / "b.md").write_text('# Brief: decision-review on "x"\n')
        elif prompt.startswith("Offer") and not (task_id in self.flaky and trial == 1):
            rs.usagelog.log("offer.made", source="skill", params={"workflow": "decision-review"})
        return {"session": f"s{self.calls}", "status": "idle", "reply": "Sure.", "question": None,
                "threads": [], "timed_out": False, "error": None}


def test_run_suite_tags_each_trial_and_passes_on_two_of_three(tmp_path: Path, usage: Path) -> None:
    src = tmp_path / "ws"
    (src / "briefs").mkdir(parents=True)
    tasks = [
        {"id": "s1", "prompt": "Run a decision review", "expect": "start", "workflow": "decision-review", "split": "tune",
         "fixtures": {"data/d.json": "seed/d.json"}},
        {"id": "o1", "prompt": "Offer please", "expect": "offer", "workflow": "decision-review", "split": "held-out"},
        {"id": "o2", "prompt": "Offer please", "expect": "offer", "workflow": "decision-review", "split": "tune"},
        {"id": "a1", "prompt": "What is a dependency?", "expect": "answer", "workflow": None, "split": "tune"},
    ]
    driver = FakeDriver(src, flaky={"o2"})
    judge = lambda prompt, reply, catalog: {"label": "answer", "workflow": None, "why": ""}  # noqa: E731
    with pytest.raises(ValueError, match="fixtures not in the workspace"):
        rs.run_suite(tasks, driver, tmp_path / "runs" / "missing", 3, "sonnet", judge, {}, log=lambda _m: None)
    assert driver.calls == 0
    (src / "seed").mkdir()
    (src / "seed" / "d.json").write_text("{}")
    judge = lambda prompt, reply, catalog: {"label": "answer", "workflow": None, "why": ""}  # noqa: E731
    out = tmp_path / "runs" / "20261122-000000-test"
    summary = rs.run_suite(tasks, driver, out, 3, "sonnet", judge, {"decision-review": "Decision review"}, log=lambda _m: None)
    assert driver.calls == 12
    assert summary["overall"] == {"passed": 4, "tasks": 4, "rate": 1.0}
    assert summary["tasks"]["o2"]["passes"] == 2  # flaky once, still passes on 2 of 3
    assert not (usage / "eval-tag.json").exists()  # the tag is cleared after every trial
    eval_lines = list(rs.usagelog.read(rs.usagelog.log_files(usage, suite="routing")))
    assert {(l["context"]["eval"]["task"]) for l in eval_lines} == {"s1", "o1", "o2"}
    assert (out / "report.md").read_text().startswith("# Routing suite")
    assert not (out / "ws").exists() or not any((out / "ws").iterdir())
    # The report can be rebuilt from the saved trials.
    rs.main(["report", str(out)])
    assert json.loads((out / "summary.json").read_text())["overall"]["passed"] == 4


def test_a_task_failing_two_trials_fails() -> None:
    task = {"id": "t", "expect": "offer", "workflow": "w", "split": "tune"}
    records = [{"task": task, "trial": n, "pass": n == 1, "observed": "none", "workflows": []} for n in (1, 2, 3)]
    summary = rs.summarize(records)
    assert summary["failing"] == ["t"] and summary["by_split"]["tune"]["passed"] == 0


# ------------------------------------------------------------------ blind pairs

def _run_dir(tmp: Path, name: str, passes: dict[str, bool]) -> Path:
    run = tmp / name
    run.mkdir()
    with (run / "trials.jsonl").open("w") as fh:
        for tid, ok in passes.items():
            rec = {"task": {"id": tid, "prompt": f"prompt {tid}", "expect": "offer", "split": "tune"}, "trial": 1,
                   "pass": ok, "observed": "offer" if ok else "none", "workflows": [],
                   "result": {"reply": f"{name} reply to {tid}"}, "evidence": _ev()}
            fh.write(json.dumps(rec) + "\n")
    return run


def test_pairs_hide_which_run_is_which_and_prefer_differences(tmp_path: Path) -> None:
    ids = [f"t{i}" for i in range(14)]
    a = _run_dir(tmp_path, "run-baseline", {t: True for t in ids})
    b = _run_dir(tmp_path, "run-change", {t: i % 2 == 0 for i, t in enumerate(ids)})
    page, key = rs.make_pairs(a, b, 10, seed=7)
    assert len(key["pairs"]) == 10
    assert "run-baseline" not in page.replace("run-baseline reply", "") and "run-change" not in page.replace("run-change reply", "")
    differing = {t for i, t in enumerate(ids) if i % 2 == 1}
    assert differing <= {p["task"] for p in key["pairs"].values()}
    sides = {p["left"] for p in key["pairs"].values()}
    assert sides == {"run-baseline", "run-change"}  # both runs appear on the left somewhere
    assert "http" not in page  # offline (no CDN, no fonts)
