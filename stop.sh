#!/bin/sh
# Stop the omnigent-slim server and host started by ./start.sh.
set -eu
ROOT=$(cd "$(dirname "$0")" && pwd)
export PATH="$ROOT/vendor/bin:$ROOT/.runtime/venv/bin:$PATH"
export OMNIGENT_DATA_DIR="${OMNIGENT_DATA_DIR:-$HOME/.omnigent-slim}"
export OMNIGENT_CONFIG_HOME="${OMNIGENT_CONFIG_HOME:-$OMNIGENT_DATA_DIR}"
"$ROOT/.runtime/venv/bin/omnigent" stop </dev/null
