
"""Gemini API client using the existing LLM interface."""

from dataclasses import dataclass
from typing import Protocol


class LLMError(Exception):
    def __init__(self, user_message: str):
        self.user_message = user_message
        super().__init__(user_message)


@dataclass(frozen=True)
class LLMReply:
    text: str
    truncated: bool = False


class LLMClient(Protocol):
    model: str

    def complete(self, system: str, user: str, max_tokens: int) -> LLMReply: ...


class GeminiLLM:
    def __init__(self, api_key: str, model: str, timeout: float = 120):
        try:
            from google import genai
        except ImportError:
            raise LLMError(
                "Google Gemini SDK is missing. Check requirements.txt."
            ) from None

        self.model = model
        self._client = genai.Client(api_key=api_key)

    def complete(self, system: str, user: str, max_tokens: int) -> LLMReply:
        try:
            from google.genai import types

            response = self._client.models.generate_content(
                model=self.model,
                contents=user,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    max_output_tokens=max_tokens,
                ),
            )
            text = response.text or ""
            truncated = False

            if response.candidates:
                reason = response.candidates[0].finish_reason
                truncated = getattr(reason, "name", "") == "MAX_TOKENS"

            return LLMReply(text=text, truncated=truncated)

        except Exception as exc:
            raise LLMError(
                f"Gemini API request failed ({type(exc).__name__}). "
                "Check the API key, model name, and quota."
            ) from None
