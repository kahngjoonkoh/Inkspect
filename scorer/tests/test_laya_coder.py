"""LayaCoder against a mocked Laya server (httpx.MockTransport, no weights)."""

from __future__ import annotations

import json

import httpx
import pytest

from scorer.coders.base import CoderUnavailable
from scorer.coders.laya import LayaCoder, decode
from scorer.coders.laya_questions import build_questions, labels_to_answers
from scorer.schema import CodeRequest, Location

REQ = CodeRequest(card=3, verbatim="two people dancing", inquiry="the red is a bow tie",
                  location=Location(code="D", number=9, label="D9"))


def yes(p=0.9):
    return {"noul": p, "confidence": p, "answer_confidence": p}


def pick(key, p=0.8):
    return {"choice": key, "confidence": p, "answer_confidence": p, "probabilities": {key: p}}


def server_answers(overrides):
    answers = {name: ({"noul": 0.05, "confidence": 0.95} if q["type"] == "noul" else pick(next(iter(q["criteria"]))))
               for name, q in build_questions().items()}
    answers.update(overrides)
    return answers


def mock_transport(answers, seen):
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"answers": answers, "usage": {"input_tokens": 50, "output_tokens": 0}})
    return httpx.MockTransport(handler)


def test_questions_are_typed_laya_decisions():
    q = build_questions()
    assert q["dq"]["type"] == "choice" and set(q["dq"]["criteria"]) == {
        "synthesized", "ordinary", "vague_synthesized", "vague"}
    assert q["pair"]["type"] == "noul"
    assert all(v["type"] in ("choice", "noul") for v in q.values())
    assert "content_H" in q and "special_MOR" in q and "move_FM" in q


def test_decodes_answers_into_codes():
    seen = []
    answers = server_answers({
        "dq": pick("synthesized"), "move_M": yes(), "movement_ap": pick("active"), "pair": yes(),
        "det_color": yes(), "det_color_dominance": pick("form_primary"),
        "content_H": yes(), "content_Cg": yes(0.7), "special_COP": yes(0.6), "fq_fallback": pick("unusual"),
    })
    coder = LayaCoder(url="http://laya:8100", transport=mock_transport(answers, seen), model="typed-decisions")
    codes = coder.code(REQ)
    assert codes.coder == "laya"
    assert codes.dq == "+"
    assert codes.determinants == ["Ma", "FC"]
    assert codes.pair is True
    assert codes.contents == ["H", "Cg"]
    assert codes.special_scores == ["COP"]
    assert codes.fq_fallback == "u"
    assert codes.confidence["H"] == pytest.approx(0.9)

    body = json.loads(seen[0].content)
    assert str(seen[0].url) == "http://laya:8100/v1/systemone"
    assert body["model"] == "typed-decisions"
    assert "Response: two people dancing" in body["state"]
    assert body["questions"] == build_questions()


def test_colour_on_achromatic_card_becomes_cp():
    answers = server_answers({"det_color": yes(), "det_color_dominance": pick("form_primary"), "content_A": yes()})
    codes = decode(answers, CodeRequest(card=5, verbatim="a pink bat"))
    assert "FC" not in codes.determinants and "CP" in codes.special_scores


def test_no_determinant_means_f_and_no_content_means_id():
    codes = decode(server_answers({}), CodeRequest(card=1, verbatim="something"))
    assert codes.determinants == ["F"]
    assert codes.contents == ["Id"]


def test_unavailable_without_url(monkeypatch):
    monkeypatch.delenv("LAYA_URL", raising=False)
    coder = LayaCoder()
    assert not coder.available()
    with pytest.raises(CoderUnavailable):
        coder.code(REQ)


def test_server_error_raises():
    transport = httpx.MockTransport(lambda r: httpx.Response(500, json={"error": "boom"}))
    with pytest.raises(httpx.HTTPStatusError):
        LayaCoder(url="http://laya:8100", transport=transport).code(REQ)


def test_labels_round_trip_through_answers():
    labels = {"dq": "+", "determinants": ["Ma", "FC", "FD"], "pair": True, "contents": ["H", "Cg"],
              "special_scores": ["COP"], "fq_fallback": "u"}
    answers = labels_to_answers(labels)
    as_server = {k: (pick(v) if isinstance(v, str) else (yes() if v else {"noul": 0.05, "confidence": 0.95}))
                 for k, v in answers.items()}
    codes = decode(as_server, CodeRequest(card=3, verbatim="x"))
    assert codes.dq == "+" and set(codes.determinants) == {"Ma", "FC", "FD"} and codes.pair
    assert codes.contents == ["H", "Cg"] and codes.special_scores == ["COP"] and codes.fq_fallback == "u"
