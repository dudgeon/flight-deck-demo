# Decision note: the hero-skill set and the lifecycle

**Decided** 22 November 2026 by Geoff, on the walkthrough. **Recorded as**
D-148 to D-152 (HS-1 to HS-5). **Written by** Claude, in the thread
"Research the product lifecycle and AI help".

## Links

- Walkthrough (live, with Geoff's answers): https://claude.ai/artifact/P3hZWy2Ht6es1KCxMDLTEv
- Walkthrough, archived offline copy: [index.html](index.html), with the
  answers as saved in [answers.json](answers.json)
  (`docs/decision-artifacts/2026-11-21-hero-skills-and-lifecycle/`)
- Research: [lifecycle-research.md](../../product/lifecycle-research.md)
  (sources, seven findings, the recommendation, checkpoints, stages,
  registers, widgets)
- Skill taxonomy: [skill-taxonomy.md](../../product/skill-taxonomy.md)
  (tiers, one card per skill, how work moves, coverage of the ten PM jobs,
  the rule for adding a skill)
- Decision log: [decisions.md](../../product/decisions.md), section "Hero
  skills and the lifecycle"; status in
  [decision-index.md](../../product/decision-index.md)
- Pull request: https://github.com/dudgeon/flight-deck-demo/pull/41
- Source research on Geoff's Mac mini: `project-agent-and-harness/` (the
  skill rigidity spectrum, PM agents' jobs to be done, the cross-ecosystem
  lifecycle map, the shaping and dependency agents, the Pathfinder design)

## What Geoff asked

Refine the hero skills into a small, flexible set: don't subdivide the
process into many subskills, and don't make it rigid. Later, from his
comments on the Skills and Templates Atlas: the requirement catalog needs one
home and a way to toggle between phases; each dependency has several options,
so an analysis of alternatives with scope and delivery levers is needed; and
a skill is needed for engaging capability and platform owners, from
self-serve sign-ups to due diligence with agent or human counterparties.

## The decisions

### D-148 (HS-1): five arcs, two moves, one companion

**Picked:** five arcs, two moves, one companion (the recommendation).

- **Arcs:** problem discovery, intent shaping, PRD to dependencies, Engage
  owners and **Deliver**.
- **Moves,** offered on any artifact: Review and Decide.
- **Companion:** the feature lifecycle skill (D-129).

**Geoff's note:** "Delivery status should just be called deliver, and
include things like statusing, but other things as well. PRD to
dependencies will be complex and multi stage, including the analysis of
alternatives."

**Rationale:**

- **Where the lines fall.** The set is split by the person's goal and by
  the agent's stance (produce, enforce or up-level), the two lines the
  evidence supports. Steps are merged only when they share both, so
  shaping (interrogate, never fill in the answer) stays apart from
  cataloging (produce).
- **Choose sits with mapping.** Geoff's Pathfinder design keeps a fit
  record for every option considered and builds the delivery plan from
  them, so choosing belongs beside mapping. PRD to dependencies therefore
  runs Specify (the catalog), Map (the board) and Choose (the alternatives,
  then a phased roadmap), and the person can move between the three.
- **How Choose works.** It uses Pathfinder's four kinds of alternative:
  capability swap (including build), scope trade, resequence, and presets.
  It shows at most four alternatives beside the baseline, each saying what
  it gives up. Effort and waiting stay as separate numbers.
- **Why onboarding is its own arc.** Onboarding with other teams runs for
  weeks, through several owners and gates. That is a different goal and
  stance from choosing, and Pathfinder puts it downstream "with their own
  skills", so it gets its own arc, Engage owners. For each step, the
  agent's reach is set by who answers: self-serve, another agent or a
  person.
- **Deliver is wider than status.** Geoff's rename makes status updates one
  part of delivery work. What else belongs in it (release readiness,
  rollout, launch comms) is for the Deliver card in the taxonomy. It also
  bears on HS-8, which holds launch and go-to-market.

**Considered:**

- Keep the seven workflows and only re-tag them.
- Engage as a move with four arcs.
- The catalog at the end of intent shaping.
- Three arcs (Understand, Define, Deliver).

### D-149 (HS-2): a suggested path plus checkpoints

**Picked:** suggested path plus checkpoints (the recommendation).

**Geoff's note:** "Completion of all components matters more to me than
enforcing a sequence; and the skill should allow and support flipping
between components, leaving and returning, working on other product
lifecycle phases, etc. it should also allow for repeated loops of the same
initiative through all phases."

**Rationale:**

- **Fix the ritual, free the content.** The good skills Geoff collected fix
  only what must always hold and leave the rest to judgment.
- **It fits the strictness levels.** At light touch the agent skips more of
  the suggested steps, at by the book it walks them all, and the
  checkpoints never move.
- **Completion is the measure.** Geoff's note makes it so: a skill shows
  which components are complete, not which step comes next. Every arc can
  be entered, left and re-entered, and an initiative can loop through all
  the phases again.

