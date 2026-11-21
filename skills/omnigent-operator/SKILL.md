---
name: omnigent-operator
description: Operate Omnigent from inside a session - show a file or page in the viewer, rename this session, list or message the user's other sessions, start a sub-agent session, set a reminder or scheduled task, or leave something in the user's Inbox. Use when the user asks for any of those, or asks what this Omnigent session can do.
---

# Operating Omnigent from a session

## 1. Check you are in Omnigent

Run `printenv OMNIGENT` once. `1` means yes. If it prints nothing, you are in
a plain Claude Code terminal: say that Omnigent isn't running this session and
do the task with ordinary files instead.

`OMNIGENT_RUNNER_PRIMARY_SESSION_ID` is this session's id (the `/c/<id>` in
the browser URL) and `OMNIGENT_RUNNER_WORKSPACE` its workspace folder. Never
print a variable whose name ends in `TOKEN`.

## 2. Pick the tool

Omnigent's tools come from the `omnigent` MCP server, so they appear as
`mcp__omnigent__<name>`. Their own descriptions are authoritative; this is the
map.

| The user wants to | Use |
|---|---|
| See a file, HTML page or image | `ui_open_file` with a workspace path (pre-allowed) |
| Act on review comments they left on a file | `list_comments`, then `update_comment` once addressed |
| Retitle this session | `sys_session_rename` |
| Know about this or another session | `sys_session_get_info`, `sys_session_get_history` |
| See their sessions or projects | `sys_session_list`, `sys_project_list` |
| Hand work to a separate session | `sys_session_create`, then `sys_session_send`; collect results with `sys_read_inbox` |
| Tell another of their sessions something | `sys_session_message` (only when they ask) |
| Be reminded later in this session | `sys_reminder_set` |
| Run a prompt on a schedule | `sys_scheduled_task_create` (they approve it) |
| Get a note in their Inbox page | `sys_user_inbox_post` |

## 3. Rules that hold in omnigent-slim

- There is no internet. Anything you show in the viewer must be self-contained:
  inline CSS, scripts and images, no CDN links or remote fonts.
- Only Claude Code agents exist here (`sys_agent_list` shows them). Don't offer
  Codex, cloud sandboxes or the embedded browser.
- Permission modes are Manual, Accept edits and Plan. Don't ask for or set a
  mode that skips approvals.
- Every Omnigent tool except `ui_open_file` asks the user the first time. If
  they decline, say what you couldn't do and carry on.

## 4. Showing a result

Write the page or file inside the workspace (an `artifacts/` folder is a good
home), call `ui_open_file` with its path, and tell the user in one line what
they're looking at. Re-open the same path after editing it to refresh the
viewer.
