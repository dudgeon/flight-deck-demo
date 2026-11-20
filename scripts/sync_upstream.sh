#!/bin/sh
# Bring upstream Omnigent changes into omnigent-slim, as a patch on a new branch.
#
#   scripts/sync_upstream.sh            # sync to upstream main
#   scripts/sync_upstream.sh <commit>   # sync to a specific upstream commit or tag
#
# UPSTREAM holds the upstream commit this tree was last synced to. The script
# diffs that commit against the target, skips the parts omnigent-slim removed
# (apps, tests, docs, CI, ...), and applies the rest with a 3-way merge on a new
# branch. Resolve any conflicts, rebuild the web UI if web/ changed
# (pnpm --filter web run build, delete *.map), re-run vendor/scripts/build_vendor.sh
# if uv.lock changed, test with ./start.sh, then merge the branch.
# Needs network access: run it on a build machine, not the offline work Mac.
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
UPSTREAM_URL=https://github.com/omnigent-ai/omnigent.git
target=${1:-main}

git diff --quiet && git diff --cached --quiet || { echo "commit or stash your changes first" >&2; exit 1; }
git remote get-url upstream >/dev/null 2>&1 || git remote add upstream "$UPSTREAM_URL"

old=$(cat UPSTREAM)
git fetch --quiet --no-tags --depth=1 upstream "$old"
git fetch --quiet --no-tags --depth=1 upstream "$target"
new=$(git rev-parse FETCH_HEAD)
if [ "$old" = "$new" ]; then
    echo "Already at upstream $new."
    exit 0
fi

# Paths omnigent-slim removed; upstream changes to them are not brought over.
set -- \
    ':!.github' ':!.claude' ':!.oss-scanner' ':!.pre-commit-config.yaml' \
    ':!AGENTS.md' ':!CLAUDE.md' ':!README.md' ':!CHANGELOG.md' ':!CONTRIBUTING.md' \
    ':!DCO' ':!SECURITY.md' ':!buf.yaml' ':!justfile' ':!openapi.json' ':!pyrefly.toml' \
    ':!railway.toml' ':!render.yaml' ':!deploy' ':!designs' ':!dev' ':!docs' \
    ':!editors' ':!feature-map' ':!integrations' ':!specs' ':!tests' \
    ':!web/ios' ':!web/android' ':!web/.storybook' ':!web/vite.storybook.config.ts' \
    ':!web/TIPTAP_MIGRATION_NOTES.md' \
    ':(glob,exclude)web/electron/**' \
    ':(glob,exclude)web/src/**/*.test.ts' ':(glob,exclude)web/src/**/*.test.tsx' \
    ':(glob,exclude)web/src/**/*.stories.tsx' ':(glob,exclude)web/src/**/__tests__/**' \
    ':(glob,exclude)web/src/**/__mocks__/**' \
    ':!examples/aws_analyst' ':!examples/deep-research' ':!examples/kimi_hello.yaml' \
    ':!examples/mcp-registry' ':!examples/remy' ':!examples/sandbox-profile-provider' \
    ':!examples/scribe' ':!examples/sentinel' ':!examples/tcp-egress' ':!examples/extensions' \
    ':!scripts/backend-smoke.sh' ':!scripts/fetch-dictation-models.sh' ':!scripts/install_oss.sh' \
    ':!scripts/test_crdb_matrix.sh' ':!scripts/update_nightly.sh' ':!scripts/update_versions.py' \
    ':!scripts/normalize_uv_lock_registry.py' ':!scripts/dump_openapi.py'

patch=$(mktemp)
git diff --binary "$old" "$new" -- . "$@" > "$patch"
branch="sync-upstream-$(echo "$new" | cut -c1-12)"
git switch -c "$branch"
if git apply --3way --index "$patch"; then
    status="applied cleanly"
else
    status="applied WITH CONFLICTS: fix the files git status shows, then git add them"
fi
echo "$new" > UPSTREAM
git add UPSTREAM
rm -f "$patch"
echo "Upstream $old -> $new $status on branch $branch."
echo "Electron helper files the web UI imports (web/electron/src/*) are not synced; check them if the build fails."
