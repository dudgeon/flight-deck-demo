#!/bin/sh
# Refresh everything omnigent-slim needs offline, then commit the result.
# Run on a Mac with internet access (a build machine, never the work machine):
#
#   vendor/scripts/build_vendor.sh            # Python runtimes + wheels + web UI
#   vendor/scripts/build_tmux.sh              # tmux (separately; rarely changes)
#
# Produces:
#   vendor/python/cpython-<ver>-aarch64.tar.gz  standalone CPython for Apple silicon
#   vendor/wheels/                              every Python dependency, for Apple silicon
#
# Apple silicon only: current cryptography releases ship no Intel Mac wheels.
#   omnigent/server/static/web-ui/              the built web UI
#
# Needs: uv, pnpm (or corepack) and node on PATH.
set -eu

PYTHON_VERSION=3.12.16
PBS_RELEASE=20261110
# Lowest macOS the wheels must run on. pip picks wheels tagged at or below it.
MACOS_TARGET=13_0

ROOT=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT"
export OMNIGENT_ALLOW_NETWORK=1
WORK=${TMPDIR:-/tmp}/omnigent-slim-vendor
rm -rf "$WORK"
mkdir -p "$WORK" vendor/python vendor/wheels

# 1. Standalone CPython.
rm -f vendor/python/*.tar.gz
for arch in aarch64; do
    name="cpython-${PYTHON_VERSION}+${PBS_RELEASE}-${arch}-apple-darwin-install_only_stripped.tar.gz"
    curl -fsSL -o "vendor/python/cpython-${PYTHON_VERSION}-${arch}.tar.gz" \
        "https://github.com/astral-sh/python-build-standalone/releases/download/${PBS_RELEASE}/${name}"
done

# A local interpreter to run pip download with.
tar -xzf "vendor/python/cpython-${PYTHON_VERSION}-aarch64.tar.gz" -C "$WORK"
PY="$WORK/python/bin/python3"

# 2. Wheels, pinned by uv.lock.
uv export --frozen --no-dev --no-emit-project --no-emit-local --no-hashes \
    --format requirements-txt > "$WORK/requirements.txt"
echo "setuptools>=68" >> "$WORK/requirements.txt"
echo "wheel" >> "$WORK/requirements.txt"
rm -f vendor/wheels/*.whl
for platform in "macosx_${MACOS_TARGET}_arm64"; do
    "$PY" -m pip download --quiet --disable-pip-version-check \
        --only-binary=:all: --implementation cp --python-version 3.12 --abi cp312 \
        --platform "$platform" -r "$WORK/requirements.txt" -d vendor/wheels
done

# claude-agent-sdk bundles a ~200 MB copy of the claude CLI. omnigent-slim runs
# the claude already installed on the machine, so strip the bundled copy.
"$PY" "$ROOT/vendor/scripts/strip_wheel.py" vendor/wheels/claude_agent_sdk-*.whl \
    --remove 'claude_agent_sdk/_bundled/'

# uvloop must never be installed: it bypasses the offline guard.
if ls vendor/wheels/uvloop-* >/dev/null 2>&1; then
    echo "uvloop wheel present; remove it from the dependency graph" >&2
    exit 1
fi

# 3. The web UI.
pnpm install --frozen-lockfile
pnpm --filter web run build
find omnigent/server/static/web-ui -name '*.map' -delete

du -sh vendor/python vendor/wheels omnigent/server/static/web-ui
