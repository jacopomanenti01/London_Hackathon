"""Chat service — grounded conversation against company profiles."""

from __future__ import annotations

from typing import Any

from ...domain.conversation import Citation, Message
from ...logging import get_logger
from ...persistence.surreal.repositories.conversation_repo import ConversationRepository
from ...persistence.surreal.repositories.profile_repo import ProfileRepository
from ...providers.llm.base import LLMAdapter
from ...providers.llm.models import LLMMessage, LLMRequest
from ...retrieval.assembler import ContextAssembler
from ...retrieval.interfaces import Retriever, RetrievalQuery

logger = get_logger(__name__)


class ChatService:
    """Evidence-backed chat against company profiles.

    Retrieves from snapshot, claims, evidence, and graph neighborhood.
    Cites claim IDs, evidence IDs, and source URLs. Distinguishes among
    known, inferred, contradictory, stale, and unknown information.
    """

    def __init__(
        self,
        llm: LLMAdapter,
        retriever: Retriever,
        context_assembler: ContextAssembler,
        conversation_repo: ConversationRepository,
        profile_repo: ProfileRepository,
    ) -> None:
        self._llm = llm
        self._retriever = retriever
        self._assembler = context_assembler
        self._conversation_repo = conversation_repo
        self._profile_repo = profile_repo

    async def chat(
        self,
        company_id: str,
        message: str,
        conversation_id: str | None = None,
        retrieval_profile: str = "schema_aware_graph_hybrid",
    ) -> dict[str, Any]:
        """Process a chat message with grounded evidence retrieval.

        Args:
            company_id: The company to chat about.
            message: The user's question or message.
            conversation_id: Existing conversation to continue, or None for new.
            retrieval_profile: Retrieval strategy to use.

        Returns:
            Dict with answer, citations, conversation_id, and metadata.
        """
        logger.info(
            "chat_started",
            company_id=company_id,
            conversation_id=conversation_id,
        )

        # Create or continue conversation
        if not conversation_id:
            conversation_id = await self._conversation_repo.create_conversation(company_id)

        # Store user message
        user_msg = Message(
            conversation_id=conversation_id,
            role="user",
            content=message,
        )
        await self._conversation_repo.add_message(user_msg)

        # Retrieve relevant context
        query = RetrievalQuery(
            company_id=company_id,
            query_text=message,
            retrieval_profile=retrieval_profile,
            top_k=15,
            include_contradictions=True,
        )
        results = await self._retriever.retrieve(query)

        # Assemble context
        context = self._assembler.assemble(
            company_id=company_id,
            retrieval_profile=retrieval_profile,
            results=results,
        )
        context_text = self._assembler.format_for_llm(context)

        # Load conversation history
        history = await self._conversation_repo.get_messages(conversation_id, limit=10)
        history_text = "\n".join(
            f"{'User' if m.role == 'user' else 'Assistant'}: {m.content}"
            for m in history[:-1]  # Exclude the just-added user message
        )

        # Generate grounded answer
        system_prompt = f"""You are a due diligence analyst assistant. Answer questions about the company
using ONLY the retrieved evidence and claims below. For each factual statement:
- Cite the evidence source
- Note confidence level
- Flag any contradictions
- If information is unknown or missing, say so explicitly

Conversation history:
{history_text}

{context_text}"""

        response = await self._llm.generate(
            LLMRequest(
                messages=[
                    LLMMessage(role="system", content=system_prompt),
                    LLMMessage(role="user", content=message),
                ],
                temperature=0.2,
                max_tokens=2000,
                task_type="chat",
            )
        )

        # Build citations from retrieval results
        citations = [
            Citation(
                claim_id=r.provenance_path[0] if r.provenance_path else None,
                evidence_id=r.provenance_path[1] if len(r.provenance_path) > 1 else None,
                url=r.source_url,
                excerpt=r.text_snippet[:200],
            )
            for r in results[:5]
        ]

        # Store assistant message
        assistant_msg = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=response.content,
            retrieval_refs=[
                {"result_type": r.result_type, "score": r.score}
                for r in results[:5]
            ],
            citations=citations,
        )
        await self._conversation_repo.add_message(assistant_msg)

        # Detect if follow-up research might be helpful
        follow_up_suggested = context.has_contradictions or any(
            "unknown" in response.content.lower()
            for _ in [1]
        )

        return {
            "conversation_id": conversation_id,
            "answer": response.content,
            "citations": [c.model_dump() for c in citations],
            "follow_up_research_suggested": follow_up_suggested,
            "retrieval_profile": retrieval_profile,
            "context_metadata": {
                "total_candidates": context.total_candidates,
                "selected": context.selected_count,
                "has_contradictions": context.has_contradictions,
                "sections_covered": context.sections_covered,
            },
        }
