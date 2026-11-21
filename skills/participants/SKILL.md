---
name: participants
description: Bring another agent or person into the conversation and show what they say under their own name. Use when the user asks to check in with, call, ask, loop in or get a view from someone else (for example "check in with Mara from design and the risk agent"), asks who is available, or when a skill tells you to call a participant.
---

# Participants

Other agents and people can take part in the user's conversation with you.
Each one is a file in the workspace's `participants/` folder. You are the host:
you look them up, call them, pass on what they say word for word under their
name, and carry the user's replies back.

You never speak for a participant and never make one up. If nobody on the
roster fits, say so and offer the closest.

## Setup

```bash
PA="python3 <this skill's folder>/../view-kit/scripts/pa.py"
```

## 1. Look up who is available

```bash
$PA who                 # the roster: id, name, kind, role, what to call them for
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
   $PA who <id> --opening --ask "<what you want from them, with the paths they need>"
   ```

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

## Adding a participant

One file per participant, `participants/<id>.md`:

```
---
name: Mara Okafor
kind: person            # agent or person
role: Design lead, Cards
initials: MO
stand_in: true          # required for a person played by an agent
backing: session        # session or script
call_for: the customer's experience, wording, flows
---
The brief: who they are, what they care about, how they talk.
```

`pa check <scenario>` checks the files of a scenario's own `participants/`
folder. To use a scenario's participants in the workspace, copy them into
`participants/` if files with those names are not already there.

## Without Omnigent

If `printenv OMNIGENT` prints nothing, there are no background sessions.
Say so, and offer scripted participants only.
