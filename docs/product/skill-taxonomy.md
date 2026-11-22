# The skill taxonomy

Date: 2026-11-22. Filed by Claude (thread "Research the product lifecycle and
AI help"). Status: **proposal, not decided.** It builds on the recommendation
in [lifecycle-research.md](lifecycle-research.md) (HS-1, open) and on the
initiative model that is already built ([initiatives-and-templates.md](initiatives-and-templates.md),
D-138 to D-142). Geoff (2026-11-22): the skill template redesign is paused
and the overall skill taxonomy goes on. So this note leaves out widgets and
templates (HS-5). It covers which skills exist, what each one is for, how
they hand work to each other, and the rule that stops the set from growing
into many small subskills.

## 1. Four tiers

Every skill in `skills/` and `workspace/.claude/skills/` belongs to one tier.
The tier decides how the skill is shown and how Aviator offers it.

| Tier | What it is | Shown | How it starts | Today |
|---|---|---|---|---|
| **Companion** | Holds the initiative: finds or creates it, links it, says where it stands and offers the next arc | Not in the Library (D-129) | "I'm working on a new feature", or opening an initiative | the lifecycle skill (D-129, not built) |
| **Arc** | Something a person sets out to do, from material to a result | In the Library as a hero skill | Named, offered once on a clear fit (D-128, D-146), or from the companion | problem discovery, intent shaping, PRD to dependencies, engage owners, delivery status |
| **Move** | Something done to an artifact at any point, in any arc | As a launcher on an artifact and an offer in the chat, not as a stage | From an artifact, or offered when an arc reaches one of its moments | review, decide |
| **Kit** | Tools that the other tiers and the Hangar use | Never | Called by other skills | view-kit, participants, document-collaboration, scenario-builder, build-person, product-aviator-design, frontend-design, director, omnigent-operator |

A person meets at most seven names: the five arcs and, when they open an
artifact, the two moves on it. The companion and the kit skills work out of
sight.

## 2. The eight skills

Each card gives the skill's job, its stance (produce, enforce or up-level,
from the rigidity research), the stages it tags, where it can be entered,
what it reads from and writes to the initiative registers (D-142), and its
checkpoints (HS-2).

### Feature lifecycle (companion)

- **Job:** keep one initiative whole while work moves between arcs and
  people. It finds or creates the initiative, links related ones, shows the
  stage tags and what is open, and offers the next arc in one line.
- **Stance:** orient and offer. It never does an arc's work itself.
- **Reads:** the whole initiative: stage state (derived, D-141), the Ready
  checks, open blocking questions.
- **Writes:** the initiative record and its links. The registers are only
  written by the skills that own the work.
