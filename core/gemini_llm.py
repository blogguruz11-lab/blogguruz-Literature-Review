
"""Gemini API client with automatic retries for temporary service errors."""

import time

from core.llm import LLMError, LLMReply


class GeminiLLM:

    MAX_ATTEMPTS = 4
    RETRY_DELAYS = (2, 4, 8)

    RETRYABLE_CODES = {500, 502, 503, 504}

    def __init__(
        self,
        api_key: str,
        model: str,
        timeout: float = 120,
    ):
        try:
            from google import genai

        except ImportError:
            raise LLMError(
                "Google Gemini SDK is missing. Check requirements.txt."
            ) from None

        self.model = model
        self.timeout = timeout
        self._client = genai.Client(api_key=api_key)

    def _is_retryable(self, exc: Exception) -> bool:
        """Identify temporary Gemini service errors."""

        code = getattr(exc, "code", None)

        if code is None:
            status = getattr(exc, "status", None)

            if isinstance(status, int):
                code = status

        if code is not None:
            try:
                if int(code) in self.RETRYABLE_CODES:
                    return True
            except (TypeError, ValueError):
                pass

        message = str(exc).upper()

        return any(
            marker in message
            for marker in (
                "503 UNAVAILABLE",
                "500 INTERNAL",
                "502 BAD GATEWAY",
                "504 GATEWAY TIMEOUT",
            )
        )

    def complete(
        self,
        system: str,
        user: str,
        max_tokens: int,
    ) -> LLMReply:

        from google.genai import types

        last_error = None

        for attempt in range(self.MAX_ATTEMPTS):

            try:
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

                    truncated = (
                        getattr(reason, "name", "") == "MAX_TOKENS"
                    )

                return LLMReply(
                    text=text,
                    truncated=truncated,
                )

            except Exception as exc:

                last_error = exc

                # Do not retry permanent errors or quota exhaustion.
                if not self._is_retryable(exc):
                    break

                # Stop after the final attempt.
                if attempt == self.MAX_ATTEMPTS - 1:
                    break

                delay = self.RETRY_DELAYS[attempt]

                time.sleep(delay)

        raise LLMError(
            f"Gemini API request failed after "
            f"{self.MAX_ATTEMPTS} attempts: "
            f"{str(last_error)[:500]}"
        ) from None
