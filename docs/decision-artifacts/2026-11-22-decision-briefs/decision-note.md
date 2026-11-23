# How decision briefs should work: decisions

Decided 2026-11-22, by Geoff, brief from the decision brief thread.

## Links

- The brief: https://claude.ai/artifact/CNNpJFboRrwDAsYsBvundE
- Archived copy: [index.html](index.html)
- Brief data (answers included): [brief.json](brief.json)
- Research: [Lifecycle walkthrough](https://claude.ai/artifact/P3hZWy2Ht6es1KCxMDLTEv): the newest pattern: pick buttons, notes and saved answers per decision
- Research: [Initiatives data model walkthrough](https://claude.ai/artifact/DHcM1SxdoecNJKtNgJ6t5p)
- Research: [Hangar builder mode walkthrough](https://claude.ai/artifact/9M4JGs5WuxigJz1jiJ9QVr)
- Research: [duo-v2: GitHub issues decisions](https://claude.ai/artifact/9GHsANtdG8XHd1hnM8rcsb): decisions as data, the recommendation in one paragraph, accept all
- Research: [duo-v2: decision walkthrough mockups](https://claude.ai/artifact/SYDWRHc8QJKhaqNidP62UA): a stage that redraws for the option, Your call beside it
- Research: duo-v2 workflow lessons, on the Mac mini: `explainers/projects/17-duo-workflow-lessons`: "Decisions as buttons, kept as numbers" and "one console, many throwaway pages"
- Research: [The 22 archived briefs in the repo](https://github.com/dudgeon/flight-deck-demo/tree/main/docs/decision-artifacts)

## What was recommended

Keep the layout you see here: one page, the briefing and picture beside your call, stacked on a phone. At work, Send puts your answers in the chat box for you to send, which works today and never sends without you; a one-press version can follow. Each decision goes to the initiative's decisions register, with a short note beside the brief that links the research and the archived page. Agents make a brief when a choice has real tradeoffs and is hard to undo, visual, linked to other choices, or needed research; a simple choice stays a question card.

## Decisions

### DB-1 · How should a brief lay out each decision?

**Decided:** One page, briefing beside your call, the recommendation. Note: We may later add the narrations — they’re useful but not a core feature set

**Why the recommendation:** It is the only layout that shows the whole set at once, works offline with no extra making, and already reads well on a phone. The other two can come later as other ways to view the same data file.

Options considered:
- One page, briefing beside your call (picked): Everything on one scrolling page: you see all the decisions, their order and what is answered. On a phone each card stacks, picture first. What you are looking at now.
- One decision at a time: A step through, Back and Next, with the picture on top. Calm on a phone, but you lose sight of the whole set and how the decisions depend on each other.
- Narrated, with a stage and captions: Like the duo-v2 walkthroughs: a voice talks you through and the stage animates. The richest, but every brief needs a script and audio, and the work Mac can't make audio offline.

Recorded as D-160 in docs/product/decisions.md.

### DB-2 · Inside Flight Deck at work, how do your answers reach the agent?

**Decided:** Straight to the agent, one press, not the recommendation (Send puts them in the chat box; you press Send). Note: hybrid: send button in the brief —- keeps user focused in the brief (no toggling back to chat)

**Why the recommendation:** It works today with no change to the app, it keeps the rule that nothing is sent without you, and it leaves a readable record of your answers in the conversation. One press fewer can come later.

Options considered:
- Send puts them in the chat box; you press Send: One button collects every answer and note into the chat box as a short list. You see exactly what goes, and press Send. Nothing leaves without you. One extra press.
- Straight to the agent, one press (picked): The page sends your answers itself, the way status changes already go. One press fewer, but the app must learn to carry notes safely, and you don't see the message before it goes.
- Saved to a file the agent reads when asked: No message at all: answers land in a file and the agent picks them up when you next say something. Quietest, but the agent doesn't know you answered until you tell it.

Recorded as D-161 in docs/product/decisions.md.

### DB-3 · Where should a decision be written down once you lock it?

**Decided:** Something else, not the recommendation (The register, plus a note beside the brief). Note: Should be exclusively within the project; briefs are just a decision artifact, so put them in the project decisions folder

**Why the recommendation:** The register is the one place skills already read before asking (D-142), and the note keeps the rationale and links without bloating it. It is what the lifecycle thread's Decide move expects, too.

Options considered:
- The register, plus a note beside the brief: Each decision becomes one line in the initiative's decisions register, so every skill sees it. A short note beside the brief keeps the why, the options considered and the links. Two places, each with one job.
- Only the note: One file per brief and nothing else. Simple, but other skills don't see the decision unless they find the note, so they may ask again.
- One decisions log for the whole workspace: Like this repo's `decisions.md`: every decision in one numbered file. Easy to scan, but it mixes initiatives and duplicates the registers the skills already use.
- Something else (picked): Should be exclusively within the project; briefs are just a decision artifact, so put them in the project decisions folder

Recorded as D-162 in docs/product/decisions.md.

### DB-4 · When should an agent make a brief instead of asking with a card?

**Decided:** Something else, not the recommendation (A rule: real tradeoffs, plus one more sign). Note: Agents will need to use judgment, but generally when the decision requires context, is more than one question, and/or has a visual component to the decision that isn’t well suited to chat

**Why the recommendation:** It matches what you have asked for so far (never decide blind on big or visual choices, tap for small ones) and it is short enough for every skill to apply the same way. It can be tuned with the routing evals later.

Options considered:
- A rule: real tradeoffs, plus one more sign: A brief when there are two or more real options with tradeoffs and the choice is hard to undo, visual, one of several linked decisions, or needed research to frame. Otherwise a card. Agents say in one line why they made a brief.
- Only when you ask for one: Everything is a card unless you say "brief me". Fewer pages, but big choices arrive as a tap with no picture, which is what you asked us not to do.
- Any choice with more than one option: Consistent, but small choices cost a page each, and you get a lot of pages.
- Something else (picked): Agents will need to use judgment, but generally when the decision requires context, is more than one question, and/or has a visual component to the decision that isn’t well suited to chat

Recorded as D-163 in docs/product/decisions.md.

## Log entries

Ready for a decisions log in the `**D-NN · date · Who.** The decision. *Why.*` form. Claim numbers the careful way before using them.

**D-160 · 2026-11-22 · Geoff.** How should a brief lay out each decision? One page, briefing beside your call. *We may later add the narrations — they’re useful but not a core feature set*

**D-161 · 2026-11-22 · Geoff.** Inside Flight Deck at work, how do your answers reach the agent? Straight to the agent, one press. *hybrid: send button in the brief —- keeps user focused in the brief (no toggling back to chat)*

**D-162 · 2026-11-22 · Geoff.** Where should a decision be written down once you lock it? Should be exclusively within the project; briefs are just a decision artifact, so put them in the project decisions folder *In their own words.*

**D-163 · 2026-11-22 · Geoff.** When should an agent make a brief instead of asking with a card? Agents will need to use judgment, but generally when the decision requires context, is more than one question, and/or has a visual component to the decision that isn’t well suited to chat *In their own words.*
