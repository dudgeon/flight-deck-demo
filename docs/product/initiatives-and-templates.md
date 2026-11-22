# Initiatives, artifacts and templates: the data model

Status: **the uncontroversial parts are built (D-138 to D-142); two questions
are with Geoff (IN-1, IN-3), and what is built follows the recommended answer
to each.** Raised by Geoff on 2026-11-21:

> We also need a data model for the templates; some templates will simply be
> markdown sections/frontmatter, others will be json plus rendering/styling,
> and we will need some kind of initiative registry with uuids/other keys to
> associate artifacts back to a shared representation of the intent/initiative.
> This can be run by the project setup skill, but the downstream hero skills
> need to know how to interact with and extend that data model.

Written with the lifecycle research thread ("Research the product lifecycle
and AI help"), whose early findings are folded in where marked.

## What already existed

| Piece | Where | What it gave us | What it lacked |
|---|---|---|---|
| A project with a goal (D-97, D-121) | `workspace/projects/<slug>.json`, `pa project` | Name, goal, area, team, state | No stable id: everything pointed at it by **name**, so a rename broke links |
| Links (D-119) | `"links"` on a record, `pa link` | Typed links between projects, read both ways | Only from dataset records, by name |
| A dataset names its project | `"project"` on a dataset | Datasets grouped by project | Nothing else (markdown, pages, context files) could say so |
| Runs (D-93) | `progress/*.json`, `pa flow`, `pa runs` | Which workflow ran on what, its state | No tie to a project |
| Workflow manifests (D-83, D-120) | `workflow.json`: `dataset`, `views`, `schemas`, `work_products`, `routing.stage` | The JSON + view kind of template, in practice | No name for "a template" apart from the workflow; nothing for markdown |
| Artifact templates (D-88) | `workspace/templates/artifacts/*.html` | Self-contained pages | No manifest, no stage, no tie to anything |
| Lifecycle stages (D-120) | `workspace/frameworks/lifecycle.json` | Stage ids | — |
| Intent graph (D-98) | held | — | Held "until it blocks something". Tying artifacts to a shared intent is that something, at the level of initiatives only; the graph's own detail stays held |
| Upstream | `omnigent/entities/project.py`: `id` is a bare 32-character UUID | A real id for app projects | Kept untouched; our meaning stays in our own files |

## The model in one picture

```
projects/<key>.json                 the initiative's card: id, key, name, goal, area, state, refs
projects/<key>/intent.md            the shared intent (judgment layer): sections owned by stages
projects/<key>/registers.json       the shared registers (checkable layer): evidence, questions,
                                    decisions, ready checks; a view-kit dataset
data/*.json, artifacts/*.md|html    artifacts: each carries a stamp naming its initiative,
briefs/*.md ...                     template, stages and what it was made from
context/*  (the person's files)     listed on the card (refs), never written into

pa artifacts  ── reads every stamp + every card's refs ──►  the registry, assembled on demand
```

There is still no store of our own: the registry is read from the files on
request, as the Connections card is (D-121), so it works from a ZIP and can be
replaced by a service later.

## Initiatives (D-138; IN-1 recommended answer)

An **initiative** is a project with a goal (D-97). It is the same thing, not a
new layer: the card in `projects/<key>.json` gains two fields the first time
it is written.

| Field | Meaning | Changes? |
|---|---|---|
| `id` | `ini_` plus a bare 32-character UUID (upstream's project id format, with a type prefix so an agent can tell an initiative id from an artifact id at a glance) | Never |
| `key` | The file's name, a slug of the first name (`held-payment-dates`). The handle people and agents type | Never; it names the folder too |
| `name`, `goal`, `area`, `team`, `state`, `state_note` | As D-97 and D-121 | Freely |
| `refs` | Files that cannot carry a stamp: the person's own `context/` documents, PDFs, decks. Each gets an `art_` id like any artifact | Added with `pa stamp` |
| `omnigent_project` | (Optional, not written yet.) The upstream project's id when the initiative has a project in the app | When linked |
| `external` | (Optional, not written yet.) Keys in other systems, e.g. `[{"system": "jira", "ref": "PAY-123"}]` | When known |

`pa project`, `pa stamp`, `pa template new` and `pa register` all find an
initiative by its id, its key or its name in any case. A card written before
ids gets one the next time it is used. Links (`pa link`) still name the other
project; the id makes a later move to ids safe.

## Artifacts and their stamps (D-140)

An **artifact** is anything made for an initiative: a dataset, a markdown
document, a page, a brief. Each says what it is in a small **stamp inside the
file**, so it carries its identity wherever it is copied, and nothing has to
be kept in step with a central list.

| Field | Meaning |
|---|---|
| `id` | `art_` plus a 32-character UUID; kept when the stamp changes |
| `initiative` | The initiative's id, or empty for a loose artifact (D-141) |
| `template` | `<template id>@<version>` it was made from |
| `stage` | A **list** of lifecycle stages it serves (a PRD can serve Specify and Map) |
| `status` | `draft`, `in-review`, `final` or `superseded` |
| `title`, `by`, `made` | Display title; who made it (a workflow id, a participant, `aviator`, `you`); when |
| `from` | Ids of the artifacts it was made from, so evidence stays attached end to end |

Where the stamp goes:

| File | Stamp |
|---|---|
| Markdown | Frontmatter: `artifact: art_…`, `initiative: ini_…`, `template: …`, `stage: ["shape"]`. Other frontmatter is kept |
| JSON (a dataset, or any object) | A top-level `"artifact": {…}` block. Views drawn from a dataset embed it, so a drawn page is read as a **rendition** of its dataset, not a second artifact |
| HTML page | `<script type="application/json" id="pa-artifact">{…}</script>` in the head |
| Anything else, and the person's `context/` files | Listed on the card under `refs`; the file is never written into |

`pa artifacts` assembles the registry: every stamp under `data/`,
`artifacts/`, `context/`, `projects/` and `briefs/`, plus every card's refs,
grouped by initiative, with renditions under their dataset. A file copied
with its stamp shows up as a problem ("a copy kept its stamp") rather than
silently sharing an id.

## Templates (D-139)

A **template** is a folder with a `template.json`. One manifest, three kinds:

| Kind | Made of | Instance | Example |
|---|---|---|---|
| `markdown` | `template.md` (headings and one-line guides) and `sections` in the manifest: each section's `id`, `heading`, `required`, `owner` (a lifecycle stage, or `any`) and `guide`; optional `fields` for frontmatter | A `.md` file with a stamp in its frontmatter | `initiative-intent` |
| `records` | `schemas` (record types and fields, as workflows already have) and `views` (view-kit specs) | A dataset with a stamp | `initiative-registers`, `alternatives`, `onboarding-track` |
| `page` | `file`: one self-contained HTML page styled with tokens | A copy of the page with a stamp | The six older artifact pages, read as `page` templates without a manifest |

Every manifest has `template` (its id), `version`, `kind`, `title`,
`summary`, `stage` (a list, or `any`) and `out`: where an instance goes, with
`{key}` for the initiative's folder and `{slug}` for the title.

Where templates live, first found wins: `templates/` in the workspace, then
each workflow's own `templates/` folder (Hangar-built ones before shipped
ones, as workflows do, D-72). A workflow's `work_products` may name a
`template`; `pa check` fails if it does not exist.

`pa template check` refuses: an unknown kind, a missing file, a markdown
section whose heading is not in the file, an owner or stage that is not a
lifecycle stage, a broken view spec, and anything loaded from the web.

## The shared representation of intent (IN-3 recommended answer)

Following the research thread: documents are the **judgment layer**, and a
few shared lists are the **checkable layer** every skill reads and adds to.
The seam none of the companies in Geoff's research has solved is research to
intent with the evidence still attached, across people; the registers are
where it stays attached.

- **`projects/<key>/intent.md`**, from `initiative-intent`: Goal, Problem,
  Customer, Outcome, Scope, Approach, Dependencies, Delivery. Each section has
  an owning stage. A workflow writes its own stage's sections directly and
  suggests changes to any other section as tracked changes (CriticMarkup,
  D-104) for the person or that section's owner to accept.
- **`projects/<key>/registers.json`**, from `initiative-registers`, a view-kit
  dataset with four record types, drawn as a board:
  - **evidence** (`E-01`): what it shows and its `source`, which is required;
    `against` when it argues the other way.
  - **question** (`Q-01`): a question or assumption, its `owner`, whether it
    is `blocking`, `open` or `answered`.
  - **decision** (`D-01`): what was decided and why. **Never edited**:
    `pa set` refuses to change one; a new decision `--supersedes` it, and the
    old one becomes `superseded`.
  - **check** (`C-01`): a pass or fail test of readiness (`pass`, `fail`,
    `unknown`), optionally tied to the stage it gates.

`pa register <initiative> evidence|question|decision|check "<one line>"`
adds one, making the file on first use.

## Templates for the arcs (after D-148 to D-152)

Geoff's hero skill decisions (PR 41) added a Choose half to PRD to
dependencies and an Engage owners arc. Two shared `records` templates serve
them, in `workspace/templates/`:

- **`alternatives`** (stages Specify and Deliver): a `choice` (the question,
  open or chosen, the option picked and the decision register id that records
  it) with `option` children. Each option has a kind from Pathfinder's four
  (`capability-swap`, `scope-trade`, `resequence`, `presets`), its scope
  effect, **effort** (our person-weeks) and **waiting** (weeks on others) kept
  as separate numbers, what it relies on, risks, and a status of proposed,
  chosen or turned down, with the reason kept for every one turned down. The
  choice itself goes in the decisions register; complex choices go through
  the decision brief skill, which writes that register entry. Deliver uses
  the same template for its ways to recover a slip.
- **`onboarding-track`** (stage Engage): a `capability` per owning team
  (owner, what it serves, needed by) with `step` children, one per step of
  that team's procedure (`intake`, `access`, `due-diligence`, `terms`,
  `provisioning`, `integration-ready`). Each step names its counterparty
  kind (`self-serve`, `agent`, `person`), owner, state (not started,
  drafted, sent, waiting on them, answered, done, blocked), lead time in
  weeks and evidence. Drafted is amber because it waits on the person to
  send; waiting on them is grey.

