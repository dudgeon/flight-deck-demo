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