**Considered:**

- Keep the fixed step list.
- No steps at all.

### D-150 (HS-3): one Discover stage; stages match the arcs

**Picked:** something else. Geoff's note: "Discover and learn should be the
same thing (push back if I'm missing something); also the answer here needs
to align to the answer to decision 1."

**What Claude chose from that:**

- **Five stages, one per arc:** Discover, Shape, Specify, Engage, Deliver.
- **Specify covers all of PRD to dependencies.** That is its Specify, Map
  and Choose parts.
- **Decide is a move,** not a stage.
- **Stages are tags, never gates** (D-141), and Deliver loops back to
  Discover.

**Rationale:**

- **No pushback on the merge.** Post-launch feedback triage is the same
  synthesis job as discovery, and the recommendation already had problem
  discovery take post-launch feedback rather than adding a skill.
- **One caution, handled.** The one thing Learn named that discovery does
  not do by default is checking what shipped against the intent's success
  measures. That is kept as a post-launch focus of problem discovery, so it
  isn't lost.
- **Why one stage per arc.** Matching stages to arcs means the progress
  strip, routing and the Library all use one vocabulary.
- **Easy to revise.** Geoff can change the stage list later without
  changing the data model, because stage is a loose tag in it.

**Considered:**

- Six tags with Learn added.
- Keep today's six.
- Four broad stages.

### D-151 (HS-4): the shared registers live on the initiative

**Picked:** on the initiative, shared (the recommendation). No note.

Evidence, open questions, decisions and ready checks are four registers on
the initiative, already built as `pa register` (D-141, D-142). Skill
datasets keep their own records and link to these by id.

**Rationale:**

- **The seam nobody has solved.** Without shared registers, a decision made
  while shaping is invisible to the dependency board. None of the nine
  companies studied has solved this.
- **The checkable layer.** These four registers are the layer the rigidity
  research says to make deterministic, and what Pathfinder keys by stable
  id.

**Considered:**

- Keep them in each skill's dataset.
- Share only decisions.

### D-152 (HS-5): the shared widgets and the alternatives worksheet first

**Picked:** shared widgets and the alternatives worksheet first (the
recommendation).

**Geoff's note:** "There is another worker working on a reusable decision
brief skill. Coordinate with that agent and include their work in your
analysis."

**Order:**

1. The five shared widgets: evidence chip, open-question card, decision
   record, ready checklist and initiative header.
2. The analysis-of-alternatives worksheet: option cards with evidence,
   scope and delivery lever toggles, a phase lane that redraws, and a
   commit step that writes to the decisions register.
3. The per-skill additions.

The template redesign stays parked, so this sets the order, not the look.

**Coordination with the decision brief skill.** This was agreed with the
thread "Build a reusable decision brief skill" on 22 November:

- **One brief layout.** The Decide move calls the `decision-brief` skill
  for complex decisions. That means a choice with real trade-offs, one that
  is hard to undo or visual, or several linked decisions. A single simple
  choice stays a question card.
- **Choose hands over to a brief.** When the person must pick between
  alternatives, Choose hands its shortlist to a brief.
- **One data file per brief.** The brief skill writes a single JSON file,
  `briefs/<slug>.json`, holding the decisions, the options with their
  consequences, and one recommended option.
- **Answers land in the decisions register.** `brief.py record` writes each
  answer to the initiative's decisions register as a
  `pa register <ini> decision` entry, so a brief's outcome lands in the
  same place D-151 puts every decision.
- **Same note format.** `brief.py note` writes notes like this one.

**Rationale:**

- **Shared by every skill.** The shared widgets show the registers that
  every skill uses, so they pay off everywhere.
- **The most interesting piece.** Geoff singled out the alternatives
  worksheet.
- **No reinvented layouts.** One brief layout saves tokens and keeps the
  experience consistent.

**Considered:**

- Per-skill widgets first.
- The worksheet only.

## Still open

The skill taxonomy's own questions come next, one at a time:

- **HS-6:** should a tier field go in the workflow manifest?
- **HS-7:** should the four-question rule gate new hero skills in the
  Hangar?
- **HS-8:** launch and go-to-market as a held arc. It now overlaps with
  Deliver's wider scope.

## What happens next

Nothing is built yet. The follow-up work, in order:

1. Merge the two requirement workflows into PRD to dependencies, keeping
   the old ids so scenarios still run.
2. Add checkpoints to `workflow.json` and `pa check`, and completion state
   per component.
3. Set the stage list to Discover, Shape, Specify, Engage and Deliver.
4. Rename the delivery arc to Deliver. Its id `delivery-status` stays until
   a rename is decided (D-35).
5. Offer Review and Decide on every artifact, with Decide using the
   decision brief.
6. Build the data-model thread's records templates for alternatives and
   onboarding tracks.
7. Build the five shared widgets, then the alternatives worksheet.
