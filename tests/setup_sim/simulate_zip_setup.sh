#!/bin/sh
# Rehearse the work-Mac install in a Linux cloud container (D-100, D-107).
# Never run this on the work Mac: it is a test rig, and it downloads things.
#
#   tests/setup_sim/simulate_zip_setup.sh ZIP SCENARIO
#
# ZIP is a ZIP of the repository as GitHub serves it, for example
#   git archive --format=zip --prefix=omnigent-slim-main/ -o /tmp/main.zip HEAD
# SCENARIO is one of:
#   happy        browser download: quarantined, execute bits lost, path with a
#                space; setup must clear both and serve the app on port 6767
#   no-claude    Claude Code missing: setup must stop and say so
#   locked       quarantine can't be removed (managed Mac): stop and say so
#   killed       macOS kills the bundled tmux: stop and say so
#   incomplete   a half-unzipped folder: stop and say so
#
# What is simulated, and how:
# - macOS itself: shims for uname (Darwin, arm64), sw_vers, sysctl, open and
#   xattr (which stores com.apple.quarantine as a Linux user xattr).
# - A browser download unzipped by Archive Utility: every file gets the
#   quarantine flag. Extracting with Python's zipfile drops the execute bits,
#   the other thing a careless unzip does.
# - Apple-silicon binaries can't run here, so only those are swapped for Linux
#   twins: the bundled Python (same version, 3.12.16), the platform wheels
#   (same versions, plus the few dependencies only Linux needs) and tmux. setup.sh, start.sh and everything else are the
#   files from the ZIP, unchanged.
#
# Needs network the first time, to fetch the Linux twins into SIM_CACHE.
set -eu

ZIP=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
SCENARIO=${2:-happy}
HERE=$(cd "$(dirname "$0")" && pwd)
CACHE=${SIM_CACHE:-${TMPDIR:-/tmp}/omnigent-slim-sim-cache}
WORK=${SIM_WORK:-${TMPDIR:-/tmp}/omnigent-slim-sim}/$SCENARIO
PBS=https://github.com/astral-sh/python-build-standalone/releases/download/20261110/cpython-3.12.16+20261110-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz

# 1. Linux twins of the Apple-silicon parts (cached).
mkdir -p "$CACHE/wheels"
if [ ! -f "$CACHE/cpython-linux.tar.gz" ]; then
    curl -fsSL -o "$CACHE/cpython-linux.tar.gz" "$PBS"
fi
if [ ! -x "$CACHE/py/python/bin/python3" ]; then
    mkdir -p "$CACHE/py"; tar -xzf "$CACHE/cpython-linux.tar.gz" -C "$CACHE/py"
fi
PY="$CACHE/py/python/bin/python3"

# 2. A fresh fake home and Downloads folder, with a space in the path.
rm -rf "$WORK"
mkdir -p "$WORK/home/Desktop" "$WORK/home/My Downloads" "$WORK/shims"
export HOME="$WORK/home"
DL="$HOME/My Downloads"
"$PY" - "$ZIP" "$DL" <<'EOF'
import sys, zipfile
zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])   # drops execute bits
EOF
APP="$DL/omnigent-slim-main"

# Platform wheels: replace the macOS ones with the same versions for Linux.
if [ ! -f "$CACHE/wheels/.done" ]; then
    # Every bundled package at its bundled version, resolved for Linux. This
    # also brings in dependencies that only Linux needs (keyring's
    # SecretStorage, SQLAlchemy's greenlet); macOS never needs them.
    ls "$APP/vendor/wheels" | "$PY" -c '
import sys
pins = {}
for l in sorted(sys.stdin):          # two versions of one package: keep the newer
    n, v = l.split("-")[:2]
    pins[n.replace("_", "-").lower()] = v
print("\n".join(n + "==" + v for n, v in pins.items()))' > "$CACHE/reqs.txt"
    "$PY" -m pip download -q --disable-pip-version-check --only-binary=:all: \
        -r "$CACHE/reqs.txt" -d "$CACHE/wheels"
    touch "$CACHE/wheels/.done"
