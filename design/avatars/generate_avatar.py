#!/usr/bin/env python3
"""Generate a Product Aviator avatar (person or role robot) from the style guide.

Dev-machine tool only: it calls the OpenAI image API, so it needs internet and
your OWN key in the OPENAI_API_KEY environment variable. The app never runs or
imports it, and no key is stored in the repo. See design/avatars/README.md.

    export OPENAI_API_KEY=sk-...            # your key, never committed
    python3 design/avatars/generate_avatar.py robot --role "risk and compliance" \
        --prop "a shield-shaped chest plate with a check mark" --bg navy \
        --out design/avatars/roles/risk.png
    python3 design/avatars/generate_avatar.py person \
        --subject "a woman in her forties with short curly hair and round glasses" \
        --bg teal --out ~/Desktop/mara.png
    python3 design/avatars/generate_avatar.py robot --role planner --prop "..." --print-prompt

Python 3 standard library only. If Pillow is installed the result is resized to
512x512; otherwise the 1024x1024 original is kept (still under the 2 MB limit
of the Hangar's Picture field once saved as PNG, usually ~1.2 MB).
"""
import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request

# Background colors: the design tokens in design/tokens.json (light theme).
# Keep the subject's own colors inside this palette too.
PALETTE = {
    "navy": "#0a223d",
    "teal": "#0d6e78",
    "magenta": "#b0237a",
    "amber": "#d99a2b",
    "indigo": "#4f46b8",
    "green": "#17794a",
    "pale-teal": "#d9f0f1",
    "pale-indigo": "#e8e6f8",
    "pale-amber": "#f9ebcf",
    "pale-green": "#ddf1e6",
    "pale-magenta": "#f8e1ef",
}

# The fixed style block. Change it only together with README.md, and
# regenerate the reference set when you do, or new avatars will stop matching.
STYLE = (
    "Style: simple flat vector art, bold geometric shapes, no outlines, no "
    "gradients, no texture, no shading beyond one flat shadow tone, minimal "
    "features (dot eyes, simple smile), like a modern design-system avatar "
    "set. Colors limited to navy #0a223d, teal #0d6e78, magenta #b0237a, "
    "amber #d99a2b, indigo #4f46b8, green #17794a, cream #fbfdfd and pale "
    "tints of these."
)

FRAME = (
    "A single square avatar picture for a team roster. The whole square is a "
    "flat solid {bg_name} ({bg_hex}) background, edge to edge, with no circle, "
    "border, frame or vignette drawn. The subject is head and shoulders, "
    "front-facing and centred, and fits inside the central 80% of the square "
    "so that both a circle crop and a rounded-square crop keep all of it. "
    "No text, letters, numbers or logos anywhere."
)

ROBOT = (
    "Subject: a friendly robot who is the team's {role} agent. Cream (#fbfdfd) "
    "body and head with accents in one or two palette colors that contrast "
    "with the background. Its role is shown by one clear prop or feature: "
    "{prop}. The prop must still read at 24 pixels, so make it large and "
    "simple. Distinct head silhouette: {head}."
)

PERSON = (
    "Subject: {subject}. Friendly neutral expression, simple clothing in a "
    "palette color that contrasts with the background."
)


def build_prompt(args):
    bg_hex = PALETTE[args.bg]
    parts = [FRAME.format(bg_name=args.bg.replace("-", " "), bg_hex=bg_hex)]
    if args.kind == "robot":
        parts.append(ROBOT.format(role=args.role, prop=args.prop,
                                  head=args.head or "your choice, unlike a plain box"))
    else:
        parts.append(PERSON.format(subject=args.subject))
    parts.append(STYLE)
    return " ".join(parts)


def generate(prompt, model, out):
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        sys.exit("Set OPENAI_API_KEY to your own OpenAI key first (it is never stored in the repo).")
    req = urllib.request.Request(
        "https://api.openai.com/v1/images/generations",
        data=json.dumps({"model": model, "prompt": prompt, "size": "1024x1024",
                         "quality": "high", "n": 1}).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"OpenAI said {e.code}: {e.read().decode(errors='replace')[:600]}")
    png = base64.b64decode(data["data"][0]["b64_json"])
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "wb") as f:
        f.write(png)
    try:
        from PIL import Image
        Image.open(out).resize((512, 512), Image.LANCZOS).save(out, optimize=True)
    except ImportError:
        pass
    print(f"saved {out}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("kind", choices=["robot", "person"])
    ap.add_argument("--role", help="robot: the role, e.g. 'risk and compliance'")
    ap.add_argument("--prop", help="robot: the one prop or feature that shows the role")
    ap.add_argument("--head", help="robot: head shape, e.g. 'tall capsule with a visor'")
    ap.add_argument("--subject", help="person: who they look like")
    ap.add_argument("--bg", choices=sorted(PALETTE), default="teal")
    ap.add_argument("--model", default=os.environ.get("AVATAR_MODEL", "gpt-image-2"))
    ap.add_argument("--out", help="PNG path to write")
    ap.add_argument("--print-prompt", action="store_true",
                    help="print the prompt (to paste into ChatGPT or another tool) and stop")
    args = ap.parse_args()
    if args.kind == "robot" and not (args.role and args.prop):
        ap.error("robot needs --role and --prop")
    if args.kind == "person" and not args.subject:
        ap.error("person needs --subject")
    prompt = build_prompt(args)
    if args.print_prompt or not args.out:
        print(prompt)
        return
    generate(prompt, args.model, args.out)


if __name__ == "__main__":
    main()
