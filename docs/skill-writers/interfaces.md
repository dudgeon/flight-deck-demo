# Omnigent interfaces available to a Claude session

When Claude Code runs inside Omnigent, the `omnigent` MCP server gives it the
tools below (Claude sees them as `mcp__omnigent__<name>`). The tool
descriptions Claude receives are authoritative; this page is the map. Tools
marked *slim* are hidden or behave differently in omnigent-slim.

Most tools need the user's approval the first time in a session, except
`ui_open_file`, which omnigent-slim pre-allows.

## Viewer and artifacts

| Tool | Use it to |
|---|---|
| `ui_open_file` | Open a workspace file in the viewer. See artifacts.md |
| `list_comments` | Read the user's review comments on session files (file, selected text, comment, status) |
| `update_comment` | Mark a comment addressed after acting on it |

From inside an artifact: `window.omnigent.prompt(text)` fills the chat box.

An artifact is reloaded whenever its file changes, and it has no storage of its
own. `window.omnigent.saveState(key, value)` keeps a small JSON value for that
file, and the next load gets it back as `window.omnigent.state[key]`. Use it
for the reader's place: an open card, a filter, edits not yet sent.

## Structured views and scenarios

For work that is many similar items reviewed one at a time, do not hand-write
HTML. The bundled `view-kit` skill draws tables, boards, cards, summaries and
forms from a JSON dataset and a small spec, with the `pa` command
(`skills/view-kit/scripts/pa.py`, standard library only), and redraws them when
the data changes. `skills/prd-to-requirements` and
`skills/requirements-to-dependencies` and `skills/document-review` are complete examples, and the
`scenario-builder` skill explains how to make another, including a standalone
click-through built with `pa preview`.

## Views in the chat

A fenced block with the language `view` asks the app to draw a rendered view
inside the conversation instead of the canvas:

    ```view
    file: artifacts/allowances-decision-D-1.html
    title: Whose consent does an under-18 allowance need?
    ```

`file` is a workspace-relative `.html` path. The frame gets `window.omnigent`
as in the canvas, and `data-host="chat"` on the root element before the page's
own script runs. Post `{ source: "pa-kit", type: "size", height }` to the
parent to set the height (pages that do not are measured). After the user's
next message the view is folded and read-only. Use it for forms, single cards
and summaries; `pa render --host chat` prints the block.

## Other participants in the conversation

The session's agent can host other agents and people. Each is a file in the
workspace's `participants/` folder (name, kind, role, how they are played and
a brief); `pa who` lists them and the Session panel shows them under People
and agents. The bundled `participants` skill is the procedure: it starts a
background session per participant with `sys_session_create` (a real session
the user can open and read), talks to it with `sys_session_send`, and passes
each reply on in a fenced block the chat draws as that participant's turn:

````
```participant
name: Risk Review
kind: agent
role: Risk and compliance
session: <their session id>
---
Their reply, word for word.
```
````

`kind: person` is drawn as a stand-in, because in this app a person is always
played by an agent. Records a participant adds to a dataset carry
`by: <their id>`, which a view shows with `"as": "who"`.
`skills/document-review` is a complete example.

## The Session panel

The Session button in a session's header opens a panel that lists the
workspace's `artifacts/` folder as Outputs and its `context/` folder as
Context. Ticking context files adds `@context/...` mentions to the message box.
A skill should write what it makes to `artifacts/` and look for the user's
documents in `context/`.

A Workflow card appears in the panel for each small JSON file in the
workspace's `progress/` folder: `{"workflow", "subject", "steps": [...],
"current": <1-based; past the end means done>, "note", "counts": {"done",
"total", "noun", "label", "waiting"}}`. `pa flow` writes it from a scenario's
`steps` and keeps the counts current as records change.

The same file describes the **run** for the project page's "In flight"
section: `"state"` (`working`, `needs-you`, `waiting`, `paused`, `finished`
or `stopped`), `"left_off"` (the note written at a pause), `"session"` (the
session to reopen), `"data"` (the dataset) and `"started"` / `"paused_at"`.
A workflow skill keeps these true with `pa flow --pause --note`, `--resume`,
`--stop` and `--state`; `pa runs` lists them. A file without `"state"` is read
as working, or finished when `current` is past the last step.

## This session

| Tool | Use it to |
|---|---|
| `sys_session_rename` | Propose a short title for the current session |
| `sys_session_get_info` | Read a session's status, title, agent and project |
| `sys_session_get_history` | Read recent messages of a session without sending to it |
| `sys_session_update` | Change one of the user's sessions as the sidebar does (title, pin, archive, project) |
| `sys_session_link_pr` | Show a GitHub pull request in a session's PR panel |

## Other sessions and agents

| Tool | Use it to |
|---|---|
| `sys_session_list` | List this session's sub-agents, or the user's sessions |
| `sys_session_create` | Start a new session from an agent (a sub-agent; it runs separately and appears in the sidebar) |
| `sys_session_send` | Send a message to a sub-agent session you created |
| `sys_read_inbox` | Collect results from sub-agents and background tasks |
| `sys_session_close` | Close a sub-agent session you created |
| `sys_session_message` | Message another of the user's sessions, only when the user asks |
| `sys_agent_list` / `sys_agent_get` | See which agents can be launched (in omnigent-slim: Claude Code only) |
| `sys_list_models` | See which models sub-agents can use |

## Projects

| Tool | Use it to |
|---|---|
| `sys_project_list` | List projects and which sessions are in each |
| `sys_project_update` | Rename a project or change its icon |

## Following up later

| Tool | Use it to |
|---|---|
| `sys_reminder_set` | Have a message arrive in this session at a set time |
| `sys_scheduled_task_create` / `_list` / `_update` / `_delete` | Run a saved prompt on a schedule (Automations page); the user approves each change |
| `sys_user_inbox_post` / `sys_user_inbox_list` | Leave an item in the user's Inbox page |

## Terminals, background work, policies

| Tool | Use it to |
|---|---|
| `sys_terminal_launch` / `_send` / `_read` / `_list` / `_close` | Drive extra named terminals declared by the agent |
| `sys_call_async` / `sys_cancel_async` / `sys_cancel_task` | Run and cancel background tasks |
| `sys_policy_registry` / `sys_add_policy` | Add a guardrail policy to the session |

## Skills

| Tool | Use it to |
|---|---|
| `load_skill` / `read_skill_file` | Omnigent's own skill loader. Claude Code's built-in Skill tool also works; prefer it |

## Not available in omnigent-slim

- `browser_*` (embedded browser): needs the Omnigent desktop app. Removed. *slim*
- Other agent harnesses (Codex, Cursor, Pi, ...), cloud sandboxes and model
  providers: hidden. *slim*

## For code outside a session: the HTTP API

Scripts on the same Mac can drive the same server over HTTP (no auth for the
local single-user server). The full reference is
[`omnigent/server/API.md`](../../omnigent/server/API.md). The ones skills and
tools reach for most:

| Call | Does |
|---|---|
| `GET /v1/sessions` | List sessions |
| `POST /v1/sessions` | Create a session (see API.md, "Create From Existing Agent") |
| `GET /v1/sessions/{id}` | Session snapshot |
| `POST /v1/sessions/{id}/ui/open-file` with `{"path": "..."}` | Open a file in that session's viewer |
| `GET /v1/projects` / `POST /v1/projects` | List or create projects |
| `GET /v1/agents` | List agents |
| `GET /v1/slim/library` | omnigent-slim: canned sessions and templates *slim* |

The web UI also opens a prefilled composer from a link:
`/?project=<name>&prompt=<url-encoded text>`. Nothing is sent until the user
presses Send.
