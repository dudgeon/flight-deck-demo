# Working on omnigent-slim

A cut-down fork of Omnigent that drives Claude Code as a terminal program and
runs offline. Read README.md first. These rules keep it usable on the work Mac:

- **Nothing may reach the internet at runtime.** Don't add CDN links, remote
  fonts or images, telemetry, update checks or downloads. Python code runs
  behind `omnigent/_offline_guard.py`; never weaken it or reintroduce uvloop.
  New Python or npm dependencies must be vendored: rebuild with
  `vendor/scripts/build_vendor.sh` and commit `vendor/wheels/` and the web UI.
- **Never bypass Claude Code permissions.** All launches go through
  `omnigent/slim_policy.py`. Don't add `--dangerously-skip-permissions`,
  `bypassPermissions`, `dontAsk` or `auto`, and don't pre-approve tools beyond
  `ui_open_file`.
- **The built web UI is committed** in `omnigent/server/static/web-ui/`. After
  changing `web/src/`, run `pnpm --filter web run build`, delete `*.map`, and
  commit the output.
- Mark slim-specific changes to upstream files with a short `omnigent-slim:`
  comment so they're easy to find when pulling from upstream.

Run it with `./start.sh` (see README). For a dev loop on a machine with
internet, `uv sync` and `uv run omnigent start` also work.
