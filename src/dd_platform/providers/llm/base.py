"""LLM adapter protocol — provider-agnostic interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .models import LLMRequest, LLMResponse, StructuredLLMRequest


class LLMAdapter(ABC):
    """Provider-agnostic LLM adapter protocol.

    All LLM access goes through this interface so that provider details
    never leak into orchestration or domain logic.
    """

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a text completion.

        Args:
            request: The LLM request with messages, model, and parameters.

        Returns:
            Normalized LLM response with content and usage metadata.
        """
        ...

    @abstractmethod
    async def generate_structured(
        self, request: StructuredLLMRequest
    ) -> LLMResponse:
        """Generate a structured (JSON schema-bound) completion.

        Args:
            request: The structured LLM request with response schema.

        Returns:
            Normalized LLM response with structured_output populated.
        """
        ...
