# Decision artifacts

Offline copies of the pages used to put decisions to Geoff: walkthroughs,
design rounds and proposals. They are kept here as the historic record behind
[../product/decisions.md](../product/decisions.md) and as worked examples of
how a decision is asked (D-32, D-33, D-105), so anyone can see them without a
claude.ai account.

**To view one,** download or clone the repository and open the folder's
`index.html` in a browser, or open [index.html](index.html) for the list.
Nothing loads from the network. Where Geoff answered on the page, the copy
shows his recorded answers (they are also in that folder's `answers.json`);
changing them in the copy saves nothing.

The decision log is the authority on what was decided. The "Led to" column is
a pointer, not a complete list. This folder is kept by the `docs-refresh`
skill (`.claude/skills/docs-refresh/`); add new artifacts with it rather than
by hand. Generated from `artifacts.json`; do not edit this table directly.

| Date | Title | Kind | What it asked | Led to | Status | Copy |
|---|---|---|---|---|---|---|
| 2026-11-21 | Product Aviator Workspace Map | Design exploration | The ways a product manager works, and what each needs from the app | D-04 | Reference | [2026-11-21-workspace-map](2026-11-21-workspace-map/index.html) |
| 2026-11-21 | Workflow Prototyping System | Design exploration | How scenarios, the view kit and the app fit together | D-05 to D-10 | Reference | [2026-11-21-workflow-prototyping-system](2026-11-21-workflow-prototyping-system/index.html) |
| 2026-11-21 | Product Aviator: what we agreed and what is open | Status document | The first night's agreements, open questions and next steps | D-05 to D-16 | Reference | not archived (see note) |
| 2026-11-21 | Conversation Participants | Design exploration | How other agents and people take part in the conversation | D-17 to D-26 | Answered in the thread | [2026-11-21-conversation-participants](2026-11-21-conversation-participants/index.html) |
| 2026-11-21 | Workspace Layout Options | Wireframes | Five layouts for outputs, context and the canvas | D-13, D-14 | Reference | [2026-11-21-workspace-layout-options](2026-11-21-workspace-layout-options/index.html) |
| 2026-11-21 | Product Aviator Use Case Designs | Screens | The PRD example screen by screen: real screenshots and design targets | D-11 | Reference | [2026-11-21-use-case-designs](2026-11-21-use-case-designs/index.html) |
| 2026-11-21 | Product Aviator Decisions | Decision walkthrough | Round one: seventeen open questions across participants, the Session panel, install, the Dock icon and how we work | D-17 to D-34, D-101 to D-103 | Answered (17) | [2026-11-21-decisions-round-one](2026-11-21-decisions-round-one/index.html) |
| 2026-11-21 | Session Layout Round Two | Design exploration | Where the Session panel, context and outputs sit beside the chat | D-13, D-14 | Reference | [2026-11-21-session-layout-round-two](2026-11-21-session-layout-round-two/index.html) |
| 2026-11-21 | Product Aviator design language | Proposal | One token system for app, views, templates and preview, with a before and after | D-36 to D-38 | Accepted | [2026-11-21-design-language](2026-11-21-design-language/index.html) |
| 2026-11-21 | Design Decisions Two | Decision walkthrough | Where navy lives, the color for your own marks, the color for needs-you, where views appear, the intent framework | D-48 to D-50, D-53, D-54 | Answered (5) | [2026-11-21-decisions-round-two](2026-11-21-decisions-round-two/index.html) |
| 2026-11-21 | Hangar Builder Mode | Decision walkthrough | A builder mode distinct from flying: name, look, drafts, the publish gate, build order | D-39 to D-47, D-51, D-52 | Answered (7) | [2026-11-21-hangar-builder-mode](2026-11-21-hangar-builder-mode/index.html) |
| 2026-11-21 | Collaborative markdown editor mockup | Mockup | Highlighted agent edits, tracked suggestions and threaded comments in one document | D-26, D-104 | Built (PR 2) | [2026-11-21-collab-editor-mockup](2026-11-21-collab-editor-mockup/index.html) |
| 2026-11-21 | Editing in the Hangar | Decision walkthrough | Editing a person in place instead of in a flying session, and the Aviator pop-over | D-63 to D-66 | Answered in the combined round | [2026-11-21-editing-in-the-hangar](2026-11-21-editing-in-the-hangar/index.html) |
| 2026-11-21 | Demos, Starters and the Library | Proposal | How demo sessions, Hangar scenarios and the Library relate | D-76 to D-81 (by way of the combined round) | Superseded by the combined round | [2026-11-21-demos-starters-library](2026-11-21-demos-starters-library/index.html) |
| 2026-11-21 | Participant messages in the Inbox mockup | Mockup | Participants reaching the user, and inviting them into a session, through the Inbox | D-68 to D-70 | Built (PR 16) | [2026-11-21-inbox-participants-mockup](2026-11-21-inbox-participants-mockup/index.html) |
| 2026-11-21 | Twelve Open Decisions | Decision walkthrough | Combined round: person editing, the Inbox, demos and the Library, naming | D-63 to D-70, D-76 to D-81 | Answered (14) | [2026-11-21-twelve-open-decisions](2026-11-21-twelve-open-decisions/index.html) |
| 2026-11-21 | Library Design Round | Decision walkthrough | The Library redesign: featured skills, demos, live turns, templates | D-82 to D-88 (in PR 19) | Answered (6) | [2026-11-21-library-design-round](2026-11-21-library-design-round/index.html) |
| 2026-11-21 | Modes and Projects | Decision walkthrough | Modes, pausing, In flight, what a project is, the intent graph (M-1 to M-11) | D-89 to D-99 | Answered (12) | [2026-11-21-modes-and-projects](2026-11-21-modes-and-projects/index.html) |
| 2026-11-21 | Director and Threads | Decision walkthrough | How the director shows a mode, where a thread opens, what a thread reports, a project's connections (M-8, M-12 to M-14) | None yet | Open | [2026-11-21-director-and-threads](2026-11-21-director-and-threads/index.html) |
| 2026-11-21 | Person Builder Icons | Design round | Five directions for avatars of people and agents | None yet (PR 25 held) | Paused by Geoff | [2026-11-21-person-builder-icons](2026-11-21-person-builder-icons/index.html) |
| 2026-11-21 | Aviator Coordination and Routing | Decision walkthrough | Coordination patterns for the director, routing to hero skills, the feature lifecycle, persona strictness and how to test it (AV-1 to AV-6) | D-120 | Open | [2026-11-21-aviator-coordination](2026-11-21-aviator-coordination/index.html) |
| 2026-11-21 | Flight Deck Usage Log | Decision walkthrough | How the local usage log works, and whether logs are committed, what a work Mac pack holds, where the numbers are seen (UL-1 to UL-3) | D-122 to D-127 | Open | [2026-11-21-usage-log](2026-11-21-usage-log/index.html) |

## Notes

- **Product Aviator: what we agreed and what is open**: This one is a Claude Doc, not a page, so there is no HTML file to copy. Its content is folded into decisions.md (D-05 to D-16) and history.md. To archive it, export it as HTML from the doc's menu (or the Claude Docs export tool) and run `add` on a folder holding that file as index.html.
- **Collaborative markdown editor mockup**: From the project files (collab-editor/mockup.html); it was never published as a page.
- **Participant messages in the Inbox mockup**: From the project files (inbox-participants/mockup.html); it was never published as a page.
