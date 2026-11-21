"""Install or update an omnigent-slim folder from a newly downloaded copy (D-111).

    python3 -I scripts/install_sync.py SOURCE DEST [--dry-run]

SOURCE is the unzipped download. DEST is the install folder (by default
~/flight-deck). setup.sh runs this with the bundled Python; it uses only the
standard library.

The rule: a newer download never overwrites anything the person made or
changed. DEST/.install-manifest.json records a hash of every file the last
install shipped, so each file falls into one of these cases:

  - Only in DEST, never shipped              the person's own file: untouched
  - Shipped, unchanged since, new version    replaced with the new version
  - Shipped, changed by the person           theirs is kept; the new version is
                                             saved under updates/<time>/new-versions/
                                             (app code outside workspace/ is the
                                             exception: it is replaced, and their
                                             copy saved under updates/<time>/replaced/)
  - Shipped, deleted by the person           stays deleted in workspace/;
                                             restored elsewhere (the app needs it)
  - No longer shipped, unchanged             removed
  - No longer shipped, changed               kept

Without a manifest (the first install into an existing folder), every file
that differs from the download counts as changed by the person.

Prints a short summary for setup.sh, and writes the details into the report
named by --report.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path

MANIFEST = ".install-manifest.json"
# Never copied, compared or removed: runtime state, the person's drafts and
# demos, and setup's own output.
SKIP_DIRS = {".git", ".runtime", "__pycache__", "node_modules"}
SKIP_PREFIXES = ("updates/", "workspace/.hangar/", "workspace/demos/")
SKIP_FILES = {MANIFEST, "setup-report.txt", ".DS_Store"}
PERSON_AREA = "workspace/"


def _skipped(rel: str) -> bool:
    parts = rel.split("/")
    if any(p in SKIP_DIRS for p in parts[:-1]) or parts[-1] in SKIP_FILES:
        return True
    if parts[-1].startswith(".setup-"):
        return True
    return rel.startswith(SKIP_PREFIXES)


def _walk(root: Path) -> dict[str, Path]:
    files: dict[str, Path] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
        rel_dir = "" if rel_dir == "." else rel_dir + "/"
        keep = []
        for d in dirnames:
            full = Path(dirpath, d)
            if full.is_symlink():  # a symlinked folder is copied as a link
                filenames.append(d)
            elif d not in SKIP_DIRS and not (rel_dir + d + "/").startswith(SKIP_PREFIXES):
                keep.append(d)
        dirnames[:] = keep
        for name in filenames:
            rel = rel_dir + name
            if not _skipped(rel):
                files[rel] = Path(dirpath, name)
    return files


def _digest(path: Path) -> str | None:
    if path.is_symlink():
        return "link:" + os.readlink(path)
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.is_symlink() or dst.exists():
        if dst.is_dir() and not dst.is_symlink():
            shutil.rmtree(dst)
        else:
            dst.unlink()
    if src.is_symlink():
        os.symlink(os.readlink(src), dst)
    else:
        shutil.copy2(src, dst)


def sync(source: Path, dest: Path, dry_run: bool = False) -> dict[str, list[str]]:
    src_files = _walk(source)
    manifest_path = dest / MANIFEST
    try:
        old: dict[str, str] = json.loads(manifest_path.read_text())["files"]
    except (OSError, ValueError, KeyError):
        old = {}
    stamp = time.strftime("%Y-%m-%d-%H%M%S")
    saved = dest / "updates" / stamp
    out: dict[str, list[str]] = {
        k: []
        for k in ("added", "updated", "kept_yours", "replaced_yours", "removed", "kept_removed", "kept_deleted")
    }
    new: dict[str, str] = {}

    for rel, src in sorted(src_files.items()):
        new_hash = _digest(src)
        if new_hash is None:
            continue
        new[rel] = new_hash
        dst = dest / rel
        cur = _digest(dst) if (dst.exists() or dst.is_symlink()) else None
        was = old.get(rel)
        if cur == new_hash:
            continue
        if cur is None:
            if was is not None and rel.startswith(PERSON_AREA):
                out["kept_deleted"].append(rel)  # they deleted it; respect that
                continue
            out["added"].append(rel)
            if not dry_run:
                _copy(src, dst)
        elif cur == was:
            out["updated"].append(rel)
            if not dry_run:
                _copy(src, dst)
        elif rel.startswith(PERSON_AREA):
            out["kept_yours"].append(rel)
            if not dry_run:
                _copy(src, saved / "new-versions" / rel)
        else:
            out["replaced_yours"].append(rel)
            if not dry_run:
                _copy(dst, saved / "replaced" / rel)
                _copy(src, dst)

    for rel, was in sorted(old.items()):
        if rel in new:
            continue
        dst = dest / rel
        if not (dst.exists() or dst.is_symlink()):
            continue
        if _digest(dst) == was:
            out["removed"].append(rel)
            if not dry_run:
                dst.unlink()
        else:
            out["kept_removed"].append(rel)

    if not dry_run:
        manifest_path.write_text(
            json.dumps({"installed": stamp, "source": str(source), "files": new}, indent=0)
        )
    out["saved_to"] = [str(saved)] if (out["kept_yours"] or out["replaced_yours"]) else []
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", type=Path)
    parser.add_argument("dest", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report", type=Path, help="append the full file lists here")
    args = parser.parse_args()
    source, dest = args.source.resolve(), args.dest.resolve()
    if source == dest:
        print("source and destination are the same folder", file=sys.stderr)
        return 2
    first = not (dest / MANIFEST).exists() and not (dest / "start.sh").exists()
    dest.mkdir(parents=True, exist_ok=True)
    out = sync(source, dest, args.dry_run)

    labels = {
        "added": "new files added",
        "updated": "files updated",
        "removed": "old files removed",
        "kept_yours": "files you changed in workspace kept as yours (the new versions are saved for you)",
        "replaced_yours": "app files you had changed replaced (your copies saved)",
        "kept_removed": "files no longer shipped but changed by you, kept",
        "kept_deleted": "files you deleted from workspace left deleted",
    }
    if first:
        print(f"INSTALLED {len(out['added'])} files")
    elif not any(out[k] for k in labels):
        print("UNCHANGED this download matches what is installed")
    for key, label in labels.items():
        if out[key] and not (first and key == "added"):
            print(f"{key.upper()} {len(out[key])} {label}")
    if out["saved_to"]:
        print(f"SAVED {out['saved_to'][0]}")
    if args.report:
        with args.report.open("a") as rep:
            for key, label in labels.items():
                if out[key] and not (first and key == "added"):
                    rep.write(f"        {label}:\n")
                    for rel in out[key][:200]:
                        rep.write(f"          {rel}\n")
                    if len(out[key]) > 200:
                        rep.write(f"          ... and {len(out[key]) - 200} more\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
