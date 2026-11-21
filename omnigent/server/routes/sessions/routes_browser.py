"""Browser action bridge routes."""

from __future__ import annotations

import asyncio
import secrets
import time
from typing import Any

from fastapi import (
    APIRouter,
    Request,
)

from omnigent.errors import ErrorCode, OmnigentError
from omnigent.runtime import (
    session_stream,
)
from omnigent.runtime.policies.approval import _ELICITATION_MODE
from omnigent.server._elicitation_registry import (
    _harness_elicitation_owners,
    _harness_elicitation_registry,
    _harness_parked_elicitations,
    _harness_pre_resolved_elicitations,
    _ParkedHarnessElicitation,
    _PreResolvedHarnessElicitation,
)
from omnigent.server.auth import (
    LEVEL_EDIT,
    AuthProvider,
)
from omnigent.server.routes._auth_helpers import (
    get_user_id as _get_user_id,
)
from omnigent.server.routes._auth_helpers import (
    require_access_and_level as _require_access_and_level,
)
from omnigent.server.routes._sessions.common import (
    _BROWSER_ACTION_NO_RENDERER_RESULT,
    _BROWSER_ACTION_TIMEOUT_RESULT,
    _browser_action_claim_events,
    _browser_action_claims,
    _browser_action_owners,
    _browser_action_registry,
    get_server_runner_router,
    set_server_runner_router,
)
from omnigent.server.schemas import (
    BrowserActionRequestEvent,
)
from omnigent.stores import ConversationStore
from omnigent.stores.permission_store import PermissionStore

# omnigent-slim: one canvas per session. When a session is open in several web UI
# tabs, each tab's viewer frame is a separate copy of the artifact with its own
# live state, so canvas_* actions must all land in the same tab. The server keeps
# one active viewer per session: the first tab to show the canvas, or the one the
# user last chose with "Use this tab". Other tabs refuse the claim and show
# themselves as inactive. Tabs heartbeat while they show a canvas; a viewer that
# stops (closed tab, closed viewer) goes stale and the next claimant takes over.
_CANVAS_VIEWER_STALE_S = 90.0
# Well inside the server's claim grace (``_BROWSER_ACTION_CLAIM_GRACE_S``, 2s).
_CANVAS_ACTIVE_CLAIM_WAIT_S = 1.0
_canvas_viewers: dict[str, dict[str, float]] = {}
_canvas_active: dict[str, str] = {}
_canvas_last_served: dict[str, str] = {}
_canvas_action_ids: set[str] = set()
_canvas_moved: set[str] = set()


def _canvas_fresh(session_id: str, viewer_id: str | None) -> bool:
    if not viewer_id:
        return False
    seen = _canvas_viewers.get(session_id, {}).get(viewer_id)
    return seen is not None and time.monotonic() - seen < _CANVAS_VIEWER_STALE_S


def _canvas_active_viewer(session_id: str) -> str | None:
    active = _canvas_active.get(session_id)
    if active and _canvas_fresh(session_id, active):
        return active
    _canvas_active.pop(session_id, None)
    return None


