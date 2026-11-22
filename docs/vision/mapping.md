# Flight Deck today, and the step it takes toward the future loop

Mapped against product-agent-and-harness's working tree of 2026-11-22
(commit `15c00d8` plus uncommitted changes: truths in `04-truths.md`, the
moves in `07-product-system.md`, artifacts and assets in `08-assets.md`).
Flight Deck as of `main` at `ecb6813`, with open PRs 53 (decision brief) and
54 (the arc called "PRD to dependencies", and the prototyping approach in the
taxonomy's section 6). Second pass, by Claude; not reviewed by Geoff.

## The two horizons

The research describes where product work is going. Flight Deck has to be
useful to a product person **now**, on a locked-down work Mac. So this is
not a scorecard of truths covered. Each row asks two things: what Flight
Deck does for someone today, and whether that step also moves toward the
loop. Things that only make sense once the future has arrived (agents that
watch signals all the time, steward agents for every platform) are marked
**later**. That is not a failing.

Status words:
- **today**: built, useful now, and on the path
- **next**: useful now and worth building soon
- **later**: needs the future to arrive first
- **platform**: belongs to the enterprise's delivery, data or risk
  platforms; Flight Deck hands work over and records decisions

## Three artifacts

Both sides use these three names and avoid "spec" and "PRD", which people
read their own meaning into.

| Artifact | What it holds | What produces it in Flight Deck |
|---|---|---|
| **Statement of intent** | Written by the person: what will change, the outcome, the risk accepted, what would prove it wrong, the trade-offs | Intent shaping, into the `initiative-intent` template's Goal, Problem, Customer, Outcome and Scope sections. There is no field for the risk accepted or what would prove it wrong (**next**) |
| **Solution design** | Drafted by agents, settled by people: how the change fits existing platforms, connections, dependencies, alternatives considered, trade-offs decided | The "PRD to dependencies" arc: Specify (requirements traced to lines), Map (dependencies) and Choose (alternatives with what each gives up). The template's Approach, Dependencies and Delivery sections hold it. Today it's one document with the statement of intent (**next**: split it) |
| **Decision record** | What was chosen or stopped, and why, linked to evidence | The Decisions register (supersede, never edit), `decision-review` and `decision-brief` (**today**) |

Seen this way, the earlier "tension" with truth 7 dissolves. Specify adds
detail to the solution design, not the statement of intent. The person's
part stays short, and agents do the expanding.

## Moves

| Move | Flight Deck now | Status | The step toward the loop |
|---|---|---|---|
| sense | Problem discovery runs on sources a person brings, including post-launch | today (on request) | Watching signals unasked is later |
| investigate | Problem discovery: problems with checked quotes, every claim cites a source | today | Interviews at scale are platform |
| hypothesize | Intent shaping asks one question at a time and never writes the person's answer | today, next | Add risk accepted and what would prove it wrong |
| prototype | The Prototype move is designed in PR 54: routed by channel, a default enterprise prototyper that takes design-system packs, and platform teams can ship their own | next | Prototypes in safe copies of real systems are platform |
| challenge | Review gets second opinions on a document | next | Argue the other side of a hypothesis: the strongest case for each rival explanation, the evidence that would separate them, and a bias check |
| decide | Decide: decision briefs and the Decisions register | today | |
| design | "PRD to dependencies" (Specify, Map, Choose); Engage owners is planned | today, next | Steward agents that propose designs are later and platform |
| build | | platform | Flight Deck hands over the statement of intent and solution design |
| verify | Ready checks verify the intent, not the change | platform | |
| release | | platform | Flight Deck can record a release decision |
| learn | Delivery status; post-launch problem discovery; the registers keep the trail | today | Reading results against "what would prove it wrong" needs that field first |

## Truths

Most truths describe outcomes, so the note says where Flight Deck helps now.

| Truth | Flight Deck now | Status |
|---|---|---|
| 1. problem discovery is the primary human craft | Problem discovery is the first arc | today |
| 2. solution work shifts to invention | Intent shaping; Choose compares alternatives | today; Challenge is next |
| 3. product judgment spreads beyond the PM title | The Hangar lets anyone build a workflow; the copy assumes a PM | next (copy), later (the shift itself) |
| 4. accountability attaches to outcomes | The Decisions register | platform |
| 5. testing an idea converges with describing it | The Prototype move (designed) | next |
| 6. several answers explored in parallel | Choose: up to four alternatives beside a baseline | today, for solution designs |
| 7. the statement of intent shrinks | A short intent template; Specify works on the solution design | today; split the two, next |
| 8. validation in loops of rising realism | | platform |
| 9. insight from the highest-signal method | Problem discovery takes any source, traced back | today |
| 10. agents do the fetch-and-carry | Delivery status; the dependency catalog ("can we already do this?") | today |
| 11. a steward agent per platform, journey and process | Engage owners (planned) is the person's side of it | later; the steward is platform |
| 12. production stays linked to intent | Initiative registers and stamped artifacts, up to hand-off | today |
| 13 to 15. ambition rises; capacity funds bigger bets | Outcomes, not skills; the usage log could measure time saved | n/a |

## What to build next, useful now and a step toward the loop

1. **Statement-of-intent fields.** Risk accepted and what would prove it
   wrong, in the template and in intent shaping's depth checks. Small.
2. **Challenge.** An option on Review that argues the other side of a
   hypothesis, as above.
3. **Split the template** into a statement of intent and a solution design,
   and give the arc a name that says what it produces.
4. **Prototype.** Build the move and the default prototyper from PR 54.
5. **Quality evals.** Only routing is measured today. First candidates:
   investigate (are the quotes real), hypothesize (does shaping draw out what
   would prove it wrong without writing it), decide (real options and a
   reason).

## Open, for Geoff

These are in the joint decision brief: line or loop (and renaming our tier
called "move"), what to build first, the rewards story as a scenario, and
renaming the "PRD to dependencies" arc and its Specify step.
