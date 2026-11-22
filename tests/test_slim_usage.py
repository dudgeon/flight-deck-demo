"""omnigent-slim: the usage log (D-122 to D-127).

One local record of how the platform is used, written by the server, the web
app, `pa` and the tool observer, with ids and words but never sentences.
"""

from __future__ import annotations

import gzip
import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/view-kit/scripts"))
_spec = importlib.util.spec_from_file_location("pa", ROOT / "skills/view-kit/scripts/pa.py")
assert _spec and _spec.loader
pa = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pa)
usagelog = pa.usagelog

from omnigent import slim_usage  # noqa: E402
from omnigent.server.routes.slim_usage import create_slim_usage_router  # noqa: E402


@pytest.fixture
def logdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "usage"
    monkeypatch.setenv(usagelog.DIR_ENV, str(root))
    for name in (usagelog.ENABLED_ENV, usagelog.LEVEL_ENV, usagelog.EVAL_ENV, usagelog.SESSION_ENV):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)
    return root


def _lines(root: Path, include_eval: bool = False) -> list[dict[str, Any]]:
    return list(usagelog.read(usagelog.log_files(root, include_eval=include_eval)))


def test_a_line_has_the_versioned_envelope(logdir: Path) -> None:
    record = usagelog.log("skill.step", source="skill", params={"step": "shape", "n": 2})
    assert record is not None
    (line,) = _lines(logdir)
    assert line["schema"] == "omnigent-slim.usage" and line["schema_version"] == 1
    assert line["event_name"] == "skill.step" and line["source"] == "skill"
    assert line["params"] == {"step": "shape", "n": 2}
    assert len(line["installation_id"]) == 32
    assert line["timestamp"].endswith("Z") and isinstance(line["timestamp_ns"], int)
    assert usagelog.check_record(line) == []
    # One file per day, named by the day.
    assert [p.name for p in usagelog.log_files(logdir)] == [line["timestamp"][:10] + ".jsonl"]


def test_sentences_never_reach_the_log(logdir: Path) -> None:
    secret = "Acquire Northwind before the board meets in March"
    usagelog.log(
        "skill.step",
        source="skill",
        params={"note": secret, "json": '[{"id":"a","title":"x"}]', "ok": "needs-you"},
    )
    text = "".join(p.read_text() for p in usagelog.log_files(logdir))
    assert "Northwind" not in text and "title" not in text
    (line,) = _lines(logdir)
    assert line["params"]["note"] == f"<text {len(secret)}>"
    assert line["params"]["ok"] == "needs-you"


def test_paths_are_made_relative_and_home_is_hidden(logdir: Path) -> None:
    usagelog.log(
        "skill.step",
        source="skill",
        params={"inside": str(ROOT / "workspace/data/x.json"), "home": str(Path.home() / "notes.md")},
    )
    (line,) = _lines(logdir)
    assert line["params"]["inside"] == "workspace/data/x.json"
    assert line["params"]["home"] == "~/notes.md"


