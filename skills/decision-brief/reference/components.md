# Visual components for a brief's stage

A visual's `html` is drawn inside the brief's stage. Compose it only from
these classes; the template styles them with the design tokens, so they
follow light and dark mode and match every other brief. No `<style>`, no
`<script>`, no colors, nothing loaded from the network (`brief.py check`
refuses them). A `style="min-height:…"` or `max-width` for sizing is fine.

## Wireframe: `.wf`

Rough screens. One or more `.wf-win` windows side by side.

```html
<div class="wf">
  <div class="wf-win"><div class="wf-title">Library</div><div class="wf-body">
    <div class="wf-row"><div class="wf-box navy">Header</div></div>
    <div class="wf-row">
      <div class="wf-col"><div class="wf-line"></div><div class="wf-line s"></div></div>
      <div class="wf-col"><div class="wf-box hi">The part this option changes</div><div class="wf-btn">Start</div></div>
    </div>
  </div></div>
</div>
```

- `.wf-win` > `.wf-title` + `.wf-body`; `.wf-row` (across), `.wf-col` (down).
- `.wf-box` a dashed block; add `solid`, `sunk`, `hi` (what changes), `attn`
  (needs the person), `you` (the person's own), `navy` (frame or main action).
- `.wf-line` text placeholder (`s` and `xs` shorter); `.wf-btn` a button;
  `.wf-label` a caption under a window.

## Flow: `.flow`

Steps left to right with arrows; they wrap on a phone.

```html
<ol class="flow">
  <li class="you"><b>You pick</b>Picks stay on the page</li>
  <li><b>Send</b>Into the chat box</li>
  <li class="hi"><b>Agent records</b>In the register</li>
</ol>
```

`li` classes: `hi`, `you`, `attn`.

## Comparison: `.cmp`

Cards side by side, one per thing compared.

```html
<div class="cmp">
  <div class="hi"><h5>Five arcs</h5><span class="chip info">Problem discovery</span> …</div>
  <div><h5>Three arcs</h5> …</div>
</div>
```

## File tree: `pre.tree`

```html
<pre class="tree">workspace/
├─ decisions/<span class="hi">scope.json</span>   <span class="dim">the brief</span>
└─ projects/checkout/registers.json</pre>
```

## Table: `table.grid`

Examples, criteria, a matrix. `td.yes` and `td.no` mark outcomes.

```html
<table class="grid"><tr><th>The ask</th><th>Gets</th></tr>
<tr><td>Cut scope or move the date?</td><td class="yes">Brief</td></tr></table>
```

## Chips: `.chip`

Inline labels: `ok` (done), `info` (ready, links), `attn` (needs the person),
`agent` (the agent working), `you` (the person's own), `navy`. Keep the
meanings in `product-aviator-design`.

## Images

Use `{"image": "shot.png", "caption": "…"}` instead of html for a real
screenshot or a rendered design. Save it beside the brief; `render` inlines
it. Keep each under about 1.5 MB.
