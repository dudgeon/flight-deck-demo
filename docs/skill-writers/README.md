# Writing skills that work inside Omnigent

Reference for people writing Claude Code skills that should be good at
operating Omnigent. Copy the files you need into your skill's `references/`
folder and point to them from `SKILL.md`, or paste the short sections straight
into `SKILL.md`.

| File | What it gives a skill |
|---|---|
| [`detect.md`](detect.md) | How to tell, in one step, whether Claude is running inside Omnigent (and inside omnigent-slim) |
| [`interfaces.md`](interfaces.md) | Every interface a Claude session in Omnigent can use: the viewer, artifacts, sessions, projects, comments, inbox, reminders, schedules, terminals |
| [`artifacts.md`](artifacts.md) | How to make, show and update artifacts, and how artifacts talk back |
| [`example-skill/SKILL.md`](example-skill/SKILL.md) | A small, complete skill that uses all of the above, to copy from |

## Vocabulary

Use these words in skills so they match what Omnigent and its users say.

- **Session**: one conversation with one agent. In omnigent-slim the agent is
  always Claude Code, running in a terminal on the user's Mac.
- **Project**: a named group of sessions with default settings, including the
  folder sessions start in (the *workspace*). omnigent-slim creates one called
  `Workspace`.
- **Workspace**: the folder a session runs in. Claude's current directory.
- **Viewer** (users often say **canvas**): the panel on the right of a session
  that shows workspace files. Upstream Omnigent calls it the *workspace viewer*
  or *file viewer*. It renders HTML and runs its JavaScript. Note that
  upstream Omnigent also has an unrelated page called "Canvas" (sessions as
  draggable cards); avoid that word in tool names and code.
- **Artifact**: a self-contained HTML file in the workspace, shown in the
  viewer. omnigent-slim keeps them in `artifacts/`.
- **Template**: an artifact to copy and fill in, from the library folder.
- **Canned session**: a prompt with fill-in fields, listed on the Library page.

## The two rules every Omnigent skill should follow

1. **Detect, then choose.** Check whether you're in Omnigent (see
   `detect.md`). If you are, show results in the viewer; if you're not,
   fall back to plain files and a reply.
2. **Stay offline and inside permissions.** omnigent-slim runs where the open
   internet is blocked and permission bypass is not allowed. Artifacts must
   inline everything; never ask the user to change permission modes.
