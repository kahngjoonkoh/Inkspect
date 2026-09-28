"""Laya coder: a local typed-decision model served over HTTP.

Talks to a Laya server (`laya-serve`, or `laya_server/server.py` in this
repo) at `LAYA_URL` using Laya's `POST /v1/systemone` shape:

    request:  {"state": str, "questions": {...}, "model": "typed-decisions"}
    response: {"answers": {name: {"choice": key, "confidence": p, ...} | {"noul": p, "confidence": p}}}
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from ..schema import ACHROMATIC_CARDS, CodeRequest, Codes, state_text
from .base import Coder, CoderUnavailable
from .laya_questions import (
    CONTENT_QUESTIONS,
    DQ_CHOICES,
    FQ_CHOICES,
    MOVEMENT_AP,
    MOVEMENT_FAMILIES,
    SHADED_FAMILIES,
    SPECIAL_QUESTIONS,
    VALIDITY_CHOICES,
    build_questions,
)

YES = 0.5


class LayaCoder(Coder):
    name = "laya"

    def __init__(self, url: str | None = None, transport: httpx.BaseTransport | None = None,
                 model: str | None = None, timeout: float = 30.0) -> None:
        self.url = (url if url is not None else os.environ.get("LAYA_URL", "")).rstrip("/")
        self.model = model or os.environ.get("LAYA_MODEL", "typed-decisions")
        self._transport = transport
        self._timeout = timeout
        self._api_key = os.environ.get("LAYA_API_KEY")

    def available(self) -> bool:
        return bool(self.url)

    def decide(self, state: str, questions: dict[str, Any]) -> dict[str, Any]:
        if not self.url:
            raise CoderUnavailable("LAYA_URL is not set")
        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        with httpx.Client(transport=self._transport, timeout=self._timeout) as client:
            try:
                r = client.post(f"{self.url}/v1/systemone", headers=headers,
                                json={"state": state, "questions": questions, "model": self.model})
            except httpx.TransportError as e:
                raise CoderUnavailable(f"Laya server unreachable: {e}") from e
            r.raise_for_status()
            return r.json()["answers"]

    def code(self, req: CodeRequest) -> Codes:
        answers = self.decide(state_text(req), build_questions())
        return decode(answers, req)


def _yes(answers: dict[str, Any], key: str) -> tuple[bool, float]:
    a = answers.get(key) or {}
    p = float(a.get("noul", 0.0))
    return p >= YES, (p if p >= YES else 1.0 - p)


def _choice(answers: dict[str, Any], key: str, table: dict[str, tuple[str, str]], default: str) -> tuple[str, float]:
    a = answers.get(key) or {}
    choice = a.get("choice")
    if choice not in table:
        return table[default][0], 0.0
    return table[choice][0], float(a.get("confidence", 0.0))


def decode(answers: dict[str, Any], req: CodeRequest) -> Codes:
    confidence: dict[str, float] = {}
    evidence: dict[str, str] = {}

    validity, confidence["validity"] = _choice(answers, "validity", VALIDITY_CHOICES, "genuine")
    dq, confidence["dq"] = _choice(answers, "dq", DQ_CHOICES, "ordinary")

    determinants: list[str] = []
    sup, sup_conf = _choice(answers, "movement_ap", MOVEMENT_AP, "passive")
    for base in MOVEMENT_FAMILIES:
        yes, p = _yes(answers, f"move_{base}")
        if yes:
            determinants.append(f"{base}{sup}")
            confidence[f"{base}{sup}"] = min(p, sup_conf) if sup_conf else p
    for fam, (_, table) in SHADED_FAMILIES.items():
        yes, p = _yes(answers, f"det_{fam}")
        if not yes:
            continue
        if fam == "color" and req.card in ACHROMATIC_CARDS:
            continue  # reported as CP below, never as a colour determinant
        default = next(iter(table))
        code, c = _choice(answers, f"det_{fam}_dominance", table, default)
        determinants.append(code)
        confidence[code] = min(p, c) if c else p
    yes, p = _yes(answers, "form_dimension")
    if yes:
        determinants.append("FD")
        confidence["FD"] = p
    if not determinants:
        determinants = ["F"]
        confidence["F"] = 0.5

    pair, confidence["(2)"] = _yes(answers, "pair")
    if any(d in ("Fr", "rF") for d in determinants):
        pair = False

    contents = []
    for code in CONTENT_QUESTIONS:
        yes, p = _yes(answers, f"content_{code}")
        if yes:
            contents.append(code)
            confidence[code] = p
    if req.fq_hint is not None and req.fq_hint.content in CONTENT_QUESTIONS and req.fq_hint.content not in contents:
        contents.insert(0, req.fq_hint.content)
        evidence[req.fq_hint.content] = req.fq_hint.item
    if not contents:
        contents = ["Id"]
    elif "Id" in contents and len(contents) > 1:
        contents.remove("Id")

    special = []
    for code in SPECIAL_QUESTIONS:
        yes, p = _yes(answers, f"special_{code}")
        if yes:
            special.append(code)
            confidence[code] = p
    if req.card in ACHROMATIC_CARDS and _yes(answers, "det_color")[0] and "CP" not in special:
        special.append("CP")
    elif req.card not in ACHROMATIC_CARDS and "CP" in special:
        special.remove("CP")

    fq_fallback = None
    if req.fq_hint is None:
        fq_fallback, confidence["fq"] = _choice(answers, "fq_fallback", FQ_CHOICES, "unusual")

    return Codes(dq=dq, determinants=determinants, pair=pair, contents=contents, special_scores=special,
                 fq_fallback=fq_fallback, validity=validity, evidence=evidence, confidence=confidence,
                 coder="laya")
