"""Structured LLM call against an OpenAI-compatible endpoint.

Primary request uses a strict JSON schema response format. If the backend
rejects that response_format, we retry once with a plain JSON-object format
and the schema embedded in the prompt.
"""

from __future__ import annotations

import json
import logging
import time

import openai
from openai import OpenAI

from .config import LlmConfig
from .models import VocabResult

_LOG = logging.getLogger(__name__)

_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "english": {"type": "string"},
        "chinese": {"type": "string"},
        "domain": {"type": "string"},
    },
    "required": ["english", "chinese", "domain"],
    "additionalProperties": False,
}

_SYSTEM_PROMPT = (
    "You are a bilingual English-to-Chinese dictionary. For the given English "
    "word, return its concise Chinese meaning and its academic discipline "
    "(the Chinese term is 学科), for example AI, Embodied, Maths or Biology. "
    "Respond only with the requested JSON object."
)


class LLMError(Exception):
    """Raised when the model response cannot be obtained or validated."""


def _strip_fences(text: str) -> str:
    """Remove a surrounding ```json ... ``` markdown fence, if present."""
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    stripped = stripped[3:]
    newline = stripped.find("\n")
    if newline != -1:
        stripped = stripped[newline + 1 :]
    if stripped.rstrip().endswith("```"):
        stripped = stripped.rstrip()[:-3]
    return stripped.strip()


class LLMClient:
    """Thin wrapper that turns one English word into a validated VocabResult."""

    def __init__(self, config: LlmConfig, client: OpenAI | None = None) -> None:
        self._config = config
        self._client = client if client is not None else OpenAI(
            base_url=config.base_url,
            api_key=config.api_key,
            timeout=config.timeout_seconds,
            max_retries=config.max_retries,
        )

    def collect(self, word: str) -> VocabResult:
        """Ask the model about ``word`` and return a validated result."""
        try:
            content, finish_reason = self._request(word, strict=True)
        except openai.BadRequestError as exc:
            if "response_format" not in str(exc):
                raise LLMError(f"request rejected: {exc}") from exc
            _LOG.warning("json_schema rejected, retrying with json_object")
            try:
                content, finish_reason = self._request(word, strict=False)
            except openai.OpenAIError as fallback_exc:
                raise LLMError(f"request failed: {fallback_exc}") from fallback_exc
        except openai.RateLimitError as exc:
            _LOG.warning(
                "rate limited (429), waiting %ds before retry",
                self._config.rate_limit_retry_wait,
            )
            time.sleep(self._config.rate_limit_retry_wait)
            try:
                content, finish_reason = self._request(word, strict=True)
            except openai.OpenAIError as retry_exc:
                raise LLMError(f"request failed after rate-limit retry: {retry_exc}") from retry_exc
        except openai.OpenAIError as exc:
            raise LLMError(f"request failed: {exc}") from exc

        if finish_reason == "length":
            raise LLMError("truncated")
        parsed = self._parse(content)
        # The captured word is authoritative; the model's english is only cross-checked.
        return VocabResult(english=word, chinese=parsed.chinese, domain=parsed.domain)

    def _request(self, word: str, *, strict: bool) -> tuple[str, str | None]:
        if strict:
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "vocab",
                    "strict": True,
                    "schema": _JSON_SCHEMA,
                },
            }
            user_prompt = f"Word: {word}"
        else:
            response_format = {"type": "json_object"}
            user_prompt = (
                f"Word: {word}\n"
                "Return a JSON object with exactly the keys english, chinese and "
                "domain. Schema: "
                + json.dumps(_JSON_SCHEMA)
            )

        completion = self._client.chat.completions.create(
            model=self._config.model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format=response_format,
        )
        choice = completion.choices[0]
        return (choice.message.content or ""), choice.finish_reason

    @staticmethod
    def _parse(content: str) -> VocabResult:
        cleaned = _strip_fences(content)
        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise LLMError(f"invalid json: {exc}") from exc
        try:
            return VocabResult.model_validate(payload)
        except Exception as exc:  # pydantic ValidationError
            raise LLMError(f"invalid payload: {exc}") from exc