- **Next-arc rule:** offer the arc whose Ready checks fail first, in lifecycle
  order. If a blocking question is open, offer Decide (or Engage owners, when
  the question is an owner's) before any other arc. Offer once (D-128). When the person declines, it stays quiet until
  something changes.

### Problem discovery (arc)

- **Job:** turn raw material (interviews, tickets, feedback, notes,
  post-launch metrics) into problems worth solving, each with its evidence.
- **Stance:** produce, with checked quotes. The person chooses.
- **Stages:** Discover, Learn. (Learn when the sources come after a launch.)
- **Enter with:** any pile of sources, or a question ("what's going on with
  onboarding?").
- **Writes:** Evidence (sources, checked quotes), Open (problems not yet
  chosen), Decisions (which problem is worth solving, and why).
- **Hands to:** intent shaping, through the chosen problem and its evidence.
- **Checkpoints:** every problem cites a source; every quote is checked
  against its source; the person chooses.

### Intent shaping (arc)

- **Job:** take an idea from a sentence to something a team could commit to,
  by questioning the person rather than writing for them.
- **Stance:** up-level. One question at a time, with the agent's guess, and
  it never fills in the person's answer.
- **Stages:** Shape.
- **Enter with:** a sentence, a chosen problem, or a brief to strengthen.
- **Writes:** Open (gaps, each with an owner), Decisions (scope in and out),
  Ready (the depth checks from the intent framework); it owns the intent
  document's problem, customer, outcome and scope sections (D-142).
- **Hands to:** PRD to dependencies, through the intent document and its
  Ready checks.
- **Checkpoints:** never writes the person's answer; every gap has an owner
  or is marked open; the person says when the target depth is reached.

### PRD to dependencies (arc)

- **Job:** turn intent or an existing PRD into requirements, find what each
  one depends on, and choose how to satisfy them, with a phased roadmap.
- **Stance:** produce, then enforce the trace; the person chooses.
- **Stages:** Specify, Map, Choose (Choose is a step of this arc, not a
  stage). The person can move between the three at any time (Geoff,
  2026-11-22).
- **Enter with:** an intent document (starts at Specify), a PRD (Specify), a
  requirements list (Map), or a board with options (Choose).
- **Writes:** Evidence (each requirement traced to a line; each option's
  evidence), Open ("could not find" dependencies), Decisions (each chosen
  option; a rejected option keeps its reason), Ready (the hand-off checks);
  it owns the intent document's approach and dependencies sections.
- **Hands to:** engage owners, through each chosen option that needs an
  owner; delivery status, through the roadmap.
- **Choose follows Pathfinder:** four kinds of alternative (capability swap
  including build, scope trade, resequence, presets), at most four beside
  the baseline, each saying what you give up; effort and waiting as separate
  numbers; every number labelled with its source.
- **Checkpoints:** every requirement traces to a line; every dependency has
  evidence or is listed "could not find"; every option shows its cost in
  time, scope and risk; the person chooses.

### Engage owners (arc)

- **Job:** get each chosen platform, process or capability in place, by
  running its owner's onboarding procedure: intake, access, due diligence
  and gates, terms, provisioning, integration ready. Onboarding at a large
  enterprise runs for weeks across several teams, so this is an arc, not a
  move (it passes question 4 of the rule in section 5; Pathfinder also puts
  it downstream "with their own skills").
- **Stages:** Map, Deliver.
- **Enter with:** the chosen options from PRD to dependencies, or one
  capability the person names ("get us onto the notifications platform").
- **Stance:** set by the counterparty. *Self-serve:* the agent acts after one
  yes from the person (off on the offline work Mac). *Agent:* the agent
  exchanges with the owner's agent, and a person approves anything that
  commits. *Person:* the agent drafts the smallest question riding a real
  ask, a person sends it, and the agent tracks the wait.
  Each step of a procedure can have a different counterparty, so the kind is
  set per step, not per capability.
- **Grows by maturity (from Geoff's dependency research):** crawl, the agent
  drafts asks and pre-fills intake forms from the spec and a person sends;
  walk, it submits where an owner's intake accepts agent requests, on behalf
  of a named person; run, routine requests are approved by policy and
  exceptions go to people. Gate evidence packs are pre-filled from the
  first stage and never submitted without a person.
- **Writes:** Evidence (answers and gate evidence, with their source, written
  back as context so no owner is asked twice), Open (steps waiting, with
  their owner and lead time), Decisions (terms accepted, due-diligence
  findings accepted).
- **Hands to:** delivery status, through each capability's ready date; back
  to Choose when an owner's answer changes an option's cost or date.
- **Checkpoints:** nothing binding is sent, submitted or signed without a
  person's yes; every step names its owner and its evidence; an answer once
  given is never asked again.

### Delivery status (arc)

- **Job:** check a plan against what is happening, project the date when
  something moves, find ways to recover, and write the update for whoever
  needs it.
- **Stance:** produce.
- **Stages:** Deliver.
- **Enter with:** a roadmap from PRD to dependencies, or any plan or list of
  milestones.
- **Writes:** Evidence (what each owner said), Decisions (a recovery chosen),
  Open (dates at risk); it owns the intent document's delivery section.
- **Hands to:** problem discovery (Learn) after launch; to choose, when a
  recovery needs a new option.
- **Checkpoints:** every date change names its cause and source; the update
  says what it asks of the reader.

### Review (move)

- **Job:** get second opinions on any artifact from agents and people, and
  gather every finding in one list.
- **Stance:** enforce.
- **Offered:** on any artifact (a problem brief, an intent brief, a PRD, a
  board, a status update), and at the end of any arc.
- **Writes:** findings (its own records), and Decisions (the author's call on
  each finding).
- **Checkpoints:** every finding points to a line and names who raised it;
  the author decides each finding.

### Decide (move)

- **Job:** settle what is open, one question at a time, and record the
  reason.
- **Stance:** present the smallest question; the person decides.
- **Offered:** on any open question, from any skill, and by the companion
  when a blocking question holds up an arc.
- **Writes:** Decisions, which supersede and never edit (D-142).
- **Checkpoints:** the person decides; every decision has a reason.

## 3. How work moves

The registers on the initiative carry the work, not the skills. An arc never
calls another arc. It finishes or pauses, and leaves the initiative in a state
that the companion reads.

```
                 ┌──────────── companion: feature lifecycle ────────────┐
                 │  reads stage state, Ready, Open; offers the next arc │
                 └──────────────────────────────────────────────────────┘
 sources ─▶ Problem discovery ─▶ Intent shaping ─▶ PRD to dependencies ─▶ Engage owners ─▶ Delivery status
   ▲          (Discover, Learn)       (Shape)       (Specify ⇄ Map ⇄ Choose)   (onboarding)      (Deliver)
   └──────────────────────────── after launch: feedback and metrics ─────────────────────────────┘

 Moves on any artifact:  Review · Decide
 Shared on the initiative: Evidence · Open · Decisions · Ready
```

Work may go backwards at any time: a requirement reworded in Choose
reopens a scope decision from shaping; a slipped date in delivery reopens
Choose. Going back is an ordinary entry into the earlier arc, not a failure.

## 4. Coverage against the ten PM jobs

The jobs come from Geoff's jobs-to-be-done map (J1 to J10). The set covers the
jobs where agents have the best evidence, and it deliberately leaves the
choosing jobs with the person, with the agent preparing.

| Job | Covered by | Note |
|---|---|---|
| J1 Customer contact and research synthesis | Problem discovery | Interviewing stays with the person; synthesis with checked quotes is the agent's |
| J2 Opportunity, strategy, vision | Not an arc; Decide on the choices | Lowest agent suitability in the evidence; problem discovery prepares, the person chooses |
| J3 Shape the solution | Intent shaping | Up-level stance |
| J4 Write, review, ratify the spec | PRD to dependencies (Specify), Review | Ratifying stays with the person; the shaper never ratifies |
| J5 Prioritise and roadmap | PRD to dependencies (Choose) | Agent prepares options and levers, person decides |
| J6 Manage delivery | Delivery status, Engage owners | Onboarding with other teams is where enterprise delivery time goes (Pathfinder's cause codes: access, waiting, gates) |
| J7 Launch and go-to-market | Gap | A candidate next arc; held until a demo needs it |
| J8 Stakeholder and exec comms | Delivery status (the update), Review | An audience choice on the update, not a skill of its own |
| J9 Metrics and experiments | Problem discovery (Learn) | Metrics readouts come in as sources |
| J10 Post-launch feedback triage | Problem discovery (Learn) | The job with the best evidence that agents help |

## 5. The rule for adding a skill

This rule keeps the set small. Before anyone adds a hero skill, in the repo or
in the Hangar, the proposal answers four questions in order. The first "yes"
decides where the work goes.

1. **Is it something done to an artifact at any stage?** Then it is a move,
   or an option on an existing move.
2. **Does it share an existing arc's stance and hand straight into or out of
   it?** Then it is a step or half of that arc (as the catalog and Choose
   are for PRD to dependencies).
3. **Is it the same job on different sources or for a different audience?**
   Then it is a focus or input option on the existing arc (as Learn is for
   problem discovery, and the audience switch is for the status update).
4. **Is it a different goal for the person, with a different stance?** Only
   then is it a new arc, and it says which stages it tags and which register
   entries it writes.

A Hangar workflow that fails the rule can still be built and flown. It is
listed as "start only when named" (D-136) and is not offered as a hero skill.

## 6. What this changes, if accepted

- `workflow.json` gains `tier` (companion, arc, move, kit). The Library shows
  arcs. Moves are offered through `launchers` on every artifact kind. `pa
  workflows` and the routing ladder read the tier, so a move is never
  offered as a starting point for open work.
- `routing.stage` becomes a list (the model already allows stage lists,
  D-141). `lifecycle.json` loses Decide and gains Learn.
- The routing eval suite (D-133, D-143) gets one case per tier boundary:
  "review this PRD" starts Review, not PRD to dependencies; "what should we
  build next?" gets no arc offer; "I'm working on a new feature" goes to the
  companion.
- The `scenario-builder` and Hangar new-workflow flow ask the rule's four
  questions before making a new hero skill.

## 7. Open questions

These follow HS-1 and wait for it. They will be asked one at a time after it.

| Label | Question | Recommendation |
|---|---|---|
| HS-6 | Should "tier" be a field in the workflow manifest, read by routing and the Library? | Yes |
| HS-7 | Should the four-question rule gate new hero skills in the Hangar? | Yes, as a prompt in the new-workflow flow; failing it lists the workflow as "start only when named", not blocked |
| HS-8 | Launch and go-to-market (J7): a fifth arc now, or held? | Held until a demo needs it |
