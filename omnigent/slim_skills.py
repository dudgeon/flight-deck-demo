"""
omnigent-slim: skills shipped in the repo, available in every session.

Every native Claude (and Codex) launch already gets a skill bundle that
Omnigent passes to Claude Code as ``--plugin-dir``; upstream links its own
skills (``build-omnigent``, ``workflow``) into it in
``_ensure_orchestrator_skills_in_bundle``. This module links each skill
folder under the repo's ``skills/`` directory into that same bundle, so a
skill committed to the repo shows up in every session without touching the
user's ``~/.claude``.

Set ``OMNIGENT_SLIM_SKILLS_DIR`` to use a different folder.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

_logger = logging.getLogger(__name__)

#: Repo-root ``skills/`` (the package is installed editable from the checkout).
DEFAULT_SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"


def slim_skills_dir() -> Path:
    """Return the folder whose subfolders are bundled skills."""
    configured = os.environ.get("OMNIGENT_SLIM_SKILLS_DIR", "").strip()
    return Path(configured).expanduser() if configured else DEFAULT_SKILLS_DIR


def slim_skill_sources() -> dict[str, Path]:
    """Map skill folder name to source path, e.g. ``{"omnigent-operator": ...}``.

    A folder counts as a skill when it holds a ``SKILL.md``.
    """
    root = slim_skills_dir()
    if not root.is_dir():
        return {}
    return {
        entry.name: entry
        for entry in sorted(root.iterdir())
        if entry.is_dir() and not entry.name.startswith(".") and (entry / "SKILL.md").is_file()
    }


def link_slim_skills(bundle_dir: Path) -> None:
    """Link the repo's skills into ``<bundle_dir>/skills/``.

    Skills the bundle already has under the same name win (an agent's own
    skill, or an upstream one). Links left over from a skill that has since
    been removed from the repo are cleaned up, so a reused bundle stays
    current. Best-effort: failures are logged and never block a launch.
    """
    root = slim_skills_dir().resolve()
    skills_dir = bundle_dir / "skills"
    sources = slim_skill_sources()
    if skills_dir.is_dir():
        for entry in skills_dir.iterdir():
            # Only ever remove our own links: ones pointing into the repo skills folder.
            if not entry.is_symlink() or entry.name in sources:
                continue
            try:
                target = Path(os.readlink(entry))
                if not target.is_absolute():
                    target = entry.parent / target
                if target.parent.resolve() == root:
                    entry.unlink()
            except OSError:
                _logger.debug("Could not check bundle skill link %s", entry, exc_info=True)
    for name, source in sources.items():
        target_dir = skills_dir / name
        try:
            if target_dir.exists() or target_dir.is_symlink():
                continue
            skills_dir.mkdir(parents=True, exist_ok=True)
            target_dir.symlink_to(source.resolve(), target_is_directory=True)
        except OSError:
            _logger.debug("Could not link the %s skill into the bundle", name, exc_info=True)


#: Repo root, where ``.claude/skills/<name>`` links to ``skills/<name>`` (D-172).
REPO_ROOT = Path(__file__).resolve().parent.parent


def repair_skill_links(repo_root: Path = REPO_ROOT) -> list[str]:
    """Make sure ``.claude/skills/<name>`` links to ``skills/<name>`` for every skill.

    Claude Code finds the skills through these committed links. Some unzip
    tools turn a link into a small text file holding the link's target, which
    would leave every session without its skills, so start.sh's bootstrap
    puts each one back. A real folder there (a contributor skill such as
    ``docs-refresh``) is never touched. Returns the names it repaired.
    """
    skills_root = repo_root / "skills"
    links_dir = repo_root / ".claude" / "skills"
    repaired: list[str] = []
    if not skills_root.is_dir():
        return repaired
    for entry in sorted(skills_root.iterdir()):
        if not entry.is_dir() or not (entry / "SKILL.md").is_file():
            continue
        link = links_dir / entry.name
        want = f"../../skills/{entry.name}"
        try:
            if link.is_symlink():
                if os.readlink(link) == want:
                    continue
                link.unlink()
            elif link.is_dir():
                continue
            elif link.exists():
                if link.stat().st_size > 256:
                    continue  # not a flattened link: leave it alone
                link.unlink()
            links_dir.mkdir(parents=True, exist_ok=True)
            link.symlink_to(want, target_is_directory=True)
            repaired.append(entry.name)
        except OSError:
            _logger.debug("Could not repair the %s skill link", entry.name, exc_info=True)
    return repaired
