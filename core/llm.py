"""The only module that talks to the Claude API.

The rest of the code depends on the small LLMClient interface, so tests can use a fake.
Error messages shown to users never include text from the API's reply or from papers.
"""
from dataclasses import dataclass
from typing import Protocol


class LLMError(Exception):
    def __init__(self, user_message: str):
        self.user_message = user_message
        super().__init__(user_message)


@dataclass(frozen=True)
class LLMReply:
    text: str
    truncated: bool = False   # True when the model stopped because it hit the output limit


class LLMClient(Protocol):
    model: str

    def complete(self, system: str, user: str, max_tokens: int) -> LLMReply: ...


_MESSAGES = {
    "AuthenticationError": "The API key was rejected. Check ANTHROPIC_API_KEY.",
    "PermissionDeniedError": "The API key is not allowed to use this model.",
    "NotFoundError": "The model name was not found. Check the model setting.",
    "RateLimitError": "The API rate limit was reached. Wait a minute and try again.",
    "APITimeoutError": "The request to the API timed out. Try again.",
    "APIConnectionError": "Could not reach the API. Check the internet connection.",
    "BadRequestError": "The API rejected the request. The paper may be too large for the model.",
    "InternalServerError": "The API service had a problem. Try again shortly.",
    "OverloadedError": "The API service is busy. Try again shortly.",
}


def to_llm_error(exc: Exception) -> LLMError:
    """Convert SDK exceptions into safe, useful error messages."""
    for cls in type(exc).__mro__:
        if cls.__name__ in _MESSAGES:
            return LLMError(
                f"{_MESSAGES[cls.__name__]} (Error type: {type(exc).__name__})"
            )
    return LLMError(
        f"The API request failed. Error type: {type(exc).__name__}. "
        "Check the API key, billing, and model settings."
    )



class AnthropicLLM:
    def __init__(self, api_key: str, model: str, timeout: float):
        try:
            import anthropic
        except ImportError:
            raise LLMError("The 'anthropic' package is not installed. "
                           "Run: pip install -r requirements.txt") from None
        self.model = model
        self._client = anthropic.Anthropic(api_key=api_key, timeout=timeout)

    def complete(self, system: str, user: str, max_tokens: int) -> LLMReply:
        try:
            response = self._client.messages.create(
                model=self.model, max_tokens=max_tokens, system=system,
                messages=[{"role": "user", "content": user}],
            )
        except Exception as exc:
            raise to_llm_error(exc) from None
        text = "".join(getattr(b, "text", "") for b in response.content
                       if getattr(b, "type", "") == "text")
        return LLMReply(text=text, truncated=getattr(response, "stop_reason", None) == "max_tokens")
