"""HTTP surface of the scorer service."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from scorer import main
from scorer.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def default_rule_coder(monkeypatch):
    """Independent of the deployment's CODER setting (the running stack may use laya)."""
    monkeypatch.setattr(main, "DEFAULT_CODER", "rule")
    monkeypatch.setattr(main, "_coders", {})  # coders read LAYA_URL / API keys when first built

REQUEST = {
    "card": 3, "orientation": "^", "verbatim": "two people dancing",
    "inquiry": "here and here, they are holding a pot, the red is blood",
    "followups": [{"prompt": "p", "answer": "their legs"}],
    "location": {"code": "D", "number": 9, "space": False, "label": "D9"},
    "fq_hint": None, "coder": None,
}


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok" and r.json()["coder"] == "rule"


def test_code_default_rule():
    r = client.post("/code", json=REQUEST)
    assert r.status_code == 200
    body = r.json()
    assert body["coder"] == "rule"
    assert set(body) >= {"dq", "determinants", "pair", "contents", "special_scores", "fq_fallback", "evidence",
                         "confidence", "coder"}
    assert "Ma" in body["determinants"] and body["contents"][0] == "H"


def test_unavailable_coders_fall_back_to_rule(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("LAYA_URL", raising=False)
    for name in ("llm", "laya"):
        r = client.post("/code", json={**REQUEST, "coder": name})
        assert r.status_code == 200 and r.json()["coder"] == "rule"


def test_failing_coder_falls_back(monkeypatch):
    from scorer import main

    class Broken:
        name = "llm"

        def available(self):
            return True

        def code(self, req):
            raise RuntimeError("boom")

    monkeypatch.setitem(main._coders, "llm", Broken())
    r = client.post("/code", json={**REQUEST, "coder": "llm"})
    assert r.status_code == 200 and r.json()["coder"] == "rule"


def test_validation_errors():
    assert client.post("/code", json={**REQUEST, "card": 11}).status_code == 422
    assert client.post("/code", json={**REQUEST, "coder": "gpt"}).status_code == 422


def test_followup_endpoint():
    r = client.post("/followup", json={"card": 1, "verbatim": "a pretty bat", "inquiry": "the wings", "asked": []})
    assert r.status_code == 200
    assert r.json()["keyword"] == "pretty"
    r = client.post("/followup", json={"card": 1, "verbatim": "a bat", "inquiry": "the wings on the sides here",
                                       "asked": []})
    assert r.json() == {"prompt": None, "keyword": None}
