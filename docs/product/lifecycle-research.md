# The product lifecycle, AI help, and the hero-skill set

Date: 2026-11-21. Filed by Claude (thread "Research the product lifecycle and
AI help"). Status: **research and a recommendation, not decided.** The open
questions are labelled HS-1 to HS-5 and are being put to Geoff one at a time.
Nothing here has a D-number yet. The walkthrough page that puts them to Geoff
is archived in [../decision-artifacts/](../decision-artifacts/).

Geoff's brief: refine the hero skills (problem discovery, intent shaping, PRD
to requirements, requirements to dependencies, decision review, document
review, delivery status, plus the lifecycle skill of D-129), with the widgets
and worksheet templates each needs, **without subdividing the process into
too many subskills and without making it rigid.**

## Where this comes from

1. **Geoff's own research library** on the Mac mini
   (`claude-home/project-agent-and-harness/`, about 1,500 source notes). The
   pieces read for this note:
   - `tasks/research-skill-rigidity-spectrum/` (01 synthesis, 03 design
     guide): how skills set rigidity, with randomised evidence on stance.
   - `tasks/research-pm-agents-jobs-to-be-done/00-brief.md` and the jobs map:
     ten PM jobs, where agents have and have not worked.
   - `tasks/pdlc-cross-ecosystem-map/`: the lifecycle across nine companies
     (Stripe, Ramp, Shopify, Anthropic, Atlassian, Intercom, Airbnb, Spotify,
     Block).
   - `tasks/define-shaping-and-dependency-agents/00-overview.md`: the two
     modules (intent shaping, delivery dependency mapping) and the intent
     lifecycle record.
   - `tasks/pathfinder-design/pathfinder-component-design.md`: seven typed
     records with stable keys, files as the truth.
   - Geoff's two first-party proposals, "Building and accelerating the intent
     factory" and "Intent shaping in a well-managed environment" (source
     notes `geoff-building-accelerating-intent-factory`,
     `geoff-intent-shaping-well-managed-environment`).