def register_browser_routes(
    router: APIRouter,
    *,
    conversation_store: ConversationStore,
    auth_provider: AuthProvider | None = None,
    permission_store: PermissionStore | None = None,
) -> None:
    """Register the browser routes on router."""

    @router.post(
        "/sessions/{session_id}/browser/action_request",
        # Internal embedded-browser flow — hidden from the public API reference.
        include_in_schema=False,
        response_model=None,
    )
    async def browser_action_request(
        request: Request,
        session_id: str,
        body: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Park one embedded-browser action and await the renderer result.

        Mints an ``action_id``, parks a Future owned by ``session_id``, publishes
        a ``browser.action_request`` event, gives a renderer a short claim grace,
        and then awaits up to ``_BROWSER_ACTION_AWAIT_S`` for the claimed action.
        An unclaimed request returns promptly so a non-renderer stream subscriber
        cannot cause the full timeout. Called by the runner's ``browser_*``
        dispatch, not the LLM.

        :param request: The inbound request, used for identity extraction.
        :param session_id: Session/conversation identifier, e.g.
            ``"conv_abc123"``.
        :param body: ``{"action": <str>, "args": <dict>}`` where ``action``
            is the ``browser_`` tool name minus the prefix.
        :returns: The renderer's action-result JSON, or the timeout result.
        :raises OmnigentError: 404 if no session exists.
        """
        user_id = _get_user_id(request, auth_provider)
        await _require_access_and_level(
            user_id, session_id, LEVEL_EDIT, permission_store, conversation_store
        )
        action = body.get("action")
        args = body.get("args")
        if not isinstance(action, str) or not action:
            raise OmnigentError(
                "browser action_request requires a non-empty 'action'",
                code=ErrorCode.INVALID_INPUT,
            )
        if not isinstance(args, dict):
            args = {}

        action_id = f"baction_{secrets.token_hex(16)}"
        future: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()
        claimed = asyncio.Event()
        _browser_action_registry[action_id] = future
        _browser_action_claim_events[action_id] = claimed
        _browser_action_owners[action_id] = session_id
        if action.startswith("canvas_"):  # omnigent-slim
            _canvas_action_ids.add(action_id)
        try:
            event = BrowserActionRequestEvent(
                type="browser.action_request",
                action_id=action_id,
                action=action,
                args=args,
            )
            from omnigent.server.routes import sessions as _sessions_facade

            delivered = _sessions_facade.session_stream.publish(session_id, event.model_dump())
            if delivered == 0:
                # Fail fast: the stream has no buffer or replay, so a
                # request delivered to zero subscribers can never be
                # answered — return immediately
                # instead of holding the runner's POST for the full
                # await budget. Checked on the publish return (not a
                # separate pre-check) so a subscriber disconnecting
                # between check and publish can't reintroduce the wait.
                return _BROWSER_ACTION_NO_RENDERER_RESULT
            try:
                await asyncio.wait_for(
                    claimed.wait(),
                    timeout=_sessions_facade._BROWSER_ACTION_CLAIM_GRACE_S,
                )
            except TimeoutError:
                # ``wait_for`` can time out in the same event-loop tick that
                # the claim handler sets the event. Honor that accepted lease
                # so the renderer cannot execute a side effect after we report
                # that no renderer claimed it.
                if not claimed.is_set():
                    return _BROWSER_ACTION_NO_RENDERER_RESULT
            done, _pending = await asyncio.wait(
                {future},
                timeout=_sessions_facade._BROWSER_ACTION_AWAIT_S,
                return_when=asyncio.FIRST_COMPLETED,
            )
            if future in done and not future.cancelled():
                result = future.result()
                # omnigent-slim: say so when this action ran in a different tab
                # from the last one, since that tab's page state may differ.
                if action_id in _canvas_moved and isinstance(result, dict):
                    result = {
                        **result,
                        "note": (
                            "the canvas moved to another browser tab since the last canvas "
                            "call; its page state may differ, so read it again"
                        ),
                    }
                return result
            # Timed out/cancelled with no renderer result (no subscribed app).
            return _BROWSER_ACTION_TIMEOUT_RESULT
        finally:
            # Drop registry entries so a resolved/timed-out action leaks nothing.
            if _browser_action_registry.get(action_id) is future:
                _browser_action_registry.pop(action_id, None)
            _browser_action_claim_events.pop(action_id, None)
            _browser_action_owners.pop(action_id, None)
            _browser_action_claims.pop(action_id, None)
            _canvas_action_ids.discard(action_id)
            _canvas_moved.discard(action_id)

    @router.post(
        "/sessions/{session_id}/canvas/viewer",
        include_in_schema=False,
        response_model=None,
    )
    async def canvas_viewer(
        request: Request,
        session_id: str,
        body: dict[str, Any],
    ) -> dict[str, Any]:
        """
        omnigent-slim: heartbeat, take over, or release a tab's canvas viewer.

        :param body: ``{"viewer_id": <str>, "take": <bool>, "closed": <bool>}``.
            ``take`` makes this tab the session's active canvas; ``closed``
            drops it (and frees the canvas if it was active). A plain heartbeat
            becomes active only when no fresh viewer is.
        :returns: ``{"active_viewer_id": <str | None>}``.
        """
        user_id = _get_user_id(request, auth_provider)
        await _require_access_and_level(
            user_id, session_id, LEVEL_EDIT, permission_store, conversation_store
        )
        viewer_id = body.get("viewer_id")
        if not isinstance(viewer_id, str) or not viewer_id or len(viewer_id) > 100:
            raise OmnigentError("canvas viewer requires a 'viewer_id'", code=ErrorCode.INVALID_INPUT)
        viewers = _canvas_viewers.setdefault(session_id, {})
        now = time.monotonic()
        for vid, seen in list(viewers.items()):
            if now - seen >= _CANVAS_VIEWER_STALE_S:
                viewers.pop(vid, None)
        if body.get("closed") is True:
            viewers.pop(viewer_id, None)
            if _canvas_active.get(session_id) == viewer_id:
                _canvas_active.pop(session_id, None)
        else:
            viewers[viewer_id] = now
            if body.get("take") is True or _canvas_active_viewer(session_id) is None:
                _canvas_active[session_id] = viewer_id
        if not viewers:
            _canvas_viewers.pop(session_id, None)
        return {"active_viewer_id": _canvas_active_viewer(session_id)}

    @router.post(
        "/sessions/{session_id}/browser/action_claim/{action_id}",
        # Internal embedded-browser flow — hidden from the public API reference.
        include_in_schema=False,
        response_model=None,
    )
    async def browser_action_claim(
        request: Request,
        session_id: str,
        action_id: str,
        viewer: str | None = None,
    ) -> dict[str, Any]:
        """
        Atomically claim a parked browser action (one winner per action).

        The request event fans out to every subscribed renderer; an atomic
        ``setdefault`` grants exactly one claim so they don't double-execute.
        Winner gets ``{"claimed": true, "claim_token": <token>}``; everyone
        else ``{"claimed": false}``.

        :param request: The inbound request, used for identity extraction.
        :param session_id: Session/conversation identifier, e.g.
            ``"conv_abc123"``.
        :param action_id: The action to claim, e.g. ``"baction_abc123"``.
        :param viewer: omnigent-slim: the claiming tab's canvas viewer id
            (``canvas_*`` actions only go to the session's active viewer).
        :returns: ``{"claimed": true, "claim_token": <str>}`` to the winner,
            ``{"claimed": false}`` to losers or for an unknown/expired action.
        :raises OmnigentError: 404 if no session exists.
        """
        user_id = _get_user_id(request, auth_provider)
        await _require_access_and_level(
            user_id, session_id, LEVEL_EDIT, permission_store, conversation_store
        )
        # Unknown / already-resolved action: nothing to claim.
        if _browser_action_owners.get(action_id) != session_id:
            return {"claimed": False}
        # omnigent-slim: a canvas action goes only to the session's active viewer;
        # with none, the first fresh viewer to claim becomes it.
        is_canvas = action_id in _canvas_action_ids
        if is_canvas:
            if viewer is None or not _canvas_fresh(session_id, viewer):
                return {"claimed": False}
            active = _canvas_active_viewer(session_id)
            if active is not None and active != viewer:
                # The active tab claims within milliseconds when it is alive. If it
                # doesn't (closed without saying so, or its viewer went away), this
                # tab takes over rather than leaving the canvas stuck until it goes stale.
                claimed_event = _browser_action_claim_events.get(action_id)
                if claimed_event is None:
                    return {"claimed": False}
                try:
                    await asyncio.wait_for(
                        claimed_event.wait(), timeout=_CANVAS_ACTIVE_CLAIM_WAIT_S
                    )
                    return {"claimed": False}
                except TimeoutError:
                    if _browser_action_owners.get(action_id) != session_id:
                        return {"claimed": False}
        # Single-winner lease via atomic setdefault: a losing racer sees the
        # winner's token, not its own, and bails.
        claim_token = secrets.token_hex(16)
        existing = _browser_action_claims.setdefault(action_id, claim_token)
        if existing != claim_token:
            return {"claimed": False}
        if is_canvas:  # omnigent-slim
            _canvas_active[session_id] = viewer
            last = _canvas_last_served.get(session_id)
            if last is not None and last != viewer:
                _canvas_moved.add(action_id)
            _canvas_last_served[session_id] = viewer
        claimed = _browser_action_claim_events.get(action_id)
        if claimed is not None:
            claimed.set()
        return {"claimed": True, "claim_token": claim_token}

    @router.post(
        "/sessions/{session_id}/browser/action_result/{action_id}",
        # Internal embedded-browser flow — hidden from the public API reference.
        include_in_schema=False,
        status_code=202,
        response_model=None,
    )
    async def browser_action_result(
        request: Request,
        session_id: str,
        action_id: str,
        body: dict[str, Any],
    ) -> dict[str, bool]:
        """
        Deliver a browser action result, resolving the parked Future.

        Guarded by owner + claim-token: the caller must present the token this
        action was leased under, so a renderer that lost the claim race can't
        resolve the Future with stale work (tokenless/mismatched → 403).

        :param request: The inbound request, used for identity extraction.
        :param session_id: Session/conversation identifier, e.g.
            ``"conv_abc123"``.
        :param action_id: The action being resolved, e.g. ``"baction_abc"``.
        :param body: ``{"result": <dict>, "claim_token": <str>}``.
        :returns: ``{"resolved": true}`` when the Future was set,
            ``{"resolved": false}`` when it was already done/gone.
        :raises OmnigentError: 404 if no session exists; 403 on a missing or
            mismatched claim token or an owner mismatch.
        """
        user_id = _get_user_id(request, auth_provider)
        await _require_access_and_level(
            user_id, session_id, LEVEL_EDIT, permission_store, conversation_store
        )
        claim_token = body.get("claim_token")
        expected = _browser_action_claims.get(action_id)
        if not isinstance(claim_token, str) or expected is None or claim_token != expected:
            raise OmnigentError(
                "browser action result requires a matching claim_token",
                code=ErrorCode.FORBIDDEN,
            )
        # Only the session that issued the action may resolve it.
        if _browser_action_owners.get(action_id) != session_id:
            raise OmnigentError(
                "browser action is not owned by this session",
                code=ErrorCode.FORBIDDEN,
            )
        future = _browser_action_registry.get(action_id)
        if future is None or future.done():
            return {"resolved": False}
        result = body.get("result")
        future.set_result(result if isinstance(result, dict) else {"result": result})
        return {"resolved": True}