fi
find "$APP/vendor/wheels" -name '*.whl' ! -name '*none-any.whl' -delete
for w in "$CACHE"/wheels/*.whl; do
    case $w in *none-any.whl) [ -e "$APP/vendor/wheels/$(basename "$w")" ] && continue ;; esac
    cp "$w" "$APP/vendor/wheels/"
done
cp "$CACHE/cpython-linux.tar.gz" "$APP"/vendor/python/cpython-*-aarch64.tar.gz
printf '#!/bin/sh\nexec /usr/bin/tmux "$@"\n' > "$APP/vendor/bin/tmux"
chmod -x "$APP/vendor/bin/tmux"   # as the unzip left it

# 3. macOS shims.
S="$WORK/shims"
cat > "$S/uname" <<'EOF'
#!/bin/sh
case "${1:-}" in -s) echo Darwin ;; -m) echo arm64 ;; *) exec /bin/uname "$@" ;; esac
EOF
printf '#!/bin/sh\necho 14.6\n' > "$S/sw_vers"
printf '#!/bin/sh\necho 0\n' > "$S/sysctl"
printf '#!/bin/sh\necho "(open $*)"\n' > "$S/open"
cat > "$S/xattr" <<EOF
#!/bin/sh
# xattr -p NAME FILE | -dr NAME DIR | -w NAME VALUE FILE
exec "$PY" - "\$@" <<'PYEOF'
import os, sys
a = sys.argv[1:]
key = lambda n: "user." + n
try:
    if a[0] == "-p":
        sys.stdout.write(os.getxattr(a[2], key(a[1])).decode() + "\n")
    elif a[0] == "-w":
        for f in a[3:]:
            os.setxattr(f, key(a[1]), a[2].encode())
    elif a[0] in ("-d", "-dr"):
        if os.environ.get("SIM_XATTR_LOCKED"):
            sys.exit("xattr: [Errno 1] Operation not permitted: " + a[2])
        paths = [a[2]]
        if a[0] == "-dr":
            for d, ds, fs in os.walk(a[2]):
                paths += [os.path.join(d, x) for x in ds + fs]
        for p in paths:
            try: os.removexattr(p, key(a[1]), follow_symlinks=False)
            except OSError: pass
except OSError as e:
    sys.exit("xattr: %s" % e)
PYEOF
EOF
cat > "$S/claude" <<'EOF'
#!/bin/sh
[ "${1:-}" = --version ] && { echo "2.1.0 (Claude Code)"; exit 0; }
echo "claude shim: sessions are not exercised by this rig" >&2; exit 1
EOF
chmod +x "$S"/*
mkdir -p "$HOME/.claude"
BASE_PATH="$S:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# 4. The browser's quarantine flag on every file (Archive Utility passes it on).
find "$APP" -type f -exec "$S/xattr" -w com.apple.quarantine '0083;6740a1b2;Safari;' {} +

# 5. Scenario tweaks.
case $SCENARIO in
    happy|locked) ;;
    no-claude) rm "$S/claude"; BASE_PATH="$S:/usr/sbin:/usr/bin:/sbin:/bin" ;;
    killed) printf '#!/bin/sh\nkill -9 $$\n' > "$APP/vendor/bin/tmux" ;;
    incomplete) rm -rf "$APP/vendor/wheels" ;;
    *) echo "unknown scenario: $SCENARIO" >&2; exit 2 ;;
esac
[ "$SCENARIO" = locked ] && export SIM_XATTR_LOCKED=1

# 6. Run it the way the README says: cd into the folder, sh setup.sh.
echo "=== scenario: $SCENARIO   folder: $APP"
set +e
(cd "$APP" && env -i HOME="$HOME" PATH="$BASE_PATH" TERM=dumb \
    ${SIM_XATTR_LOCKED:+SIM_XATTR_LOCKED=1} sh setup.sh --yes --no-open)
rc=$?
set -e
echo "=== setup.sh exit code: $rc"
echo "=== report on the Desktop: $(ls "$HOME/Desktop")"
echo "$rc" > "$WORK/exit-code"
echo "$APP" > "$WORK/app-path"
