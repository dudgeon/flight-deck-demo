---
name: build-skill
description: Write or change a skill (a kit or move every session can use, such as a checklist, a memo format or a way of reviewing) as a Hangar draft, checked and published with `pa`. Use when the user asks to make, change, copy or retire a skill that is not a workflow, or when a session was started from a skill's page in the Hangar. Workflows (kinds of work with steps, records and views) use scenario-builder instead.
---

# Build a skill

A skill is a folder with a `SKILL.md`: a `---` block with `name:` (the folder's
id) and `description:` (what it does and when to use it), then the instructions.
Every session gets every skill, so a change reaches everyone who starts a
session after it is published. That is why you never edit a live skill: you
build a **draft**, the draft is checked on every change, and it goes live only
when it is **published**, which keeps the previous version so it can be
restored (D-167).

```bash
PA="python3 <this skill's folder>/../view-kit/scripts/pa.py"
```

Work in the workspace folder (where `participants/` is).

## Where the work happens

The skill's page in the Hangar is the editor (`/hangar/skills/<id>`, and the
draft at `/hangar/drafts/skill/<id>`). The person types into it, and you work
from the Aviator pop-over on that page. Your changes to the draft show on the
page as you make them, so say what you changed in one line and don't repeat it.

**If this conversation did not start in the Hangar** (its first message does
not say you are editing something in the Hangar), don't build the skill in the
chat. Start the draft, then hand the person the page, and stop:

```bash
$PA draft skill --name "Risk memo"      # a new one
$PA draft skill participants            # a change to one that exists
```

> I started a draft of **Risk memo**. [Open it in the Hangar](/hangar/drafts/skill/risk-memo)
> to write it; I'll be in the Ask Aviator pop-over there.

Use the id `pa` printed. Keep the link exactly in that form: it opens in the app.

## Drafts

- New: `$PA draft skill --name "Risk memo"`. The id comes from the name and must
  be free (a workflow's id counts as taken). The draft starts with a `SKILL.md`
  to fill in.
- A copy: `$PA draft skill --name "Risk memo EU" --duplicate risk-memo`.
- A change: `$PA draft skill <id>`. A skill that ships with the app is never
  changed in place: publishing puts a workspace copy in
  `.claude/skills/<id>/` that takes over its id, and removing that copy brings
  the shipped one back.
- Edit files only inside the draft folder `.hangar/drafts/skills/<id>/`, then run
  `$PA draft skill <id>` to see the checks.

## Writing it

1. **The description decides when it is used.** Say what it does, then "Use
   when …" with the words a person would actually say. Under 1024 characters,
   one line. Propose one and let the person correct it.
2. **Instructions are for the agent.** Short steps in the order they happen.
   Ask one thing at a time. Point to files in the folder for anything long (a
   checklist in `references/`, a template in `templates/`) rather than pasting
   it in.
3. **Style.** Plain language, sentence case. Anything it makes for people to
   see uses the `--pa-…` design tokens (see `product-aviator-design`), and
   nothing reaches the internet.

## Trying it

When the person asks to try it (the pop-over's "Try it" tab), read the draft's
`SKILL.md` and follow it for their request as if it were installed. Say first
whether the description would have picked the skill for that request. Change
no live files and publish nothing.

## Publishing and going back

The person presses Publish on the page, or asks you: `$PA publish skill <id>
--summary "what changed"`. It refuses while a check fails. `$PA history skill
<id>` lists earlier versions; `--restore <version>` brings one back through the
same checks. Retiring a skill built here: `$PA draft skill <id> --remove`, then
publish; it is blocked while a person lists it in their skills.

## Never

- Edit a live skill folder (`skills/` or `.claude/skills/`) directly.
- Turn a skill into a workflow or the reverse; build a workflow with
  scenario-builder.