The lifecycle file now has the five stages Geoff chose: Discover, Shape,
Specify, Engage, Deliver. Moves that fit every stage (review, decide) use the
stage `any` in their routing.

## How a hero skill uses it (D-142)

1. **Find the initiative first.** From the brief (D-89 threads are handed it),
   else `pa project` to list and match, else ask the director. A hero skill
   never creates an initiative; the lifecycle skill does (D-129). Working
   without one is fine: stamp the work as loose (D-141), and the lifecycle
   skill adopts it later with `pa stamp --initiative`.
2. **Read before writing.** `pa artifacts --initiative <key>` for what exists;
   `projects/<key>/intent.md` for the shared intent; the registers for open
   questions and decisions already made. Do not re-ask a decided question.
3. **Stamp everything it makes**: `pa template new <id> --initiative <key>`
   for a new document, or `pa stamp <file> --initiative <key> --template <id>
   --stage <stage> --from <art_ id>` for one made another way. Datasets given
   to a project with `pa project --data` are stamped already.
4. **Add to the registers, not to prose**: evidence with its source, open
   questions with an owner, decisions (supersede, never edit), ready checks.
5. **Write only its own sections** of the intent document; suggest the rest.
6. **Extend in its own space.** New fields go in its own artifacts and
   records (documented in its schemas). Never add keys to an initiative's
   card except through `pa project`; never add record types to the registers.
   A new kind of artifact is a new template, not a new field on the card.

