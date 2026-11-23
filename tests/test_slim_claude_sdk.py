"""Sessions run Claude Code through its structured messages (D-172, D-173).

Company managed settings can refuse plugins, hooks and extra tool servers
(disableSideloadFlags, allowManagedHooksOnly, allowedMcpServers), so every
Flight Deck session runs the ``claude-code`` agent on the claude-sdk harness,
with Claude Code's own tools and permission checks and skills loaded from
``.claude/skills`` folders instead of a plugin.
"""

from __future__ import annotations

import os
from pathlib import Path

import httpx
import pytest
import yaml

from omnigent import slim_bootstrap, slim_policy

ROOT = Path(__file__).resolve().parent.parent
AGENT = ROOT / "omnigent" / "slim_agents" / "claude-code" / "config.yaml"


def test_the_agent_is_claude_code_over_structured_messages() -> None:
    spec = yaml.safe_load(AGENT.read_text())
    assert spec["name"] == slim_bootstrap.CLAUDE_AGENT_NAME == "claude-code"
    config = spec["executor"]["config"]
    assert config["harness"] == "claude-sdk"
    assert config["system_prompt_preset"] == "claude_code"
    # No permission mode that skips Claude Code's checks, and no os_env: the
    # sys_os_* stand-ins would replace Claude Code's own tools.
    assert config.get("permission_mode") in (None, *slim_policy.ALLOWED_CLAUDE_PERMISSION_MODES)
    assert "os_env" not in spec


def test_start_offers_only_that_agent() -> None:
    start = (ROOT / "start.sh").read_text()
    assert (
        'OMNIGENT_BUILTIN_AGENT_DIRS="${OMNIGENT_BUILTIN_AGENT_DIRS:-$ROOT/omnigent/slim_agents/claude-code}"'
        in start
    )
    assert 'OMNIGENT_SEEDED_AGENTS="${OMNIGENT_SEEDED_AGENTS-}"' in start


def test_claude_code_keeps_its_own_tools() -> None:
    tools = slim_policy.slim_sdk_tools(["Skill", "ToolSearch", "Bash"])
    for name in ("Bash", "Read", "Edit", "Write", "Glob", "Grep", "Skill", "ToolSearch"):
        assert tools.count(name) == 1
    assert not any(name.startswith("Web") for name in tools)  # offline


@pytest.mark.parametrize(
    ("asked", "runs"),
    [
        (None, slim_policy.DEFAULT_CLAUDE_PERMISSION_MODE),
        ("default", "default"),
        ("bypassPermissions", "default"),
        ("dontAsk", "default"),
    ],
)
def test_permission_modes_never_skip_checks(asked: str | None, runs: str) -> None:
    assert slim_policy.slim_sdk_permission_mode(asked) == runs


def test_model_and_effort_fall_back_to_the_slim_defaults() -> None:
    assert slim_policy.slim_sdk_model("claude-haiku-5-5") == "claude-haiku-5-5"
    assert slim_policy.slim_sdk_model(None) == (slim_policy.DEFAULT_CLAUDE_MODEL or None)
    assert slim_policy.slim_sdk_effort("high") == "high"
    assert slim_policy.slim_sdk_effort(None) == (slim_policy.DEFAULT_CLAUDE_EFFORT or None)


def test_the_executor_sends_no_plugins() -> None:
    source = (ROOT / "omnigent" / "inner" / "claude_sdk_executor.py").read_text()
    assert "omnigent-slim: no plugins" in source
    assert "base_tools = slim_sdk_tools(base_tools)" in source


