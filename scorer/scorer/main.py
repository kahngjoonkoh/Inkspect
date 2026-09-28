"""Scorer HTTP service (internal; called by the api)."""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI

from .coders import Coder, RuleCoder, get_coder
from .followup import next_followup
from .schema import CodeRequest, Codes, FollowupRequest, FollowupResponse

log = logging.getLogger("scorer")
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))

DEFAULT_CODER = os.environ.get("CODER", "rule")

app = FastAPI(title="Inkspect scorer", version="1.0.0")
_rule = RuleCoder()
_coders: dict[str, Coder] = {}


def coder_for(name: str) -> Coder:
    if name not in _coders:
        _coders[name] = get_coder(name)
    return _coders[name]


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "coder": DEFAULT_CODER,
        "available": {name: coder_for(name).available() for name in ("rule", "llm", "laya")},
    }


@app.post("/code", response_model=Codes)
def code(req: CodeRequest) -> Codes:
    name = req.coder or DEFAULT_CODER
    coder = coder_for(name)
    if name != "rule":
        if not coder.available():
            log.info("coder %s unavailable; using rule coder", name)
        else:
            try:
                return coder.code(req)
            except Exception:  # any backend failure falls back to the deterministic coder
                log.exception("coder %s failed; using rule coder", name)
    return _rule.code(req)


@app.post("/followup", response_model=FollowupResponse)
def followup(req: FollowupRequest) -> FollowupResponse:
    return next_followup(req)
