"""omnigent-slim: the usage log's routes (D-122 to D-127).

``POST /v1/slim/usage/events`` takes the web app's analytics events, sent by
our host analytics sink (``web/src/lib/slimUsage.ts``) for upstream's own
emitters (``web/src/lib/host.ts``), and writes them to the usage log.
``GET /v1/slim/usage/summary`` returns the counts ``pa usage summary`` prints,
for a later Hangar page. The log itself: ``omnigent/slim_usage.py``.
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Request

from omnigent.server.auth import AuthProvider
from omnigent.server.routes._auth_helpers import require_user
from omnigent.slim_usage import log, usagelog, web_event_to_line

MAX_WEB_BATCH = 100


def create_slim_usage_router(*, auth_provider: AuthProvider | None = None) -> APIRouter:
    """``POST /v1/slim/usage/events`` and ``GET /v1/slim/usage/summary``."""
    router = APIRouter()

    @router.post("/slim/usage/events")
    async def post_usage_events(request: Request, body: dict[str, Any] = Body(...)) -> dict[str, Any]:
        require_user(request, auth_provider)
        events = body.get("events")
        if not isinstance(events, list):
            raise HTTPException(status_code=400, detail="events must be a list")
        mode = body.get("mode") if body.get("mode") in ("flying", "hangar", "demo") else None
        lines = []
        for event in events[:MAX_WEB_BATCH]:
            mapped = web_event_to_line(event)
            if mapped is not None:
                lines.append(mapped)

        def _write() -> int:
            for name, params, session in lines:
                path = params.get("path")
                line_mode = mode
                if isinstance(path, str) and "/hangar" in path:
                    line_mode = "hangar"
                log(
                    name,
                    source="web",
                    params=params,
                    context={"mode": line_mode} if line_mode else None,
                    session_id=session,
                )
            return len(lines)

        written = await asyncio.to_thread(_write)
        return {"written": written, "dropped": len(events) - written}

    @router.get("/slim/usage/summary")
    async def get_usage_summary(request: Request, since: str | None = None, eval: bool = False) -> dict[str, Any]:
        require_user(request, auth_provider)
        module = usagelog()
        if module is None:
            return {"enabled": False}

        def _summary() -> dict[str, Any]:
            try:
                since_ns = module.parse_since(since)
            except ValueError as err:
                raise HTTPException(status_code=400, detail=str(err)) from err
            summary = module.summarize(module.read(module.log_files(include_eval=eval), since_ns))
            summary["enabled"] = module.enabled()
            summary["folder"] = str(module.usage_dir())
            summary["level"] = module.level()
            return summary

        return await asyncio.to_thread(_summary)

    return router