def test_every_bundled_skill_is_linked_where_claude_code_finds_it() -> None:
    shipped = {p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md")}
    links = ROOT / ".claude" / "skills"
    linked = {p.name for p in links.iterdir() if p.is_symlink()}
    assert linked == shipped
    for name in shipped:
        assert os.readlink(links / name) == f"../../skills/{name}"
        assert (links / name / "SKILL.md").is_file()


def _fake_server(projects: list[dict], patched: list[dict]) -> httpx.MockTransport:
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/projects" and request.method == "GET":
            return httpx.Response(200, json={"data": projects})
        if request.url.path == "/v1/agents":
            return httpx.Response(200, json={"data": [{"id": "new", "name": "claude-code"}]})
        if request.method == "PATCH":
            patched.append(__import__("json").loads(request.content))
            return httpx.Response(200, json={})
        return httpx.Response(404)

    return httpx.MockTransport(handle)


def test_existing_projects_move_to_the_new_agent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    patched: list[dict] = []
    transport = _fake_server(
        [
            {
                "id": "p1",
                "name": "Workspace",
                "config": {"agent_id": "old", "workspace": str(tmp_path)},
            }
        ],
        patched,
    )
    real = httpx.Client
    monkeypatch.setattr(
        slim_bootstrap.httpx, "Client", lambda **kw: real(transport=transport, **kw)
    )
    slim_bootstrap.ensure_project("http://x", "Workspace", tmp_path)
    assert patched and patched[0]["config"]["agent_id"] == "new"


def test_flattened_skill_links_are_put_back(tmp_path: Path) -> None:
    """An unzip that writes links as text files must not cost sessions their skills."""
    from omnigent.slim_skills import repair_skill_links

    for name in ("alpha", "beta", "gamma"):
        (tmp_path / "skills" / name).mkdir(parents=True)
        (tmp_path / "skills" / name / "SKILL.md").write_text("---\nname: x\n---\n")
    links = tmp_path / ".claude" / "skills"
    links.mkdir(parents=True)
    (links / "alpha").write_text("../../skills/alpha")  # flattened by an unzip
    (links / "beta").symlink_to("../../skills/beta")  # already right
    (links / "own").mkdir()  # a real skill folder of its own
    assert repair_skill_links(tmp_path) == ["alpha", "gamma"]
    for name in ("alpha", "beta", "gamma"):
        assert (links / name).is_symlink() and (links / name / "SKILL.md").is_file()
    assert (links / "own").is_dir() and not (links / "own").is_symlink()
    assert repair_skill_links(tmp_path) == []


def test_only_the_file_viewer_is_pre_approved() -> None:
    from omnigent.slim_policy import slim_sdk_preapproved

    asked = ["mcp__omnigent__ui_open_file", "mcp__omnigent__sys_session_rename", "Bash"]
    assert slim_sdk_preapproved(asked) == ["mcp__omnigent__ui_open_file"]
    src = (ROOT / "omnigent/inner/claude_sdk_executor.py").read_text()
    assert "allowed_tools = slim_sdk_preapproved(allowed_tools)" in src


def test_projects_whose_agent_is_gone_move_to_claude_code(monkeypatch: pytest.MonkeyPatch) -> None:
    """A flown demo made before D-173 names the old agent; start-up moves it over."""
    patched: list[dict] = []
    transport = _fake_server(
        [
            {"id": "p1", "name": "◆ Demo · The launch slips", "config": {"agent_id": "old"}},
            {"id": "p2", "name": "Workspace", "config": {"agent_id": "new"}},
            {"id": "p3", "name": "No agent", "config": {}},
        ],
        patched,
    )
    real = httpx.Client
    monkeypatch.setattr(
        slim_bootstrap.httpx, "Client", lambda **kw: real(transport=transport, **kw)
    )
    assert slim_bootstrap.repoint_orphaned_projects("http://x") == ["◆ Demo · The launch slips"]
    assert [p["config"]["agent_id"] for p in patched] == ["new"]


def test_flying_again_brings_a_demo_project_onto_the_workspace_agent(tmp_path: Path) -> None:
    from types import SimpleNamespace

    from omnigent.server.routes import slim_hangar

    folder = tmp_path / "demos" / "x"
    projects = [
        SimpleNamespace(id="w", name="Workspace", config={"agent_id": "new", "host_id": "h"}),
        SimpleNamespace(
            id="d",
            name="◆ Demo · X",
            config={"agent_id": "old", "host_id": "h", "workspace": str(folder)},
        ),
    ]
    updates: list[dict] = []
    store = SimpleNamespace(
        list=lambda user_id=None: projects,
        update=lambda pid, user_id=None, config=None: updates.append(config),
    )
    assert slim_hangar._ensure_demo_project(store, None, "◆ Demo · X", folder) == "d"
    assert updates and updates[0]["agent_id"] == "new"


# --- The session view says Claude Code, has no terminal tab, and picks mode and effort (D-174).


def test_the_harness_reads_as_claude_code_and_offers_effort() -> None:
    from omnigent.harness_plugins import SLIM_PICKER_HARNESSES, harness_catalog

    rows = {row["id"]: row for row in harness_catalog()}
    assert "claude-sdk" in SLIM_PICKER_HARNESSES
    assert rows["claude-sdk"]["label"] == "Claude Code"
    assert rows["claude-sdk"]["capabilities"]["effort"] == "anthropic"


def test_no_word_sdk_where_people_see_it() -> None:
    web = ROOT / "web/src"
    assert '"claude-sdk": "Claude Code"' in (web / "lib/agentLabels.ts").read_text()
    assert (
        'if (name === "claude-code") return "Claude Code";'
        in (web / "lib/agentLabels.ts").read_text()
    )
    assert 'startsWith("claude_sdk_")' in (web / "lib/nativeCodingAgents.ts").read_text()
    executor = (ROOT / "omnigent/inner/claude_sdk_executor.py").read_text()
    assert "Claude SDK session crashed" not in executor
    assert "Claude SDK connect failed: {exc}" not in executor


def test_sessions_get_no_repl_terminal_tab() -> None:
    from omnigent.server.routes._sessions.helpers import _repl_terminal_ui_labels
    from omnigent.slim_policy import SLIM_REPL_TERMINAL

    assert SLIM_REPL_TERMINAL is False
    assert _repl_terminal_ui_labels(agent=None, agent_cache=object(), harness_override=None) == {}
    assert "SLIM_REPL_TERMINAL  # omnigent-slim" in (ROOT / "omnigent/runner/app.py").read_text()


def test_claude_code_is_ready_whenever_the_cli_is(monkeypatch: pytest.MonkeyPatch) -> None:
    """No "isn't configured, run omni setup" banner when the CLI is signed in."""
    from omnigent.onboarding import harness_readiness as hr

    monkeypatch.setattr(
        hr, "_harness_availability", lambda h: True if h == "claude-native" else "needs-auth"
    )
    monkeypatch.setattr(hr, "tmux_unavailable_reason", lambda: None)
    assert hr.configured_harness_map()["claude-sdk"] is True


def test_a_picked_mode_reaches_claude_code() -> None:
    from omnigent.server.schemas import CreateResponseRequest

    assert (
        CreateResponseRequest(
            model="claude-code", input="hi", permission_mode="plan"
        ).permission_mode
        == "plan"
    )
    adapter = (ROOT / "omnigent/runtime/harnesses/_executor_adapter.py").read_text()
    assert 'extra["permission_mode"] = request.permission_mode' in adapter
    runner = (ROOT / "omnigent/runner/app.py").read_text()
    assert "_session_permission_mode[conversation_id] = cast(str, mode)" in runner
    assert 'harness_body["permission_mode"] = _session_permission_mode[conv]' in runner
    executor = (ROOT / "omnigent/inner/claude_sdk_executor.py").read_text()
    assert "new_mode = slim_sdk_permission_mode(requested_mode)" in executor
    assert "or mode_changed or" in executor
    # The picker never offers a bypass: the server checks against the slim list.
    routes = (ROOT / "omnigent/server/routes/sessions/routes_core.py").read_text()
    assert "allowed_permission_modes = tuple(ALLOWED_CLAUDE_PERMISSION_MODES)" in routes


def test_the_viewer_reads_claude_code_session_files() -> None:
    """The agent has no os_env, yet views and artifacts must load, not 404 (D-175)."""
    routes = (ROOT / "omnigent/runner/resource_routes.py").read_text()
    assert 'and spec.executor.config.get("harness") == "claude-sdk"' in routes


def test_flown_demos_start_on_sonnet(tmp_path: Path) -> None:
    from omnigent import slim_policy

    demo = tmp_path / "workspace" / "demos" / "problem-discovery"
    assert slim_policy.is_demo_workspace(str(demo))
    assert slim_policy.slim_new_session_model(str(demo)) == "claude-sonnet-5-5"
    assert slim_policy.slim_new_session_model(str(tmp_path / "workspace")) is None
    assert slim_policy.slim_new_session_model(None) is None
    orchestration = (ROOT / "omnigent/server/routes/_sessions/orchestration.py").read_text()
    assert "model_override = slim_new_session_model(canonical_workspace)" in orchestration
