"""omnigent-slim: participant messages in the Inbox (``/v1/slim/inbox/participant-messages``).

A participant from the roster (``workspace/participants/``) can write to the
user outside the session they are looking at, or invite the user into a
session of their own. ``pa tell`` posts here; the message becomes an ordinary
Inbox item carrying a ``participant`` media block, so the Inbox lists, counts
and resolves it like any other item (D-68 to D-70).

Unlike ``POST /v1/inbox/items``, the caller is not an agent's runner: on the
single-user Flight Deck the CLI runs in a session's shell. The session named
in the body must exist and belong to the caller.
"""

from __future__ import annotations

import asyncio
import dataclasses
import time
from typing import Any, Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

from omnigent.errors import ErrorCode, OmnigentError
from omnigent.server.auth import RESERVED_USER_LOCAL, AuthProvider
from omnigent.server.inbox_dedupe import DedupeInputs, canonical_link, dedupe_key, normalize_topic
from omnigent.server.inbox_media import ParticipantBlock, ParticipantCard
from omnigent.server.routes._auth_helpers import require_user
from omnigent.stores import ConversationStore
from omnigent.stores.inbox_item_store import (
    INBOX_ITEMS_PER_SESSION,
    InboxItemStore,
    InboxSessionCapError,
    NewInboxItem,
)


class ParticipantMessageRequest(BaseModel):
    """Body for ``POST /v1/slim/inbox/participant-messages``."""

    model_config = ConfigDict(extra="forbid")

    participant: ParticipantCard
    intent: Literal["message", "invite"] = "message"
    session_id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=200)
    body_md: str = Field(min_length=1, max_length=8000)


def create_slim_participant_inbox_router(
    store: InboxItemStore,
    *,
    conversation_store: ConversationStore,
    auth_provider: AuthProvider | None = None,
) -> APIRouter:
    """Build the participant-message router.

    :param store: Store for Inbox items.
    :param conversation_store: Store used to check the named session.
    :param auth_provider: Auth provider; ``None`` when auth is off.
    :returns: The configured router.
    """
    router = APIRouter()

    @router.post("/slim/inbox/participant-messages")
    async def post_participant_message(
        request: Request, body: ParticipantMessageRequest
    ) -> dict[str, Any]:
        """Put one participant message or invitation in the caller's Inbox."""
        user_id = require_user(request, auth_provider)
        owner = user_id if user_id is not None else RESERVED_USER_LOCAL
        conversation = await asyncio.to_thread(
            conversation_store.get_conversation, body.session_id
        )
        if conversation is None:
            raise OmnigentError(
                f"No session {body.session_id!r} to point the message at",
                code=ErrorCode.NOT_FOUND,
            )
        label = conversation.title or "the session"
        link = {"type": "session", "ref": body.session_id, "label": label}
        # Each message is its own item: the topic carries the time, so two
        # messages never fold together the way repeated suggestions do.
        inputs = DedupeInputs(
            kind="info",
            primary_link=canonical_link(link),
            topic=normalize_topic(f"participant {body.participant.id} {time.time_ns()}"),
        )
        block = ParticipantBlock(
            type="participant", participant=body.participant, intent=body.intent
        )
        try:
            item = await asyncio.to_thread(
                lambda: store.create(
                    NewInboxItem(
                        user_id=owner,
                        source_session_id=body.session_id,
                        agent_id=conversation.agent_id or "",
                        kind="info",
                        title=body.title,
                        body_md=body.body_md,
                        links=[link],
                        actions=[],
                        media=[block.stored()],
                        primary_link=inputs.primary_link,
                        topic=inputs.topic,
                        dedupe_key=dedupe_key(inputs),
                    )
                )
            )
        except InboxSessionCapError as exc:
            raise OmnigentError(
                f"That session already has {INBOX_ITEMS_PER_SESSION} Inbox items; "
                "point the message at another session",
                code=ErrorCode.INVALID_INPUT,
            ) from exc
        return {"item": dataclasses.asdict(item)}

    return router
