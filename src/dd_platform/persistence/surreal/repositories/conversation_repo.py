"""Conversation repository."""

from __future__ import annotations

from ....domain.conversation import Conversation, Message
from ....logging import get_logger
from ..client import SurrealClient

logger = get_logger(__name__)


class ConversationRepository:
    """Handles conversation and message persistence in SurrealDB."""

    def __init__(self, client: SurrealClient) -> None:
        self._client = client

    async def create_conversation(self, company_id: str) -> str:
        """Create a new conversation for a company.

        Args:
            company_id: The company this conversation is about.

        Returns:
            Created conversation record ID.
        """
        result = await self._client.create("conversation", {"company_id": company_id})
        conv_id = result.get("id") if isinstance(result, dict) else str(result)

        await self._client.execute(
            f"RELATE {conv_id}->conversation_about_company->{company_id};",
        )
        logger.info("conversation_created", conversation_id=conv_id, company_id=company_id)
        return conv_id

    async def add_message(self, message: Message) -> str:
        """Add a message to a conversation.

        Args:
            message: The message to add.

        Returns:
            Created message record ID.
        """
        data = message.model_dump(exclude={"id", "citations"})
        result = await self._client.create("message", data)
        msg_id = result.get("id") if isinstance(result, dict) else str(result)

        # Update conversation timestamp
        await self._client.execute(
            f"UPDATE {message.conversation_id} SET updated_at = time::now();",
        )

        logger.info(
            "message_added",
            message_id=msg_id,
            conversation_id=message.conversation_id,
            role=message.role,
        )
        return msg_id

    async def get_messages(
        self, conversation_id: str, limit: int = 50
    ) -> list[Message]:
        """Get messages for a conversation.

        Args:
            conversation_id: The conversation to query.
            limit: Max messages.

        Returns:
            List of Message records, oldest first.
        """
        result = await self._client.execute(
            "SELECT * FROM message WHERE conversation_id = $cid ORDER BY created_at ASC LIMIT $limit;",
            {"cid": conversation_id, "limit": limit},
        )
        if result and result[0].get("result"):
            return [Message(**r) for r in result[0]["result"]]
        return []

    async def get_conversation(self, conversation_id: str) -> Conversation | None:
        """Get a conversation by ID."""
        try:
            result = await self._client.select(conversation_id)
            if result:
                data = result if isinstance(result, dict) else result[0] if result else None
                if data:
                    return Conversation(**data)
        except Exception:
            pass
        return None
