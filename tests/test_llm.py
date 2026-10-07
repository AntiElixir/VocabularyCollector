import json
from types import SimpleNamespace

import httpx2 as httpx
import openai
import pytest

from vocab_collector.config import LlmConfig
from vocab_collector.llm import LLMClient, LLMError


class FakeCompletions:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def _completion(content, finish_reason="stop"):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content), finish_reason=finish_reason
            )
        ]
    )


def _bad_request(message):
    request = httpx.Request("POST", "https://example.test/api/v1/chat/completions")
    response = httpx.Response(400, request=request)
    return openai.BadRequestError(message, response=response, body=None)


def _client(responses):
    completions = FakeCompletions(responses)
    fake = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    config = LlmConfig(base_url="https://example.test/api/v1", api_key="sk-test", model="m")
    return LLMClient(config, client=fake), completions


def test_strict_schema_happy_path():
    content = json.dumps({"english": "heterogeneous", "chinese": "异质的", "domain": "AI"})
    client, completions = _client([_completion(content)])

    result = client.collect("heterogeneous")

    assert result.english == "heterogeneous"
    assert result.chinese == "异质的"
    assert result.domain == "AI"
    assert completions.calls[0]["response_format"]["type"] == "json_schema"
    assert completions.calls[0]["response_format"]["json_schema"]["strict"] is True


def test_model_english_is_ignored_in_favour_of_captured_word():
    content = json.dumps({"english": "WRONG", "chinese": "异质的", "domain": "AI"})
    client, _ = _client([_completion(content)])

    assert client.collect("heterogeneous").english == "heterogeneous"


def test_fenced_json_is_parsed():
    content = "```json\n" + json.dumps({"english": "a", "chinese": "中", "domain": "AI"}) + "\n```"
    client, _ = _client([_completion(content)])
    assert client.collect("a").chinese == "中"


def test_junk_content_raises_llm_error():
    client, _ = _client([_completion("not json at all")])
    with pytest.raises(LLMError):
        client.collect("word")


def test_finish_reason_length_raises():
    client, _ = _client([_completion("{}", finish_reason="length")])
    with pytest.raises(LLMError):
        client.collect("word")


def test_empty_field_raises():
    content = json.dumps({"english": "a", "chinese": "   ", "domain": "AI"})
    client, _ = _client([_completion(content)])
    with pytest.raises(LLMError):
        client.collect("a")


def test_response_format_rejection_triggers_one_fallback():
    good = json.dumps({"english": "a", "chinese": "中", "domain": "AI"})
    client, completions = _client(
        [_bad_request("response_format is not supported"), _completion(good)]
    )

    result = client.collect("a")

    assert result.chinese == "中"
    assert len(completions.calls) == 2
    assert completions.calls[1]["response_format"] == {"type": "json_object"}


def test_unrelated_bad_request_does_not_fall_back():
    client, completions = _client([_bad_request("model not found")])
    with pytest.raises(LLMError):
        client.collect("a")
    assert len(completions.calls) == 1


def test_fallback_failure_raises_llm_error():
    client, completions = _client(
        [_bad_request("response_format unsupported"), _completion("still junk")]
    )
    with pytest.raises(LLMError):
        client.collect("a")
    assert len(completions.calls) == 2