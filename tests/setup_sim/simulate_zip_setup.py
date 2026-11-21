"""Rehearse the work-Mac install and update in a Linux cloud container.

    python3 tests/setup_sim/simulate_zip_setup.py ZIP [SCENARIO ...]

Never run this on the work Mac: it is a test rig, and it downloads things.

ZIP is a ZIP of the repository as GitHub serves it, for example
    git archive --format=zip --prefix=omnigent-slim-main/ -o /tmp/main.zip HEAD
With no scenario named, all of them run. Each checks its own expectations and
the rig exits non-zero if any fails.

  install       browser download in ~/Downloads (quarantined, execute bits
                lost): setup installs into ~/flight-deck, serves port 6767
  update        after an install the person adds and edits files; a newer ZIP
                lands in ~/Downloads; `sh ~/flight-deck/setup.sh` updates
                without losing any of it
  moved         the app was first run from the Downloads folder itself
                (--here); setup installs it and moves the Workspace project
  no-claude     Claude Code missing: stop and say so
  locked        the quarantine flag can't be removed: stop and say so
  killed        macOS kills the bundled tmux: stop and say so
  incomplete    a half-unzipped folder: stop and say so

How macOS is simulated: shims for uname (Darwin, arm64), sw_vers, sysctl,
open and xattr (com.apple.quarantine stored as a Linux user xattr). Extracting
with Python's zipfile drops execute bits, as a careless unzip does. The
Apple-silicon binaries can't run here, so only those are swapped for Linux
twins of the same versions: the bundled Python (3.12.16), the platform wheels
(plus the few dependencies only Linux needs) and tmux. setup.sh, start.sh,
install_sync.py and everything else are the files from the ZIP, unchanged.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request
import zipfile
from pathlib import Path

PBS = (
    "https://github.com/astral-sh/python-build-standalone/releases/download/20261110/"
    "cpython-3.12.16+20261110-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz"
)
TMP = Path(os.environ.get("TMPDIR", "/tmp"))
CACHE = Path(os.environ.get("SIM_CACHE", TMP / "omnigent-slim-sim-cache"))
WORK = Path(os.environ.get("SIM_WORK", TMP / "omnigent-slim-sim"))
PREFIX = "omnigent-slim-main/"
QUARANTINE = "user.com.apple.quarantine"

SHIMS = {
    "uname": '#!/bin/sh\ncase "${1:-}" in -s) echo Darwin ;; -m) echo arm64 ;; *) exec /bin/uname "$@" ;; esac\n',
    "sw_vers": "#!/bin/sh\necho 14.6\n",
    "sysctl": "#!/bin/sh\necho 0\n",
    "open": '#!/bin/sh\necho "(open $*)"\n',
    "claude": '#!/bin/sh\n[ "${1:-}" = --version ] && { echo "2.1.0 (Claude Code)"; exit 0; }\nexit 1\n',
    "xattr": """#!/usr/bin/env python3
import os, sys
a = sys.argv[1:]
key = "user." + a[1]
try:
    if a[0] == "-p":
        sys.stdout.write(os.getxattr(a[2], key).decode() + "\\n")
    elif a[0] == "-w":
        for f in a[3:]:
            os.setxattr(f, key, a[2].encode())
    elif a[0] in ("-d", "-dr"):
        if os.environ.get("SIM_XATTR_LOCKED"):
            sys.exit("xattr: [Errno 1] Operation not permitted: " + a[2])
        paths = [a[2]]
        if a[0] == "-dr":
            for d, ds, fs in os.walk(a[2]):
                paths += [os.path.join(d, x) for x in ds + fs]
        for p in paths:
            try: os.removexattr(p, key, follow_symlinks=False)
            except OSError: pass
except OSError as e:
    sys.exit("xattr: %s" % e)
