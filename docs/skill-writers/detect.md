# Detecting Omnigent

## Inside Omnigent?

Omnigent sets `OMNIGENT=1` in the environment of every agent it runs (the same
idea as Claude Code's own `CLAUDECODE`). Check it with one command:

```bash
printenv OMNIGENT
```

`1` means you are in an Omnigent session. Nothing printed means you are not.

A second, independent signal: Omnigent's tools are available to you under the
`omnigent` MCP server, e.g. `mcp__omnigent__ui_open_file`. If that tool is in
your tool list, you can use the viewer, whatever the environment says.

Useful variables in the same environment:

| Variable | Example | Meaning |
|---|---|---|
| `OMNIGENT` | `1` | Running under Omnigent |
| `OMNIGENT_RUNNER_PRIMARY_SESSION_ID` | `f185233f…` | This session's id (the one in the browser URL `/c/<id>`) |
| `OMNIGENT_RUNNER_LAUNCH_HARNESS` | `claude-native` | Claude Code running in a terminal driven by the web UI |
| `OMNIGENT_RUNNER_WORKSPACE` | `/Users/me/project` | The session's workspace folder |
| `OMNIGENT_CLIENT_SURFACE` | `web` | Started from the web UI (`cli` when started with `omnigent claude`) |

Treat these as read-only. Don't print or copy any variable whose name ends in
`TOKEN`.

## Inside omnigent-slim specifically?

omnigent-slim adds a paragraph to every session's system prompt that starts
"You are running inside the Omnigent web app (omnigent-slim)". If you can see
that, you are in omnigent-slim, and:

- there is no internet access for artifacts (inline everything);
- permission modes are limited to Manual, Accept edits and Plan;
- artifact templates live in the library folder named in that paragraph,
  usually `<repo>/workspace/templates/artifacts/`.

## Snippet for SKILL.md

```markdown
## Where am I?

Run `printenv OMNIGENT` once at the start.
- `1`: you're in Omnigent. Show visual results in the viewer: write an HTML
  file to `artifacts/` and call `ui_open_file` (see references/artifacts.md).
- empty: you're in a plain Claude Code terminal. Write files and describe them
  in your reply; don't call Omnigent tools.
```
