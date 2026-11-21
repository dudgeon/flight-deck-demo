# Aviator as director: coordination, skill routing and persona strictness

Status: **proposed, nothing decided, nothing built.** Asked for by Geoff on
2026-11-21. Put to him as a walkthrough,
https://claude.ai/artifact/La4Qa5THk5JhwQBQGcVY7d (answers in its database,
collection `answers`; offline copy in
[../decision-artifacts/2026-11-21-aviator-coordination/](../decision-artifacts/2026-11-21-aviator-coordination/index.html)).
The open questions are labelled AV-1 to AV-6 and take D-numbers only when
Geoff answers them. Read with [modes-and-projects.md](modes-and-projects.md)
(D-89 to D-99, and D-116 to D-119 in PR 32) and the `director` skill (PR 33).

## What was asked

> Research the patterns that the Claude Code projects coordinator/director
> agent uses; we need to replicate those coordination patterns in the
> Product Aviator skill. As well, we need to think through an approach for
> how it guides the use of the hero skills for relevant tasks, while still
> coordinating open ended work and ideation when appropriate. This will
> require a lot of thinking and nuance, and we will need to test and
> optimize how strictly it applies the skills personae.

And, a minute later, an option to include:

> The user can say, I'm working on a new feature, which invokes a feature
> lifecycle skill and creates a new project to begin assembling assets.

## Sources

The coordinator's own instructions are not shareable, so the patterns below
are taken from **what it visibly does** in this project (Geoff's project
chat with its threads is the live example), and from public Anthropic
writing:

- [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system):
  a subagent brief needs an objective, an output format, guidance on tools
  and sources, and clear boundaries; vague briefs caused duplicated work and
  gaps. Scale effort to the ask (early versions spawned 50 subagents for
  simple questions). Subagents write results to files and pass references
  back. Prefer heuristics to rigid rules. Multi-agent costs about 15 times
  the tokens of chat and suits high-value, separable work; it fits poorly
  where everything shares context.
- [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents):
  routing (classify, then hand to a specialist) works when the categories are
  distinct and classification is accurate; orchestrator-workers when subtasks
  can't be predicted; start simple and add complexity only when it measurably
  helps.
- [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents):
  tasks, trials, graders, transcripts, outcomes; 20 to 50 tasks from real
  failures is a good start; test both that a behaviour happens and that it
  doesn't when it shouldn't; pass^k (all k trials pass) for behaviour people
  rely on; grade outcomes, not paths; read the transcripts; calibrate model
  judges against people and let them answer "unknown".
