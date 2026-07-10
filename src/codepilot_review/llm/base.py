from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class LLMClient(ABC):
    """Abstract LLM client interface.

    Implementations (Groq, Bedrock) should provide a `generate` method that
    returns the raw provider response as a dict.
    """

    @abstractmethod
    def generate(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        """Generate text for the given prompt.

        Args:
            prompt: The textual prompt to send to the model.
            **kwargs: Provider-specific options.

        Returns:
            The provider's JSON-decoded response.
        """

        raise NotImplementedError
