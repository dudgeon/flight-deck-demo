"""omnigent-slim: participant messages and invitations land in the Inbox (D-68 to D-70)."""

from __future__ import annotations

import dataclasses
from types import SimpleNamespace
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from omnigent.entities import InboxItem
from omnigent.errors import OmnigentError
from omnigent.server.routes.slim_participant_inbox import create_slim_participant_inbox_router
from omnigent.stores.inbox_item_store import NewInboxItem

SESSION = "0123456789abcdef0123456789abcdef"
MARA = {
    "id": "mara-okafor",
    "name": "Mara Okafor",
    "kind": "person",
    "role": "Design lead, Cards",
    "stand_in": True,
}


class _Store:
    def __init__(self) -> None:
        self.created: list[NewInboxItem] = []

    def create(self, item: NewInboxItem, *, retire_item_id: str | None = None) -> InboxItem:
        self.created.append(item)
        fields = {f.name: getattr(item, f.name) for f in dataclasses.fields(item)}
        return InboxItem(
            id="f" * 32,
            status="unread",
            resolution="none",
            feedback_text=None,
            created_at=1,
            **fields,
        )


class _Conversations:
    def get_conversation(self, conversation_id: str) -> Any:
        if conversation_id != SESSION:
            return None
        return SimpleNamespace(title="Allowances PRD", agent_id="agent1")


def _client() -> tuple[TestClient, _Store]:
    store = _Store()
    app = FastAPI()

    @app.exception_handler(OmnigentError)
    async def _error(request: Request, exc: OmnigentError) -> JSONResponse:
        return JSONResponse({"error": str(exc)}, status_code=exc.http_status)

    app.include_router(
        create_slim_participant_inbox_router(store, conversation_store=_Conversations()),  # type: ignore[arg-type]
        prefix="/v1",
    )
    return TestClient(app), store


def _post(client: TestClient, **over: Any) -> Any:
    body = {
        "participant": MARA,
        "session_id": SESSION,
        "title": "Can we talk about 5.2?",
        "body_md": "Can I get 20 minutes before Thursday?",
        **over,
    }
    return client.post("/v1/slim/inbox/participant-messages", json=body)


def test_a_message_becomes_an_inbox_item_with_the_sender() -> None:
    client, store = _client()
    response = _post(client)
    assert response.status_code == 200, response.text
    item = store.created[0]
    assert item.source_session_id == SESSION
    assert item.links == [{"type": "session", "ref": SESSION, "label": "Allowances PRD"}]
    assert item.media == [{"type": "participant", "participant": MARA, "intent": "message"}]
    assert response.json()["item"]["status"] == "unread"


def test_an_invitation_is_marked_invite() -> None:
    client, store = _client()
    assert _post(client, intent="invite").status_code == 200
    assert store.created[0].media[0]["intent"] == "invite"


def test_two_messages_never_fold_together() -> None:
    client, store = _client()
    _post(client)
    _post(client)
    assert store.created[0].dedupe_key != store.created[1].dedupe_key


def test_an_unknown_session_is_refused() -> None:
    client, store = _client()
    assert _post(client, session_id="f" * 32).status_code == 404
    assert store.created == []
