# Avatars: style and prompt guide

Pictures for people and agents in Product Aviator. Pick one on a person's
Hangar page (Picture, under "Who they are"); the Hangar copies it into
`workspace/participants/avatars/<id>.png` and sets the `avatar:` line (D-74).
This folder is the library to pick from, and the recipe for making more that
match.

| Folder | What's in it |
| --- | --- |
| `people/` | Nine generic people (`person-01` to `person-09`), for real colleagues and stand-ins. |
| `robots/` | Nine generic robots (`robot-01` to `robot-09`), for agents with no particular role yet. |
| `roles/` | Robots whose role shows at a glance, one per kind of workflow agent (table below). |
| `generate_avatar.py` | Builds the prompt from this guide and, with your own OpenAI key, makes the picture. |

The look was chosen by Geoff on 21 Nov 2026 ("Solid flat"). Every new avatar
should follow it so a mixed cast reads as one team.

## The style

- **Flat vector, solid colors.** Bold geometric shapes, no outlines, no
  gradients, no texture, one flat shadow tone at most. Minimal faces: dot
  eyes, a simple smile.
- **Full-bleed square.** A 1024x1024 square (saved at 512x512), the whole
  background one flat color, edge to edge, with no circle or frame drawn.
  People show as a circle and agents as a rounded square, so the subject sits
  head and shoulders, centered, inside the middle 80% where both crops keep it.
- **Token colors only.** Backgrounds and accents come from the design tokens
  in `design/tokens.json`: navy `#0a223d`, teal `#0d6e78`, magenta `#b0237a`,
  amber `#d99a2b`, indigo `#4f46b8`, green `#17794a`, cream `#fbfdfd`, and pale
  tints of these. Robots are cream with one or two accent colors that contrast
  with the background.
- **No words.** No text, letters, numbers or logos.
- **One role, one prop.** A role robot shows its job with a single large,
  simple prop or feature, plus a head shape no other robot uses.

## Role robots

Give each workflow agent persona the role robot that fits, or make a new one
(below) when none does.

| File | Role | Prop that shows it | Head | Background |
| --- | --- | --- | --- | --- |
| `risk.png` | Risk and compliance | Shield chest plate with a check mark | Rounded dome with a narrow visor | navy |
| `planner.png` | Planning | Clipboard with checklist ticks, calendar-page antenna | Square, one antenna | teal |
| `researcher.png` | Research | Big magnifying glass beside its face | Round, large lens eyes | indigo |
| `architect.png` | Architecture | Rolled blueprint, set-square behind its ear | Hexagonal | amber |
| `engineer.png` | Platform engineering | Gear antenna, wrench held up | Boxy, bolt ears | green |
| `analyst.png` | Data and insights | Chest screen with three rising bars | Tall capsule | pale-teal |
| `support.png` | Customer support insights | Headset with a microphone boom | Round, small dial ears | pale-indigo |
| `reviewer.png` | Review and editing | Half-moon glasses, big pen | Oval | pale-amber |
| `designer.png` | Design | Pen-nib antenna, color swatch fan | Soft rounded square | magenta |
| `tester.png` | Quality and testing | Check-mark badge, bug-catching net | Dome, two short antennae | pale-green |
| `scribe.png` | Note-taking | Open notepad, pencil behind its ear | Wide and flat, grille mouth | pale-magenta |
| `strategist.png` | Strategy | Compass-rose chest emblem, pointing forward | Tall and pointed, fin on top | indigo |

The built-in participants use: Risk Review `risk`, Cards Platform `engineer`,
Support Insights `support`, Mara Okafor `people/person-09`.

## Making a new one

Before you start, pick a prop and a head shape that no row above uses, and a
background that differs from the agents it usually appears with.

**With the script** (needs internet and your own OpenAI key; nothing is stored
in the repo):

```sh
export OPENAI_API_KEY=sk-...        # your own key; never commit it
python3 design/avatars/generate_avatar.py robot \
  --role "security" \
  --prop "a large padlock held against its chest" \
  --head "round head with a single wide visor" \
  --bg teal \
  --out design/avatars/roles/security.png

python3 design/avatars/generate_avatar.py person \
  --subject "a man in his fifties with a grey beard and a navy cardigan" \
  --bg pale-amber --out design/avatars/people/person-10.png
```

It uses `gpt-image-2` (set `AVATAR_MODEL` to change it) and, if Pillow is
installed, saves at 512x512. Add `--print-prompt` to see the prompt without
calling anything.

**Without an API key**, paste this prompt into ChatGPT, Gemini or any image
tool, filling in the brackets (or run the script with `--print-prompt` to fill
them for you):

> A single square avatar picture for a team roster. The whole square is a flat
> solid [background name] ([hex]) background, edge to edge, with no circle,
> border, frame or vignette drawn. The subject is head and shoulders,
> front-facing and centred, and fits inside the central 80% of the square so
> that both a circle crop and a rounded-square crop keep all of it. No text,
> letters, numbers or logos anywhere. Subject: a friendly robot who is the
> team's [role] agent. Cream (#fbfdfd) body and head with accents in one or two
> palette colors that contrast with the background. Its role is shown by one
> clear prop or feature: [prop]. The prop must still read at 24 pixels, so make
> it large and simple. Distinct head silhouette: [head]. Style: simple flat
> vector art, bold geometric shapes, no outlines, no gradients, no texture, no
> shading beyond one flat shadow tone, minimal features (dot eyes, simple
> smile), like a modern design-system avatar set. Colors limited to navy
> #0a223d, teal #0d6e78, magenta #b0237a, amber #d99a2b, indigo #4f46b8, green
> #17794a, cream #fbfdfd and pale tints of these.

For a person, replace the robot sentences with: "Subject: [who they look like].
Friendly neutral expression, simple clothing in a palette color that contrasts
with the background."

## Before you add it

- Look at it at 24px (the size in chat turns): the prop or face still reads.
- It sits beside the others in this folder without standing out: same flatness,
  same palette, same framing.
- PNG, JPEG, WebP or GIF, under 2 MB (the Picture field's limit). 512x512 PNG
  is about 200 KB.
- No real person's likeness and no company logos.
- New role robot: add its row to the table above in the same pull request.

## Keeping it in one place

The prompt wording lives in `generate_avatar.py` (`FRAME`, `ROBOT`, `PERSON`,
`STYLE`). If you change the style, change the script and the paste-in prompt
here together, and say why in `docs/product/decisions.md`.
