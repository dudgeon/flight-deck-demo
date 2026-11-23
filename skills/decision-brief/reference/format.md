# The brief's data file

One JSON object. `brief.py check` enforces the rules marked *(checked)*.
`examples/decision-briefs.json` uses every field.

## The brief

| Field | Type | Meaning |
|---|---|---|
| `id` | text *(checked)* | Short slug; also the key the page keeps picks under. |
| `title` | text *(checked)* | What is being decided, as a name. The page's title. |
| `for`, `from`, `date` | text | Who decides, who made the brief, when. Shown under the title. |
| `description` | text | One sentence for galleries and the Library. Optional. |
| `initiative` | text | The initiative's key or id. `record` writes each decision to its register. |
| `why` | text or list *(checked)* | What this is and why the person is seeing it. |
| `how_to_answer` | text | Replaces the default line on how to answer. Rarely needed. |
| `recommendation` | text or list | All the recommendations in one paragraph. |
| `read` | list of `{label, href, note}` | What you read. `href` optional. |
| `findings` | list of `{title, body}` | What you found, a sentence or two each. |
| `decisions` | list *(checked: at least one)* | See below. More than eight warns. |
| `after` | text or list | What happens once they decide. |
| `url` | text | The published page, once there is one; `note` links it. |
| `recorded_at` | time | Set by `record`. |

## A decision

| Field | Type | Meaning |
|---|---|---|
| `id` | slug *(checked)* | Lowercase letters, digits, hyphens; unique in the brief. Answers are keyed by it. |
| `label` | text | A short handle shown faint (DB-1, HS-3, Q-12). |
| `question` | text *(checked)* | A sentence ending in a question mark. |
| `context` | text or list *(checked)* | What the person needs to know to decide. |
| `know` | list | "What you need to know": the facts that change the answer. |
| `stage` | visual | The picture for the decision as a whole. |
| `stage_title` | text | The stage's heading when no option is shown. |
| `options` | list *(checked: 2 or more)* | See below. Never a "Something else" option *(checked)*. |
| `reason` | text *(checked)* | Why you recommend the recommended option. |
| `depends_on` | list of decision ids *(checked)* | Decisions this one builds on. |
| `supersedes` | text | A register decision this replaces (`record` passes it on). |
| `d` | text | A log number once claimed (for example D-150); the note uses it. |
| `answer` | object | Written by `answer`, `import` and `record`: `pick`, `label`, `note`, `at`, `via`, `locked`. |
| `record` | text | Where it was written down; set by `record`. |

## An option

| Field | Type | Meaning |
|---|---|---|
| `id` | slug *(checked)* | Unique in the decision. `else` is reserved for Something else. |
| `label` | text *(checked)* | The option, short. |
| `consequence` | text *(checked)* | What happens, and what it gives up. |
| `cost` | text | A size or a state: S, M, L, Built, "M (app change)". |
| `recommended` | true *(checked: exactly one per decision)* | Your recommendation. |
| `visual` | visual | Shown on the stage while the person points at or picks this option. |

## A visual

`{"html": "...", "caption": "..."}` or `{"image": "relative/path.png",
"alt": "...", "caption": "..."}`. Html uses only the components in
`components.md` *(checked: no scripts, styles, colors or remote loads)*.
Images are inlined when the page is drawn *(checked: exists, local)*.

## Text

Text fields take plain words with `**bold**`, `` `code` `` and
`[links](https://…)`. Nothing else is interpreted.

## Answers as text

What the page's Send and Copy produce, and `import --text` reads:

```
Decision brief answers: <title> (<id>)
- <decision id> | <option id or else> | <option label> | note: <their note>
```
