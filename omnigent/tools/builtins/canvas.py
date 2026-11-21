"""omnigent-slim: schema-only ``canvas_*`` tools that operate the visible canvas.

The canvas is the right-hand viewer in the Omnigent web UI, where
``ui_open_file`` shows a workspace HTML file in a sandboxed iframe. These tools
let the agent read and drive *that* frame, in the user's own browser tab, so the
user watches the actions happen. Nothing here reaches another browser, a
debugging port or the network.

Like the ``browser_*`` tools, execution lives in the runner dispatch layer
(``_CANVAS_TOOLS`` in ``omnigent/runner/tool_dispatch.py``). It reuses the
server's claim-first action relay (``/browser/action_request``) with action
names that start with ``canvas_``; the web UI's canvas relay
(``web/src/lib/canvasRelay.ts``) claims them and runs them inside the frame via
the artifact bridge (``web/src/lib/artifactBridge.ts``).
"""

from __future__ import annotations

from typing import Any

from omnigent.tools.base import Tool

_SELECTOR = {
    "type": "string",
    "description": (
        "CSS selector for the target element, e.g. '#display', 'button[data-key=\"7\"]'. "
        "Read the DOM with canvas_read to pick one."
    ),
}
_INDEX = {
    "type": "integer",
    "minimum": 0,
    "description": "Which match to use when several elements match (0 = first).",
}


def _schema(name: str, description: str, properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False,
            },
        },
    }


class _CanvasTool(Tool):
    """Shared shape: subclasses set ``NAME``, ``DESCRIPTION``, ``PROPERTIES``, ``REQUIRED``."""

    NAME = ""
    DESCRIPTION = ""
    PROPERTIES: dict[str, Any] = {}
    REQUIRED: list[str] = []

    @classmethod
    def name(cls) -> str:
        """Return the tool name."""
        return cls.NAME

    @classmethod
    def description(cls) -> str:
        """Return the agent-facing contract."""
        return cls.DESCRIPTION

    def get_schema(self) -> dict[str, Any]:
        """Return the OpenAI-format tool schema."""
        return _schema(self.NAME, self.DESCRIPTION, self.PROPERTIES, self.REQUIRED)


_AFTER = (
    " Runs in the canvas the user is looking at (the right-hand viewer), so they see it "
    "happen. Returns the page's visible text afterwards; call canvas_read for the full DOM "
    "and a screenshot."
)


class CanvasReadTool(_CanvasTool):
    """Read the live DOM and a screenshot of the canvas."""

    NAME = "canvas_read"
    DESCRIPTION = (
        "Read the artifact open in the canvas (the right-hand viewer in the Omnigent web UI): "
        "returns its full live DOM as HTML (current input values included) and a screenshot "
        "of the whole rendered page. Use it to check an artifact works and to see its current "
        "state. Open the file with ui_open_file first. Do not use Chrome or any other browser "
        "for the canvas."
    )
    PROPERTIES = {
        "dom": {"type": "boolean", "description": "Include the full DOM (default true)."},
        "screenshot": {
            "type": "boolean",
            "description": "Include a screenshot of the rendered page (default true).",
        },
        "selector": {
            "type": "string",
            "description": "Optional CSS selector: return only that element's DOM.",
        },
    }


class CanvasClickTool(_CanvasTool):
    """Click an element in the canvas."""

    NAME = "canvas_click"
    DESCRIPTION = (
        "Click an element in the canvas artifact, chosen by CSS selector or by its visible "
        "text (e.g. text '7' clicks the button labelled 7)." + _AFTER
    )
    PROPERTIES = {
        "selector": _SELECTOR,
        "text": {
            "type": "string",
            "description": (
                "Visible text of the element to click, matched exactly after trimming "
                "(buttons, links and other clickable elements first)."
            ),
        },
        "index": _INDEX,
    }


class CanvasTypeTool(_CanvasTool):
    """Type into an input in the canvas."""

    NAME = "canvas_type"
    DESCRIPTION = (
        "Type text into an input, textarea or contenteditable element in the canvas "
        "artifact, firing the input and change events a user's typing would." + _AFTER
    )
    PROPERTIES = {
        "selector": _SELECTOR,
        "text": {"type": "string", "description": "Text to type."},
        "clear": {
            "type": "boolean",
            "description": "Replace the current value (default true); false appends.",
        },
        "press_enter": {"type": "boolean", "description": "Press Enter afterwards."},
        "index": _INDEX,
    }
    REQUIRED = ["selector", "text"]


class CanvasSetContentTool(_CanvasTool):
    """Replace the contents of any element in the canvas."""

    NAME = "canvas_set_content"
    DESCRIPTION = (
        "Replace the contents of any element in the canvas artifact's live DOM, with HTML or "
        "plain text (for inputs, sets the value). This changes what the user sees now, not "
        "the file: edit the file too if the change should last." + _AFTER
    )
    PROPERTIES = {
        "selector": _SELECTOR,
        "html": {"type": "string", "description": "New inner HTML."},
        "text": {"type": "string", "description": "New text content (used if html is absent)."},
        "all": {"type": "boolean", "description": "Apply to every match, not just one."},
        "index": _INDEX,
    }
    REQUIRED = ["selector"]


class CanvasPressKeyTool(_CanvasTool):
    """Press a key in the canvas."""

    NAME = "canvas_press_key"
    DESCRIPTION = (
        "Press a keyboard key in the canvas artifact (keydown, keypress, keyup), on the "
        "focused element or on the element a selector names. Keys use KeyboardEvent.key "
        "names, e.g. 'Enter', 'Escape', 'Backspace', 'ArrowUp', '7', '+'." + _AFTER
    )
    PROPERTIES = {
        "key": {"type": "string", "description": "The key, e.g. 'Enter' or '7'."},
        "selector": {
            "type": "string",
            "description": "Optional CSS selector of the element to focus first.",
        },
    }
    REQUIRED = ["key"]


class CanvasEvalTool(_CanvasTool):
    """Run JavaScript inside the canvas frame."""

    NAME = "canvas_eval"
    DESCRIPTION = (
        "Run JavaScript inside the canvas artifact's sandboxed frame and return the result "
        "(JSON-serialised; promises are awaited). Use it to read app state or to do what the "
        "other canvas tools can't. The frame cannot reach the network or the Omnigent page."
    )
    PROPERTIES = {
        "script": {
            "type": "string",
            "description": (
                "An expression or statements; the value of the last expression is returned, "
                "e.g. 'document.querySelector(\"#display\").textContent'."
            ),
        }
    }
    REQUIRED = ["script"]


CANVAS_TOOL_CLASSES: tuple[type[_CanvasTool], ...] = (
    CanvasReadTool,
    CanvasClickTool,
    CanvasTypeTool,
    CanvasSetContentTool,
    CanvasPressKeyTool,
    CanvasEvalTool,
)

CANVAS_TOOL_NAMES: frozenset[str] = frozenset(cls.NAME for cls in CANVAS_TOOL_CLASSES)
