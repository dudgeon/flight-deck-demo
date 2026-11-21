# Artifacts and the viewer

## Show something in the viewer

1. Write one self-contained HTML file inside the session workspace, by
   convention `artifacts/<short-kebab-name>.html`.
2. Call the `ui_open_file` tool (MCP server `omnigent`, full name
   `mcp__omnigent__ui_open_file`) with the path **relative to the workspace**:

   ```json
   {"path": "artifacts/q3-roadmap.html"}
   ```

3. Tell the user in one line what it shows and what they can click.

Rules for the path: forward slashes, no leading `/`, no `~`, no `..`, no URLs.
The tool returns once the request is sent; it does not prove the file opened.
Missing files show an error in the viewer.

`ui_open_file` opens any workspace file, not only HTML: Markdown, code, images,
CSV and notebooks render too.

## Update it

Edit the file, then call `ui_open_file` again with the same path. The viewer
reloads.

## What the viewer runs

- HTML renders in a sandboxed frame with JavaScript on. It cannot read the
  Omnigent page, cookies or other files.
- omnigent-slim sends a Content Security Policy that blocks every other host:
  no CDN scripts, web fonts, remote images or API calls. Inline all CSS and
  JavaScript; use inline SVG for charts and icons.
- Relative links to other files don't resolve. One file per artifact.
- Style it with Product Aviator's design tokens (`var(--pa-navy)`,
  `var(--pa-ink)` and the rest; see `skills/product-aviator-design`). The
  viewer injects the current tokens into every artifact and sets
  `data-theme="light"` or `"dark"` on its root to match the app, so an
  artifact that uses only tokens follows the app's mode and any later design
  change. For a file that should also look right opened on its own, start
  from a template, which carries a generated copy of the tokens.

## Talking back to the session

In the viewer, every artifact has:

```js
window.omnigent?.prompt("I pick option B");
```

It puts the text into the session's chat box. The user reviews it and presses
Send; nothing is sent automatically. Use it for buttons and forms ("Send my
answers", "Use these weights"). Always use `?.` so the file still works when
opened outside Omnigent.

When the next message comes from an artifact, update that artifact rather than
making a new one.

## Comments on artifacts

Users can select text in a rendered HTML artifact and leave a comment. Read
them with `list_comments`; after acting on one, mark it with `update_comment`
(see interfaces.md).

## Templates (omnigent-slim)

The library folder (`workspace/templates/` by default) holds:

- `artifacts/*.html`: templates. Each keeps its content in
  `<script type="application/json" id="artifact-data">` and renders itself from
  it, so a skill only has to copy the file and edit that JSON.
- `sessions/*.md`: extra starters (prompts) shown as another way into a
  featured skill on the Library page.

A template needs a `<title>` and `<meta name="description">`; the Hangar lists
it by those. Templates are not on the Library page (D-88). See the repository README for the full format.

## Reading and operating the canvas (omnigent-slim)

Claude can see and drive the artifact open in the viewer with the `canvas_*`
tools (MCP server `omnigent`, e.g. `mcp__omnigent__canvas_read`). They act on
the frame the user is looking at, in their own browser tab, so the user watches
each click happen.

| Tool | Does |
| --- | --- |
| `canvas_read` | Returns the full live DOM (current input values included) and a PNG screenshot of the whole rendered page. `{"dom": false}` or `{"screenshot": false}` skips one; `{"selector": "#form"}` returns one element's DOM. |
| `canvas_click` | Clicks by CSS selector (`{"selector": "#go"}`) or by visible text (`{"text": "7"}`); `index` picks among several matches. |
| `canvas_type` | Types into an input, textarea, select or contenteditable, firing `input` and `change`. `clear: false` appends; `press_enter: true` presses Enter. |
| `canvas_set_content` | Replaces any element's contents with `html` or `text` (for fields, sets the value). Changes the live page only, not the file. |
| `canvas_press_key` | Sends keydown/keypress/keyup (`{"key": "Enter"}`) to the focused element or a selector. |
| `canvas_eval` | Runs JavaScript in the frame and returns the JSON result (promises awaited). |

The click, type, set-content and key tools return the page's visible text
afterwards, so a skill can check the effect without a screenshot. Actions run
one at a time in the order they were sent, so a batch of clicks is safe.

Rules:

- Open the file with `ui_open_file` first, as an HTML preview. With nothing
  open (or the session not open in a browser tab) the tools fail at once with
  "nothing is open in the canvas".
- Don't use Claude in Chrome, computer use or any other browser for the
  canvas: they open a different copy of the page that the user can't see.
- With the session open in several browser tabs, each tab is its own copy of
  the page, so the tools use one of them: the tab where the canvas was opened
  most recently while visible, or the one the user picked with "Use this tab".
  The other tabs dim their canvas. When the tools move to another tab (the user
  took over, or the active tab closed), the result carries a `note` saying so:
  read the page again before relying on earlier state.
- Screenshots are drawn inside the frame from the DOM (an SVG
  `foreignObject`), so they match the page closely but skip CSS pseudo-element
  content and cross-origin images. Chrome and Edge support it; if a browser
  refuses, `canvas_read` still returns the DOM and says why there's no image.
- The tools need approval like any other tool unless the session's permission
  mode allows them (Auto usually does).

A good check after building an artifact: `canvas_read`, a couple of
`canvas_click`s on the main controls, then `canvas_read` again.

How it works: the runner sends each call through the server's action relay
(`/v1/sessions/<id>/browser/action_request`, the same route Omnigent's desktop
browser tools use, with `canvas_*` action names). The web UI tab showing that
session's canvas claims it (`web/src/lib/canvasRelay.ts`) and posts it into the
sandboxed frame, where the artifact bridge runs it
(`web/src/lib/canvasFrameRuntime.ts`). The server keeps one active canvas tab
per session (`POST /v1/sessions/<id>/canvas/viewer` heartbeats, take-overs and
releases) and only that tab's claim succeeds. Nothing leaves this machine and the frame
keeps its sandbox and Content Security Policy.
