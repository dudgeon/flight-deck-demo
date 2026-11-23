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
    assert 'OMNIGENT_BUILTIN_AGENT_DIRS="${OMNIGENT_BUILTIN_AGENT_DIRS:-$ROOT/omnigent/slim_agents/claude-code}"' in start
    assert 'OMNIGENT_SEEDED_AGENTS="${OMNIGENT_SEEDED_AGENTS-}"' in start


def test_claude_code_keeps_its_own_tools() -> None:
    tools = slim_policy.slim_sdk_tools(["Skill", "ToolSearch", "Bash"])
    for name in ("Bash", "Read", "Edit", "Write", "Glob", "Grep", "Skill", "ToolSearch"):
        assert tools.count(name) == 1
    assert not any(name.startswith("Web") for name in tools)  # offline


@pytest.mark.parametrize(
    ("asked", "runs"),
    [(None, slim_policy.DEFAULT_CLAUDE_PERMISSION_MODE), ("default", "default"),
     ("bypassPermissions", "default"), ("dontAsk", "default")],
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


def test_existing_projects_move_to_the_new_agent(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    patched: list[dict] = []
    transport = _fake_server(
        [{"id": "p1", "name": "Workspace", "config": {"agent_id": "old", "workspace": str(tmp_path)}}],
        patched,
    )
    real = httpx.Client
    monkeypatch.setattr(slim_bootstrap.httpx, "Client", lambda **kw: real(transport=transport, **kw))
    slim_bootstrap.ensure_project("http://x", "Workspace", tmp_path)
    assert patched and patched[0]["config"]["agent_id"] == "new"
