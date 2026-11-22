# Vision: what has to be true, and what Flight Deck does about it

Flight Deck is one piece of a larger picture. A separate research project,
[product-agent-and-harness](https://github.com/dudgeon/product-agent-and-harness)
(task "the future of product"), writes the point of view: the truths about how
product work will run, the moves that make up the product loop, scenarios of
notional people doing that work, and the assets that would have to exist.
Flight Deck owns the targeted implementation: skills, the harness, templates
and evals.

## Who owns what

| | Research project | Flight Deck (this repo) |
|---|---|---|
| Truths, moves, scenarios, assets as needs | Owns and edits | Reads; never edits |
| Skills, harness, templates, evals | Is told what exists | Owns and edits |
| [mapping.md](mapping.md) | Reads, sends corrections | Owns |
| Decisions that change either side | Geoff decides, through one decision brief | Same |

## Handles

Items are cited by the names they already have, with no added codes, because
the research text is Geoff's prose and stays free of registry ids:

- truths by number (1 to 15), in `tasks/research-future-of-product/04-truths.md`
- moves by name (sense, investigate, hypothesize, prototype, challenge,
  decide, design, build, verify, release, learn), in
  `tasks/research-future-of-product/07-product-system.md`, "The moves"
- assets by their bold name in `tasks/research-future-of-product/08-assets.md`

When the research side splits, merges or renumbers anything, it messages the
old-to-new change. Nothing there is a rule yet: a scenario can bend a truth as
easily as the reverse, so expect the mapping to move.

Scenarios written about a real kind of business stay in the research
project's local files and are not cited here.

## How the two stay in step

- [mapping.md](mapping.md) has a short row per move and truth: what serves it, what is
  missing, and which eval would test it. Each version records the research
  project's commit it was mapped against.
- Live coordination is by direct message between the two Claude sessions on
  the Mac mini. Corrections to the research files are sent as messages; this
  repo does not edit them.
- When a choice changes the goal on either side, it goes to Geoff as one
  decision brief. Neither side settles it alone.
