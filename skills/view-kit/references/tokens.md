# Design tokens

The kit draws every color, font and corner from Product Aviator's design
tokens, the `--pa-…` CSS variables. They are defined once, in
`design/tokens.json` at the root of the repository. `design/build_tokens.py`
copies them into `kit/pa-kit.css` (between the `pa-tokens:begin` and
`pa-tokens:end` comments), and the canvas viewer injects the current values
and the app's light or dark mode into every view it shows. So use the
variables, never the values, and a token change restyles every view,
including ones drawn before the change.

The full list, with what each one is for, is in the `product-aviator-design`
skill. The ones views use most:

| Token | Use |
|---|---|
| `--pa-bg`, `--pa-surface`, `--pa-sunk` | Page, cards, recessed areas |
| `--pa-ink`, `--pa-ink-2`, `--pa-ink-3` | Text: main, secondary, faint |
| `--pa-line` | Hairlines and borders |
| `--pa-navy`, `--pa-on-navy` | The brand color and text on it. Primary buttons. |
| `--pa-you`, `--pa-you-soft` | Anything the person did: their edits, their notes, things they sent back. Nothing else uses this color. |
| `--pa-ok`, `--pa-info`, `--pa-attn`, `--pa-warn`, `--pa-fail`, `--pa-idle`, `--pa-agent` (each with `-soft`) | Status tones: reviewed, ready, needs the person, caution, failed, not started, the agent working |
| `--pa-font`, `--pa-mono` | System fonts only. Mono is for ids and code. |
| `--pa-r`, `--pa-r-panel`, `--pa-gap` | Corner radius of controls and of panels, and the standard gap |

In a spec, statuses pick a tone by name (`ok`, `info`, `attn`, `warn`,
`fail`, `idle`, `agent`, `you`), never a color.

Conventions the layouts follow, so one-off views should too:

- Status is always shown with an icon and a word, never by color alone.
- One primary button per card. Everything else is plain.
- Ids are mono and faint. Titles are sentences, not labels.
- Labels and section names are sentence case, not small capitals. Body text
  is 14px.
- No shadows except on things that float over the view.
