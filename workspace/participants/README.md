# Participants

This folder is the roster: every other agent or person your agent can bring
into a conversation. One markdown file each. Add a file to add someone, edit
it to change them, delete it to remove them. Files that start with `_` and
this README are ignored.

You can also ask the agent: "add a participant", "who can I call?".

## The file

```
---
name: Mara Okafor
kind: person
role: Design lead, Cards
initials: MO
stand_in: true
backing: session
call_for: the customer's experience, wording, flows
---
Everything below the second line of dashes is theirs.
```

| Line | Meaning |
|---|---|
| `name` | How they appear in the chat. |
| `kind` | `agent` or `person`. Agents get a square mark, people a round one. |
| `role` | Shown beside their name. |
| `initials` | Two letters for their mark. Optional. |
| `stand_in` | `true` when an agent is playing a real person. Required for every `person`. The chat always labels them "stand-in". |
| `backing` | How they answer: `session` or `script`. See below. |
| `call_for` | When the agent should think of them. This is what "the risk agent" or "someone from design" is matched against. |
| `skills` | Skills the session playing them is told to use, comma-separated. Optional. |
| `avatar` | Their picture, `avatars/<id>.png` (or .jpg, .webp, .gif) in this folder. Optional; set it from the Hangar, which copies the file in. |

The file name is their id: `mara-okafor.md` is `mara-okafor`.

## Two ways to answer

**`backing: session`.** The text below the header is a brief: who they are,
what they care about, how they talk. When they are called, a background
session starts with that brief and answers in character. You can open that
session from any of their turns in the chat and read everything it saw.

**`backing: script`.** The text below the header holds fixed answers, for
demos that must go the same way every time:

```
## Script

### Can it block a purchase
Yes, at approval time, within limits. ...

### Timelines and cost
One sprint for the counter. ...

### Anything else
I have no answer for that. Ask the team directly.
```

Each `###` heading is a kind of question. The agent picks the entry that fits
and passes the answer on word for word. Keep a last entry for everything else.

## Talking to them

Ask your agent ("check in with Mara and the risk agent"), or address someone
directly by starting a message with `@` and their id or name: `@mara-okafor
which alert would you keep?`. They answer under their own name. A message
without an `@`, or with `@aviator`, goes to your agent. Your agent may also
bring someone in on its own when the work calls for it, and says so when it
does. Everyone called can read the whole conversation.

## Who can be called where

Everyone here can be called from any session, unless something narrows it:

- A workflow can list who may take part: `"participants": ["risk-review",
  "mara-okafor"]` in its `scenario.json`. Its demo preview uses the same list.
- A session can be started with a line such as "Participants for this
  session: risk-review, mara-okafor".

The Session panel shows the people a running workflow allows, with the rest of
the roster one click away.

## Checking

`python3 skills/view-kit/scripts/pa.py who --check` (from the app's folder,
with `--dir workspace/participants`) reports anything missing.
