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
