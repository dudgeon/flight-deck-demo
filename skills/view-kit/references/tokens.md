# Design tokens

Defined in `kit/pa-kit.css`, for light and dark. Use the variables, never the
values, so a restyle of the kit restyles every view.

| Token | Use |
|---|---|
| `--pa-bg`, `--pa-surface`, `--pa-sunk` | Page, cards, recessed areas |
| `--pa-ink`, `--pa-ink-2`, `--pa-ink-3` | Text: main, secondary, faint |
| `--pa-line` | Hairlines and borders |
| `--pa-navy`, `--pa-on-navy` | The brand color and text on it. Primary buttons. |
| `--pa-you`, `--pa-you-soft` | Anything the person did: their edits, their notes, things they sent back. Nothing else uses this color. |
| `--pa-ok`, `--pa-info`, `--pa-warn`, `--pa-attn`, `--pa-idle` (each with `-soft`) | Status tones: reviewed, ready, working, needs the person, not started |
| `--pa-font`, `--pa-mono` | System fonts only. Mono is for ids, counts and labels. |
| `--pa-r`, `--pa-gap` | Corner radius and the standard gap |

Conventions the layouts follow, so one-off views should too:

- Status is always shown with an icon and a word, never by color alone.
- One primary button per card. Everything else is plain.
- Ids are mono and faint. Titles are sentences, not labels.
- Small uppercase mono labels name sections. Body text is 14px.
- No shadows except on things that float over the view.
