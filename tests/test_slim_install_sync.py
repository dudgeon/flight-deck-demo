"""Updates from a newer download keep what the person made (D-111)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_sync():
    spec = importlib.util.spec_from_file_location("install_sync", ROOT / "scripts/install_sync.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["install_sync"] = module
    spec.loader.exec_module(module)
    return module


sync_mod = _load_sync()


def _write(root: Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)


RELEASE_1 = {
    "start.sh": "start 1",
    "omnigent/app.py": "app 1",
    "workspace/participants/mara.md": "mara 1",
    "workspace/participants/risk.md": "risk 1",
    "workspace/frameworks/intent.md": "intent 1",
    "workspace/context/old.md": "old 1",
}


def _install(tmp_path: Path) -> tuple[Path, Path]:
    r1, app = tmp_path / "r1", tmp_path / "app"
    _write(r1, RELEASE_1)
    out = sync_mod.sync(r1, app)
    assert sorted(out["added"]) == sorted(RELEASE_1)
    assert json.loads((app / sync_mod.MANIFEST).read_text())["files"].keys() == RELEASE_1.keys()
    return r1, app


def test_update_keeps_what_the_person_made(tmp_path: Path) -> None:
    _, app = _install(tmp_path)
    # The person works in the app folder.
    _write(app, {
        "workspace/context/mine.md": "mine",
        "workspace/participants/mara.md": "my mara",
        "omnigent/app.py": "patched by hand",
        ".runtime/venv/marker": "runtime",
        "workspace/.hangar/draft.json": "{}",
    })
    (app / "workspace/frameworks/intent.md").unlink()

    r2 = tmp_path / "r2"
    release_2 = dict(RELEASE_1)
    release_2.update({
        "start.sh": "start 2",
        "omnigent/app.py": "app 2",
        "workspace/participants/mara.md": "mara 2",
        "workspace/participants/risk.md": "risk 2",
        "workspace/frameworks/intent.md": "intent 2",
        "workspace/context/new.md": "new 2",
    })
    del release_2["workspace/context/old.md"]
    _write(r2, release_2)
    out = sync_mod.sync(r2, app)

    read = lambda rel: (app / rel).read_text()  # noqa: E731
    assert read("workspace/context/mine.md") == "mine"
    assert read("workspace/.hangar/draft.json") == "{}"
    assert read(".runtime/venv/marker") == "runtime"
    assert read("workspace/participants/mara.md") == "my mara"
    saved = Path(out["saved_to"][0])
    assert (saved / "new-versions/workspace/participants/mara.md").read_text() == "mara 2"
    assert read("workspace/participants/risk.md") == "risk 2"
    assert not (app / "workspace/frameworks/intent.md").exists()
    assert not (app / "workspace/context/old.md").exists()
    assert read("workspace/context/new.md") == "new 2"
    # App code is always the release's; a hand edit is saved, not lost.
    assert read("omnigent/app.py") == "app 2"
    assert (saved / "replaced/omnigent/app.py").read_text() == "patched by hand"
    assert read("start.sh") == "start 2"
    assert out["kept_yours"] == ["workspace/participants/mara.md"]
    assert out["kept_deleted"] == ["workspace/frameworks/intent.md"]
    assert out["removed"] == ["workspace/context/old.md"]


def test_same_download_twice_changes_nothing(tmp_path: Path) -> None:
    r1, app = _install(tmp_path)
    out = sync_mod.sync(r1, app)
    assert not any(out[k] for k in out if k != "saved_to")


def test_removed_file_the_person_changed_is_kept(tmp_path: Path) -> None:
    _, app = _install(tmp_path)
    _write(app, {"workspace/context/old.md": "I edited this"})
    r2 = tmp_path / "r2"
    release_2 = {k: v for k, v in RELEASE_1.items() if k != "workspace/context/old.md"}
    _write(r2, release_2)
    out = sync_mod.sync(r2, app)
    assert (app / "workspace/context/old.md").read_text() == "I edited this"
    assert out["kept_removed"] == ["workspace/context/old.md"]


def test_first_install_over_an_existing_folder_keeps_differences(tmp_path: Path) -> None:
    r1, app = tmp_path / "r1", tmp_path / "app"
    _write(r1, RELEASE_1)
    _write(app, {"workspace/participants/mara.md": "edited before any manifest"})
    sync_mod.sync(r1, app)
    assert (app / "workspace/participants/mara.md").read_text() == "edited before any manifest"


def test_symlinks_are_copied_as_links(tmp_path: Path) -> None:
    r1, app = tmp_path / "r1", tmp_path / "app"
    _write(r1, {"AGENTS.md": "guide"})
    (r1 / "CLAUDE.md").symlink_to("AGENTS.md")
    sync_mod.sync(r1, app)
    assert (app / "CLAUDE.md").is_symlink() and (app / "CLAUDE.md").read_text() == "guide"


def test_project_moves_only_from_another_app_copy(tmp_path: Path) -> None:
    from omnigent.slim_bootstrap import _other_app_workspace

    old_app = tmp_path / "Downloads/omnigent-slim-main"
    _write(old_app, {"start.sh": "", "omnigent/slim_bootstrap.py": "", "workspace/x": ""})
    new_ws = tmp_path / "flight-deck/workspace"
    new_ws.mkdir(parents=True)
    chosen = tmp_path / "my-project"
    chosen.mkdir()
    assert _other_app_workspace(str(old_app / "workspace"), new_ws)
    assert not _other_app_workspace(str(new_ws), new_ws)
    assert not _other_app_workspace(str(chosen), new_ws)  # the person's own folder
    assert not _other_app_workspace("", new_ws)
