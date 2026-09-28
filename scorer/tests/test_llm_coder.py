"""LLMCoder with a mocked Anthropic client (no network)."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from scorer.coders.base import CoderUnavailable
from scorer.coders.llm import DEFAULT_MODEL, OUTPUT_SCHEMA, LLMCoder
from scorer.schema import CodeRequest, FQHint, Location

REQ = CodeRequest(card=3, verbatim="two people dancing", inquiry="here, the legs and heads",
                  location=Location(code="D", number=9, label="D9"),
                  fq_hint=FQHint(item="Human", content="H", fq="o"))

GOOD = {
    "dq": "+", "determinants": ["Ma"], "pair": True, "contents": ["H"], "special_scores": ["COP"],
    "fq_fallback": "none",
    "evidence": [{"code": "Ma", "span": "dancing"}, {"code": "COP", "span": "dancing"}],
    "confidence": [{"code": "Ma", "value": 0.95}, {"code": "COP", "value": 0.8}],
}


class FakeMessages:
    def __init__(self, payload, stop_reason="end_turn"):
        self.payload = payload
        self.stop_reason = stop_reason
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        text = self.payload if isinstance(self.payload, str) else json.dumps(self.payload)
        return SimpleNamespace(stop_reason=self.stop_reason, content=[SimpleNamespace(type="text", text=text)])


def fake_client(payload, stop_reason="end_turn"):
    messages = FakeMessages(payload, stop_reason)
    return SimpleNamespace(beta=SimpleNamespace(messages=messages)), messages


def test_parses_structured_output():
    client, messages = fake_client(GOOD)
    codes = LLMCoder(client=client).code(REQ)
    assert codes.coder == "llm"
    assert codes.dq == "+" and codes.determinants == ["Ma"] and codes.pair
    assert codes.contents == ["H"] and codes.special_scores == ["COP"]
    assert codes.fq_fallback is None
    assert codes.evidence["Ma"] == "dancing"
    assert codes.confidence["Ma"] == pytest.approx(0.95)


def test_request_shape(monkeypatch):
    monkeypatch.delenv("LLM_MODEL", raising=False)
    client, messages = fake_client(GOOD)
    LLMCoder(client=client).code(REQ)
    call = messages.calls[0]
    assert call["model"] == DEFAULT_MODEL
    assert call["output_config"]["format"] == {"type": "json_schema", "schema": OUTPUT_SCHEMA}
    assert call["fallbacks"] == "default"
    user = call["messages"][0]["content"]
    assert "Card: III" in user and "two people dancing" in user and "D9" in user and "Human" in user


def test_model_from_env(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "claude-sonnet-5")
    client, messages = fake_client(GOOD)
    LLMCoder(client=client).code(REQ)
    assert messages.calls[0]["model"] == "claude-sonnet-5"


@pytest.mark.parametrize("bad", [
    "not json",
    {**GOOD, "determinants": ["XYZ"]},
    {**GOOD, "contents": ["Bogus"]},
    {k: v for k, v in GOOD.items() if k != "dq"},
])
def test_invalid_output_raises(bad):
    client, _ = fake_client(bad)
    with pytest.raises(Exception):
        LLMCoder(client=client).code(REQ)


def test_refusal_raises():
    client, _ = fake_client(GOOD, stop_reason="refusal")
    with pytest.raises(RuntimeError):
        LLMCoder(client=client).code(REQ)


def test_unavailable_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    coder = LLMCoder()
    assert not coder.available()
    with pytest.raises(CoderUnavailable):
        coder.code(REQ)


def test_schema_is_strict():
    assert OUTPUT_SCHEMA["additionalProperties"] is False
    assert set(OUTPUT_SCHEMA["required"]) == set(OUTPUT_SCHEMA["properties"])
