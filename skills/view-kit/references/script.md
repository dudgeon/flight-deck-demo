# Preview scripts

A scenario's `script.md` is the screenplay for its standalone preview
(`pa preview`). It is plain markdown, meant to be edited by hand. Each
paragraph or bracketed line is one step; the viewer presses Next to move on.
Steps that only change data run on by themselves, so the canvas moves like a
live run.

```
# Review a document with others

One or two sentences shown at the top of the preview.

[start: hide finding]

[open document as "allowances-prd.md"]

**You:** I have finished the Allowances PRD. Help me review it.

**Aviator:** I read it end to end. Two comments, one needs you.
[task: Reviewing · first read]

[comment by Aviator on "It applies from the next cycle.": This contradicts 3.3.]

[call Risk Review: Review the PRD for conduct and fraud risk.]

**Risk Review:** Four findings, one High.

[widget question from Risk Review]
[hint: Answer the question, then Send.]
[wait for submit]

[Risk Review leaves: 4 findings, 1 High.]
```

## Who speaks

`**Name:** what they say`. A following line without a blank line between
continues the same turn.

| Name | Who |
|---|---|
| `You` | The person using the app |
| `Aviator` | Their agent |
| A participant's name or id | That participant. They must be listed in `participants` in `scenario.json`, and they must have been called first. |

## Directions

One per line, in square brackets. Names in angle brackets are yours to fill.

| Direction | What happens |
|---|---|
| `[open <fixture> as "<tab title>"]` | Opens a markdown fixture (a name under `fixtures` in `scenario.json`) in the canvas. |
| `[show <view>]`, `[show <view> empty]`, `[show <view> as "<tab title>"]`, `... by <name>` | Opens a view in the canvas. `empty` starts it with no records. `by` marks the tab as opened by a participant. |
| `[widget <view>]`, `[widget <view> for <record id>]`, `[widget <view> from <name>]` | Puts a view in the chat. `from` attributes it to a participant. |
| `[tab "<tab title>"]` | Brings a canvas tab to the front. |
| `[reveal <id>, <id>]` | Makes hidden records appear. |
| `[status <id>, <id>: <status>]` | Sets the scenario's status field on records. |
| `[set <id>: <field>=<value>, <field>=<value>]` | Changes fields of one record. `null` clears a field; put text with spaces or commas in double quotes. |
| `[restore <id>, <id>]` | Puts records back as they are in the fixture, and shows their children. |
| `[apply edits]` | Saves what the viewer changed in the canvas. |
| `[comment by <name> on "<exact passage>": <comment>]` | Marks a passage of the open document with a comment from that person. |
| `[resolve comment on "<exact passage>"]` | Settles that comment. |
| `[call <name>: <what they are asked>]` | Aviator calls a participant in. Their turns appear inside a block until they leave. |
| `[<name> leaves: <one-line result>]` | Ends the call. |

These attach to the step above them:

| Direction | What happens |
|---|---|
| `[task: <text>]`, `[task: none]` | Sets or clears the progress line above the chat. |
| `[hint: <text>]` | Shows the viewer what to try. |
| `[wait]` | Waits until the viewer sends a message. |
| `[wait for submit]` | Waits for the viewer to submit the widget and send. |

Once, before the first step:

| Direction | What happens |
|---|---|
| `[start: hide <record type>, <record type>]` | Those records start hidden, to be revealed. |
| `[start: set <field>=<value> where <field>=<value>]` | Changes matching records before the run starts. |

Lines that start with `>` or `##` are notes for whoever edits the script and
are not shown. `pa check <scenario folder>` reports a line it cannot read, a
view that does not exist, or a speaker who is not in the scenario.
