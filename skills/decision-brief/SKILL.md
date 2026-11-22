---
name: decision-brief
description: Put a complex decision to the person as a decision brief, a page with context, drawn options, tradeoffs and a recommendation where they pick, comment and send their answers, from one JSON file and a fixed template. Use when a decision needs context, is more than one question, or has a visual side that chat can't show, when any skill's Decide step needs the person, or when asked to "brief me", for a decision walkthrough or to lay out options. Not for one quick choice; ask that with a question card.
---

# Decision brief

A brief puts one or more decisions in front of the person so they never
decide blind: what they need to know, a picture of each option, what each
gives up, your recommendation and why, and a place to pick, write
"Something else" and add a note. Every brief in Flight Deck uses this skill,
so they all look and work the same, and you write only the content.

**You write one JSON file. Never write the page.** `scripts/brief.py` draws
it from `template/brief.html`, which holds the layout, the styles, the
visual components and the answer handling. Changing how briefs look is a
change to the template, once, for every brief.

```bash
BRIEF="python3 <this skill's folder>/scripts/brief.py"   # standard library only
```

## When to make one

Use your judgment (D-163). Generally make a brief when the decision:

- **needs context** the person doesn't have in front of them (research,
  tradeoffs, what other teams depend on);
- **is more than one question**, especially linked ones;
- **has a visual side** that chat can't show well (layouts, designs, flows,
  what something will look like).

A single quick choice is one question card (`AskUserQuestion`,
recommendation first, with "Something else"); work that is easy to undo you
just do. The person can always say "brief me on this" or "just ask me". When
you make a brief on your own judgment, say why in one line.

Other skills don't copy any of this. A skill whose step needs the person to
choose says "put it to the person with the `decision-brief` skill" and hands
over what it found: the question, the options, the evidence. A workflow's
own checklist questions stay in its own views.

## 1. Gather before you write

- Read what the decision rests on: the files, datasets and earlier
  decisions. In a workspace, `pa artifacts --initiative <key>` and the
  initiative's `registers.json`; do not re-ask what a decision there already
  settled.
- Find the real options. Each one is something someone would actually do,
  not a straw man. Three or four is usually right.
- Know what each option costs and gives up, and which you recommend and why.
- Find or make the pictures: screenshots, a wireframe, a flow, a file tree,
  a table of examples. Saved images go next to the brief.

## 2. Write the brief

A brief is one of the project's decision artifacts, so it lives in the
project (D-162): **`projects/<key>/decisions/`** holds `<slug>.json` (the
brief and the answers), `<slug>.html` (the page) and `<slug>.md` (the
decision note), side by side. `pa project` lists the projects; for work not
yet in one, use `decisions/` at the workspace root and move the files when
the work joins a project.

Start from a skeleton, or copy `examples/decision-briefs.json`, which shows
every field in use:

```bash
D=projects/<key>/decisions
$BRIEF new $D/<slug>.json --title "<the choice, as a name>" --decisions 3 --initiative <key> --for "<person>"
```

The fields, in full in `reference/format.md`:

| Field | What it holds |
|---|---|
| `id`, `title`, `for`, `from`, `date` | Names the brief. The title is what is being decided. |
| `initiative` | The initiative's key, so the answers go to its decisions register. |
| `why` | Two or three sentences: what this is and why the person is seeing it. |
| `recommendation` | All your recommendations together, in one paragraph. |
| `read`, `findings` | What you read (with links) and what you found, each in a sentence. |
| `decisions[]` | `id`, `label`, `question`, `context`, `know`, `stage`, `options[]`, `reason`, `depends_on` |
| `options[]` | `id`, `label`, `consequence` (what happens and what it gives up), `cost`, `recommended` (exactly one), `visual` |
| `after` | What happens once they decide. |

A **visual** is `{"html": "...", "caption": "..."}` or `{"image": "file.png"}`.
Put one on the decision (`stage`) or on each option; the page shows the
option the person points at. Build html only from the components in
`reference/components.md` (wireframes, flows, comparisons, file trees,
tables, chips). They follow the design tokens in light and dark; never set a
color or load anything.

Do not write a "Something else" option: the page adds it to every decision.
Write in plain words, sentence case, and keep each consequence to a sentence
or two.

## 3. Check, draw and show it

```bash
$BRIEF check $D/<slug>.json      # errors stop the render: blind, no recommendation, remote loads, own colors
$BRIEF render $D/<slug>.json     # writes $D/<slug>.html beside it
```

Run both from the workspace, so the page names its brief by a workspace
path. Then show it where the person is. Every page has a **Send answers to
Claude** button, so the person answers and sends without leaving the brief
(D-161):

- **In Flight Deck:** open it with `ui_open_file`. Send reaches you at once
  as a message the app writes: `Decision brief answers for <file>, sent from
  the brief by the person`, one line per decision, notes quoted.
- **On claude.ai** (contributors putting decisions to Geoff): render with
  `--fragment` and publish it as an Artifact with
  `capabilities: {"db": {}, "comments": {}}`. Picks save to the page's
  `answers` collection as they are made; Send posts them as a comment sent
  to you, which wakes this session. Give the person the direct link.
- **Anywhere else** the page keeps picks in the browser and offers **Copy
  answers** for pasting into the chat.

Tell the person in one or two lines what the brief asks and how many
decisions; don't repeat the brief in the chat.

## 4. Take the answers

Answers come back one of three ways. Write them into the brief, never only
in your head:

```bash
$BRIEF import $D/<slug>.json --text -     # the message Send produced, or Copy's text, on stdin
$BRIEF import $D/<slug>.json --db <dir>   # an `answers` collection saved with ArtifactData list (out_dir)
$BRIEF answer $D/<slug>.json <decision> <option|else> --note "..."   # an answer given in words
```

Record only what the person said or picked; a pick from another agent is
not their answer. "Something else" needs their words in `--note`. If an
answer changes what another decision means, say so before going on.

## 5. Record and write the note

When the person says they are done, or all decisions are answered:

```bash
$BRIEF record $D/<slug>.json      # locks the answers; with `initiative`, one line each in the project's decisions register
$BRIEF note $D/<slug>.json [--url <artifact link>] [--archive <archived copy>]   # writes $D/<slug>.md
$BRIEF render $D/<slug>.json      # the page now shows them as decided
```

The note holds each decision, the pick, the person's note, whether it was
the recommendation, the reason, the options considered, and links to the
brief, the archived copy and the research. A recorded answer is never
edited; a later change is a new brief whose decision names `supersedes`.
Reply with the outcome in a line or two and the note's link.

**In this repository** (contributors), the decisions also go in
`docs/product/decisions.md` and the index with numbers claimed the careful
way `CLAUDE.md` describes (the note's "Log entries" are written in that
form), the page is archived with the `docs-refresh` skill, and the note goes
in that archive folder as `decision-note.md`.