def test_fingerprint_level_hashes_names_but_keeps_the_vocabulary(
    logdir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(usagelog.LEVEL_ENV, "fingerprint")
    usagelog.log("skill.step", source="skill", params={"data": "falcon-deal.json", "status": "ready"})
    (line,) = _lines(logdir)
    assert line["params"]["status"] == "ready"
    assert line["params"]["data"].startswith("#") and "falcon" not in line["params"]["data"]
    assert line["level"] == "fingerprint"


def test_bad_names_are_refused_and_logging_never_raises(logdir: Path) -> None:
    with pytest.raises(ValueError):
        usagelog.make_record("NotDotted", source="skill")
    with pytest.raises(ValueError):
        usagelog.make_record("skill.step", source="somewhere")
    assert usagelog.log("NotDotted", source="skill") is None
    assert _lines(logdir) == []


def test_off_switch(logdir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(usagelog.ENABLED_ENV, "0")
    assert usagelog.log("skill.step", source="skill") is None
    assert not logdir.exists()


def test_every_pa_command_is_logged_without_its_text(logdir: Path) -> None:
    assert pa.main(["init", "data/plan.json", "--title", "A secret plan title"]) == 0
    assert pa.main(["get", "data/missing.json"]) == 2
    lines = _lines(logdir)
    assert [l["event_name"] for l in lines] == ["pa.init", "pa.get"]
    init, get = lines
    assert init["source"] == "pa" and init["params"]["exit"] == 0
    assert init["params"]["data"] == "plan.json"
    assert init["params"]["title"].startswith("<text ")
    assert get["params"]["exit"] == 2
    assert "secret" not in json.dumps(lines)


def test_pa_flow_names_its_workflow_and_session(logdir: Path) -> None:
    assert pa.main(["init", "data/a.json", "--title", "A"]) == 0
    session = "0123456789abcdef0123456789abcdef"
    assert pa.main(["flow", "data/a.json", "--scenario", str(ROOT / "skills/intent-shaping"), "--session", session]) == 0
    flow = _lines(logdir)[-1]
    assert flow["event_name"] == "pa.flow"
    assert flow["context"]["workflow"] == "intent-shaping"
    assert flow["session_id"] == session


def test_pa_log_writes_a_skill_event(logdir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert pa.main(["log", "offer.made", "workflow=intent-shaping", "accepted=yes", "turns=3", "--session", "s-1"]) == 0
    (line,) = _lines(logdir)
    assert (line["event_name"], line["source"], line["session_id"]) == ("offer.made", "skill", "s-1")
    assert line["params"] == {"workflow": "intent-shaping", "accepted": True, "turns": 3}
    assert pa.main(["log", "Bad Name"]) == 2
    assert pa.main(["log", "offer.made", "no-equals"]) == 2


def test_eval_trials_are_tagged_and_kept_apart(logdir: Path) -> None:
    assert pa.main(["usage", "eval", "start", "routing", "r-07", "2"]) == 0
    usagelog.log("skill.step", source="skill")
    assert pa.main(["usage", "eval", "stop"]) == 0
    usagelog.log("skill.step", source="skill")
    assert len(_lines(logdir)) == 1  # real use only, by default
    (trial,) = list(usagelog.read(usagelog.log_files(logdir, suite="routing")))
    assert trial["context"]["eval"] == {"suite": "routing", "task": "r-07", "trial": "2"}
    assert trial["context"]["mode"] == "eval"
    assert (logdir / "eval" / "routing").is_dir()


def test_summary_counts_what_matters(logdir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    usagelog.log("web.page_view", source="web", params={"page": "library"})
    usagelog.log("web.page_view", source="web", params={"page": "library"})
    usagelog.log("tool.used", source="tool", params={"tool": "Skill", "skill": "intent-shaping"}, session_id="s1")
    usagelog.log("upstream.turn_end", source="server", params={"status": "completed"}, session_id="s1")
    usagelog.log(
        "upstream.native_session_usage",
        source="server",
        params={"input_tokens": 1000, "output_tokens": 200, "cost_usd": 0.5},
        session_id="s1",
    )
    usagelog.log("hangar.publish", source="server", params={"kind": "person"})
    summary = usagelog.summarize(usagelog.read(usagelog.log_files(logdir)))
    assert summary["pages"] == [["library", 2]]
    assert summary["skills"] == [["intent-shaping", 1]]
    assert summary["turns"]["completed"] == 1
    assert summary["tokens"] == {"input": 1000, "output": 200, "cost_usd": 0.5}
    assert summary["hangar"] == [["publish", 1]]
    assert summary["sessions"] == 1
    assert pa.main(["usage", "summary"]) == 0
    out = capsys.readouterr().out
    assert "Skills loaded" in out and "intent-shaping" in out


def test_cost_survives_a_restart_and_workflow_paths_count_once(
    logdir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # First live flight: an app restart reset a session's running cost, and
    # the summary kept only the last (smaller) reading; `pa flow --scenario
    # ../skills/x` and `x` were listed as two workflows; tokens showed as 0.
    for cost in (0.4, 1.2, 0.3):  # restart after 1.2
        usagelog.log("upstream.native_session_usage", source="server",
                     params={"cost_usd": cost}, session_id="s1")
    usagelog.log("upstream.native_session_usage", source="server",
                 params={"cost_usd": 0.5}, session_id="s2")
    usagelog.log("pa.flow", source="pa", params={"workflow": "../skills/intent-shaping"})
    usagelog.log("pa.brief", source="pa", params={"workflow": "intent-shaping"})
    summary = usagelog.summarize(usagelog.read(usagelog.log_files(logdir)))
    assert summary["tokens"]["cost_usd"] == 2.0
    assert summary["workflows"] == [["intent-shaping", 2]]
    assert pa.main(["usage", "summary"]) == 0
    out = capsys.readouterr().out
    assert "about $2.0" in out and "tokens in 0" not in out


def test_pack_rechecks_and_can_take_upstreams_shape(logdir: Path, tmp_path: Path) -> None:
    usagelog.log("skill.step", source="skill", params={"step": "frame"})
    # A line written by something that skipped the rules is left out of a pack.
    bad = usagelog.make_record("skill.step", source="skill")
    bad["params"] = {"note": "a whole sentence written by hand"}
    usagelog.write(bad)
    result = usagelog.pack(tmp_path / "p.jsonl.gz", usagelog.log_files(logdir))
    assert (result["lines"], result["left_out"]) == (1, 1)

    out = tmp_path / "up.jsonl.gz"
    usagelog.pack(out, usagelog.log_files(logdir), shape="upstream")
    (rec,) = [json.loads(l) for l in gzip.open(out, "rt")]
    assert set(rec) == {"data", "partition-key"}
    data = rec["data"]
    assert data["event_name"] == "skill.step" and data["schema_version"] == 1
    assert json.loads(data["params"])["step"] == "frame"


def test_pa_usage_check_finds_a_bad_line(logdir: Path) -> None:
    usagelog.log("skill.step", source="skill")
    assert pa.main(["usage", "check"]) == 0
    path = usagelog.log_files(logdir)[0]
    with path.open("a") as handle:
        handle.write('{"schema": "omnigent-slim.usage", "event_name": "x"}\n')
    assert pa.main(["usage", "check"]) == 2


@dataclass
class SessionCreatedEvent:
    installation_id: str | None
    session_id: str
    anon_user_id: str | None
    harness: str | None
    is_fork: bool


def test_upstream_telemetry_events_are_kept_locally(logdir: Path) -> None:
    slim_usage.tee_upstream(SessionCreatedEvent("inst", "conv_9", "anon", "claude-native", False))
    (line,) = _lines(logdir)
    assert line["event_name"] == "upstream.session_created"
    assert line["session_id"] == "conv_9"
    assert line["params"] == {"harness": "claude-native", "is_fork": False, "upstream_event": "SessionCreatedEvent"}


def test_upstream_emit_tees_even_with_telemetry_off(logdir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from omnigent import telemetry

    monkeypatch.setenv("OMNIGENT_DISABLE_TELEMETRY", "1")
    telemetry.emit(SessionCreatedEvent(None, "conv_1", None, "claude-native", True))
    assert [l["event_name"] for l in _lines(logdir)] == ["upstream.session_created"]


def test_tool_observer_keeps_names_not_input(logdir: Path) -> None:
    slim_usage.observe_tool(
        {"tool_name": "Skill", "tool_input": {"skill": "claude:intent-shaping", "args": "the secret brief"}},
        "conv_2",
    )
    slim_usage.observe_tool({"tool_name": "Bash", "tool_input": {"command": "cat secrets.txt"}}, "conv_2")
    skill, bash = _lines(logdir)
    assert skill["params"] == {"tool": "Skill", "skill": "intent-shaping"}
    assert bash["params"] == {"tool": "Bash"}
    assert "secret" not in json.dumps([skill, bash])


def test_web_events_route_maps_upstream_analytics(logdir: Path) -> None:
    app = FastAPI()
    app.include_router(create_slim_usage_router(), prefix="/v1")
    client = TestClient(app)
    events = [
        {"type": "page_view", "pageId": "chat", "path": "/c/conv_abc123"},
        {"type": "click", "componentId": "library.start", "componentKind": "button", "path": "/library"},
        {"type": "page_view", "pageId": "hangar", "path": "/hangar/people"},
        {"type": "interaction_phase", "interactionId": "i1", "interactionKind": "agent_run",
         "phase": "complete", "status": "success", "durationMs": 4200},
        {"type": "unknown"},
        {"type": "slim", "event": "not-web.thing"},
    ]
    response = client.post("/v1/slim/usage/events", json={"events": events})
    assert response.json() == {"written": 4, "dropped": 2}
    chat, click, hangar, run = _lines(logdir)
    assert (chat["event_name"], chat["params"]["page"], chat["session_id"]) == ("web.page_view", "chat", "conv_abc123")
    assert click["params"] == {"component": "library.start", "component_kind": "button", "path": "/library"}
    assert hangar["context"]["mode"] == "hangar"
    assert run["params"]["duration_ms"] == 4200
    summary = client.get("/v1/slim/usage/summary").json()
    assert summary["events"] == 4 and summary["enabled"] is True
    assert client.post("/v1/slim/usage/events", json={"events": "x"}).status_code == 400


def test_slim_route_writes_are_logged_by_what_they_did(logdir: Path) -> None:
    slim_usage.route_event("POST", "/v1/slim/hangar/drafts/person/mara-okafor/publish", 200, 12)
    slim_usage.route_event("POST", "/v1/slim/hangar/repo/send", 200, 900)
    slim_usage.route_event("POST", "/v1/slim/inbox/participant-messages", 201, 5)
    slim_usage.route_event("GET", "/v1/slim/hangar", 200, 5)
    publish, send, inbox = _lines(logdir)
    assert publish["event_name"] == "hangar.publish"
    assert (publish["params"]["kind"], publish["params"]["id"]) == ("person", "mara-okafor")
    assert send["event_name"] == "hangar.send_to_repo"
    assert inbox["event_name"] == "api.slim_write" and inbox["params"]["area"] == "inbox"


def test_logs_are_gitignored_and_never_touched_by_updates() -> None:
    assert "/logs/" in (ROOT / ".gitignore").read_text().splitlines()
    spec = importlib.util.spec_from_file_location("install_sync", ROOT / "scripts/install_sync.py")
    assert spec and spec.loader
    install_sync = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(install_sync)
    assert install_sync._skipped("logs/usage/2026-11-21.jsonl")
    assert install_sync._skipped("logs/usage/install-id")


def test_pytest_runs_stay_out_of_the_real_log(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(usagelog.DIR_ENV, raising=False)
    assert usagelog.enabled() is False


def test_a_fingerprinted_pack_hides_names_but_keeps_counts(logdir: Path, tmp_path: Path) -> None:
    usagelog.log("pa.get", source="pa", params={"data": "falcon-deal.json", "exit": 0, "status": "ready"},
                 context={"workflow": "intent-shaping", "project": "falcon"})
    usagelog.log("skill.step", source="skill", params={"note": "a sentence here"})
    out = tmp_path / "fp.jsonl.gz"
    assert pa.main(["usage", "pack", "--out", str(out), "--fingerprint"]) == 0
    first, second = [json.loads(l) for l in gzip.open(out, "rt")]
    assert "falcon" not in json.dumps([first, second])
    assert first["params"]["status"] == "ready" and first["params"]["exit"] == 0
    assert first["context"]["workflow"] == "intent-shaping"
    assert second["params"]["note"] == "<text 15>"
    assert usagelog.check_record(first) == []


def test_pa_loads_as_a_module_without_its_folder_on_the_path() -> None:
    """The Hangar routes load pa.py by file path; usagelog must come with it."""
    import subprocess

    code = (
        "import importlib.util, sys;"
        f"spec = importlib.util.spec_from_file_location('x', {str(ROOT / 'skills/view-kit/scripts/pa.py')!r});"
        "m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m);"
        "print(m.usagelog.SCHEMA)"
    )
    out = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, cwd="/")
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "omnigent-slim.usage"
