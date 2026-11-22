# Frameworks

A framework is a markdown file that says how deep and how broad a piece of
thinking has to be before it moves on. Skills read these files; nothing here
is code. Edit them, or add your own, and the skills follow.

- `intent.md`: used by the `intent-shaping` skill. It is **notional**: an
  invented stand-in for a company's real framework for defining intent.
  Replace it with the real one when there is one, keeping the same headings.

To use a different framework in one session, say so: "shape this using
frameworks/my-framework.md".
- `lifecycle.json`: the stages a feature moves through (Discover, Shape,
  Specify, Engage, Deliver; D-148 to D-152). Moves that fit every stage, such as review and decide, use the stage `any`. Each workflow names its stage in the
  `routing` block of its `workflow.json`, so a new workflow lands under its
  stage by itself, and a new stage is one line here (D-120). `pa workflows`
  lists the workflows by stage.
