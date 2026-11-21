---
name: build-person
description: Guided build of a person or agent for the roster, in the Hangar (Product Aviator's builder mode). Works on a draft that nobody else sees until it is published, with checks, a trial and history. Use when the user asks to add, change, duplicate or retire a participant, persona, stakeholder or platform agent, or when a session was started from the Hangar's "New person or agent", "Edit" or "Duplicate".
---

# Build a person or agent

People and agents on the roster (`participants/`) are used by other people's
sessions and workflows. So you never edit a roster file directly. You build a
**draft** with `pa draft`, the draft is checked on every change, and it only
goes live when it is **published**, which keeps the previous version so it can
be restored. The Hangar (`/hangar` in the app) shows the same draft, its checks,
what would change and who is affected.

In the app, the person's page in the Hangar is itself the editor (D-63): the
user can type into the fields, and you may be the Aviator in its pop-over,
working on the draft that is open. Your changes to the draft show on that page
as you make them, so you don't need to repeat them in the chat. Keep to small
steps and say what you changed.

```bash
PA="python3 <this skill's folder>/../view-kit/scripts/pa.py"
```

Work in the workspace folder (where `participants/` is).

## The five steps

Say which step you are on, ask **one thing at a time**, and record the step on
the draft with `--step` so the Hangar shows it. Propose wording instead of
asking the user to write it; they correct you.

### 1. Who they are

- New: `$PA draft person --name "Fraud Ops" --step "Who they are"`. The id is
  made from the name and must be free; if it is taken, ask for another name.
- A copy of someone: `$PA draft person --name "Fraud Ops EU" --duplicate fraud-ops`.
- A change: `$PA draft person mara-okafor --step "Who they are"`. The id never
  changes, even if the name does.

Ask whether they are an **agent** or a **real person**, and their role. A real
person is always played by an agent and is marked as a stand-in; `pa` enforces
it. Then:

```bash
$PA draft person <id> --set kind=agent --set role="Fraud operations"
```

### 2. How they answer

- `backing=session` (most): they answer live from a **brief**. Write the brief
  to them ("You are..."): who they are, what they look for, how they work, how
  they talk. A page at most. For a real person, use only what the user tells
  you about them, and say what you assumed.
- `backing=script`: fixed answers for demos that must go the same way every
  time. One or two lines on who they are, then `## Script`, a `### <kind of
  question>` above each answer, and a last `### Anything else`.

Write the brief to a scratch file and set it, with the call-for line:

```bash
$PA draft person <id> --set backing=session --set call_for="chargebacks, fraud rules, dispute timelines" \
  --brief-file /tmp/<id>-brief.md --step "How they answer"
```

`call_for` is what Aviator matches "the fraud agent" or "someone from fraud"
against, so make it a short list of topics.

### 3. Where they can be called

Everyone on the roster can be called from any session. Some workflows,
scenarios and starters list who may take part. Show them (the Hangar's
Workflows and Scenarios shelves, or `$PA uses person <id>`) and ask whether
they should be in any. Set the full list for each kind on the draft; publishing
writes it into each `workflow.json` and `scenario.json` cast and each
starter's participant line:

```bash
$PA draft person <id> --cast workflows=document-review,decision-review \
  --cast scenarios=document-review --cast starters=review-with-others \
  --step "Where they can be called"
```

The checks block taking someone out of a scenario whose script has them
speak, and say when a scenario is ticked but its workflow is not.

**Skills.** A person or agent can bring skills (from the Skills shelf): the
session that plays them is told to use them. Ask if any fit, then
`--set skills="frontend-design, prd-to-requirements"`.

### 4. Try them

Ask the draft a real question before publishing. Print their opening as the
roster would, from the draft:

```bash
$PA who <id> --dir .hangar/drafts/people --opening --ask "<the user's test question>"
```

and answer **as them**, in a participant block labelled with the draft's name,
starting with a line that says this is a trial of an unpublished draft. For a
script-backed draft, pick the matching `###` entry and pass it on word for
word. Ask the user if it sounds right; change the draft if not.
Record the step: `--step "Try them"`.

### 5. Publish

Run `$PA draft person <id>` to see the checks. Fix every failure. Then show
the user, in a few lines: what changes, and who is affected (`$PA uses person
<id>`: the workflows, scenarios and starters that name them; only sessions started after
publishing see the change). Publish only when the user says so, either with
the Publish button on the draft in the Hangar, or:

```bash
$PA publish person <id> --summary "one line on what changed"
```

## Retiring someone

`$PA draft person <id> --remove`. Publishing it is blocked while any workflow
scenario or starter names them (`$PA uses person <id>`): tell the user what still uses
them. Discard with `$PA draft person <id> --discard`.

## Going back

`$PA history person <id>` lists earlier versions; `$PA history person <id>
--restore <version>` makes one live again through the same checks, and keeps
the version it replaces.

## Never

- Never write to `participants/` directly, and never publish without the
  user's go-ahead.
- Never invent things a real person said or believes. A stand-in brief comes
  from what the user tells you.
