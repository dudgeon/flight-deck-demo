"""Rich content an agent can attach to an Inbox item, as typed blocks.

An item's ``media`` is a list of blocks shaped like OpenAI content parts:
``{"type": "chart", "chart": {...}}``. The server accepts only block types it
can validate, and the web app skips types it cannot draw, so a new type (an
SVG, a reference to a stored file) adds a block model here and a renderer in
the web app, with no schema change.
"""

from __future__ import annotations

import json
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from omnigent.server.inbox_chart import InboxChartV1

MAX_MEDIA_BLOCKS = 3
# Serialized size limit for all blocks, below the column's 16,383 stored-byte cap.
MAX_MEDIA_JSON_BYTES = 16_000


class ChartBlock(BaseModel):
    """A chart drawn on the card; see :class:`InboxChartV1`."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["chart"]
    chart: InboxChartV1

    def stored(self) -> dict[str, Any]:
        """The block as stored and returned, using the wire field names."""
        return {"type": self.type, "chart": self.chart.stored()}


class ParticipantCard(BaseModel):
    """Who a participant message is from, as the roster file describes them."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z][a-z0-9-]{0,63}$")
    name: str = Field(min_length=1, max_length=120)
    kind: Literal["agent", "person"]
    role: str = Field(default="", max_length=200)
    stand_in: bool = False


class ParticipantBlock(BaseModel):
    """omnigent-slim: marks an item as a message from a roster participant.

    ``intent`` is ``"message"`` when they write to the user about a session,
    or ``"invite"`` when they ask the user to join a session of their own.
    The item's first session link is the session the card opens.
    """

    model_config = ConfigDict(extra="forbid")

    type: Literal["participant"]
    participant: ParticipantCard
    intent: Literal["message", "invite"] = "message"

    def stored(self) -> dict[str, Any]:
        """The block as stored and returned."""
        return {
            "type": self.type,
            "participant": self.participant.model_dump(),
            "intent": self.intent,
        }


# The block types the server accepts. Add a type as a union member with a
# ``type`` literal and annotate the union with ``Field(discriminator="type")``.
InboxMediaBlock = Annotated[ChartBlock | ParticipantBlock, Field(discriminator="type")]


def stored_media(blocks: list[InboxMediaBlock]) -> list[dict[str, Any]]:
    """Return *blocks* as stored.

    :raises ValueError: If they serialize to more than
        :data:`MAX_MEDIA_JSON_BYTES` bytes of JSON.
    """
    stored = [block.stored() for block in blocks]
    if len(json.dumps(stored).encode("utf-8")) > MAX_MEDIA_JSON_BYTES:
        raise ValueError(f"media is larger than {MAX_MEDIA_JSON_BYTES} bytes of JSON")
    return stored
