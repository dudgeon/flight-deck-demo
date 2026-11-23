"""Make sure the running local server has the omnigent-slim project.

``start.sh`` runs ``python -m omnigent.slim_bootstrap`` after the server is up.
It creates (once) a project named ``OMNIGENT_SLIM_PROJECT`` whose sessions run
in ``OMNIGENT_SLIM_WORKSPACE`` on this machine with the Claude Code agent, so
Library Start buttons and the "New session" button land in the workspace folder.
It also creates a "Hangar" project in the same folder for the Hangar's guided
builds (``OMNIGENT_SLIM_HANGAR_PROJECT``).
An existing project of that name is left as the user configured it, with one
exception (D-111): when its folder is the ``workspace`` of another copy of the
app (for example a download that setup.sh has since installed into
~/flight-deck), it is moved to this copy's workspace. A folder the person
chose themselves is never another copy's workspace, so it is never touched.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import httpx

DEFAULT_URL = "http://127.0.0.1:6767"
DEFAULT_PROJECT = "Workspace"
HANGAR_PROJECT = "Hangar"
#: The agent every session runs (D-173); see omnigent/slim_agents/claude-code.
CLAUDE_AGENT_NAME = "claude-code"


def _wait_for_local_host(client: httpx.Client, timeout_s: float = 30.0) -> str:
    deadline = time.monotonic() + timeout_s
    while True:
        hosts = client.get("/v1/hosts").json().get("hosts", [])
        online = [
            host
            for host in hosts
            if host.get("owner") == "local" and host.get("status") == "online"
        ]
        if online:
            return str(online[0]["host_id"])
        if time.monotonic() > deadline:
            raise RuntimeError("no local host registered with the server")
        time.sleep(1)


def _claude_agent_id(client: httpx.Client) -> str | None:
    for agent in client.get("/v1/agents").json().get("data", []):
        if agent.get("name") == CLAUDE_AGENT_NAME:
            return str(agent["id"])
    return None


def _other_app_workspace(stored: str, workspace: Path) -> bool:
    """True when ``stored`` is the ``workspace`` folder of another app copy."""
    if not stored:
        return False
    path = Path(stored).expanduser()
    try:
        if path.resolve() == workspace.resolve():
            return False
    except OSError:
        return False
    app = path.parent
    return path.name == "workspace" and (app / "start.sh").is_file() and (
        app / "omnigent" / "slim_bootstrap.py"
    ).is_file()


def ensure_project(base_url: str, name: str, workspace: Path, icon: str = "🗂️") -> str:
    """Create the project if missing; return a one-line status."""
    with httpx.Client(base_url=base_url, timeout=15.0) as client:
        projects = client.get("/v1/projects", params={"limit": 200}).json().get("data", [])
        existing = next((p for p in projects if p.get("name") == name), None)
        if existing is not None:
            config = dict(existing.get("config") or {})
            stored = str(config.get("workspace") or "")
            # Projects made before D-173 point at the terminal agent; move them over.
            agent_id = _claude_agent_id(client)
            if agent_id and config.get("agent_id") != agent_id:
                config["agent_id"] = agent_id
                client.patch(
                    f"/v1/projects/{existing['id']}", json={"config": config}
                ).raise_for_status()
            if _other_app_workspace(stored, workspace):
                config["workspace"] = str(workspace)
                client.patch(
                    f"/v1/projects/{existing['id']}", json={"config": config}
                ).raise_for_status()
                return f"moved project '{name}' from {stored} to {workspace}"
            return f"project '{name}' already exists"
        config: dict[str, object] = {
            "host_id": _wait_for_local_host(client),
            "workspace": str(workspace),
            "use_worktree": False,
            "icon": icon,
        }
        agent_id = _claude_agent_id(client)
        if agent_id:
            config["agent_id"] = agent_id
        response = client.post("/v1/projects", json={"name": name, "config": config})
        response.raise_for_status()
        return f"created project '{name}' in {workspace}"


def repoint_orphaned_projects(base_url: str) -> list[str]:
    """Point every project whose agent no longer exists at the Claude Code agent.

    Projects made before D-173 (flown demos, ones the person made) can name the
    old terminal agent, which is gone, so their new sessions would fail. A
    project whose agent still exists is left as it is. Returns the names moved.
    """
    moved: list[str] = []
    with httpx.Client(base_url=base_url, timeout=15.0) as client:
        agent_id = _claude_agent_id(client)
        if not agent_id:
            return moved
        known = {str(a["id"]) for a in client.get("/v1/agents").json().get("data", [])}
        projects = client.get("/v1/projects", params={"limit": 200}).json().get("data", [])
        for project in projects:
            config = dict(project.get("config") or {})
            current = config.get("agent_id")
            if not current or str(current) in known:
                continue
            config["agent_id"] = agent_id
            client.patch(f"/v1/projects/{project['id']}", json={"config": config}).raise_for_status()
            moved.append(str(project.get("name")))
    return moved


def main() -> int:
    workspace = Path(os.environ.get("OMNIGENT_SLIM_WORKSPACE", "workspace")).expanduser().resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    # Put back skill links that an unzip flattened into files (D-172).
    from omnigent.slim_skills import repair_skill_links

    fixed = repair_skill_links()
    if fixed:
        print(f"repaired {len(fixed)} skill links")
    url = os.environ.get("OMNIGENT_SLIM_URL", DEFAULT_URL).rstrip("/")
    try:
        print(
            ensure_project(
                url, os.environ.get("OMNIGENT_SLIM_PROJECT", DEFAULT_PROJECT), workspace
            )
        )
        # The Hangar's guided builds run in a project of their own, in the same
        # folder, so builder sessions stay out of the flying project (D-43).
        print(
            ensure_project(
                url, os.environ.get("OMNIGENT_SLIM_HANGAR_PROJECT", HANGAR_PROJECT), workspace, "🛠️"
            )
        )
    except Exception as error:  # report and carry on: the UI still works without it
        print(f"could not set up the project: {error}", file=sys.stderr)
        return 1
    try:
        moved = repoint_orphaned_projects(url)
        if moved:
            print(f"moved {len(moved)} projects to the Claude Code agent: {', '.join(moved)}")
    except Exception as error:
        print(f"could not check the other projects: {error}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