""",
}


# ------------------------------------------------------------ twins ----

def linux_python() -> Path:
    tarball = CACHE / "cpython-linux.tar.gz"
    if not tarball.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(PBS, tarball)
    py = CACHE / "py/python/bin/python3"
    if not py.exists():
        with tarfile.open(tarball) as t:
            t.extractall(CACHE / "py", filter="tar")
    return py


def linux_wheels(names: list[str]) -> Path:
    wheels = CACHE / "wheels"
    if not (wheels / ".done").exists():
        wheels.mkdir(parents=True, exist_ok=True)
        pins: dict[str, str] = {}
        for name in sorted(names):  # two versions of one package: keep the newer
            n, v = name.split("-")[:2]
            pins[n.replace("_", "-").lower()] = v
        reqs = CACHE / "reqs.txt"
        reqs.write_text("\n".join(f"{n}=={v}" for n, v in pins.items()) + "\n")
        subprocess.run(
            [str(linux_python()), "-m", "pip", "download", "-q", "--disable-pip-version-check",
             "--only-binary=:all:", "-r", str(reqs), "-d", str(wheels)],
            check=True,
        )
        (wheels / ".done").touch()
    return wheels


def twin_zip(src_zip: Path, out_zip: Path, edit=None) -> None:
    """Rewrite a release ZIP with Linux twins of the Apple-silicon parts."""
    stage = WORK / "_stage"
    shutil.rmtree(stage, ignore_errors=True)
    stage.mkdir(parents=True)
    with zipfile.ZipFile(src_zip) as z:
        z.extractall(stage)
    app = stage / PREFIX.rstrip("/")
    wheel_dir = app / "vendor/wheels"
    cache = linux_wheels([p.name for p in wheel_dir.glob("*.whl")])
    for w in wheel_dir.glob("*.whl"):
        if not w.name.endswith("none-any.whl"):
            w.unlink()
    for w in cache.glob("*.whl"):
        if not (wheel_dir / w.name).exists():
            shutil.copy(w, wheel_dir)
    for t in (app / "vendor/python").glob("cpython-*-aarch64.tar.gz"):
        linux_python()
        shutil.copy(CACHE / "cpython-linux.tar.gz", t)
    (app / "vendor/bin/tmux").write_text('#!/bin/sh\nexec /usr/bin/tmux "$@"\n')
    if edit:
        edit(app)
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_STORED) as z:
        for path in sorted(stage.rglob("*")):
            rel = path.relative_to(stage).as_posix()
            if path.is_symlink():
                info = zipfile.ZipInfo(rel)
                info.external_attr = 0o120777 << 16
                z.writestr(info, os.readlink(path))
            elif path.is_file():
                z.write(path, rel)
    shutil.rmtree(stage)


# ------------------------------------------------------------ a Mac ----

class Mac:
    def __init__(self, name: str):
        self.root = WORK / name
        shutil.rmtree(self.root, ignore_errors=True)
        self.home = self.root / "home"
        self.shims = self.root / "shims"
        for d in (self.home / "Desktop", self.home / "Downloads", self.shims, self.home / ".claude"):
            d.mkdir(parents=True)
        for name, body in SHIMS.items():
            p = self.shims / name
            p.write_text(body)
            p.chmod(0o755)
        self.env = {
            "HOME": str(self.home),
            "PATH": f"{self.shims}:/usr/local/bin:/usr/bin:/bin",
            "TERM": "dumb",
        }
        self.app = self.home / "flight-deck"

    def download(self, zip_path: Path, folder: str = "omnigent-slim-main") -> Path:
        """Unzip like Archive Utility: every file flagged; execute bits lost."""
        target = self.home / "Downloads"
        with zipfile.ZipFile(zip_path) as z:
            for info in z.infolist():
                out = target / info.filename.replace(PREFIX, folder + "/", 1)
                if info.is_dir():
                    out.mkdir(parents=True, exist_ok=True)
                    continue
                out.parent.mkdir(parents=True, exist_ok=True)
                if (info.external_attr >> 16) & 0o170000 == 0o120000:
                    os.symlink(z.read(info).decode(), out)
                    continue
                out.write_bytes(z.read(info))
                os.setxattr(out, QUARANTINE, b"0083;6740a1b2;Safari;")
        return target / folder

    def run(self, *cmd: str, cwd: Path | None = None, extra: dict | None = None) -> tuple[int, str]:
        env = dict(self.env, **(extra or {}))
        p = subprocess.run(list(cmd), cwd=cwd or self.home, env=env, text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=600)
        return p.returncode, p.stdout

    def setup(self, script: Path, *args: str, extra: dict | None = None) -> tuple[int, str]:
        return self.run("sh", str(script), "--yes", "--no-open", *args, extra=extra)

    def stop(self) -> None:
        if (self.app / "stop.sh").exists():
            self.run("sh", str(self.app / "stop.sh"))

    def report(self) -> str:
        p = self.home / "Desktop/flight-deck-setup-report.txt"
        return p.read_text() if p.exists() else ""


def answers() -> bool:
    try:
        urllib.request.urlopen("http://127.0.0.1:6767/", timeout=3)
        return True
    except Exception:
        return False


def projects() -> dict[str, str]:
    req = urllib.request.Request("http://127.0.0.1:6767/v1/projects?limit=200")
    data = json.load(urllib.request.urlopen(req, timeout=5))["data"]
    return {p["name"]: (p.get("config") or {}).get("workspace", "") for p in data}


# ------------------------------------------------------ scenarios ----

class Check:
    def __init__(self, name: str):
        self.name, self.results = name, []

    def __call__(self, what: str, ok: bool) -> None:
        self.results.append((what, bool(ok)))


def s_install(z: Path, c: Check) -> None:
    mac = Mac("install")
    dl = mac.download(z)
    rc, out = mac.setup(dl / "setup.sh")
    c("exit 0", rc == 0)
    c("installed into ~/flight-deck", (mac.app / "start.sh").exists() and (mac.app / ".install-manifest.json").exists())
    c("flag cleared on the download", "Download flag removed" in out)
    c("execute bits restored", "Execute permission restored" in out)
    c("app answers on 6767", answers() and "answers at http://127.0.0.1:6767" in out)
    c("Workspace project in ~/flight-deck/workspace", projects().get("Workspace") == str(mac.app / "workspace"))
    c("report in app folder and on Desktop", (mac.app / "setup-report.txt").exists() and mac.report())
    rc2, out2 = mac.setup(mac.app / "setup.sh")
    c("second run from the app folder starts it", rc2 == 0 and "No newer download" in out2)
    mac.stop()
    print(out)


def s_update(z: Path, c: Check) -> None:
    mac = Mac("update")
    dl = mac.download(z)
    rc, out = mac.setup(dl / "setup.sh")
    c("first install ok", rc == 0)
    ws = mac.app / "workspace"
    # The person works: adds files, edits a shipped one, deletes one.
    (ws / "context/my-notes.md").write_text("mine\n")
    (ws / "artifacts/my-dashboard.html").write_text("<p>mine</p>\n")
    (ws / ".hangar").mkdir(exist_ok=True)
    (ws / ".hangar/draft.json").write_text("{}\n")
    (ws / "participants/mara-okafor.md").write_text("my edit of Mara\n")
    (ws / "frameworks/intent.md").unlink()
    mac.stop()
    time.sleep(1.1)

    def newer(app: Path) -> None:  # what the next release changes
        w = app / "workspace"
        (w / "participants/mara-okafor.md").write_text("Mara, release 2\n")
        (w / "participants/risk-review.md").write_text("Risk review, release 2\n")
        (w / "frameworks/intent.md").write_text("intent, release 2\n")
        (w / "context/platform-map.md").unlink()
        (w / "context/new-in-release-2.md").write_text("new\n")
        (app / "docs/history.md").write_text("history, release 2\n")

    z2 = WORK / "release2.zip"
    twin_zip(ORIGINAL_ZIP, z2, newer)
    shutil.copy(z2, mac.home / "Downloads/omnigent-slim-main (1).zip")
    rc, out = mac.setup(mac.app / "setup.sh")
    print(out)
    c("update exit 0", rc == 0)
    c("found the newer ZIP in Downloads", "Found a newer download" in out)
    c("my new files kept", (ws / "context/my-notes.md").read_text() == "mine\n"
      and (ws / "artifacts/my-dashboard.html").exists() and (ws / ".hangar/draft.json").exists())
    c("my edit kept", (ws / "participants/mara-okafor.md").read_text() == "my edit of Mara\n")
    saved = list((mac.app / "updates").glob("*/new-versions/workspace/participants/mara-okafor.md"))
    c("new version of my edited file saved beside it", saved and saved[0].read_text() == "Mara, release 2\n")
    c("unedited shipped file updated", (ws / "participants/risk-review.md").read_text() == "Risk review, release 2\n")
    c("file I deleted stays deleted", not (ws / "frameworks/intent.md").exists())
    c("file dropped by the release removed", not (ws / "context/platform-map.md").exists())
    c("file new in the release added", (ws / "context/new-in-release-2.md").exists())
    c("app file updated", (mac.app / "docs/history.md").read_text() == "history, release 2\n")
    c("app answers on 6767", answers())
    rc3, out3 = mac.setup(mac.app / "setup.sh")
    c("third run ignores the already-installed ZIP", rc3 == 0 and "No newer download" in out3)
    mac.stop()


def s_moved(z: Path, c: Check) -> None:
    mac = Mac("moved")
    dl = mac.download(z)
    rc, out = mac.setup(dl / "setup.sh", "--here")
    c("old-style run from Downloads ok", rc == 0)
    c("project pointed at the download", projects().get("Workspace") == str(dl / "workspace"))
    (dl / "workspace/context/made-while-in-downloads.md").write_text("mine\n")
    rc, out = mac.setup(dl / "setup.sh")
    print(out)
    c("install exit 0", rc == 0)
    c("stopped the copy running from Downloads", "Stopped the copy running from" in out)
    c("file made in the Downloads copy carried over", (mac.app / "workspace/context/made-while-in-downloads.md").exists())
    p = projects()
    c("Workspace project moved to ~/flight-deck", p.get("Workspace") == str(mac.app / "workspace"))
    c("Hangar project moved too", p.get("Hangar") == str(mac.app / "workspace"))
    mac.stop()


def _failure(name: str, expect: str, prep=None, extra=None):
    def run(z: Path, c: Check) -> None:
        mac = Mac(name)
        dl = mac.download(z)
        if prep:
            prep(mac, dl)
        rc, out = mac.setup(dl / "setup.sh", extra=extra)
        print(out)
        c("exit 1", rc == 1)
        c(f"says: {expect}", expect in out)
        c("report on the Desktop", "Setup stopped here." in mac.report())
        c("nothing running", not answers())
    return run


def _no_claude(mac: Mac, dl: Path) -> None:
    (mac.shims / "claude").unlink()
    mac.env["PATH"] = f"{mac.shims}:/usr/bin:/bin"


def _killed(mac: Mac, dl: Path) -> None:
    (dl / "vendor/bin/tmux").write_text("#!/bin/sh\nkill -9 $$\n")


SCENARIOS = {
    "install": s_install,
    "update": s_update,
    "moved": s_moved,
    "no-claude": _failure("no-claude", "isn't installed, or Terminal can't find it", _no_claude),
    "locked": _failure("locked", "wouldn't let setup remove the download flag", extra={"SIM_XATTR_LOCKED": "1"}),
    "killed": _failure("killed", "stopped the bundled tmux from running", _killed),
    "incomplete": _failure("incomplete", "The folder is incomplete", lambda m, d: shutil.rmtree(d / "vendor/wheels")),
}


def main() -> int:
    global ORIGINAL_ZIP
    ORIGINAL_ZIP = Path(sys.argv[1]).resolve()
    names = sys.argv[2:] or list(SCENARIOS)
    WORK.mkdir(parents=True, exist_ok=True)
    z = WORK / "release1.zip"
    twin_zip(ORIGINAL_ZIP, z)
    failed = 0
    table = []
    for name in names:
        c = Check(name)
        print(f"\n===== {name} =====")
        try:
            SCENARIOS[name](z, c)
        except Exception as error:  # a crash in the rig is a failure too
            c(f"rig error: {error!r}", False)
        table.append(c)
    print("\n===== summary =====")
    for c in table:
        for what, ok in c.results:
            print(f"{'PASS' if ok else 'FAIL'}  {c.name:11} {what}")
            failed += not ok
    print(f"\n{sum(len(c.results) for c in table) - failed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
