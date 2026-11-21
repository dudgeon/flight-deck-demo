# Product notes

Why Product Aviator is built the way it is. Written for whoever builds the
production version later: they can read what was decided, what each feature is
for, and what was tried, without asking the people who were there.

- `decision-index.md`: every decision number with its current status
  (built, replaced, pending, open) and a one-line reason. Start here.
- `decisions.md`: the decision log. One entry per decision, newest last, with
  who decided, when, and why. Add to it whenever something is decided. Never
  rewrite an old entry; add a new one that replaces it.
- `features.md`: what each feature is for, how it behaves, and where it lives
  in the code.
- `roadmap.md`: where each workstream stands: done, partial, next, open
  decisions and source docs. Update it when a workstream moves.
- `hangar.md`: the spec for the Hangar (builder mode).
- `modes-and-projects.md`: a design exploration, not yet decided: modes that
  workflows put a session into, pausing and resuming runs, what a project is,
  and the intent graph. Lists the open decisions.
- `initiatives-and-templates.md`: the data model for initiatives (projects
  with a goal and a fixed id), the stamps that tie artifacts to them,
  templates (markdown, records, page) and the shared registers.
- `usage-logging.md`: the usage log: what it records, the line's schema,
  privacy rules, where files live, evals, and how logs leave a machine.

Outside this folder: `../history.md` tells the story from the first import
to now, `../architecture.md` explains how each part is built, and
`../decision-artifacts/` keeps offline copies of the walkthroughs and design
rounds the decisions were made on, with Geoff's recorded answers (D-115).

Rules for keeping these current, including how to claim a decision number,
are in the repository's `CLAUDE.md`.
