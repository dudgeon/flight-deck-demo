# Mapping: the future of product against Flight Deck

Mapped against product-agent-and-harness at commit `15c00d8` plus its
uncommitted working tree of 2026-11-22 (third pass of the truths, the
eleven-move loop, the first asset draft). Flight Deck as of `main` at
`ecb6813`, with open PRs 53 (decision brief) and 54 (PRD to dependencies, and the
prototyping approach in the taxonomy's section 6).
First pass, by Claude; not reviewed by Geoff.

Status words: **covered** (a built skill does the job), **partial** (part of
it is built or planned), **gap** (nothing built or planned, and a PM harness
could do it), **platform** (belongs to the enterprise's delivery, data or risk
platforms, not to a person's workspace; Flight Deck at most records it).

## Moves of the product loop

The research describes eleven moves that run in any order and loop. Flight
Deck's taxonomy is a line of arcs (Discover, Shape, Specify, Engage, Deliver)
that allows going back. Each arc below serves several moves.

| Move | What serves it in Flight Deck | Status | What's missing |
|---|---|---|---|
| sense notice that something matters | `problem-discovery` (post-launch input, D-150) | partial | It runs only when a person brings sources. Nothing watches outcomes and signals and raises a problem unasked. A scheduled or standing discovery run would close it |
| investigate find out why | `problem-discovery`: problems with checked quotes, every claim cites a source | covered (synthesis) | Running interviews at scale is platform (consented customer access) |
| hypothesize state a falsifiable belief | `intent-shaping` (up-level, never writes the person's answer); `initiative-intent` template | partial | The intent template has Goal, Problem, Customer, Outcome, Scope, Approach, Dependencies, Delivery. It has no "risk accepted" or "what would prove it wrong" |
| prototype make the idea testable in hours | Planned (PR 54, taxonomy section 6): a Prototype move that routes by channel to a declared prototyper; a default enterprise prototyper ships with Flight Deck and takes design-system packs from channel teams, and platform teams can ship their own. Output is one stamped, self-contained artifact; reactions go to Evidence | partial (designed, not built) | Prototypes in real systems' safe copies are platform. The move takes intent in; nothing yet checks the prototype against the hypothesis's falsifier |
| challenge attack the hypothesis | `document-review` and `decision-review` (Review move: second opinions from agents and people, every finding to a line); `participants` (bring in a colleague) | partial | Nothing argues the other side of a hypothesis on purpose or asks for the evidence that would separate explanations. Replays and simulations are platform |
| decide commit, stop or go round again | Decide move: `decision-review`, `decision-brief` (PR 53), Decisions register (supersede, never edit) | covered | |
| design fit the change to existing systems | `prd-to-dependencies` (PR 54: Specify, Map, Choose with Pathfinder alternatives); planned Engage owners arc | partial | Steward agents that propose the design are platform. Engage owners is not built |
| build write the production change | none | platform | Coding agents; Flight Deck hands intent to them |
| verify independent checks and evidence | none | platform | Flight Deck's Ready checks verify the intent, not the change |
| release ship within limits | none | platform | Flight Deck could record a release-limit decision; it does not set limits |
| learn read results, keep the trail | `delivery-status`; `problem-discovery` post-launch; initiative registers | partial | Nothing reads results against the hypothesis's own "what would prove it wrong", because the hypothesis doesn't record one |

## Truths

| Truth | What serves it | Status | Note |
|---|---|---|---|
| 1. problem discovery is the primary human craft | `problem-discovery` arc, the first hero skill | partial | Strong on synthesis traced to sources. Weak on widening the aperture unasked (sense) |
| 2. solution work shifts to invention | `intent-shaping` (questions, never writes for the person); Choose in `prd-to-dependencies` | partial | Choose compares delivery options (capability swaps, scope trades), not rival solutions to the problem |
| 3. product judgment spreads beyond the PM title | The Hangar lets anyone build a workflow; `participants` | gap | Flight Deck's framing, taxonomy jobs (J1 to J10) and copy assume a PM. The research's people are builders, engineers and operations leads |
| 4. accountability attaches to outcomes | Decisions register | platform | Review thresholds and release limits belong to the delivery and risk platforms |
| 5. testing an idea converges with describing it | The planned Prototype move and default prototyper (PR 54) | partial (designed) | Intent shaping is still prose first; the move is called after shaping, not during it |
| 6. teams explore several answers in parallel | Choose: up to four alternatives beside a baseline, each saying what you give up (`alternatives` template, PR 52) | partial | Built for delivery options. Could carry rival solutions if Choose (or a new arc) is aimed at the problem |
| 7. specs shrink to intent, risk and trade-offs | `initiative-intent` (short sections); `prd-to-dependencies` traces requirements to lines and finds dependencies | partial, with a tension | Our Specify step expands intent into requirements. The truth says agents supply the standing rules so the human spec stays short. Nothing reads rules or obligations in machine form; that store is platform |
| 8. validation runs in loops of rising realism | none | platform | Simulation, replay and live cohorts |
| 9. customer insight from the highest-signal method | `problem-discovery` takes interviews, tickets, metrics, notes; summaries link back to sources | covered (for the harness's part) | Getting consented signals in is platform |
| 10. agents do the fetch-and-carry | `delivery-status` (status from where work happens); director memory; requirements-to-dependencies catalog ("can we already do this?") | partial | Depends on documentation existing, which the research calls the widest gap |
| 11. every platform, journey and process has a steward agent | Engage owners (planned): the "agent" counterparty mode exchanges with the owner's agent; `participants` can stand in for a steward in demos | partial | Flight Deck is the person's side. The steward agent itself is platform |
| 12. production stays linked to intent | Initiatives with Evidence, Open, Decisions and Ready registers; stamped artifacts (D-138 to D-142); decision briefs archived | covered up to hand-off | The link stops where code starts. Carrying the initiative id into the change is platform |
| 13. feature-level ambition rises | nothing directly | n/a | An outcome of the others, not a skill |
| 14. portfolio-level ambition rises | initiatives link to each other; the companion (planned) | n/a | Inference in the research too |
| 15. reclaimed capacity funds bigger bets | Usage log (D-122) could measure time saved | n/a | A leadership choice |

## Assets (from `08-assets.md`)

Assets are named as in `08-assets.md`, which already carries these corrections from Flight Deck:
`prd-to-requirements` and `requirements-to-dependencies` are becoming one arc,
`prd-to-dependencies` (PR 54); Decide is `decision-review` plus
`decision-brief` (PR 53); Engage owners and the feature-lifecycle companion
are planned and touch the steward-agent and trail assets.

| Asset | Flight Deck | Status |
|---|---|---|
| Problem discovery agent | `problem-discovery` | partial (on request only) |
| Framing a hypothesis | `intent-shaping`, `initiative-intent` | partial (no falsifier, no risk accepted) |
| Arguing the other side | none | gap |
| Writing short intent | `initiative-intent`, `prd-to-dependencies` | partial |
| Finding what a change depends on | `prd-to-dependencies` (Map), Engage owners (planned) | partial |
| Recording a decision | Decide move, `decision-brief` | covered |
| Reporting where work stands | `delivery-status` | covered |
| The trail | initiative registers and stamps | covered up to hand-off |
| A place where one person runs their agents and skills | Flight Deck itself (Product Aviator on Omnigent) | covered (prototype) |
| Customer research, prototyping, challenge (replay, simulation), steward, coding, checking and risk agents; safe copies; machine-readable rules; shared definitions; release limits | none | platform |

## Evals

Only the routing suite exists: does Aviator start, offer or stay out of the
way. Nothing yet measures whether a skill does its move well. Each covered
or partial move above wants a quality suite in the routing suite's form (real
app, Claude Code as agent and judge, held-out split). Candidates in order of
evidence: investigate (are quotes real and problems traced), hypothesize
(does shaping draw out a falsifier without writing it), decide (does the
brief state real options and a reason).

## Gaps a harness could close, ranked

1. **Hypothesis fields.** Add "risk accepted" and "what would prove it wrong"
   to the intent template and to intent shaping's depth checks. Small; serves
   hypothesize and learn.
2. **Challenge.** An option on the Review move, or a new arc, that argues the
   other side of a hypothesis and asks for the evidence that would separate
   explanations. Serves challenge, truth 2, truth 6.
3. **Standing discovery.** Let problem discovery run on a schedule over a
   folder of signals and raise what changed. Serves sense, truth 1.
4. **Prototype.** Build the Prototype move and default enterprise prototyper
   designed in PR 54 (one contract; channel teams add design-system packs or
   ship their own prototyper). Serves prototype, truth 5. Largest of the four.
5. **Quality evals** for the moves above.

## Tensions to settle

- **Line or loop.** Our arcs run in lifecycle order and allow going back. The
  research's moves loop many times before a bet, and its author was told that
  linear reads as wrong. Either the arcs stay and each is tagged with the
  moves it serves, or the moves become the organising idea.
- **"Move" means two things.** Our tier called "move" (Review, Decide: done
  to any artifact) and the research's eleven moves overlap but differ.
- **Who it is for.** Flight Deck is framed for PMs; truth truth 3 says product
  work spreads to anyone closest to the problem.