- [Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
  and [Optimizing skill descriptions](https://agentskills.io/skill-creation/optimizing-descriptions):
  only a skill's name and description are loaded until it is used, so the
  description carries routing; degrees of freedom (tight where mistakes are
  costly, loose where many approaches are valid); trigger evals with about
  20 should-trigger and should-not-trigger queries, near misses as negatives,
  three runs each, a fixed 60/40 tuning and held-out split.

## Part 1. Coordination patterns

Each pattern: what it looks like in a Claude Code project, and where Aviator
stands. "Has" means the `director` skill in PR 33 already says it.

| Pattern | As seen in a Claude Code project | In Aviator | |
|---|---|---|---|
| One thread per piece of work | Real work gets its own thread, named after the goal in the person's words. Quick questions stay in the main chat. | A thread per workflow run; other deep work on Aviator's judgment, said in one line. | Has |
| A written brief | The thread starts from a brief: the goal, what to read, what is decided, where the result goes. | `pa brief` writes it as a file. | Has |
| The smallest sign that fits | A quick answer gets the answer; work gets a short acknowledgement, then the result. No narration of the working. | One line and the run card when a thread starts; not yet a rule for every turn. | Gap |
| Only what needs the person | Progress goes on a checklist; the chat carries results, blockers and questions. Choices come one card at a time with a recommendation and "Something else" (D-32, D-33, D-105). Messages lead with the outcome. | Threads report at their own discretion (D-118). When Aviator itself stays quiet, and the card format, are not written down. | Gap |
| Hold while the person is talking | News from other threads waits for a break in the person's current exchange, unless it blocks them or something failed. | Not in the skill. AV-5. | Gap |
| Answers go to the owner | An answer given in the main chat reaches the thread that asked, in the person's own words. | The direct line (D-116) covers most of it. For an answer given on a card, Aviator forwards the exact words, marked as the person's. | Gap |
| Status from records | "Where are we?" is answered from reports and notes, not by rereading every thread. | `pa runs` and the run file's reports. | Has |
| Carry findings across | When one thread finds what another needs, tell that thread and say so in one line. | Section 3 of the skill. | Has |
| Only the person approves | A request from a thread or another agent is not the person's approval. Steps that can be undone go ahead and are reported; steps that can't wait for the person. | Not stated for threads. Matters once threads call participants or write outside the project. | Gap |
| Project memory | Lasting facts (who is who, what was decided, how the person likes to work) are saved once, so a new thread does not ask again. | Not built. Proposed: a `memory.md` per project, handed to every brief. | Gap |
| Close the loop | A thread ends when its work has ended, not when it is handed over; a document stays open until the person says it is good. | Run states finished and stopped exist. A "ready for review" state before finished does not. | Gap |
| Don't spawn for small things | Effort scales with the ask. | Each thread is a Claude Code process and about a minute per answer, so the bar must be explicit. | Gap |

**Proposed without asking** (none changes a decision Geoff made): the eight
gaps become rules in `skills/director/SKILL.md`, written as heuristics with
their reasons. A run gains a `review` state between working and finished.
Project memory is a file, not a service, so it works from a ZIP.

## Part 2. Routing to the hero skills

The hero skills are the workflows featured in the Library (D-83): problem
discovery, intent shaping, document review, PRD to requirements, decision
review, delivery status. Starting one changes the conversation: its persona
takes over, asks one thing at a time and holds a standard. That is right when
the person wants it and wrong in the middle of ideation. The costly mistake
is a **false start**; the cheap one is a missed offer.

### The routing ladder (AV-1, recommended)

| Rung | When | What Aviator does | Example |
|---|---|---|---|
| Named | The person names the skill, presses Start in the Library, or uses its verb ("shape this") | Start it in a thread | "Shape this using intent shaping." |
| Clear fit | The request fits one hero skill and there is material to work on | Offer once, in one line with a button; if declined, carry on openly and don't offer again until something new firms up | "Here are 40 interview notes, what's going on?" (problem discovery) |
| Open | Ideation, comparing directions, thinking out loud | Work openly as Aviator; offer once later when one idea firms up | "What else could we do about those calls?" |
| Quick | A lookup, a single card or summary, a question about the project | Just answer | "When is the steering meeting?" |

Signals that an open conversation has firmed up into a clear fit: one idea is
named and the person asks whether it is ready or good enough (intent
shaping); a document is named with a verb like review or catalog (document
review, PRD to requirements); a list of open choices appears (decision
review); a date or plan is in question (delivery status); a pile of raw
material arrives (problem discovery). Near misses that must **not** start a
skill: "shape the roadmap slide", "review my calendar", "what decisions did
we make last week" (a lookup, not a decision review).

Alternatives put to Geoff: start whenever it fits (fewest steps, most false
starts); ask what kind of work at each new topic (never wrong, tiring).

### "I'm working on a new feature" (AV-2, Geoff's option, recommended)

A **feature lifecycle** skill, Aviator's playbook for a goal project rather
than a seventh hero skill. On "I'm working on a new feature" (or "starting",
"kicking off", "new project for"):

1. Creates the project in its area (D-97), named in the person's words.
2. Asks only what it cannot find, then gathers what exists: files in
   `context/`, datasets from earlier runs (a problem picked in discovery), a
   PRD draft. It links, never moves or copies.
3. Shows a lifecycle view in the canvas: Discover, Shape, Specify, Map,
   Decide, Deliver, each with its hero skill, its state (from `pa runs`) and
   the assets it produced.
4. Recommends the next stage from what exists, as the clear-fit offer of the
   ladder. Stages can be skipped, entered at any point, or done again; each
   runs in its own thread.

The view is the project's spine: routing has context instead of guessing, and
the project page can show what is missing. Alternatives: no lifecycle skill
(projects by hand, nothing says what is next); a fixed pipeline (stages in
order, skipping needs an override; predictable for demos, fights how PMs work,
since a PRD often comes before any discovery).

Build questions, not for Geoff: how an agent creates a project (upstream's
projects route, plus our manifest file beside it, D-97); where the lifecycle
view's data lives (a project-level dataset drawn with the view kit).

## Part 3. Persona strictness

Each hero skill's persona has two kinds of rule:

- **Rules that never relax** (honesty and agency). Intent shaping never
  scores an area deeper than what exists to support it and never writes the
  intent for the person. Problem discovery reads only what it was given,
  states problems in the words of the people who have them and looks for
  evidence against. Document review attributes every finding to who raised
  it. Decision review records what the person picks; it does not pick.
  Delivery status checks with owners before projecting a date.
- **Style**: questions per turn, whether a missing piece blocks progress,
  whether it drafts for the person, how hard it challenges, how often it
  checks in.

Strictness is a setting for the style; the honesty rules hold at every level.

| Level | Behaviour | Example (hurried PM: "just put Problem as framed") |
|---|---|---|
| Light touch | Takes the person's word as evidence, marked as theirs, and keeps moving | Problem goes to 2 · Framed, "your word"; the brief says so. Bends the first honesty rule. |
| **Guide** (recommended default, AV-3) | Honesty rules hard, style flexible: a missing piece becomes a gap with who could close it, the score stays true, work moves on | Problem stays 1 · Spark; a gap is sent to Support Insights; on to Outcome. |
| By the book | Every area held to the framework's line before moving on; missing evidence stops the run | Problem needs you; Outcome waits. |

Proposed shape in the workflow manifest (not built; names provisional):

```json
"persona": {
  "strictness": "guide",
  "invariants": ["Never score an area deeper than the evidence", "Never write the intent for the person"],
  "flexes": {"questions_per_turn": [1, 2], "missing_evidence": ["assume-marked", "gap-and-continue", "block"]}
}
```

**Who changes it (AV-4, recommended):** the person, in words, per run ("be
tough on this one", "go easier"); the switch is said in one line, shown on the
mode strip (D-90) and recorded in the run, so a brief can say "shaped by the
book". The Hangar sets each workflow's default. The agent may suggest a switch
but never makes one silently. Alternatives: Hangar only; the agent adapts on
its own.

Aviator's own persona as director is separate: brief, outcome first, a
recommendation with every choice. It must not take on a skill's stance in
open work.

## Part 4. News while the person is mid-conversation (AV-5)

Recommended: hold other threads' news until the person's current exchange
pauses (their last reply has been answered and nothing new is asked), then
deliver it as one line and the run card. Failures and blockers that affect
the person come through at once (red is failures only, D-50). Alternatives:
show at once as a quiet line; only when asked.

## Part 5. Testing and tuning (AV-6)

Everything above is prompt text, so it is measured, not argued.

**Terms** (from the evals article): a *task* is one scenario with a starting
workspace and success criteria; a *trial* is one run of it; *graders* score
it; the *transcript* is the record; the *outcome* is the state of the
workspace afterwards (datasets, run files, threads started).

**Three suites, recommended:**

| Suite | Size to start | What it checks | Graded by |
|---|---|---|---|
| Routing | ~30 single-turn prompts, each labelled start, offer, open or answer, about a third near misses | The ladder (AV-1) and the lifecycle trigger (AV-2) | Code: which skill loaded, whether a thread or brief was made, whether the reply holds an offer. 3 trials; pass if 2 of 3 match. Tuned on 60% of prompts, judged on the held-out 40%. |
| Personas | 12 scripted conversations per hero skill: four simulated PMs (hurried, vague, pushes back, expert with evidence) × three levels | Strictness (AV-3): honesty rules kept, and whether the person got somewhere useful and felt in control | Code on the dataset (scores against a reference); a Claude judge per rubric line, allowed to say "unknown". Hard gate: honesty rules kept in **all three** trials. |
| Coordination | 8 multi-thread stories: two runs at once, pause and resume, a finding to carry across, news while mid-answer, a thread asking for something irreversible | Part 1 patterns and AV-5 | Code on the event order and run files; a judge on message quality (short, outcome first). Hard gate: nothing irreversible without the person. |

**How it runs:** on the Mac mini, through the real app (driven by its own
session API), so the skills, threads, bridge and tools are the ones Geoff
flies. A fresh copy of the workspace per trial (shared state inflates scores).
The simulated PM is a second Claude Code session given a script and the
transcript so far, like a participant (D-19). The judge is Claude Code too;
nothing uses the Claude API (D-02). Batches run overnight, three at a time.
Each round, Geoff picks the better of ten pairs of transcripts with labels
hidden; agreement with the judge is tracked and the judge's rubric is fixed
when they disagree. Scenarios already have `script.md`; good flights can
become tasks, and every failure seen in a real flight should become one.

**Tuning loop:** change one thing (a skill description, a rule in the director
skill, a strictness definition), run the suite, read the failing transcripts,
keep the change if the held-out score rises and no hard gate drops. Report:
a matrix per skill, simulated person by level, with the hard gate as its own
row; the default level per skill is the best column that passes the gate.

**Cost:** at about a minute per agent answer, a six-turn persona conversation
takes 8 to 10 minutes. The starting set (30 routing prompts × 3, plus 12
conversations per skill × 3) fits a night for one or two skills. The full
matrix for all six skills is about a day and a half per round, which is why
it is not the recommendation.

Alternatives: routing suite only for now (an afternoon to build, says nothing
about personas); the full matrix before any change.

## Open questions

| | Question | Recommended |
|---|---|---|
| AV-1 | How forward Aviator is when a request fits a hero skill | The ladder: start when named, offer once when it clearly fits, otherwise work openly |
| AV-2 | "I'm working on a new feature" | A lifecycle skill that makes the project, links assets, shows the stages and offers the next one |
| AV-3 | Default persona strictness | Guide: honesty rules hard, style flexible |
| AV-4 | Who changes strictness | The person in words, per run, visible; the Hangar sets the default |
| AV-5 | News while the person is mid-conversation | Hold until a break, except failures and blockers |
| AV-6 | How to test and tune | Three suites through the real app on the Mac mini, with Geoff ranking blind pairs |

## Build order once answered

1. Director skill rules for the eight pattern gaps, and the routing ladder
   (needs AV-1, AV-5).
2. Routing suite and runner on the Mac mini (needs AV-6). Build it before
   tuning anything else, so every later change is measured.
3. Persona blocks in each hero workflow's manifest, strictness on the strip
   and in the run (needs AV-3, AV-4); persona suite.
4. Feature lifecycle skill and its view (needs AV-2, and D-97's project
   manifest).
5. Coordination suite, once the direct line (D-116) is built.
