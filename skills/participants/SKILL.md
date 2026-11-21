---
name: participants
description: Bring another agent or person into the conversation and show what they say under their own name, and manage the roster of who can be called. Use when the user asks to check in with, call, ask, loop in or get a view from someone else (for example "check in with Mara from design and the risk agent"), asks who is available, asks to add, change or remove a participant, persona, stakeholder or platform agent, or when a skill tells you to call a participant.
---

# Participants

Other agents and people can take part in the user's conversation with you.
Each one is a file in the workspace's `participants/` folder. You are the host:
you look them up, call them, pass on what they say word for word under their
name, and carry the user's replies back.

You never speak for a participant and never make one up. If nobody on the
roster fits, say so and offer the closest.

## Who a message is for

- A message with no `@`, or with `@aviator`, is for you.
- A message that mentions a participant with `@` (`@mara-okafor`, `@mara`,
  `@Risk Review`) is for that participant. You still read it, because you see
  everything, but they answer it, not you. Send it to them as written (step
  2), and pass their reply on in a participant block (step 4). Add nothing of
  your own unless the reply needs an action from you, and then one line.
  If they have not been called yet in this session, call them now with the
  message as what they are asked.
- A message that mentions several participants goes to each of them.

## Calling someone in

You may call a participant on your own judgment when the work needs what they
are for (their `call for` line), without asking first. Always say that you are
doing it, in one line, before you call: who, and why ("I am bringing in Risk
Review: section 7 makes promises about consent."). If the user says not to,
stop. Do not call people for things you can settle yourself.

## Setup

```bash
PA="python3 <this skill's folder>/../view-kit/scripts/pa.py"
```

## 1. Look up who is available

```bash
$PA who                 # the roster: id, name, kind, role, what to call them for
$PA who --scenario DIR  # only those eligible for a workflow (see "Who is eligible")
$PA who mara            # one participant, by id or part of a name or role
```

Match what the user said ("Susie from design", "the risk agent", "someone
from platform") against names, roles and `call for`. If two fit, ask which.
If the user asks who they can call, show the roster as a short list.

Each participant has a `backing`:

| backing | Who answers | How you call them |
|---|---|---|
| `session` | A background session that plays them from their brief | Step 2 |
| `script` | Nobody: the answers are written in their file | Step 3 |

A participant with `stand_in: true` is a real person played by an agent. Say so
the first time they join ("an agent is standing in for Mara today").

## 2. Call a participant backed by a session

A background session is a real session of its own. The user can open it and
read everything it saw and did.

1. Look for a session you already started for them: `sys_session_list` with
   view `sub_agents`. If one has their name as its title, reuse it with step 4.
2. Otherwise write their opening message and start the session:

   ```bash
   $PA who <id> --opening --conversation <your session id> \
       --ask "<what you want from them, with the paths they need>"
   ```

   Your session id is the `conversation_id` that `sys_session_get_info`
   returns when called with no arguments. Passing it lets the participant
   read the whole conversation so far, which they are meant to see.

   Call `sys_agent_list`, take the `agent_id` of the first builtin, then call
   `sys_session_create` with that `agent_id`, `title` set to the participant's
   name, and `message` set to the opening text exactly as printed.
   Keep the `conversation_id` it returns: that is their session id.
3. Tell the user in one line that they have been called ("Calling Risk Review.
   I will pass on what they say."). To call several people about the same
   thing, start all their sessions before waiting for any of them.
4. To say more to them later, including the user's replies, call
   `sys_session_send` with `session_id` and the text in `args`.
5. Their reply does not come back from those calls. Call `sys_read_inbox`. If
   it is empty, end your turn; a notice that they finished starts your next
   one. Then read the inbox again, or `sys_session_get_history` with their
   `conversation_id` for the full text.

When they need files or a dataset, name the paths in what you ask. If they
should add structured items, give them the exact `pa add` command for the
dataset and remind them to set `by` to their id.

## 3. Call a participant backed by a script

Read their file. Under `## Script`, each `###` heading is a kind of question
and the text below it is their answer. Pick the entry that fits what was asked
and pass it on word for word, as in step 4 below, without a `session` line. If
nothing fits, use the entry that says so, or tell the user they have no answer
for that. Never improvise their answer.

## 4. Pass on what they said

Everything a participant says goes in a block like this, and nothing else
does. The app draws it as their turn, with their name and mark:

````
```participant
name: Risk Review
kind: agent
role: Risk and compliance
session: 4f0c2d...
---
Their reply, word for word.
```
````

Get the lines above `---` from `$PA who <id> --header --session <their session id>`.
Rules:

- Word for word. Do not shorten, tidy or merge replies. Leave out only a final
  `DONE:` line, which is for you.
- One block per reply. Your own words go outside the block, before or after.
- If their reply itself contains a ``` fence, open and close the block with
  four backticks.
- After the block, add at most one line of your own: what you did with it, or
  what the user needs to answer.

When the user answers a participant's question, send the answer to that
participant (step 2.4) rather than answering for them. When a reply ends with
`DONE:`, the call is over: say so in one line using their summary. Leave the
session open so the user can come back to them; do not close it unless asked.

## 5. Attribute what they make

- Records they add to a dataset carry `by: <their id>`. Yours carry
  `by: aviator`. A view shows it with a column `{ "field": "by", "as": "who" }`.
- You open views in the canvas, not them. When they say they added records,
  open or refresh the view and say whose items are new.
- If the user pushes back on something a participant raised, send the push
  back to that participant and pass on the answer.

## 6. Comments in documents

The user can comment on a markdown document in the editor and @mention a
participant. You then get a message like "I mentioned Mara Okafor
(mara-okafor) in a comment on `artifacts/brief.md`, thread t3". The
conversation happens in the document's comment thread, not in this chat:

1. For each id mentioned, print the message that asks them:

   ```bash
   $PA review ask <doc> <thread> <id> --pa "$PA"
   ```

2. Send it to them exactly as printed: to their existing session with
   `sys_session_send`, or start one as in step 2 with this as the `--ask`
   text. Script-backed participants: pick their script entry and post it
   yourself with `$PA review reply <doc> <thread> --by <id> --text "..."`.
3. They answer in the thread with `pa review reply`, so the user sees it there
   under their name. Do not relay their answer as a participant block in the
   chat; when they finish, say in one line that they have replied.
4. `$PA review pending <doc>` lists mentions nobody has answered yet.

Participants never edit a document directly. Any change they want is a
suggestion the user accepts or rejects (`pa review suggest --by <id>`). When
you ask a participant to work on a document, say so in what you ask. See the
`document-collaboration` skill for the rest of `pa review`.

## Who is eligible

`participants/` is the one roster for the whole workspace. A demo or a session
can narrow it:

- **A workflow.** A scenario's `scenario.json` may list `participants`, the ids
  that may take part in it. While you are running that workflow, use
  `$PA who --scenario <scenario folder>` instead of `$PA who`.
- **A session.** If the user's opening message names who is available
  ("Participants for this session: risk-review, mara-okafor"), that is the
  list for the session.
- Otherwise everyone on the roster is eligible.

If the user asks for someone who is on the roster but not eligible here, say
so and ask whether to call them anyway. Their answer decides.

## Adding, changing or retiring a participant

Use the `build-person` skill. It works on a draft that nobody else sees until
the user publishes it, checks it on every change, lets the user try it, and
keeps the previous version. Never edit or delete a file in `participants/`
directly: other people's sessions and workflows use them. (The user may still
edit the files by hand; `participants/README.md` explains the format.)

## Without Omnigent

If `printenv OMNIGENT` prints nothing, there are no background sessions.
Say so, and offer scripted participants only.
