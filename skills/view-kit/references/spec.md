# View spec reference

A spec is one JSON object. Text values can use `{field}` for the current
record, `{dataset.title}` (or any dataset fact), `{dataset}` for the dataset's
path, and `{note}` for what the user typed into an action's question.

## Common keys

| Key | Meaning |
|---|---|
| `view` | Short id, unique in the dataset. Used to key saved state. |
| `layout` | `tree-table`, `board`, `detail`, `summary` or `form`. |
| `eyebrow`, `title`, `subtitle` | Header text. |
| `records` | Which records the view is about: `{ "type": "requirement" }` or `{ "type": ["capability", "requirement"], "status": ["ready"] }`. |
| `status_field` | The state field this view reads and writes. Default `status`. |
| `statuses` | Extra or relabelled statuses: `{ "parked": { "label": "Parked", "tone": "idle" } }`. Tones: `ok`, `info`, `warn`, `attn`, `idle`, `you`. |
| `summary` | `{ "count_by": "status", "records": {...} }` draws the count pills and progress strip under the header. Pills filter the view. |
| `details` | One entry per record type: what its detail card shows. |
| `actions` | Buttons. See below. |
| `empty` | Text when there are no records. |
| `show_id` | `false` hides record ids. |

## Columns and fields (`columns`, `tile.fields`, detail `fields`)

`{ "field": "priority", "label": "Priority", "as": "chip", "only": "requirement", "edit": {...} }`

| `as` | Draws |
|---|---|
| (none) | Plain text |
| `status` | Status pill |
| `chip` | Small outlined label |
| `tags` | A chip per array item |
| `check` | Tick, or a checkbox when editable |
| `meter` | Five bars for a 1 to 5 value |
| `count` | Number of child records |
| `ref` | The title of the record whose id is in this field |
| `who` | The participant whose id is in this field (a file in `participants/`), as a mark and name. Use it on a field such as `by` to show who made a record. |

`only` limits a column to one record type. `edit` makes it editable in place:
`true` for a checkbox or text, `{ "options": [...] }` for a menu,
`{ "kind": "number" }` for a number. Edits collect as unsent changes.

## tree-table

`columns` as above. Records nest under their `parent`. Parent rows collapse and
show how many children are reviewed.

## board

```json
"lanes": { "field": "explore_status", "order": ["queued", "working", "needs-you", "ready", "reviewed"] },
"tile": { "fields": [ { "field": "priority", "as": "chip" } ] }
```

Lanes with no records are hidden unless listed first in `order`. An action
with `"inline": true` shows on the tile itself.

## detail

`"detail": "<record type>"` picks which entry of `details` to draw, and
`--record <id>` on `pa render` picks the record.

## Detail sections (`details.<type>.sections`)

| `kind` | Keys | Draws |
|---|---|---|
| `fields` | `fields: [...]` | A grid of labelled values, editable where marked |
| `text` | `field`, `label`, `edit` | A paragraph, editable when `edit` is true |
| `list` | `field`, `label` | A bulleted list from an array |
| `evidence` | `field`, `label` | Quotes with their source, from `[{source, quote}]` |
| `callout` | `field`, `label`, `tone` | A highlighted box, shown only when the field has a value |
| `choices` | `field`, `pick`, `recommended`, `label` | A pick-one list. `field` names a list of `{label, consequence}` on the record; pressing one stores its label in the `pick` field (default `choice`) as an unsent edit. The option whose label equals the `recommended` field is marked. Locked records show the pick but cannot change it |
| `note` | `text` | Fixed helper text |
| `children` | `records`, `columns`, `label`, `empty` | A table of child records. Rows open that child's own card. |
| `children` with `"as": "options"` | `records`, `fields`, `pick: { "field": "selected_option" }` | Cards to compare, with a Choose button that sets `pick.field` on the parent |

## summary

`blocks` is a list of:

- `{ "kind": "tiles", "tiles": [ { "label": "...", "where": {...} } ] }`
- `{ "kind": "bars", "label": "...", "count_by": "field", "records": {...} }`
- `{ "kind": "list", "label": "...", "records": {...}, "field": "question", "empty": "..." }`
- `{ "kind": "text", "text": "..." }`

## form

```json
"fields": [
  { "id": "grain", "label": "...", "kind": "choice", "default": "A", "options": [ { "value": "A", "hint": "..." }, "B" ] },
  { "id": "include", "kind": "multi", "options": [...] },
  { "id": "strict", "kind": "toggle", "default": true },
  { "id": "note", "kind": "text" }
],
"submit": { "label": "Start", "prompt": "Setup:\n{answers}", "skip": "Use your judgment", "skip_prompt": "..." }
```

Field kinds: `choice`, `multi`, `toggle`, `text`, `line`, `number`.

## Actions

```json
{ "id": "return", "label": "Send back", "tone": "primary",
  "scope": "record", "when": { "type": "requirement", "status": ["ready", "reviewed"] },
  "ask": { "label": "What should change?", "field": "return_note" },
  "set": { "status": "returned" },
  "prompt": "Rework requirement {id} ({title}). My note: {note}",
  "inline": false, "next": true }
```

| Key | Meaning |
|---|---|
| `scope` | `record` (default, shown on the detail card) or `view` (shown in the header). |
| `when` | Field values the record must have for the button to show. |
| `set` | Fields to change. Without a `prompt` this only adds an unsent edit. |
| `ask` | Ask the user one question first. The answer goes in `ask.field` and in `{note}`. |
| `prompt` | The sentence put in the chat box. End it with `: ` to let the user finish it. |
| `next` | After the action, move to the next record that needs the same attention. |
| `inline` | Also show on board tiles. |
| `tone` | `primary` for the main action. |
| `direct` | `true` for an action that only changes state (`status`, `locked`, `*_status`, with a lower-case word or true/false as the value). It goes to the agent without the chat box. On a `view` action add `records` to say which records the `set` applies to. Keep a `prompt` as the fallback for hosts without direct actions. |

Give every action a stable `id`. The scenario's SKILL.md says what the agent
does for each id.

## From inside the page

`window.PA` exposes `pending()` (unsent edits), `answers()` (form answers),
`state()`, `open(id)`, `setData(dataset)` and `clearEdits()`.

## Narrow canvases

Below 680 px a `tree-table` hides read-only `chip`, `meter` and `tags` columns
so the title, status and editable cells stay readable. Set `"narrow": "keep"`
on a column to always show it, or `"narrow": "hide"` to drop any other column.
