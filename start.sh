#!/bin/sh
# Start omnigent-slim: the local server, web UI and host, all on this Mac.
#
#   ./start.sh            set up on first run (offline), start, open the browser
#   ./start.sh --no-open  same, without opening the browser
#   ./stop.sh             stop everything
#
# First run unpacks the bundled Python and installs the bundled wheels into
# .runtime/ (no network). Nothing here downloads anything.
set -eu

ROOT=$(cd "$(dirname "$0")" && pwd)
RUNTIME="$ROOT/.runtime"
VENV="$RUNTIME/venv"
OPEN_BROWSER=1
for arg in "$@"; do
    case $arg in
        --no-open) OPEN_BROWSER=0 ;;
        -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
        *) echo "unknown option: $arg" >&2; exit 2 ;;
    esac
done

die() { echo "omnigent-slim: $*" >&2; exit 1; }

[ "$(uname -s)" = Darwin ] || die "this build runs on macOS only."
[ "$(uname -m)" = arm64 ] || die "this build needs an Apple silicon Mac."
command -v claude >/dev/null 2>&1 || die "Claude Code ('claude') is not on your PATH. Install it and sign in first."
if xattr -p com.apple.quarantine "$ROOT/vendor/bin/tmux" >/dev/null 2>&1; then
    die "macOS has flagged this copy as downloaded from the internet, so it won't
run the bundled tmux and Python. Run the setup script once, which explains the
flag and clears it from this folder (README, step 2):
  sh setup.sh"
fi

# 1. Python runtime and dependencies, rebuilt when the lock or project changes.
stamp=$(cat "$ROOT/uv.lock" "$ROOT/pyproject.toml" | shasum | cut -d' ' -f1)
if [ ! -x "$VENV/bin/python" ] || [ "$(cat "$RUNTIME/stamp" 2>/dev/null)" != "$stamp" ]; then
    echo "Setting up the Python runtime (first run, offline)..."
    rm -rf "$RUNTIME"
    mkdir -p "$RUNTIME"
    tarball=$(ls "$ROOT"/vendor/python/cpython-*-aarch64.tar.gz 2>/dev/null | head -1)
    [ -n "$tarball" ] || die "vendor/python has no Python runtime."
    tar -xzf "$tarball" -C "$RUNTIME"
    "$RUNTIME/python/bin/python3" -m venv "$VENV"
    pip_install() {
        PIP_NO_INDEX=1 PIP_DISABLE_PIP_VERSION_CHECK=1 OMNIGENT_SKIP_WEB_UI=true PYTHONWARNINGS=ignore \
            "$VENV/bin/python" -m pip install --quiet --no-index --find-links "$ROOT/vendor/wheels" "$@"
    }
    pip_install setuptools wheel editables "hatchling>=1.27,<1.32.0"
    pip_install --no-build-isolation -e "$ROOT/sdks/python-client" -e "$ROOT/sdks/ui" -e "$ROOT"
    echo "$stamp" > "$RUNTIME/stamp"
fi

# 2. Settings for this run. Override any of them from your shell.
export PATH="$ROOT/vendor/bin:$VENV/bin:$PATH"
export OMNIGENT_DATA_DIR="${OMNIGENT_DATA_DIR:-$HOME/.omnigent-slim}"
export OMNIGENT_CONFIG_HOME="${OMNIGENT_CONFIG_HOME:-$OMNIGENT_DATA_DIR}"
export OMNIGENT_SLIM_WORKSPACE="${OMNIGENT_SLIM_WORKSPACE:-$ROOT/workspace}"
export OMNIGENT_SLIM_LIBRARY_DIR="${OMNIGENT_SLIM_LIBRARY_DIR:-$OMNIGENT_SLIM_WORKSPACE/templates}"
export OMNIGENT_SLIM_PROJECT="${OMNIGENT_SLIM_PROJECT:-Workspace}"
export OMNIGENT_HOST_NO_OPEN=1
# Claude Code itself: skip telemetry, error reporting and auto-updates. It still
# talks to Anthropic for the model, as it does when you run it by hand.
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="${CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC:-1}"
mkdir -p "$OMNIGENT_DATA_DIR"

# 3. Start the server and host, then make sure the workspace project exists.
# The server prefers port 6767 and takes another free port if that one is busy.
"$VENV/bin/omnigent" start --no-open --non-interactive </dev/null
SERVER_URL=$("$VENV/bin/omnigent" server status </dev/null 2>/dev/null \
    | sed -n 's/.*running at \(http:\/\/[^ ]*\).*/\1/p' | head -1)
SERVER_URL=${SERVER_URL:-http://127.0.0.1:6767}
OMNIGENT_SLIM_URL="$SERVER_URL" "$VENV/bin/python" -m omnigent.slim_bootstrap || true

URL="$SERVER_URL/library"
echo "omnigent-slim is running: $URL"
if [ "$OPEN_BROWSER" = 1 ]; then
    open "$URL"
fi