2. **Public lifecycle frameworks**, to check the stage list against practice:
   the Design Council's Double Diamond
   (https://www.designcouncil.org.uk/our-resources/framework-for-innovation),
   dual-track agile (Jeff Patton, https://jpattonassociates.com/dual-track-development/),
   Teresa Torres's continuous discovery and opportunity solution tree
   (https://www.producttalk.org/opportunity-solution-tree-origin/),
   Shape Up (https://basecamp.com/shapeup), Amazon's Working Backwards
   PR/FAQ (https://www.aboutamazon.com/news/workplace/an-insider-look-at-amazons-culture-and-processes),
   and spec-driven development (GitHub Spec Kit, Kiro; notes already in
   Geoff's library).

Evidence labels carry over from the library: nearly everything about PM
agents is first-party or anecdote. The strongest independent evidence is on
*stance* (how a skill treats the person's thinking), from education and
decision-support studies, not product work.

## Seven findings

**1. The jobs are stable; the frameworks agree on a few kinds of thinking,
not on steps.** Atlassian's CPO: the PM job "is really the same as it always
was". The jobs map has ten recurring jobs. The public frameworks reduce to the
same four moves, named differently: understand the problem (Double Diamond's
Discover and Define; Torres's opportunity space), shape a bet (Shape Up's
shaping and pitch; Amazon's PR/FAQ; Double Diamond's Develop), commit and
build (Shape Up's betting table and cycle; delivery), and learn (Torres's
assumption tests; post-launch triage). Nobody who is doing well runs more
than four or five named phases.

**2. Stages overlap and loop; they are not a sequence of gates.** Dual-track
agile runs discovery and delivery *at the same time*, as two kinds of work,
not two teams. Torres's discovery is weekly and never "done". Geoff's own
dependency research shows the arrow back: a requirement is reworded once its
delivery path is known (the "pre-approved" offer example). The cross-ecosystem
map finds code to review to release documented everywhere and goal to intent
inferred or unknown in six of nine. So stage is a lens on the work, not a
place the work is.

**3. Deciding, reviewing and reporting are not stages; they happen at every
stage.** A decision is needed in discovery (which problem), shaping (what is
out of scope), specifying (which wording) and delivery (cut scope or slip).
Review is the same: a problem brief, an intent brief and a PRD all get second
opinions. The rigidity research names these as "rituals" (silent read,
alternatives required, pre-mortem, senior speaks last) that are fixed in form
and open in content, and that apply to any artifact.

**4. A skill is a score, not a dial.** Every real skill file sets its freedom
per step. Make a step rigid only where a rule must always hold (every claim
has a source link, the person decides, the definition of ready is checked);
leave the rest to the model with a stopping condition. "Fix the ritual, free
the content." This is how a small set of skills can stay flexible: few fixed
checkpoints, a free path between them. D-130's strictness levels (light
touch, guide, by the book) already move along this axis.

**5. A skill should do one job: produce, enforce or up-level.** The designs
are opposite (deliver the answer vs withhold it). Intent shaping is an
up-level job (ask before drafting, one question at a time with a guess, never
fill the person's answer). PRD to requirements and dependency mapping are
produce jobs with an enforce check at the end. Document review is enforce.
Mixing an up-level step and a produce step in one skill is fine only as
clearly separate steps. This is the limit on merging: merge skills that share
a stance, not ones that don't.

**6. AI is best at bounded, reviewable work, and worst at choosing.**
Strongest evidence: feedback and research synthesis *with quotes checked
against source* (Torres found about 30% of a model's direct quotes wrong or
missing), status aggregation and drafting, spec first drafts plus gap review,
"ask the org" Q&A. Weakest: choosing the opportunity, strategy, trade-offs,
interviewing. Over-reliance is the default and grows as the agent improves,
so the person keeps the decision and the agent makes verification cheap
(show the line and its source).

**7. The seam nobody has solved is research to intent with the evidence still
attached, across people.** In none of the nine companies is it documented.
Each closes it by role blur, a shared place, a senior person, or an object
that carries the *what* without the *why*. This is the strongest argument for
Flight Deck's initiative record: if every skill writes its evidence, open
questions and decisions to the same initiative, the *why* travels with the
work. Geoff's Pathfinder design reaches the same place from the other side
(typed records with stable keys, files as the truth, views generated over
them).

## The recommendation

**Four arcs, two moves, one companion.** Seven skills, not eight, and only
four of them are stages.

| Kind | Skill | Stages it serves | Stance | Built from |
|---|---|---|---|---|
| Companion | **Feature lifecycle** (D-129) | all | Orient and offer | new; owns the initiative record |
| Arc | **Problem discovery** | Discover, Learn | Produce (synthesis with checked quotes) | `problem-discovery`, plus post-launch feedback as a source |
| Arc | **Intent shaping** | Shape | Up-level (interrogate, never fill the answer) | `intent-shaping` |
| Arc | **PRD to dependencies** | Specify, Map | Produce, with an enforce check | `prd-to-requirements` and `requirements-to-dependencies` as two halves of one skill; enter at either half |
| Arc | **Delivery status** | Deliver | Produce | `delivery-status` |
| Move | **Review** | any | Enforce | `document-review`, offered on any artifact |
| Move | **Decide** | any | Present the smallest question; person decides | `decision-review`, offered on any open question |

Why this shape:

- **Arcs are the person's goal, moves are rituals.** An arc is something a
  person sets out to do ("make sense of these interviews", "get this idea to
  committable"). A move is something done *to* an artifact at any point
  ("get second opinions", "settle what's open"). Moves appear as launchers on
  an artifact and as offers in the director (D-128), not as stages.
- **One merge, chosen by stance.** PRD to requirements and requirements to
  dependencies share a stance (produce, then check) and a hand-off (the
  catalog is the board's input). Geoff's own two-module model treats
  "validated requirements to delivery map" as one module. Intent shaping
  stays separate because its stance is the opposite.
- **Learn without a new skill.** Post-launch feedback triage is the job with
  the best evidence that agents help, and it is the same synthesis job as
  discovery. Problem discovery takes post-launch feedback and metrics notes
  as sources and tags its output Learn, which loops straight back to
  Discover.
- **Flexible by construction.** Any arc can be entered at any point (bring a
  PRD and start at its catalog half; bring a sentence and start shaping).
  Stages are tags, steps are suggested, and only a few checkpoints per arc
  are fixed (below).

Alternatives considered (on the walkthrough with their trade-offs): keep the
seven as they are and only re-tag stages; three arcs (Understand, Define,
Deliver), which is fewer but forces an up-level and a produce stance into one
"Define" skill; and something else.

## Fixed checkpoints, free path (HS-2)

Today each workflow's `steps` list reads as a fixed sequence. Recommended:
keep `steps` as the suggested path the agent may skip or reorder, and add a
short list of **checkpoints** per arc that always hold, whatever the
strictness level. These are the checkable layer the rigidity research says to
make deterministic.

| Arc or move | Checkpoints that always hold |
|---|---|
| Problem discovery | Every problem cites at least one source; every quote is checked against its source; the person chooses what is worth solving |
| Intent shaping | The agent never writes the person's answer; every gap has an owner or is marked open; the person sets the target depth and says when it is reached |
| PRD to dependencies | Every requirement traces to a line in the document; every dependency has evidence or is listed "could not find"; asks are drafted, a person sends |
| Delivery status | Every date change names its cause and source; the update says what is asked of the reader |
| Review | Every finding points to a line and names who raised it; the author decides each finding |
| Decide | The person decides; each decision records its reason and supersedes, never edits, an earlier one |

`pa check` can test the structural half of each (fields present, links
resolve) on the dataset, the way it checks routing today (D-136).

## Stages (HS-3)

Recommended stage list, as loose tags: **Discover, Shape, Specify, Map,
Deliver, Learn.** Decide leaves the list and becomes a move. A workflow, an
artifact and an initiative may carry several stages; nothing gates on a stage.
This was sent to the "Design template and initiative data model" thread,
which keeps stage a loose tag in its model so the list can change without
changing the model.

## The initiative's shared registers (HS-4)

Each skill keeps its own dataset today. Recommended: the initiative record
owns four registers that every skill reads and appends to, so the *why*
travels between skills and people (finding 7):

- **Evidence:** sources with links and checked quotes.
- **Open:** questions and assumptions, each with an owner and a blocking flag.
- **Decisions:** small, numbered, immutable records, superseded rather than
  edited, each with its reason.
- **Ready:** the definition of ready, as pass/fail checks with their reason.

Skill datasets keep their own records (problems, areas, requirements,
dependencies, milestones) and link to register entries by id. The registers
are the checkable layer; the documents are the judgment layer. The data
model work owns the shape; this note owns the reason. That work (PR 42,
[initiatives-and-templates.md](initiatives-and-templates.md)) builds the four
registers this way through `pa register`, and makes stages a list on every
artifact, never a gate (D-141). With it, dropping Decide and adding Learn is a
one-line change to `lifecycle.json`, plus a "What we learned" section in the
intent template owned by Learn.

## Widgets and worksheet templates per skill (HS-5)

"Have" are the views each workflow ships today. "Add" is recommended. Three
widgets are shared by every skill because they show the shared registers.

**Shared widgets (new):** an *evidence chip* (a claim with its source line,
one click to the source; the Torres check made visible), an *open-question
card* (owner, blocking flag, answer in place), a *decision record card*
(reason, who, what it supersedes), a *ready checklist* (pass/fail with the
reason), and an *initiative header* (name, id, stage tags, linked artifacts).

| Skill | Have | Add (widgets) | Worksheet templates (kind) |
|---|---|---|---|
| Feature lifecycle | project page, run card | stage strip with tags not gates; "what's next" offer | initiative record (json) |
| Problem discovery | focus form, sources, problems, summary | evidence chip on every quote; a "post-launch feedback" focus option | problem brief (markdown with frontmatter); problem list (json) |
| Intent shaping | target form, map, area, summary | one-question card with the agent's guess; pre-mortem card; assumption list | intent brief or one-pager (markdown with frontmatter); shaping map (json) |
| PRD to dependencies | scope form, catalog, board, review card, summaries | trace-to-line on each requirement; drafted-ask card; ready checklist at the hand-off | PRD or spec (markdown); requirements catalog (json); dependency board (json); asks (markdown) |
| Delivery status | plan, milestone, summary | cause-of-change chip; audience switch on the update | status update (markdown with frontmatter); milestone plan (json) |
| Review | findings, who form, consent question, summary | works on any artifact kind, not only markdown | review findings (json) |
| Decide | queue, card, summary | opens on any open-question entry, from any skill | decision log (json, from the Decisions register) |

## What this changes, if accepted

Not built. If Geoff accepts the shape, the follow-up work is: merge the two
requirement workflows into one with two entry points (keeping both ids as
aliases so scenarios keep working); add `checkpoints` to `workflow.json` and
to `pa check`; let `routing.stage` take a list; move Decide out of
`lifecycle.json` and add Learn; offer Review and Decide as launchers on every
artifact kind; build the five shared widgets in the view kit; and give the
eval suites (D-133) a stance check for intent shaping ("did the person's
answers change"), which the rigidity research says an up-level skill needs.

## Open questions

| Label | Question | Recommendation |
|---|---|---|
| HS-1 | What shape should the hero-skill set take? | Four arcs, two moves, one companion |
| HS-2 | How fixed should each skill's steps be? | Suggested path, plus a few checkpoints that always hold |
| HS-3 | Which stages, and are they gates? | Discover, Shape, Specify, Map, Deliver, Learn; tags, never gates |
| HS-4 | Where do evidence, open questions, decisions and readiness live? | On the initiative, shared by every skill |
| HS-5 | Which widgets and templates come first? | The five shared widgets, then the per-skill additions |
