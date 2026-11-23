#!/usr/bin/env python3
"""Write the Product Aviator design tokens out to everything that uses them.

design/tokens.json is the only place colors, type and corners are defined.
This script copies them, as CSS variables named --pa-<name>, into:

  web/src/designTokens.generated.css     the app (light on :root, dark on .dark)
  web/src/lib/designTokens.generated.ts  the canvas viewer, which hands the
                                         current tokens to every artifact frame
  skills/view-kit/kit/pa-kit.css         chat widgets and canvas views
  skills/view-kit/kit/harness.html       the scenario preview player
  skills/decision-brief/template/brief.html  the decision brief page
  workspace/templates/artifacts/*.html   artifact templates

In the last three, only the text between the `pa-tokens:begin` and
`pa-tokens:end` comments is replaced. Standard library only, no network.

  python3 design/build_tokens.py          rewrite every consumer
  python3 design/build_tokens.py --check  fail if any consumer is out of date
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "design" / "tokens.json"
BEGIN = "/* pa-tokens:begin: generated from design/tokens.json by design/build_tokens.py. Do not edit here. */"
END = "/* pa-tokens:end */"
REGION = re.compile(r"/\* pa-tokens:begin[^*]*\*/.*?/\* pa-tokens:end \*/", re.S)
REGION_FILES = [
    ROOT / "skills/view-kit/kit/pa-kit.css",
    ROOT / "skills/view-kit/kit/harness.html",
    ROOT / "skills/decision-brief/template/brief.html",
]
TEMPLATE_DIR = ROOT / "workspace/templates/artifacts"


def load() -> dict:
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    light, dark = data["light"], data["dark"]
    if set(light) != set(dark):
        missing = sorted(set(light) ^ set(dark))
        raise SystemExit(f"tokens.json: light and dark must name the same tokens; differ in {missing}")
    return data


def decls(values: dict, indent: str = "  ") -> str:
    return "\n".join(f"{indent}--pa-{k}: {v};" for k, v in values.items())


def standalone_css(data: dict) -> str:
    """Tokens for a self-contained HTML file: follows the system setting, and
    the viewer's data-theme attribute when it sets one."""
    light = {**data["base"], **data["light"]}
    return "\n".join([
        BEGIN,
        ":root {", decls(light), "}",
        '@media (prefers-color-scheme: dark) {',
        '  :root:not([data-theme="light"]) {', decls(data["dark"], "    "), "    color-scheme: dark;", "  }",
        "}",
        ':root[data-theme="dark"] {', decls(data["dark"]), "  color-scheme: dark;", "}",
        END,
    ])


def web_css(data: dict) -> str:
    light = {**data["base"], **data["light"]}
    return "\n".join([
        "/* Generated from design/tokens.json by design/build_tokens.py. Do not edit. */",
        "/* omnigent-slim: Product Aviator design tokens. The app's own color",
        " * variables point at these in index.css and themePalette.ts. */",
        ":root {", decls(light), "}", "", ".dark {", decls(data["dark"]), "}", "",
    ])


def web_ts(data: dict) -> str:
    body = json.dumps({"base": data["base"], "light": data["light"], "dark": data["dark"]}, indent=2)
    return (
        "// Generated from design/tokens.json by design/build_tokens.py. Do not edit.\n"
        "// omnigent-slim: the canvas viewer hands these to every artifact frame\n"
        "// (see injectDesignTokens in artifactBridge.ts).\n"
        f"export const PA_TOKENS = {body} as const;\n"
    )


def outputs(data: dict) -> tuple[dict[Path, str], list[str]]:
    out: dict[Path, str] = {
        ROOT / "web/src/designTokens.generated.css": web_css(data),
        ROOT / "web/src/lib/designTokens.generated.ts": web_ts(data),
    }
    problems: list[str] = []
    block = standalone_css(data)
    targets = list(REGION_FILES) + sorted(TEMPLATE_DIR.glob("*.html"))
    for path in targets:
        text = path.read_text(encoding="utf-8")
        if not REGION.search(text):
            problems.append(f"{path.relative_to(ROOT)}: no pa-tokens:begin/end region")
            continue
        out[path] = REGION.sub(lambda _m: block, text, count=1)
    return out, problems


def main(argv: list[str]) -> int:
    check = "--check" in argv
    data = load()
    out, problems = outputs(data)
    stale = []
    for path, text in out.items():
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current == text:
            continue
        if check:
            stale.append(str(path.relative_to(ROOT)))
        else:
            path.write_text(text, encoding="utf-8")
            print(f"wrote {path.relative_to(ROOT)}")
    for p in problems:
        print(f"error: {p}", file=sys.stderr)
    if stale:
        print("out of date (run python3 design/build_tokens.py): " + ", ".join(stale), file=sys.stderr)
    if not check and not problems:
        print(f"tokens up to date in {len(out)} files")
    return 1 if (problems or stale) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
