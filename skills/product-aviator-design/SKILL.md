---
name: product-aviator-design
description: Product Aviator's design language and its design tokens. Use whenever you make or restyle anything people will see in this app: an HTML artifact, a canvas view, a chat widget, an artifact template, a scenario preview, or the app's own UI. It overrides frontend-design wherever the two disagree.
---

# Product Aviator design language

Everything people see in this app (the app itself, chat widgets, canvas
views, artifact templates, scenario previews) draws from one set of design
tokens. Change a token and all of it changes, including artifacts that were
made before the change. That only works if nothing sets its own colors.

## The one rule

**Use `var(--pa-…)` tokens. Never write a color, a font stack or a corner
radius by hand.** Not in an artifact, a template, a view, a widget or a
React component.

The tokens are defined once in `design/tokens.json` at the root of this
repository. The canvas viewer injects the current values, in the user's light
or dark mode, into every HTML artifact it shows. To make a file that also
looks right opened on its own, start from a template in
`templates/artifacts/` (it carries a generated copy of the tokens between
`pa-tokens:begin` and `pa-tokens:end`), or inline `kit/pa-kit.css` from the
`view-kit` skill. Never hand-edit the text between those markers.

## What the tokens mean

| Token | Use it for |
|---|---|
| `--pa-bg`, `--pa-surface`, `--pa-sunk` | Page and canvas, cards and chat, recessed areas |
| `--pa-ink`, `--pa-ink-2`, `--pa-ink-3` | Main text, secondary text, faint text (ids, hints) |
| `--pa-line`, `--pa-line-strong` | Hairlines and borders; stronger dividers |
| `--pa-navy`, `--pa-navy-hover`, `--pa-on-navy` | The brand. Primary buttons, the one main action, selection. Text on navy. |
| `--pa-chrome`, `--pa-chrome-*` | The app's frame (sidebar). Not for content. |
| `--pa-you`, `--pa-you-soft`, `--pa-on-you` | Only what the person did: their edits, ticks, notes, things they sent back. |
| `--pa-ok` | Done, reviewed, accepted |
| `--pa-info` | Ready for review, advisory, links |
| `--pa-attn` | Needs the person |
| `--pa-warn` | Caution that is not waiting on the person |
| `--pa-fail` | Failed or blocked. Reserve it for real failures. |
| `--pa-idle` | Not started, queued |
| `--pa-agent` | The main agent and work in progress by it |
| `--pa-author-1` … `--pa-author-8` | Other agents and people, one hue each, in order of appearance |
| `--pa-shadow` | Shadow color; only for things that float over the page |
| `--pa-font`, `--pa-mono` | System fonts only (no web fonts work offline). Mono only for ids and code. |
| `--pa-r`, `--pa-r-panel`, `--pa-gap` | Corners of controls, corners of panels, the standard gap |
| `--pa-text`, `--pa-text-sm`, `--pa-text-title`, `--pa-weight-title`, `--pa-tracking-title` | Body size, small size, title size and weight |

Every status color also has a `-soft` partner for its background. Pair them:
text in `--pa-ok` on `--pa-ok-soft`.

## Conventions

- Color carries meaning, not decoration. If something is colored, a reader
  should be able to say why. Most of the page is ink on surface.
- Status always shows an icon and a word as well as a color.
- One primary (navy) button per card or form. Everything else is plain.
- Labels and headings are sentence case. No small all-caps labels, no
  tracked-out eyebrows above headings.
- Titles are sentences that say what the thing is. Ids are mono and faint.
- No shadows except on things that float (menus, popovers, drawers).
- Numbers that line up use `font-variant-numeric: tabular-nums`.
- Design for both light and dark: only tokens, never a literal that works in
  one mode.

## Relation to frontend-design

`frontend-design` (bundled, from Anthropic) is good general advice on
typography, layout, copy and avoiding generic looks. Use it for those. Where
it asks for a distinctive palette, its own typefaces or a fresh visual
identity, this skill wins: inside Product Aviator the identity is already
set, and consistency across views is the point.

## Changing the design language

Edit `design/tokens.json`, then run `python3 design/build_tokens.py` (it
rewrites the app, the view kit, the preview player and the templates) and
rebuild the web UI (`pnpm --filter web run build`). `--check` reports any
copy that is out of date. Record the change in `docs/product/decisions.md`.
