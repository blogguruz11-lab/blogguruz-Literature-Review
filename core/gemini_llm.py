"""Gemini API client using the existing LLM interface."""

from core.llm import LLMError, LLMReply


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
                f"Gemini API request failed: {str(exc)[:500]}"
            ) from None