## What the lifecycle skill does with it (D-129)

On "I'm working on a new feature": find or create the initiative
(`pa project`), make its intent document and registers
(`pa template new initiative-intent`, the first `pa register`), list the
person's files on it (`pa stamp context/… --initiative`), adopt loose work
(`pa artifacts --loose`), then show the stages with what each produced
(`pa artifacts --initiative … --stage …`) and the runs (`pa runs`). Stage
state is read from runs and artifacts, never stored (D-141).

## Forward compatibility with upstream

Upstream's project table is untouched (D-121). Ids use upstream's UUID format
with a prefix, so a production store can keep them as they are. An initiative
can name its upstream project in `omnigent_project`; sessions already belong
to an upstream project and runs carry their session, so every link back to
upstream goes through ids upstream already has. A registry service can
replace `artifact_registry()` without changing a stamp.

## Decided by Claude while building

| D | Choice | Why |
|---|---|---|
| D-138 | Initiative ids `ini_…` and artifact ids `art_…`, each a type prefix and a 32-character UUID; a fixed key that is the file's name; the name can change | Names were the only key, and a rename broke every link. Upstream's id format, so production can keep them |
| D-139 | One `template.json` contract with three kinds (markdown, records, page), versioned `id@n`, in `templates/` or a workflow's `templates/`; older pages read as `page` | Geoff named two kinds; the page kind is what the existing templates already are, and leaving them out would split the Library from the model |
| D-140 | The tie from an artifact to its initiative is a stamp inside the file; the registry is assembled by reading files; the person's `context/` files and files that cannot hold a stamp are listed on the card instead | A stamp travels with a copy and cannot fall out of step with a list; the person's own documents are theirs and are linked, never changed (D-129) |
| D-141 | An artifact may be loose (no initiative); stages are a list of tags, never a gate; stage state is derived from runs and artifacts | The research thread: discovery and delivery run at once and work loops back. Stand-alone use of a hero skill must still work |
| D-142 | The hero skill contract above: find, read, stamp, register, own sections, extend in your own space; decisions are superseded, never edited, and `pa set` enforces it | Skills from different authors extend one shared model without stepping on each other |

## Open questions for Geoff

| # | Question | Recommended | Built as |
|---|---|---|---|
| IN-1 | Is an initiative the same thing as a project with a goal, or a separate layer above projects? | The same thing: one record, the card gains an id | Recommended |
| IN-3 | What is the shared representation of intent? | A short intent document with stage-owned sections plus four shared registers (evidence, questions, decisions, ready checks) | Recommended |

(IN-2, where the tie from artifact to initiative lives, was settled as a build
choice, D-140.)

## Not built yet

- The project page does not show the registry or the registers; the Hangar has
  no shelf for templates. Both read the same files when built.
- No hero workflow names a `template` in its `work_products` yet, and none
  stamps what it makes; each needs its SKILL.md updated (next, with the hero
  skills refresh).
- The lifecycle skill itself (D-129).
- `omnigent_project` and `external` are described, not written by any command.
- No arc uses `alternatives` or `onboarding-track` yet; they wait for the
  arcs to be rebuilt (D-148 to D-152).

## Where

`skills/view-kit/scripts/pa.py`, section "initiatives, artifacts and
templates": `pa project` (ids), `pa stamp`, `pa artifacts`, `pa template`,
`pa register`, and the decision guard in `pa set`. Templates:
`workspace/templates/initiative-intent/`, `workspace/templates/initiative-registers/`.
Tests: `tests/test_slim_initiatives.py`.
